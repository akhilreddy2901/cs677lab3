import http.client
import json

def test_order_replication():
    # Place an order
    conn = http.client.HTTPConnection('localhost', 8080)
    order_data = json.dumps({'name': 'Tux', 'quantity': 2})
    headers = {'Content-Type': 'application/json'}
    conn.request('POST', '/orders', body=order_data, headers=headers)
    response = conn.getresponse()
    order_info = json.loads(response.read().decode())
    assert response.status == 200
    order_number = order_info['data']['order_number']

    # Check replication on each replica
    replicas = ['8082', '8083', '8084']  # Assuming these are the replica ports
    for port in replicas:
        conn = http.client.HTTPConnection('localhost', port)
        conn.request('GET', f'/query/{order_number}')
        response = conn.getresponse()
        replica_order_info = json.loads(response.read().decode())
        assert response.status == 200
        assert replica_order_info['data']['number'] == order_number
        print(f'Replica {port} has order {order_number}.')
    print("Test Case 11 Passed: Order Replication Test")

if __name__ == '__main__':
    test_order_replication()
