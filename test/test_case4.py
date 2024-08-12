import http.client
import json

def test_place_order_for_non_existing_product():
    conn = http.client.HTTPConnection('localhost', 8080)
    order_details = json.dumps({
        "name": "NonExistingToy",
        "quantity": 1
    })
    headers = {'Content-type': 'application/json'}
    conn.request("POST", "/orders", order_details, headers)
    response = conn.getresponse()
    data = json.loads(response.read().decode())
    assert response.status == 200
    assert 'error' in data, "Expected 'error' field in response"
    assert data['error']['code'] == 404, "Error code is not correct"
    print("Test Case 4 Passed: Place Order for Non-Existing Product")
    conn.close()

if __name__ == '__main__':
    test_place_order_for_non_existing_product()
