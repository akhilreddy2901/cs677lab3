## Steps to run:

**Part 1:**

- Ensure that the 'caching_enabled' variable is set to 'True' in front_end.py
- Navigate inside src folder using "cd src"
- Run the front end server using the command "ORDER_REPLICAS='[{"host":"localhost", "port":8082,"id":"1"}]'  python3 frontend_service/front_end.py"
- Run the order service using the command 'python3 order_service/order.py 8082 1'
- Run the catalog service using the command 'python3 catalog_service/catalog.py'
- Note the frontend IP address after running the frontend server
- Use the frontend IP addresss obtained from the frontend server and update the 'front_end_ip' variable in the client file(can use 'localhost' if client is running on same local machine as frontend server)
- Set the variables 'no_of_requests_per_client', 'order_probability' and 'no_of_client_processes' as required
- Run the client using 'python3 client/client.py'
- Ensure that both the frontend server and client are using the same port for communication
- You can check that few queries are processed at the front end server itself by looking at the log statements. You can also ensure cache invalidation and cache replacement by looking at the log statements.

**Part 2 & 3:**
We ran the front end service, catalog service, leader order service and client on one machine and the remaining 2 order replicas on 2 different machines. replica1ip,replica2ip, replica3ip correspond to the ip address of machines on which replica 1,2 & 3 are running respectively.

**Machine 1:**
- Navigate inside src folder using "cd src"
- Run the replica1 using the command "REPLICAS='[{"host":"replica2ip", "port":8082,"id":"2"},{"host":"replica3ip", "port":8082,"id":"3"}]' python3 order_service/order.py 8082 1"

**Machine 2:**
- Navigate inside src folder using "cd src"
- Run the replica2 using the command "REPLICAS='[{"host":"replica1ip", "port":8082,"id":"1"},{"host":"replica3ip", "port":8082,"id":"3"}]' python3 order_service/order.py 8082 2"

**Machine 3:**
- Navigate inside src folder using "cd src"
- Run the front end server using the command "ORDER_REPLICAS='[{"host":"replica1ip", "port":8082,"id":"1"},{"host":"replica2ip", "port":8082,"id":"2"},{"host":"replica3ip", "port":8082,"id":"3"}]'  python3 frontend_service/front_end.py"
- Run the replica3 (Leader order service) using the command "REPLICAS='[{"host":"replica1ip", "port":8082,"id":"1"},{"host":"replica2ip", "port":8082,"id":"2"}]' python3 order_service/order.py 8082 3"
- Run the catalog service using the command 'python3 catalog_service/catalog.py'
- Note the frontend IP address after running the frontend server
- Use the frontend IP addresss obtained from the frontend server and update the 'front_end_ip' variable in the client file(can use 'localhost' if client is running on same local machine as frontend server)
- Set the variables 'no_of_requests_per_client', 'order_probability' and 'no_of_client_processes' as required
- Run the client using 'python3 client/client.py'
- Ensure that both the frontend server and client are using the same port for communication

- You can verify the replication part by ensuring that all the order services have the same database file.
- You can also kill one of the order services randomly and check that the client queries are not affected. You can later restart the crached replica and again ensure that the database is synchronized with others.

**Part 4:**

## How to run tests:
- Navigate to test directory inside src using 'cd src/test'
- Run all the tests using the command 'python3 all_tests.py'

## Testing and Evaluation with Deployment on AWS:
- Start Lab on AWS and Click the "AWS Details" button. On the right side panel there will be a "Show" button following AWS CLI, click on that. The code that appeared in the textbox below contains the credentials that the AWS CLI uses to interact with AWS. Copy the code and save it to $HOME/.aws/credentials on Linux/macOS.
- Run 'aws configure' to configure the AWS settings
- Creating the  EC2 instances. We used 3 m5a.large instances to deploy the application. For image id we used the Ubuntu 18.04 server image, AMI (Amazon Machine Images) ID is ami-0d73480446600f555. 
- Create 3 instances using "aws ec2 run-instances --image-id ami-0d73480446600f555 --instance-type m5a.large --key-name vockey > instance.json"
- To check the status of the instance: aws ec2 describe-instances --instance-id <your-instance-id>
- Access EC2 via SSH: set the right permission for the PEM key using "chmod 400 labsuser.pem"
- Authorize port 8080(or whatever port the front end will be using to communicate with the client) (used by ssh) in the default security group (allow ssh access from anywhere for frontend) using "aws ec2 authorize-security-group-ingress --group-name default --protocol tcp --port 8080 --cidr 0.0.0.0/0"
- ssh -i labsuser.pem ubuntu@<your-instance's-public-DNS-name>
- We installed a specific version of python (python3.7) to run our code on this Ubuntu 18.04 server image.
- Steps to install python3.7: "sudo apt update"->"sudo apt install software-properties-common"->"sudo add-apt-repository ppa:deadsnakes/ppa"->"sudo apt update"->"sudo apt install python3.7"

