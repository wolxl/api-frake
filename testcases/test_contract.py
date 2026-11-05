"""契约测试：不测"功能对不对"，测"接口承诺的东西还在不在"。

和 test_product.py 的分工：
- test_product.py 管行为（能不能增删改查、错误码对不对）；
- 这个文件管契约（字段是否存在、类型是否退化、不变量是否被破坏）。

这一类用例最适合放进 CI：字段改名、类型从 int 变 str、库存变负数，
功能测试可能全绿，但契约测试会立刻红。
"""

from common.assertions import (
    assert_ok,
    assert_has_keys,
    assert_type,
    assert_field,
    assert_status,
)


# ============ 商品对象契约 ============

def test_product_contract_fields(api):
    """详情返回必须包含 id/name/price/stock 四个字段"""
    resp = api.get_product(1)
    assert_ok(resp)
    assert_has_keys(resp, "id", "name", "price", "stock")


def test_product_contract_types(api):
    """字段类型不能退化：id 是整数、name 是字符串"""
    resp = api.get_product(1)
    assert_ok(resp)
    assert_type(resp, "id", int)
    assert_type(resp, "name", str)


def test_product_price_not_negative(api):
    """不变量：商品价格不能是负数"""
    resp = api.get_product(1)
    assert_ok(resp)
    price = resp.json()["data"]["price"]
    assert price >= 0, f"价格出现负数：{price}"


def test_product_stock_is_int(api):
    """库存必须是整数（出现 1.5 件就是数据层出了问题）"""
    resp = api.get_product(1)
    assert_ok(resp)
    assert_type(resp, "stock", int)


# ============ 列表契约 ============

def test_list_contract_is_dict_indexed_by_id(api):
    """列表返回的 data 是 "id → 商品" 的字典，不是数组"""
    resp = api.list_products()
    assert_ok(resp)
    data = resp.json()["data"]
    assert isinstance(data, dict), f"列表结构变了，期望 dict，实际 {type(data).__name__}"


def test_list_contract_item_shape(api):
    """列表里每个商品也必须带 name/price/stock"""
    resp = api.list_products()
    assert_ok(resp)
    data = resp.json()["data"]
    assert data, "列表为空，无法校验元素结构"
    for pid, item in data.items():
        missing = [k for k in ("name", "price", "stock") if k not in item]
        assert not missing, f"商品 {pid} 缺字段 {missing}（实际 {list(item.keys())}）"


# ============ 新增返回契约 ============

def test_create_returns_id(api):
    """新增成功必须回传新 id，否则前端拿不到"""
    resp = api.add_product({"name": "契约校验商品", "price": 12.5, "stock": 3})
    assert_status(resp, 201)
    assert_ok(resp, status=201)
    assert_has_keys(resp, "id")
    assert_type(resp, "id", int)


def test_create_echoes_input(api):
    """回传的商品名要与提交的一致（防止后端写死或截断）"""
    resp = api.add_product({"name": "回显校验", "price": 8, "stock": 2})
    assert_ok(resp, status=201)
    assert_field(resp, "name", "回显校验")
