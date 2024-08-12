import http.server
import json
import csv
import os
from locks import RWLock # Importing custom RWLock for managing concurrent access
import time
import threading

toys_db_file = "data/toys_db.csv" # File path for storing toy database
toys_db = {}
my_obj_rwlock = RWLock() # Initialize RWLock object for thread-safe access
front_end_host = os.getenv('FRONT_END_HOST', 'localhost')

#Save the toy database to a CSV file.
def save_database():
    print("writing to db")
    with open(toys_db_file, mode='w', newline='') as file:
        col_names = ['name', 'price', 'stock']
        csv_writer = csv.DictWriter(file, fieldnames=col_names)

        csv_writer.writeheader()
        print("toys_db=",toys_db)
        for toy_name, toy_data in toys_db.items():
            print("writing row:",toy_data)
            csv_writer.writerow({'name': toy_name, 'price': toy_data['price'], 'stock': toy_data['stock']})

#Load the toy database from a CSV file.
def load_database():
    global toys_db
    print("loading toys data")
    if os.path.exists(toys_db_file):
        with open(toys_db_file, mode='r') as db:
            csv_reader = csv.DictReader(db)
            for entry in csv_reader:
                toy_name = entry['name']
                with my_obj_rwlock.w_locked():
                    toys_db[toy_name] = {
                        'name': entry['name'],
                        'price': float(entry['price']),
                        'stock': int(entry['stock'])
                    }
    else:
        print("file not found")
        #Create default toy database if the file doesn't exist
        with my_obj_rwlock.w_locked():
            toys_db =   {
                            "Tux": {"name": "Tux","price": 25.99, "stock": 100},
                            "Whale": {"name": "Whale","price": 19.99, "stock": 100},
                            "Elephant": {"name": "Elephant","price": 29.99, "stock": 100},
                            "Fox": {"name": "Fox","price": 39.99, "stock": 100},
                            "Python": {"name": "Python","price": 9.99, "stock": 100},
                            "Dolphin": {"name": "Dolphin","price": 42.99, "stock": 100},
                            "Barbie": {"name": "Barbie","price": 34.99, "stock": 100},
                            "Lego": {"name": "Lego","price": 44.99, "stock": 100},
                            "Monopoly": {"name": "Monopoly","price": 32.99, "stock": 100},
                            "Frisbee": {"name": "Frisbee","price": 6.99, "stock": 100}
                        }
            save_database()
        pass

    print("load_database toys_db=",toys_db)

# Function to invalidate item by sending a POST request to the front end
def invalidate_item(toy_name):
    print("Start of invalidate_item")
    conn = http.client.HTTPConnection(front_end_host,8080)
    conn.request("POST", f"/invalidate/{toy_name}")
    resp = conn.getresponse()
    print("Front End Server Response is:",resp.status, resp.reason)
    data = resp.read()
    print("Front End Server replied: ",data.decode())
    conn.close()

class CatalogHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle HTTP GET requests."""
        path = self.path
        print(path)
        contents = path.split('/')
        product_name = contents[len(contents)-1]
        print(product_name)

        if path.startswith("/query"):
            # Check if the product exists in the database
            if product_name in toys_db:
                # Send a successful response with product details
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                # Read the product details under a read lock to ensure thread safety
                time.sleep(0.2)
                with my_obj_rwlock.r_locked():
                    print(f"Returning data of {product_name} from catalog")
                    resp = {"data":toys_db[product_name]}
                self.wfile.write(json.dumps(resp).encode())
                
            else:
                # Send a response indicating product not found
                self.send_response(200)
                resp = {
                            "error": {
                                "code": 404,
                                "message": "product not found"
                            }
                        }
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
    
    # Method to update toy stock
    def update_toy_stock(self, toy_name, order_qty):
        time.sleep(0.2) # Simulate processing delay
        with my_obj_rwlock.w_locked():
            if toys_db[toy_name]["stock"]>=order_qty:
                print("Catalog Updating toy ",toy_name)
                print("Start time=",time.time())
                toys_db[toy_name]["stock"] = toys_db[toy_name]["stock"] - order_qty
                resp = {"data":toys_db[toy_name]}
                
                # invalidate_item(toy_name)

                # Send a successful response with updated product details
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
                save_database() # Save the updated database to file
                print("End time=",time.time())
                return True
            else:
                # Send a response indicating insufficient stock
                # time.sleep(0.2) # Simulate processing delay
                resp = {
                            "error": {
                                "code": 404,
                                "message": "not enough stock"
                            }
                        }
                self.send_response(200)

                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
                return False

    def do_POST(self):
        """Handle HTTP POST requests."""
        print("inside post of catalog")
        # Read and parse the JSON data from the request body
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode())
        print("POST data = ",data)
        toy_name = data["name"]
        order_qty = data["quantity"]
        print("toy_name=",toy_name)
        print("order_qty=",order_qty)
        path = self.path
        if path.startswith("/buy_qty"):
            # Check if the product exists in the database
            if toy_name in toys_db:
                # Update the stock if there's sufficient quantity
                if self.update_toy_stock(toy_name, order_qty):
                    invalidate_item(toy_name)
            else:
                
                self.send_response(200)
                resp = {
                            "error": {
                                "code": 404,
                                "message": "product not found"
                            }
                        }
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())

# Function to check and reset toy quantity if it's zero
def check_and_reset_toy_quantity(toys_db,toy):
    with my_obj_rwlock.w_locked():
        if toys_db[toy]["stock"]==0:
            toys_db[toy]["stock"] = 100
            return True
        else:
            return False
# Function to restock the toy database at regular intervals
def restock_db():
    while True:
        for toy, toy_data in toys_db.items():
            if check_and_reset_toy_quantity(toys_db,toy):
                invalidate_item(toy)
        save_database()
        time.sleep(10)

def start_catalog_service():
    server_address = ('', 8081)
    # httpd = http.server.HTTPServer(server_address, CatalogHTTPRequestHandler)
    httpd = http.server.ThreadingHTTPServer(server_address, CatalogHTTPRequestHandler)
    httpd.serve_forever()
    return 

if __name__ == '__main__':
    load_database()
     # Start a thread to restock the database periodically
    restocking_thread = threading.Thread(target = restock_db)
    restocking_thread.daemon = True
    restocking_thread.start()

    start_catalog_service()

