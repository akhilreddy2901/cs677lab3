from test_case1 import test_query_existing_product
from test_case2 import test_query_non_existing_product
from test_case3 import test_place_order_for_existing_product
from test_case4 import test_place_order_for_non_existing_product
from test_case5 import test_place_order_exceeding_stock
from test_case6 import test_catalog_query_product
from test_case7 import test_catalog_update_stock
from test_case8 import test_order_place_order
from test_case8 import test_order_query_order
from test_case9 import test_front_end_place_order
from test_case10 import test_front_end_query_product
from test_case11 import test_order_replication

if __name__ == "__main__":
    test_query_existing_product()
    test_query_non_existing_product()
    test_place_order_for_existing_product()
    test_place_order_for_non_existing_product()
    test_place_order_exceeding_stock()
    test_catalog_query_product()
    test_catalog_update_stock()
    test_order_place_order()
    test_order_query_order()
    test_front_end_place_order()
    test_front_end_query_product()
    test_order_replication() #Uncomment this if the order services are running on ['8082', '8083', '8084'] ports of localhost