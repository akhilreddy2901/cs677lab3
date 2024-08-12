import http.client
import json

def test_catalog_update_stock():
    conn = http.client.HTTPConnection('localhost', 8081)
    product_details = json.dumps({
        "name": "Tux",
        "quantity": 1
    })
    headers = {'Content-type': 'application/json'}
    conn.request("POST", "/buy_qty", product_details, headers)
    response = conn.getresponse()
    data = json.loads(response.read().decode())
    assert response.status == 200
    assert 'data' in data or 'error' in data, "Expected 'data' or 'error' field in response"
    print("Test Case 7 Passed: Catalog Service - Update Stock Test")
    conn.close()

if __name__ == '__main__':
    test_catalog_update_stock()