We ran the front end service, catalog service, leader order service on one instance and the remaining 2 order replicas on 2 different instances and client on local machine. replica1ip,replica2ip, replica3ip correspond to the ip address of instances on which replica 1,2 & 3 are running respectively

**Instance 1:**
- Navigate inside src folder using "cd src"
- Run the replica1 using the command "REPLICAS='[{"host":"replica2ip", "port":8082,"id":"2"},{"host":"replica3ip", "port":8082,"id":"3"}]' python3.7 order_service/order.py 8082 1"

**Instance 2:**
- Navigate inside src folder using "cd src"
- Run the replica2 using the command "REPLICAS='[{"host":"replica1ip", "port":8082,"id":"1"},{"host":"replica3ip", "port":8082,"id":"3"}]' python3.7 order_service/order.py 8082 2"

**Instance 3:**
- Navigate inside src folder using "cd src"
- Run the front end server using the command "ORDER_REPLICAS='[{"host":"replica1ip", "port":8082,"id":"1"},{"host":"replica2ip", "port":8082,"id":"2"},{"host":"replica3ip", "port":8082,"id":"3"}]'  python3.7 frontend_service/front_end.py"
- Run the replica3 (Leader order service) using the command "REPLICAS='[{"host":"replica1ip", "port":8082,"id":"1"},{"host":"replica2ip", "port":8082,"id":"2"}]' python3.7 order_service/order.py 8082 3"
- Run the catalog service using the command 'python3.7 catalog_service/catalog.py'

**Local machine for client:**
- Navigate inside src folder using "cd src"
- Note the public IP address of the instance on which frontend_server is deployed and update the 'front_end_ip' variable in the client file
- Run the client using 'python3 client/client.py'
- Ensure that both the frontend server and client are using the same port for communication
- Change the variables 'order_probability' and 'no_of_client_processes' in the client.py file as needed and record the observations with and without caching by changing the 'caching_enabled' variable in front_end.py

**Part 5:**
- Note: All code related to raft is implemented in raft_node.py(equivalent to order.py) which is inside src/order_service and the orders are stored inside src/order_service/raft_data folder 
- We ran all the services on the local machine. In this part we are running all the replicas on local machine and instead using different database files for each replica which are taken using command line arguments
- Navigate inside src folder using "cd src"
- Run the replica1 using the command "REPLICAS='[{"host":"localhost", "port":8082,"id":"3"},{"host":"localhost", "port":8083,"id":"2"}]' python3 order_service/raft_node.py 8084 1 order_service/raft_data/orders1.csv"
- Run the replica2 using the command "REPLICAS='[{"host":"localhost", "port":8082,"id":"3"},{"host":"localhost", "port":8084,"id":"1"}]' python3 order_service/raft_node.py 8083 2 order_service/raft_data/orders2.csv"
- Run the replica3 (Leader order service) using the command "REPLICAS='[{"host":"localhost", "port":8084,"id":"1"},{"host":"localhost", "port":8083,"id":"2"}]' python3 order_service/raft_node.py 8082 3 order_service/raft_data/orders3.csv"
- Run the front end server using the command "ORDER_REPLICAS='[{"host":"localhost", "port":8084,"id":"1"},{"host":"localhost", "port":8083,"id":"2"},{"host":"localhost", "port":8082,"id":"3"}]'  python3 front_end.py"
- Run the catalog service using the command 'python3 catalog_service/catalog.py'
- Note the frontend IP address after running the frontend server
- Use the frontend IP addresss obtained from the frontend server and update the 'front_end_ip' variable in the client file(can use 'localhost' if client is running on same local machine as frontend server)
- Set the variables 'no_of_requests_per_client', 'order_probability' and 'no_of_client_processes' as required
- Run the client using 'python3 client/client.py'
- Ensure that both the frontend server and client are using the same port for communication

- You can verify the replication part by ensuring that all the order services have the same database file.
- You can also kill one of the order services randomly and check that the client queries are not affected. You can later restart the crached replica and again ensure that the database is synchronized with others.
- You can kill 2 order services and see that order doesn't get placed and client gets notified accordingly.

## How to run tests:
- Navigate to test directory inside src using 'cd src/test'
- Run all the tests using the command 'python3 all_tests.py'

## Work distribution:
- Both of us collaborated closely throughout the lab for all the parts. We implented all the parts of the lab together and have made equal contributions. Our joint efforts were instrumental in successfully completing all aspects of the lab.
- Together, we worked collaboratively to ensure the success of the lab, leveraging our complementary skills and expertise to deliver a comprehensive solution.