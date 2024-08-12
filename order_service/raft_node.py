import http.server
import json
import csv
import os
import threading
import time
import random
import os
import sys
sys.path.append('../')
from catalog_service.locks import RWLock # Importing custom RWLock for managing concurrent access

# Get environment variable for catalog service host
catalog_service_host = os.getenv('CATALOG_SERVICE_HOST', 'localhost')

replicas = json.loads(os.getenv('REPLICAS', '[]'))

# Define the file path for storing orders and initialize variables
# orders_db_file = "data/orders2.csv"
orders_db_file = sys.argv[3]
# Contains orders which are executed and are present in db
committed_orders = {}

# Lock for synchronizing access to the order log
# order_log_lock = threading.Lock()
order_log_lock = RWLock() # Initialize RWLock object for thread-safe access
order_no_lock = threading.Lock()
#Function to save order log to disk
def save_order_log():
    global raft_log
    print("writing to order log")
    with open(orders_db_file, mode='w', newline='') as file:
        col_names = ['order_no', 'name', 'quantity', 'price']
        csv_writer = csv.DictWriter(file, fieldnames=col_names)

        csv_writer.writeheader()
        print(raft_log.commit_index)
        final_order_no = 0
        for entry in raft_log.entries[:raft_log.commit_index+1]:
            final_order_no+=1
            entry.order_no = final_order_no
            print("writing row:",entry.order_no)
            order_data = entry.command
            committed_orders[entry.order_no] = {"name":order_data["name"],"price":order_data["price"],"quantity":order_data["quantity"]} # Update the order database with new order information
            csv_writer.writerow({'order_no': entry.order_no, 'name': order_data['name'], 'price': order_data['price'], 'quantity': order_data['quantity']})

# Function to load order log from disk
def load_order_log():
    global committed_orders, raft_log
    if os.path.exists(orders_db_file):
        with open(orders_db_file, mode='r') as db:
            csv_reader = csv.DictReader(db)
            for entry in csv_reader:
                curr_order_no = entry['order_no']
                committed_orders[curr_order_no] = {
                    'name': entry['name'],
                    'price': float(entry['price']),
                    'quantity': int(entry['quantity'])
                }
                
                command = {'name': entry['name'], 'price': float(entry['price']), 'quantity': int(entry['quantity'])}
                log_entry = LogEntry(command, 0)  # Default term to 0 for existing entries
                log_entry.order_no = curr_order_no
                raft_log.entries.append(log_entry)
                raft_log.commit_index += 1
    else:
        print("file not found")
        pass

# Define the HTTP request handler for handling order requests
class isLeader():
    is_leader = False

class LogEntry:
    """Class to represent a single entry in the log."""
    def __init__(self, command, term):
        self.command = command
        self.term = term
        self.order_no = 0

