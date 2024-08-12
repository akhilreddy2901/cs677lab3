import http.client
import json

def test_place_order_exceeding_stock():
    conn = http.client.HTTPConnection('localhost', 8080)
    # Assuming the stock for 'Tux' is less than 1000000
    order_details = json.dumps({
        "name": "Tux",
        "quantity": 1000000
    })
    headers = {'Content-type': 'application/json'}
    conn.request("POST", "/orders", order_details, headers)
    response = conn.getresponse()
    data = json.loads(response.read().decode())
    assert response.status == 200
    assert 'error' in data, "Expected 'error' field in response"
    assert data['error']['message'] == 'not enough stock', "Unexpected error message"
    print("Test Case 5 Passed: Place Order Exceeding Stock")
    conn.close()

if __name__ == '__main__':
    test_place_order_exceeding_stock()
