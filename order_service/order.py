import http.server
import json
import csv
import os
import threading
import time
import os
import sys
sys.path.append('../')
from catalog_service.locks import RWLock # Importing custom RWLock for managing concurrent access

# Get environment variable for catalog service host
catalog_service_host = os.getenv('CATALOG_SERVICE_HOST', 'localhost')

replicas = json.loads(os.getenv('REPLICAS', '[]'))

# Define the file path for storing orders and initialize variables
orders_db_file = "data/orders.csv"
order_no = 0
orders_db = {}

# Lock for synchronizing access to the order log
# order_log_lock = threading.Lock()
order_log_lock = RWLock() # Initialize RWLock object for thread-safe access
order_no_lock = threading.Lock()
#Function to save order log to disk
def save_order_log():
    print("writing to order log")
    with open(orders_db_file, mode='w', newline='') as file:
        print("orders_db=",orders_db)
        col_names = ['order_no', 'name', 'quantity', 'price']
        csv_writer = csv.DictWriter(file, fieldnames=col_names)

        csv_writer.writeheader()
        for o_no, order_data in orders_db.items():
            print("writing row:",o_no)
            csv_writer.writerow({'order_no': o_no, 'name': order_data['name'], 'price': order_data['price'], 'quantity': order_data['quantity']})

# Function to load order log from disk
def load_order_log():
    global orders_db
    if os.path.exists(orders_db_file):
        with open(orders_db_file, mode='r') as db:
            csv_reader = csv.DictReader(db)
            for entry in csv_reader:
                curr_order_no = entry['order_no']
                global order_no
                if int(curr_order_no) > order_no:
                    order_no = int(curr_order_no)
                orders_db[curr_order_no] = {
                    'name': entry['name'],
                    'price': float(entry['price']),
                    'quantity': int(entry['quantity'])
                }
    else:
        print("file not found")
        pass

# Define the HTTP request handler for handling order requests
class isLeader():
    is_leader = False
class OrderHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    id = None
    is_leader = isLeader()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle HTTP GET requests."""
        path = self.path
        print(path)
        if path == "/health_check":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        elif path == "/latest_order_no":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'latest_order_no': order_no}
            self.wfile.write(json.dumps(response).encode())
        elif path.startswith("/orders_since"):
            try:
                order_no_str = path.split('/')[-1] 
                starting_order_no = int(order_no_str)
                orders_to_send = {key: val for key, val in orders_db.items() if int(key) > starting_order_no}
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(orders_to_send).encode())
            except ValueError:
                self.send_error(400, "Invalid order number")
        elif path.startswith("/query"):
            contents = path.split('/')
            q_order_no = int(contents[len(contents)-1])
            print(q_order_no)
            print(orders_db)

            # Check if the order no exists in the orders database
            if q_order_no in orders_db:
                # Send a successful response with order details
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                # Read the order details under a read lock to ensure thread safety
                time.sleep(0.2)
                with order_log_lock.r_locked():
                    order_json = {"name":orders_db[q_order_no]["name"],"number":q_order_no,"quantity":orders_db[q_order_no]["quantity"]}
                    resp = {"data":order_json}
                self.wfile.write(json.dumps(resp).encode())
                
            else:
                # Send a response indicating order not found
                self.send_response(200)
                resp = {
                            "error": {
                                "code": 404,
                                "message": "Order Number Not Found"
                            }
                        }
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
    
    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode()) # Parse JSON data from request
        if self.path == "/set_leader": # setting the leader node
            self.is_leader.is_leader = (data['leader_id'] == self.id)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        elif self.path == "/replicate_order":
            self.update_db(data)
        elif self.path == "/order":
            # Handle HTTP POST requests for placing orders
            print("POST data = ",data)
            toy_name = data["name"]
            toy_q = data["quantity"]
            
            # Send a request to the catalog service to buy the specified quantity of the item
            headers = {"Content-type":"application/json"}
            conn = http.client.HTTPConnection(catalog_service_host,8081)
            conn.request("POST", "/buy_qty", json.dumps(data), headers)
            resp = conn.getresponse()
            print("Response is:",resp.status, resp.reason)
            # Print order details
            print("toy_name=",toy_name)
            print("toy_q=",toy_q)
            result = resp.read()
            # Get the result from the catalog service response
            json_result = json.loads(result.decode())
            if "error" in json_result: # Check if there is an error in the response
                # If there's an error, send the error response to the client
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(result)
            else :
                with order_no_lock:
                    global order_no
                    order_no+=1
                    data["order_no"]=order_no
                    data["price"]=json_result["data"]["price"]
                
                print("calling propagate_to_followers")
                #send the data to all the replicas
                self.propagate_to_followers(data)
                # If the order is successful, update the order log with the new order
                self.update_db(data)
            
    def update_db(self,order_info):
        time.sleep(0.2)
        with order_log_lock.w_locked(): # Acquire a write lock to access the order log
            print("Order service Updating order log ",order_info["name"])
            print("Start time=",time.time())
            orders_db[order_info["order_no"]] = {"name":order_info["name"],"price":order_info["price"],"quantity":order_info["quantity"]} # Update the order database with new order information
            save_order_log()
            resp = {
                    "data": {
                        "order_number": order_info["order_no"]
                    }
                }
            global order_no
            if int(order_info["order_no"]) > order_no: #Check if the new order number is greater than the global order number
                order_no = int(order_info["order_no"]) # Update the global order number if necessary
            print("End time=",time.time())
        # Send the order number response to the client
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(resp).encode())

    def update_new_order(self, new_order={}):
        """Update local orders with the received new_order details."""
        # print("new_order=",new_order)
        global order_no
        with order_log_lock.w_locked():
            orders_db[new_order[0]] = new_order[1] # Add the new order to the local database
            order_no = max(order_no, int(new_order[0])) # Update the global order number if necessary
            save_order_log() # Save the updated order log to disk
    
    def synchronize_with_replicas(self):
        """Synchronize state with other replicas."""
        print("synchronize_with_replicas:",replicas)
        for replica in replicas:
            if replica['id'] != os.getenv('REPLICA_ID'):
                try:
                    print("trying to connect to:",replica)
                    conn = http.client.HTTPConnection(replica['host'], replica['port'])
                    conn.request("GET", "/latest_order_no")
                    response = conn.getresponse()
                    print(response)
                    latest_order_no = json.loads(response.read().decode())['latest_order_no']

                    if latest_order_no > order_no:  # Check if the replica has new orders
                        conn.request("GET", f"/orders_since/{order_no}")  # Request new orders since the last synchronized order number
                        new_orders = json.loads(conn.getresponse().read().decode())
                        print(new_orders)
                        # for key,val in new_orders.items():
                        for new_order in new_orders.items():
                            # print(order_num)
                            print(new_order)
                            self.update_new_order(self,new_order) # Update the local database with the new orders

                except Exception as e:
                    print(f"Failed to synchronize with replica {replica['id']}: {str(e)}")
    
    def propagate_to_followers(self, data):
        print("propagate_to_followers")
        print("replicas:",replicas)
        for replica in replicas:
            try:
                print("Trying to connect to:",replica["host"], replica["port"])
                conn = http.client.HTTPConnection(replica['host'], replica['port'])
                conn.request("POST", "/replicate_order", json.dumps(data), headers={"Content-Type": "application/json"})  # Send new order data to the replica
                response = conn.getresponse()
                print(f"Propagated to {replica['host']}:{replica['port']}, status: {response.status}")
            except Exception as e:
                print(f"Failed to propagate to {replica['host']}:{replica['port']}, error: {str(e)}")

# Function to start the order service
import socket

def get_local_ip():
    # Create a socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to a known external server
        s.connect(('8.8.8.8', 80))
        # Get the local IP address
        local_ip = s.getsockname()[0]
    finally:
        s.close()
    return local_ip

def start_order_service(port_no=8082,id=0):
    
    local_ip = get_local_ip()
    print("Local IP Address:", local_ip)

    server_address = ('', port_no)
    # httpd = http.server.HTTPServer(server_address, OrderHTTPRequestHandler)
    handler_class = OrderHTTPRequestHandler
    handler_class.id = id # Set the ID of the handler class
    httpd = http.server.ThreadingHTTPServer(server_address, handler_class)
    load_order_log() # Load order log from disk
    handler_class.synchronize_with_replicas(handler_class) # Synchronize state with replicas
    httpd.serve_forever()

if __name__ == '__main__':
    local_ip = socket.gethostbyname(socket.gethostname())
    print("local addr:",local_ip)
    start_order_service(int(sys.argv[1]),int(sys.argv[2]))