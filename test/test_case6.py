import http.client
import json

def test_catalog_query_product():
    conn = http.client.HTTPConnection('localhost', 8081)
    conn.request("GET", "/query/Tux")
    response = conn.getresponse()
    data = json.loads(response.read().decode())
    assert response.status == 200
    assert 'data' in data, "Expected 'data' field in response"
    assert data['data']['name'] == 'Tux', "Product name does not match"
    print("Test Case 6 Passed: Catalog Service - Query Product Test ")
    conn.close()

if __name__ == '__main__':
    test_catalog_query_product()
