import http.client
import json

def test_query_existing_product():
    conn = http.client.HTTPConnection('localhost', 8080)
    conn.request("GET", "/products/Tux")
    response = conn.getresponse()
    data = json.loads(response.read().decode())
    assert response.status == 200
    assert 'data' in data, "Expected 'data' field in response"
    assert data['data']['name'] == 'Tux', "Product name does not match"
    print("Test Case 1 Passed: Query Existing Product")
    conn.close()

if __name__ == '__main__':
    test_query_existing_product()