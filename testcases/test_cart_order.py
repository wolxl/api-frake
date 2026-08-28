"""电商链路用例：购物车 + 订单（含库存校验，四维度设计）"""
from api.mall_api import MallApi


# ============ 购物车接口 ============

def test_add_to_cart(api):
    """加购：数量累加（相对断言，不依赖初始状态）"""
    before = api.get_cart().json()["data"].get("1", 0)
    resp = api.add_to_cart(1, 2)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    after = resp.json()["data"].get("1", 0)
    assert after == before + 2


def test_add_product_not_found(api):
    """加购不存在的商品：400 + 错误信息"""
    resp = api.add_to_cart(999, 1)
    assert resp.status_code == 400
    assert resp.json()["message"] == "商品不存在"


def test_add_quantity_zero(api):
    """加购数量为 0：400"""
    resp = api.add_to_cart(1, 0)
    assert resp.status_code == 400
    assert resp.json()["message"] == "quantity必须是正整数"


def test_add_quantity_negative(api):
    """加购数量为负数：400"""
    resp = api.add_to_cart(1, -1)
    assert resp.status_code == 400


def test_add_quantity_string(api):
    """加购数量是字符串：400"""
    resp = api.add_to_cart(1, "2")
    assert resp.status_code == 400


def test_add_over_stock(api):
    """加购数量超过库存：400 库存不足"""
    resp = api.add_to_cart(2, 9999)
    assert resp.status_code == 400
    assert resp.json()["message"] == "库存不足"


def test_add_to_cart_without_token():
    """加购不带 token：401"""
    resp = MallApi().add_to_cart(1, 1)
    assert resp.status_code == 401


def test_get_cart_without_token():
    """看购物车不带 token：401"""
    resp = MallApi().get_cart()
    assert resp.status_code == 401


def test_add_twice_accumulates(api):
    """重复加购累加：加 2 次 3 本 → 相对值 +6"""
    before = api.get_cart().json()["data"].get("2", 0)
    api.add_to_cart(2, 3)
    resp = api.add_to_cart(2, 3)
    after = resp.json()["data"].get("2", 0)
    assert after == before + 6


# ============ 订单接口 ============

def test_create_order_success(api):
    """下单：201 + 总价正确 + 状态 created"""
    resp = api.create_order([{"product_id": 1, "quantity": 2}])
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["total_price"] == 398.0
    assert data["status"] == "created"


def test_create_order_empty_items(api):
    """下单空 items：400"""
    resp = api.create_order([])
    assert resp.status_code == 400
    assert resp.json()["message"] == "items不能为空"


def test_create_order_product_not_found(api):
    """下单不存在的商品：400"""
    resp = api.create_order([{"product_id": 999, "quantity": 1}])
    assert resp.status_code == 400


def test_create_order_bad_quantity(api):
    """下单数量非法：400"""
    resp = api.create_order([{"product_id": 1, "quantity": 0}])
    assert resp.status_code == 400


def test_create_order_over_stock(api):
    """下单数量超过库存：400 库存不足"""
    resp = api.create_order([{"product_id": 2, "quantity": 9999}])
    assert resp.status_code == 400
    assert resp.json()["message"] == "库存不足"


def test_create_order_without_token():
    """下单不带 token：401"""
    resp = MallApi().create_order([{"product_id": 1, "quantity": 1}])
    assert resp.status_code == 401


def test_order_clears_cart(api):
    """下单成功后购物车清空"""
    api.add_to_cart(1, 1)
    api.create_order([{"product_id": 1, "quantity": 1}])
    cart = api.get_cart().json()["data"]
    assert cart == {}


def test_order_deducts_stock(api):
    """下单成功后库存扣减：先查库存，下单后再查，减少对应数量"""
    before = api.get_product(2).json()["data"]["stock"]
    api.create_order([{"product_id": 2, "quantity": 1}])
    after = api.get_product(2).json()["data"]["stock"]
    assert after == before - 1


def test_get_order(api):
    """查订单：200 + 状态正确"""
    resp = api.create_order([{"product_id": 2, "quantity": 1}])
    order_id = resp.json()["data"]["id"]
    resp2 = api.get_order(order_id)
    assert resp2.status_code == 200
    assert resp2.json()["data"]["status"] == "created"


def test_get_order_not_found(api):
    """查不存在的订单：404"""
    resp = api.get_order(9999)
    assert resp.status_code == 404
    assert resp.json()["message"] == "订单不存在"


def test_get_order_without_token():
    """查订单不带 token：401"""
    resp = MallApi().get_order(1)
    assert resp.status_code == 401
