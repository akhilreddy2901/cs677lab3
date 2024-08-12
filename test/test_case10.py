import http.client
import json

def test_front_end_query_product():
    conn = http.client.HTTPConnection('localhost', 8080)
    conn.request("GET", "/products/Tux")
    response = conn.getresponse()
    data = json.loads(response.read().decode())
    assert response.status == 200
    assert 'data' in data, "Expected 'data' field in response"
    assert data['data']['name'] == 'Tux', "Product name does not match"
    print("Test Case 10 Passed: Front-End Service - Query Product Test")
    conn.close()

if __name__ == '__main__':
    test_front_end_query_product()
