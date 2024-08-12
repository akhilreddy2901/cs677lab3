### Introduction

The Gauls have embraced the digital era, turning to online commerce for their daily needs, with a special inclination towards buying toys. This transition necessitates a high-performance, resilient, and scalable online store capable of handling the dynamic and growing demands of modern e-commerce. To achieve this, the Gauls need a system designed with state-of-the-art distributed systems principles, including caching, replication, fault tolerance and implementing the RAFT consensus protocol to manage these processes effectively, which this lab seeks to implement and explore.

### Objectives

The objectives of this lab are designed to align with practical and theoretical aspects of distributed systems, including:
- Understanding and implementing caching mechanisms to improve query response times and reduce backend load.
- Developing a replication model that ensures data durability and high availability.
- Establishing fault tolerance in distributed applications to maintain service continuity in the face of node failures.
- Gaining hands-on experience with cloud deployment to understand the nuances of real-world application deployment.
- Explore the RAFT consensus protocol that uses state machine replication to manage replica synchronization and consistency.

### Solutions Overview/Architecture

**Architecture Description:**
The toy store application is divided into three distinct microservices:
1. **Front-End Service:** Serves as the interface to the customers, handling requests for product information and order processing. 
2. **Catalog Service:** Manages the inventory of toys, including details like name, price, and stock levels.
3. **Order Service:** Processes and stores orders, ensuring that transactions are logged and state is consistent across replicas.
4. **Client Overview**: The client component of the Microservices-Based Toy Store plays a critical role in interacting with the Front-End service, sending queries for toy information and making purchase requests. The client is designed to simulate real-world user interactions with the store, capable of conducting a sequence of actions in a session, reflecting typical browsing and shopping activities.

**Client Implementation Details**

- **Random Toy Queries**: Clients start sessions by randomly selecting toys and querying their details from the front-end service, which tests both the caching mechanism and the database retrieval processes.
- **Order Probability (`p`)**: The likelihood of placing an order after a query is controlled by the adjustable probability `p`, allowing simulations of various user purchase behaviors from low to high demand scenarios.
- **Operational Workflow**: During each session, the client conducts multiple iterations where it queries toys, potentially places orders based on `p`, tracks successful orders, and verifies each order at session end to ensure data integrity and consistency.
- **Response Times and Success Rates**: The client measures latencies for all operations and tracks the success rates of requests to assess system responsiveness and reliability.
- **Data Integrity Checks**: At the end of sessions, the client verifies the integrity and consistency of the stored data by comparing server responses against local records, ensuring the effectiveness of the system’s replication and fault tolerance mechanisms.

**Caching:**
- The front-end service uses an LRU cache to store frequently requested toy information, which reduces the number of queries to the catalog service and speeds up response times.
- Upon receiving a toy query request, it first checks the in-memory cache to see whether it can be served from the cache. If not, the request will then be forwarded to the catalog service, and the result returned by the catalog service will be stored in the cache
- Cache invalidation is triggered by the catalog service whenever a toy is purchased or restocked, ensuring the front-end always serves up-to-date information.

**Replication:**
- The order service is replicated across three nodes (on three different machines), each with a unique id number and its own database file, with one acting as the leader and the others as followers. The port number and unique id of the replica are taken as inputs from user through command line arguments.
- The front-end service will always try to pick the node with the highest id number which is responsive as the leader. It will notify all the replicas that a leader has been selected with the id number. The front-end always interacts with the leader for writing operations, which then replicates the information to the followers. We are using environment variables to pass the ip addresses of order replicas to the front end service which will be used during leader selection.
- This design ensures that even if the leader fails, one of the followers can take over without loss of data.

**Fault Tolerance:**
- The system is designed to detect failures, particularly focusing on the leader node within the order service. If the leader fails, the next node with the highest ID that is responsive is elected as the new leader.
- Nodes that recover from failures synchronize with the current leader to update their state and resume normal operations.We are using environment variables to pass the ip addresses of the other order replicas which will be used during database synchronization. 

