import http.server
import http.client
import json
import time
import threading
import socket
import collections
import os
# Get environment variables for catalog and order service hosts
catalog_service_host = os.getenv('CATALOG_SERVICE_HOST', 'localhost')
order_service_host = os.getenv('ORDER_SERVICE_HOST', 'localhost')

current_term = 0
class LeaderStatus():
    leader_order_service_node = None # Initialize leader_order_service_node attribute to store the leader order service node

class CustomHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    toys_db_cache = collections.OrderedDict() # Cache for storing toy data
    toys_db_lock = threading.Lock() # Lock for thread-safe access to toys database
    toys_db_cache_size = 5 #Size limit for the toy cache
    caching_enabled = True
    # leader_order_service_node = {"host":"localhost","port":8082}
    leader = LeaderStatus()
    # leader_order_service_node = None
    leader_order_service_lock = threading.Lock()
    order_replicas = json.loads(os.getenv('ORDER_REPLICAS','[]'))

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     print("__init__")
    
     # Method to select leader among order replicas and notify other replicas
    def select_leader_and_notify(self, order_replicas):
        print("select_leader_and_notify")
        order_replicas.sort(key=lambda x: x["id"], reverse=True)
        for replica in order_replicas:
            if self.ping_node(replica):
                with self.leader_order_service_lock:  # Acquiring lock before updating leader information
                    self.leader.leader_order_service_node = replica
                print(f"Leader selected: {replica['id']} at {replica['host']}:{replica['port']}")
                self.notify_all_replicas(replica,order_replicas)
                break
    # Method to ping a node and check if it's online
    def ping_node(self, replica):
        print("ping_node")
        try:
            conn = http.client.HTTPConnection(replica["host"], replica["port"])
            conn.request("GET", "/health_check") # Sending GET request for health check
            resp = conn.getresponse()
            return resp.status == 200
        except:
            return False

    # Method to notify all replicas about the leader
    def notify_all_replicas(self, leader,order_replicas):
        print("notify_all_replicas")
        global current_term
        current_term = current_term+1
        for node in order_replicas:
            try:
                print("Trying to connect to:",node["host"], node["port"])
                conn = http.client.HTTPConnection(node["host"], node["port"])
                conn.request("POST", "/set_leader", json.dumps({"leader_id": leader['id'],"current_term":current_term}), headers={"Content-Type": "application/json"}) # Sending POST request to notify about leader
                resp = conn.getresponse()
                print(resp)
                print(f"Notified {node['host']}:{node['port']} about the leader {leader['id']}, status: {resp.status}")
            except Exception as e:
                print(f"Failed to notify {node['host']}:{node['port']}, error: {str(e)}")

    # Method to remove a toy from the cache
    def remove_toy_from_cache(self,toy_name):
        with self.toys_db_lock:
            print("self.toys_db_cache=",self.toys_db_cache)
            if toy_name in self.toys_db_cache:
                del self.toys_db_cache[toy_name]
                print(f"Removing {toy_name} from cache as its invalidated")
    
     # Method to check if leader is online and select a new leader if required
    def check_if_leader_is_online(self):
        print("leader.leader_order_service_node=",self.leader.leader_order_service_node)
        if not self.leader.leader_order_service_node or not self.ping_node(self.leader.leader_order_service_node):
            self.select_leader_and_notify(self.order_replicas)
    
    def do_GET(self):
        print("do_GET")
        # print("self.toys_db_cache=",self.toys_db_cache)
        # print("self.leader.leader_order_service_node=",self.leader.leader_order_service_node)

        self.check_if_leader_is_online() # Checking leader status and selecting new leader if required

        if self.leader.leader_order_service_node:
            try:
                # Handle HTTP GET requests
                path = self.path
                print(path)
                contents = path.split('/')
                # request_type = contents[len(contents)-2]

                if path.startswith("/products"): # Handling requests related to product catalog

                    product_name = contents[len(contents)-1]
                    
                    thread_id  = threading.get_ident()
                    print("Front end checking for ",product_name)
                    print("thread_id=",thread_id)
                    # time.sleep(5)
                    #  get product details from cache if product is in cache
                    with self.toys_db_lock:
                        if product_name in self.toys_db_cache:
                            print("Item found in cache")
                            data = self.toys_db_cache[product_name]
                        else:
                            # Send a GET request to the catalog service
                            conn = http.client.HTTPConnection(catalog_service_host,8081)
                            conn.request("GET", f"/query/{product_name}")
                            resp = conn.getresponse()
                            print("Catalog Response is:",resp.status, resp.reason)
                            data = resp.read()
                            if self.caching_enabled: # Caching product details if caching is enabled
                                if len(self.toys_db_cache) == self.toys_db_cache_size:
                                    item_key,item_value = self.toys_db_cache.popitem(last=False)    
                                    print(f"Cache full. Removing {item_key},{item_value} from cache as its least used.")
                                self.toys_db_cache[product_name] = data
                            print("Catalog Service replied: ",data.decode())
                elif path.startswith("/orders"):
                    order_no = contents[len(contents)-1]
                    
                    thread_id  = threading.get_ident()
                    print("Front end checking for ",order_no)
                    print("thread_id=",thread_id)
                    # time.sleep(5)

                    # Send a GET request to the order service
                    with self.leader_order_service_lock:
                        leader_details = self.leader.leader_order_service_node
                    conn = http.client.HTTPConnection(leader_details["host"],leader_details["port"])
                    conn.request("GET", f"/query/{order_no}")
                    resp = conn.getresponse()
                    print("Order service Response is:",resp.status, resp.reason)
                    data = resp.read()
                    print("Catalog Service replied: ",data.decode())

                self.send_response(200) # Send the response back to the client
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                print(f"Failed to forward request to leader: {str(e)}")
                self.send_error(500, "Internal Server Error")
        else:
            self.send_error(503, "Service Unavailable")
    
    def do_POST(self):
        print("do_POST")
        # Handle HTTP POST requests
        # print("POST data = ",data)
        # toy_name = data["name"]
        # toy_q = data["quantity"]
        # print("toy_name=",toy_name)
        # print("toy_q=",toy_q)
        # Checking leader status and selecting new leader if required
        self.check_if_leader_is_online()

        if self.leader.leader_order_service_node: # Checking if leader is available
            try:
                path = self.path
                print(path)
                contents = path.split('/')
                # request_type = contents[len(contents)-2]

                if path.startswith("/orders"):
                    data = json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode())
                    # Send a POST request to the order service
                    # conn = http.client.HTTPConnection(order_service_host,8082)
                    # Sending request to order service to place an order
                    with self.leader_order_service_lock:
                        leader_details = self.leader.leader_order_service_node
                    print("Trying to connect to:",leader_details["host"], leader_details["port"])
                    conn = http.client.HTTPConnection(leader_details["host"],leader_details["port"])
                    headers = {"Content-type":"application/json"}
                    str_data = json.dumps(data)
                    conn.request("POST", "/order", str_data, headers)

                    resp = conn.getresponse()  # Get and print the response from the order service
                    print("Response is:",resp.status, resp.reason)

                    self.send_response(200) 
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(resp.read())
                elif path.startswith("/invalidate"): # Handling requests related to cache invalidation
                    product_name = contents[len(contents)-1]
                    print(f"Removing {product_name} from front end cache")
                    self.remove_toy_from_cache(product_name) #Removing specified product from the cache
                    self.send_response(200) 
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    resp_json = {"data":"Removed item from front end cache"}
                    self.wfile.write(json.dumps(resp_json).encode())
            except Exception as e:
                print(f"Failed to forward request to leader: {str(e)}")
                self.send_error(500, "Internal Server Error")
        else:
            self.send_error(503, "Service Unavailable")

def start_server():
    # Start the HTTP server
    server_address = ('', 8080)
    # httpd = http.server.HTTPServer(server_address, CustomHTTPRequestHandler)
    httpd = http.server.ThreadingHTTPServer(server_address, CustomHTTPRequestHandler)
    local_ip = socket.gethostbyname(socket.gethostname())
    print("local addr:",local_ip)
    httpd.serve_forever()


if __name__ == '__main__':
    start_server()