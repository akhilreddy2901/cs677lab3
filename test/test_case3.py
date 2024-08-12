import http.client
import json

def test_place_order_for_existing_product():
    conn = http.client.HTTPConnection('localhost', 8080)
    order_details = json.dumps({
        "name": "Tux",
        "quantity": 1
    })
    headers = {'Content-type': 'application/json'}
    conn.request("POST", "/orders", order_details, headers)
    response = conn.getresponse()
    data = json.loads(response.read().decode())
    assert response.status == 200
    assert 'data' in data, "Expected 'data' field in response"
    assert 'order_number' in data['data'], "Order number is missing"
    print("Test Case 3 Passed: Place Order for Existing Product")
    conn.close()

if __name__ == '__main__':
    test_place_order_for_existing_product()