**Replication and Consensus with RAFT**
The order service is also implemented with RAFT for consensus to ensure all replicas stay consistent despite potential network failures or node crashes. 
For part 5, the order service is replicated across three nodes on the same machine, each with a unique id number and its own database file (taken as input from user as an argument), with one acting as the leader and the others as followers. 
This setup involves:
- **Leader Election**: The leader election algorithm from previous parts is reused
- **Log Replication**: Each order is logged in a sequence, which is replicated across the nodes to ensure consistency.
- **Consensus**: The leader replica executes the order and updates the database(commits the order entry) only if a majority of the followers successfully replicate the leader's log and acknowledge the leader. In this case, the leader then instructs the followers to update their own databases with their respective logs. If a majority of followers do not replicate the leader's log, then the leader doesn't execute the buy order and notifies the client that the order has failed. The leader removes the uncommitted entries from its log and instructs the followers to do the same.
- **Fault Tolerance**: On leader failure, a new leader is elected, and the system reconfigures to continue processing without data loss.
- **Log Repair**: Upon detecting inconsistencies in the log of a follower, the log will be repaired and synchronized with the leader's log.

**Communication Protocol:**
- The system leverages HTTP-based REST APIs for communication between the front-end and backend services. This choice promotes interoperability, simplicity, and the efficient use of resources.
- The Front-End Service also communicates with clients over HTTP, offering RESTful endpoints for product queries and order placements.
- JSON is used for data serialization, offering lightweight data interchange between clients and services.

**Concurrency Management:**
- Threads are used to manage concurrent client requests in all services, ensuring efficient resource use and scalability. We use http.server.ThreadingHTTPServer which listens for incoming requests over HTTP and assigns them to a new thread for each client and this connection will be kept alive untill the client closes the connection (one thread per each client session)
- Synchronization mechanisms (e.g., locks and read-write locks) are employed to ensure data consistency during concurrent read and write operations.

**Note:** 
- We incorporated a simulated processing time of 200 ms while reading and writing to databases(both toys_db.csv and orders.csv). This choice aimed to emulate the realistic processing time typically encountered when handling read and write requests on an actual database. Moreover, without the inclusion of the sleep time, the differences in network speed exert a more pronounced influence on the observed latencies from the client side. This occurs because the actual processing time of the query and buy functions on the server side is shorter in comparison to the time taken to transmit and receive requests over the network. In essence, the absence of a simulated processing time accentuates the impact of network latency on overall response times.

### APIs

**Detailed API Descriptions:**
- **Front-End Service:**
  - `GET /products/<product_name>`: Fetches and returns the details of the specified product, utilizing the cache when possible.
  - `POST /orders`: Accepts order details (product and quantity) and processes the transaction through the order service.
  - `POST /invalidate`: Used to invalidate an item in cache whenever it is purchased or restocked, ensuring the front-end always serves up-to-date information.
  - `GET /orders/<order_number>`: Retrieves and returns the details of a specific order, verifying its existence and accuracy.

- **Catalog Service:**
  - `GET /query/<product_name>`: Provides detailed information on a specific product, used internally by the front-end service.
  - `POST /buy_qty`: Updates inventory levels after a purchase, and triggers cache invalidation.

- **Order Service:**
  - `GET /health_check`: Used by the front-end to check the responsiveness of order service nodes.
  - `GET /latest_order_no`: Used by the order replicas to fetch the latest order number from the leader replica to see if their own database is updated
  - `GET /orders_since`: Used by the order replicas to fetch the orders from a given order number from the leader replica to update their database and synchronize it with the leader
  - `GET /query/<product_name>`: Provides detailed information on a specific product, used internally by the front-end service.
  - `POST /set_leader`: Used internally by the front end service to set the order replica with highest ID as the leader
  - `POST /replicate_order`: Ensures all follower nodes have consistent and up-to-date order information.
  - `POST /order`: Used to make an order for a product and generates order number.

- **Order Service Using RAFT:**
  - `GET /query/<product_name>`: Provides detailed information on a specific product, used internally by the front-end service.
  - `POST /order`: Used to make an order for a product and generates order number.
  - `POST /set_leader`: Used internally by the front end service to set the order replica with highest ID as the leader
  - `POST /append_entries`: Used by the leader to send its log entries to the followers so that the log can be replicated by the followers
  - `POST /commit_entries`: Used by the leader to communicate to the followers to commit their log to their database
  - `POST /truncate_log`: Used by the leader to communicate to the followers to flush their uncommitted entries from their log

### Testing