class RaftLog:
    """Class to manage the log entries."""
    def __init__(self):
        self.entries = []
        self.commit_index = 0
    
    def handle_append_entries(self, term, leader_id, prev_log_index, prev_log_term, entries, leader_commit):
        """Handle appending new log entries."""
        print('handle_append_entries')
        print('leader term',term)
        global current_term

        # If the leader's term is less than the current term of the follower, it implies that the leader is an outdated one and we can simply ignore this handle_append_entries call
        if term < current_term:
            return False
        
        print('old current_term',current_term)
        current_term = term
        print('new current_term',current_term)
    
        # Ensuring log consistency before appending new entries
        # If the current log has more entries than leader's log then remove the extra entries
        if len(self.entries)-1 > prev_log_index :
            # Remove conflicting entries
            self.entries = self.entries[:prev_log_index+1]
            # return False

        # Append any new entries not already in the log
        for i in range(min(len(self.entries),prev_log_index+1), len(entries)):
            # for entry in entries:
            entry = entries[i]
            command = {'name': entry['name'], 'price': float(entry['price']), 'quantity': int(entry['quantity'])}
            new_entry = LogEntry(command, term)
            self.entries.append(new_entry)

        print('leader_commit=',leader_commit)
        print('self.commit_index=',self.commit_index)
        # Commit the entries which are already committed by the leader but not yet by the follower
        # Update commit index if leader's commit index is greater than node's commit index
        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, len(self.entries)-1)
            print('self.commit_index=',self.commit_index)
            save_order_log()# Apply committed log entries to the state machine

        return True

    def append_entry(self, entry):
        """Append a new entry to the log."""
        self.entries.append(entry)
        return self.replicate_log()
    
    def replicate_log(self):
        """Replicate log entries across replicas."""
        global current_term
        self_id = int(sys.argv[2])
        majority = len(replicas) // 2 + 1
        ack_count = 1  # Leader itself counts as an acknowledgment
        print(ack_count)
        for replica in replicas:
            print(replica['id'])
            if replica['id'] != self_id:
                try:
                    print(replica['port'])
                    conn = http.client.HTTPConnection(replica['host'], replica['port'])
                    data = json.dumps({
                        'term': current_term,
                        'leader_id': self_id,
                        'prev_log_index': len(self.entries) - 2,
                        'prev_log_term': self.entries[-2].term if len(self.entries) > 1 else 0,
                        'entries': [{'order_no': e.order_no, 'name': e.command['name'], 'price': e.command['price'], 'quantity': e.command['quantity']} for e in self.entries],
                        'leader_commit': self.commit_index,
                    })
                    conn.request("POST", "/append_entries", data, headers={"Content-Type": "application/json"})
                    response = conn.getresponse()
                    if response.status == 200:
                        ack_count += 1
                    print(ack_count)
                        
                except Exception as e:
                    print(f"Failed to append entries to {replica['id']}: {str(e)}")

        print(ack_count)
        # Commit entries if majority of followers acknowledge and then notify followers to commit
        if ack_count >= majority:
            self.commit_entries()
            self.notify_followers_commit()
            return True
        elif ack_count < majority:
            # Handle failure scenario by truncating log
            self.entries = self.entries[:len(self.entries)-1]
            self.notify_followers_truncate(len(self.entries)-1)
            return False

    def commit_entries(self):
        print('commit_entries')
        """Commit log entries."""
        self.commit_index = len(self.entries) - 1
        save_order_log()

    def notify_followers_commit(self):
        print('notify_followers_commit')
        """Notify followers about committed entries."""
        for replica in replicas:
            if replica['id'] != int(sys.argv[2]):
                try:
                    conn = http.client.HTTPConnection(replica['host'], replica['port'])
                    conn.request("POST", "/commit_entries", json.dumps({'commit_index': self.commit_index}), headers={"Content-Type": "application/json"})
                except Exception as e:
                    print(f"Failed to notify commit to {replica['id']}: {str(e)}")

    def notify_followers_truncate(self, truncate_index):
        """Notify followers about truncated log."""
        for replica in replicas:
            try:
                conn = http.client.HTTPConnection(replica['host'], replica['port'])
                conn.request("POST", "/truncate_log", json.dumps({'truncate_index': truncate_index}), headers={"Content-Type": "application/json"})
            except Exception as e:
                print(f"Failed to notify truncate to {replica['id']}: {str(e)}")

# Global RAFT state
raft_log = RaftLog()
current_term = 0
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
        elif path.startswith("/query"):
            contents = path.split('/')
            q_order_no = int(contents[len(contents)-1])
            print(q_order_no)

            # Check if the order no exists in the orders database
            if q_order_no in committed_orders:
                # Send a successful response with order details
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                # Read the order details under a read lock to ensure thread safety
                time.sleep(0.2)
                with order_log_lock.r_locked():
                    order_json = {"name":committed_orders[q_order_no]["name"],"number":q_order_no,"quantity":committed_orders[q_order_no]["quantity"]}
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
        global current_term
        global raft_log
        print(self.path)
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode()) # Parse JSON data from request
        if self.path == "/set_leader":
            self.is_leader.is_leader = (data['leader_id'] == self.id)
            current_term = data["current_term"]
            print("current_term=",current_term)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        elif self.path == "/append_entries":
            success = raft_log.handle_append_entries(
                data['term'],
                data['leader_id'],
                data['prev_log_index'],
                data['prev_log_term'],
                data['entries'],
                data['leader_commit']
            )
            self.send_response(200 if success else 500)
            self.end_headers()
            self.wfile.write(json.dumps({'success': success, 'term': current_term}).encode())
        elif self.path in ["/commit_entries", "/truncate_log"]:
            if self.path == "/commit_entries":
                # Update commit index and save order log
                raft_log.commit_index = min(data['commit_index'], len(raft_log.entries) - 1)  # Ensure we do not commit beyond what we have
                save_order_log()
            elif self.path == "/truncate_log":
                # Truncate log based on the given index
                raft_log.entries = raft_log.entries[:data['truncate_index']]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
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
                    data["price"]=json_result["data"]["price"]
                    command = {'name': data['name'], 'price': float(data['price']), 'quantity': int(data['quantity'])}
                    new_entry = LogEntry(command, current_term)
                    
                    if raft_log.append_entry(new_entry):
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        resp = {
                            "data": {
                                "order_number": new_entry.order_no
                            }
                        }
                        self.wfile.write(json.dumps(resp).encode())
                    else:
                        self.send_response(200)
                        resp = {
                                    "error": {
                                        "code": 404,
                                        "message": "Order not placed"
                                    }
                                }
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(resp).encode())

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
    handler_class.id = id
    httpd = http.server.ThreadingHTTPServer(server_address, handler_class)
    load_order_log() # Load order log from disk
    httpd.serve_forever()

if __name__ == '__main__':
    local_ip = socket.gethostbyname(socket.gethostname())
    print("local addr:",local_ip)
    start_order_service(int(sys.argv[1]),int(sys.argv[2]))