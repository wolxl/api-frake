"""用例层：商品模块（列表/详情/新增/修改/删除）+ 登录，四维度设计"""
from pathlib import Path

import pytest
import requests
import yaml

from api.mall_api import MallApi

BASE_URL = "http://127.0.0.1:5000"

# 读取 yaml 里的登录测试数据
LOGIN_DATA = yaml.safe_load(
    (Path(__file__).parent.parent / "data" / "login.yaml").read_text(encoding="utf-8")
)["login"]


# ============ 登录用例（数据驱动） ============

@pytest.mark.parametrize("case", LOGIN_DATA, ids=lambda c: c["name"])
def test_login(case):
    """登录：正确返回 200+token，错误返回 401"""
    resp = MallApi().login(case["username"], case["password"])
    assert resp.status_code == case["code"]
    if case["code"] == 200:
        assert resp.json()["token"]


# ============ 商品列表接口 ============

def test_list_products_with_token(api):
    """带 token 查列表：200 + 业务码 0 + 初始商品存在"""
    resp = api.list_products()
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert "1" in resp.json()["data"]


def test_list_products_without_token():
    """不带 token：401 + 业务码 401"""
    resp = MallApi().list_products()
    assert resp.status_code == 401
    assert resp.json()["code"] == 401


def test_list_products_bad_token():
    """token 乱写：401"""
    resp = MallApi("not-a-real-token").list_products()
    assert resp.status_code == 401


def test_list_products_wrong_header_format():
    """header 没有 Bearer 前缀：401"""
    resp = requests.get(f"{BASE_URL}/api/products", headers={"Authorization": "abc123"})
    assert resp.status_code == 401


# ============ 商品详情接口 ============

def test_get_product_exists(api):
    """查存在的 id=1：200 + 商品名正确 + 有库存字段"""
    resp = api.get_product(1)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["name"] == "无线蓝牙耳机"
    assert "stock" in resp.json()["data"]


def test_get_product_not_found(api):
    """查不存在的 id：404 + 错误信息"""
    resp = api.get_product(999)
    assert resp.status_code == 404
    assert resp.json()["message"] == "商品不存在"


def test_get_product_without_token():
    """不带 token 查详情：401"""
    resp = MallApi().get_product(1)
    assert resp.status_code == 401


def test_get_product_bad_token():
    """token 乱写查详情：401"""
    resp = MallApi("bad-token").get_product(1)
    assert resp.status_code == 401


def test_get_product_fields(api):
    """字段完整性：id=2 的商品包含 name/price/stock"""
    resp = api.get_product(2)
    data = resp.json()["data"]
    assert data["name"] == "机械键盘"
    assert "price" in data
    assert "stock" in data


# ============ 新增商品接口 ============

def test_add_product_success(api):
    """正常新增：201 + 返回带 id 的数据"""
    resp = api.add_product({"name": "测试商品", "price": 29.9, "stock": 10})
    assert resp.status_code == 201
    assert resp.json()["code"] == 0
    assert "id" in resp.json()["data"]


def test_add_product_missing_name(api):
    """缺 name：400 + 错误信息"""
    resp = api.add_product({"price": 29.9, "stock": 10})
    assert resp.status_code == 400
    assert resp.json()["message"] == "name不能为空"


def test_add_product_empty_name(api):
    """name 为空字符串：400"""
    resp = api.add_product({"name": "", "price": 29.9, "stock": 10})
    assert resp.status_code == 400


def test_add_product_negative_price(api):
    """price 为负数：400"""
    resp = api.add_product({"name": "商品", "price": -1, "stock": 10})
    assert resp.status_code == 400
    assert resp.json()["message"] == "price必须是非负数字"


def test_add_product_string_price(api):
    """price 是字符串：400"""
    resp = api.add_product({"name": "商品", "price": "abc", "stock": 10})
    assert resp.status_code == 400


def test_add_product_negative_stock(api):
    """stock 为负数：400"""
    resp = api.add_product({"name": "商品", "price": 10, "stock": -1})
    assert resp.status_code == 400
    assert resp.json()["message"] == "stock必须是非负整数"


def test_add_product_without_token():
    """不带 token 新增：401"""
    resp = MallApi().add_product({"name": "商品", "price": 1, "stock": 1})
    assert resp.status_code == 401


def test_add_then_get(api):
    """新增后立刻能查到（数据闭环）"""
    resp = api.add_product({"name": "闭环商品", "price": 10, "stock": 5})
    product_id = resp.json()["data"]["id"]
    resp2 = api.get_product(product_id)
    assert resp2.status_code == 200
    assert resp2.json()["data"]["name"] == "闭环商品"


# ============ 修改商品接口 ============

@pytest.fixture
def new_product(api):
    """每个测试自己新建一个商品，互不污染"""
    resp = api.add_product({"name": "待修改的商品", "price": 20, "stock": 10})
    return resp.json()["data"]["id"]


def test_update_name(api, new_product):
    """正常改 name：200 + 字段更新"""
    resp = api.update_product(new_product, {"name": "改后的商品名"})
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "改后的商品名"


def test_update_not_found(api):
    """改不存在的 id：404"""
    resp = api.update_product(999, {"name": "x"})
    assert resp.status_code == 404


def test_update_negative_price(api, new_product):
    """price 为负数：400"""
    resp = api.update_product(new_product, {"price": -5})
    assert resp.status_code == 400


def test_update_negative_stock(api, new_product):
    """stock 为负数：400"""
    resp = api.update_product(new_product, {"stock": -1})
    assert resp.status_code == 400


def test_update_without_token():
    """不带 token 修改：401"""
    resp = MallApi().update_product(1, {"name": "x"})
    assert resp.status_code == 401


def test_update_price_only(api, new_product):
    """只改 price：200，name 保持不变"""
    resp = api.update_product(new_product, {"price": 99})
    data = resp.json()["data"]
    assert data["price"] == 99
    assert data["name"] == "待修改的商品"


def test_update_empty_name_keeps_old(api, new_product):
    """name 传空字符串：200，原值保留（后端忽略空值）"""
    resp = api.update_product(new_product, {"name": ""})
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "待修改的商品"


# ============ 删除商品接口 ============

def test_delete_success(api, new_product):
    """删除自己新建的商品：200"""
    resp = api.delete_product(new_product)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


def test_delete_not_found(api):
    """删除不存在的 id：404"""
    resp = api.delete_product(999)
    assert resp.status_code == 404


def test_delete_without_token():
    """不带 token 删除：401"""
    resp = MallApi().delete_product(1)
    assert resp.status_code == 401


def test_delete_then_get_404(api, new_product):
    """删除后再查：404"""
    api.delete_product(new_product)
    resp = api.get_product(new_product)
    assert resp.status_code == 404


def test_delete_twice(api, new_product):
    """重复删除第二次：404"""
    api.delete_product(new_product)
    resp = api.delete_product(new_product)
    assert resp.status_code == 404