**Testing Strategy:**
- **Unit Tests:** Verify the functionality of individual components within each service, such as cache operations, database updates, and API response correctness.
- **Integration Tests:** Simulate scenarios where services interact to ensure the system operates cohesively, particularly testing the interactions involving caching and replication. RAFT functionalities such as leader election, log replication, and log repair are also tested.
- **Performance Tests:** Measure the response times and system throughput under different loads, especially comparing performance metrics with and without caching enabled.
- **Cache Testing:** Added logs to check if a query request is being processed using the front end cache and manually verified it by querying the same item consecutively. This ensures that the item will be added to the cache after the first query if it was not already present. Also added logs to check if an item is being invalidated and manually verified this when a buy request is processed or an item is restocked.
- **Replication Testing:** Manually checked the database of all the replicas to ensure that they are the same after a sequence of client requests.
- **Fault Tolerance Testing:** Killed the leader node and verified that the client requests are properly redirected to other replicas without any failure. Also restarted the node after some time and ensured that the synchronization takes place and the database gets updated with the leader.
- We used the ‘time’ library in python to systematically measure the latency between the moment a client initiates a query and the time it receives a response from the server. As each client is programmed to execute 10 queries, we compute the average latency across these 10 queries for each individual client. This process is replicated across all five clients to gather comprehensive latency data.

### Deployment

The application is deployed on AWS using 3 m5a.xlarge instances based in the us-east-1 region, leveraging AWS services and management tools for monitoring and maintaining the deployment. One instance was used to deploy the catalog service, the front end service and the leader order service while the other instances were used to deploy the replicas of the order service. Exact implementation details are mentioned in README.md file.

### Known Issues/Alternatives

**Issues and Alternatives:**
- **Cache Coherence Delays:** Delays in cache invalidation could lead to temporary inconsistencies. An alternative could be the adoption of a more aggressive invalidation strategy or the use of write-through caches.
- **Database Integration:** Migrating from file-based persistence to a database could improve performance and scalability.
- **Network Latency:** It is susceptible to variations in network latency, which can affect response times observed by clients. In our implementation, we added a 0.2s delay using time.sleep while accessing databases to simulate processing time and make it more practical. This added offset reduces the impact of variations in network latency too. Implementing caching mechanisms or using content delivery networks (CDNs) could help alleviate this issue. Optimization techniques, such as caching, could be employed to mitigate the impact of network latency. 
- **RAFT Complexity**: RAFT increases the complexity of the system, which could introduce new bugs or performance issues.
- **Data Loss Risk**: While RAFT significantly reduces the risk, under extreme conditions (e.g., simultaneous failure of a majority of nodes), data loss can still occur.

**Error Handling**

- **Leader Unavailability and Failure Detection**: The system continuously monitors the health of each node involved in the replication process.The system pre-defines the next node (based on a priority list) that takes over if the current leader fails. This ensures continuity in processing requests without significant delays.
- **Data Consistency**: After a replication failure or when discrepancies are detected, the system initiates a consistency check. If inconsistencies are found, the system may revert to the last known good state and resynchronize the data. Moreover, Synchronization mechanisms such as locks are used to prevent conflicts that may arise from concurrent access to shared resources.
- **Redundancy**: Critical components of the system, such as the order servers, are replicated across different physical machines, providing redundancy to protect against hardware failures.
- **Exception Handling**: The system implements comprehensive error handling to manage exceptions and errors gracefully. This includes input validation, handling of non-existent resources, and communication errors between services.
- **Handling Missing Files**: When the catalog service starts, if there's no toys_db.csv file present at the required location, a new toys_db.csv file is generated. A default toy items database is created in memory and it is dumped into the created toys_db.csv file.When the order service starts, if there's no orders.csv file present at the required location, a new orders.csv file is generated.

### Conclusion

This lab provides a comprehensive experience in designing and implementing a fault-tolerant, highly available, and efficient distributed system using modern software engineering practices and tools. It bridges theoretical knowledge with practical implementation, offering students a deep insight into the challenges and solutions in distributed systems. By integrating RAFT, the project not only achieves high availability and fault tolerance but also provides a robust platform for further exploration of distributed consensus protocols.

### References

- Reused code from Lab2
- Technical documentation for HTTP, JSON, and Python threading.
- Python documentation for `http.client` and `http.server`.
- Used ChatGPT to understand the concepts of replication, fault tolerance, RAFT consensus, log replication, repair, etc.
- Reused some part of design documentation from Lab2
- Used ChatGPT to debug issues faced during aws deployment and some other errors
- Implemented Read Write locks using this https://gist.github.com/tylerneylon/a7ff6017b7a1f9a506cf75aa23eacfd6 
- Scholarly articles on distributed systems, focusing on caching strategies and RAFT consensus.