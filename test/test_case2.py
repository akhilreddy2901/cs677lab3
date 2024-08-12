import http.client
import json

def test_query_non_existing_product():
    conn = http.client.HTTPConnection('localhost', 8080)
    conn.request("GET", "/products/NonExistingToy")
    response = conn.getresponse()
    data = json.loads(response.read().decode())
    assert response.status == 200
    assert 'error' in data, "Expected 'error' field in response"
    assert data['error']['code'] == 404, "Error code is not correct"
    print("Test Case 2 Passed: Query Non-Existing Product")
    conn.close()

if __name__ == '__main__':
    test_query_non_existing_product()
