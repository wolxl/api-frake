"""用例层：只写业务场景和断言"""
from pathlib import Path

import pytest
import requests
import yaml

from api.book_api import BookApi

BASE_URL = "http://127.0.0.1:5000"

# 读取 yaml 里的登录测试数据
LOGIN_DATA = yaml.safe_load(
    (Path(__file__).parent.parent / "data" / "login.yaml").read_text(encoding="utf-8")
)["login"]


# ============ 登录用例（数据驱动） ============

@pytest.mark.parametrize("case", LOGIN_DATA, ids=lambda c: c["name"])
def test_login(case):
    """登录：正确返回 200+token，错误返回 401"""
    resp = BookApi().login(case["username"], case["password"])
    assert resp.status_code == case["code"]
    if case["code"] == 200:
        assert resp.json()["token"]


# ============ 列表接口 ============

def test_list_books_with_token(api):
    """带 token 查列表：200 + 业务码 0 + 初始数据存在"""
    resp = api.list_books()
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert "1" in resp.json()["data"]


def test_list_books_without_token():
    """不带 token：401 + 业务码 401"""
    resp = BookApi().list_books()
    assert resp.status_code == 401
    assert resp.json()["code"] == 401


def test_list_books_bad_token():
    """token 乱写：401"""
    resp = BookApi("not-a-real-token").list_books()
    assert resp.status_code == 401


def test_list_books_wrong_header_format():
    """header 没有 Bearer 前缀：401"""
    resp = requests.get(f"{BASE_URL}/api/books", headers={"Authorization": "abc123"})
    assert resp.status_code == 401


# ============ 详情接口 ============

def test_get_book_exists(api):
    """查存在的 id=1：200 + 书名正确"""
    resp = api.get_book(1)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["title"] == "软件测试的艺术"


def test_get_book_not_found(api):
    """查不存在的 id：404 + 错误信息"""
    resp = api.get_book(999)
    assert resp.status_code == 404
    assert resp.json()["message"] == "图书不存在"


def test_get_book_without_token():
    """不带 token 查详情：401"""
    resp = BookApi().get_book(1)
    assert resp.status_code == 401


def test_get_book_bad_token():
    """token 乱写查详情：401"""
    resp = BookApi("bad-token").get_book(1)
    assert resp.status_code == 401


def test_get_book_fields(api):
    """字段完整性：id=2 的书包含 author 和 price"""
    resp = api.get_book(2)
    data = resp.json()["data"]
    assert data["author"] == "Al Sweigart"
    assert "price" in data


# ============ 新增接口 ============

def test_add_book_success(api):
    """正常新增：201 + 返回带 id 的数据"""
    resp = api.add_book({"title": "新增测试书", "author": "测试员", "price": 29.9})
    assert resp.status_code == 201
    assert resp.json()["code"] == 0
    assert "id" in resp.json()["data"]


def test_add_book_missing_title(api):
    """缺 title：400 + 错误信息"""
    resp = api.add_book({"author": "测试员", "price": 29.9})
    assert resp.status_code == 400
    assert resp.json()["message"] == "title和author不能为空"


def test_add_book_missing_author(api):
    """缺 author：400"""
    resp = api.add_book({"title": "书", "price": 29.9})
    assert resp.status_code == 400


def test_add_book_empty_title(api):
    """title 为空字符串：400"""
    resp = api.add_book({"title": "", "author": "测试员", "price": 29.9})
    assert resp.status_code == 400


def test_add_book_negative_price(api):
    """price 为负数：400"""
    resp = api.add_book({"title": "书", "author": "测试员", "price": -1})
    assert resp.status_code == 400
    assert resp.json()["message"] == "price必须是非负数字"


def test_add_book_string_price(api):
    """price 是字符串：400"""
    resp = api.add_book({"title": "书", "author": "测试员", "price": "abc"})
    assert resp.status_code == 400


def test_add_book_without_token():
    """不带 token 新增：401"""
    resp = BookApi().add_book({"title": "书", "author": "测试员", "price": 1})
    assert resp.status_code == 401


def test_add_then_get(api):
    """新增后立刻能查到（数据闭环）"""
    resp = api.add_book({"title": "闭环书", "author": "测试员", "price": 10})
    book_id = resp.json()["data"]["id"]
    resp2 = api.get_book(book_id)
    assert resp2.status_code == 200
    assert resp2.json()["data"]["title"] == "闭环书"


# ============ 修改接口 ============

@pytest.fixture
def new_book(api):
    """每个测试自己新建一本书，互不污染"""
    resp = api.add_book({"title": "待修改的书", "author": "测试员", "price": 20})
    return resp.json()["data"]["id"]


def test_update_title(api, new_book):
    """正常改 title：200 + 字段更新"""
    resp = api.update_book(new_book, {"title": "改后的书名"})
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "改后的书名"


def test_update_not_found(api):
    """改不存在的 id：404"""
    resp = api.update_book(999, {"title": "x"})
    assert resp.status_code == 404


def test_update_negative_price(api, new_book):
    """price 为负数：400"""
    resp = api.update_book(new_book, {"price": -5})
    assert resp.status_code == 400


def test_update_without_token():
    """不带 token 修改：401"""
    resp = BookApi().update_book(1, {"title": "x"})
    assert resp.status_code == 401


def test_update_price_only(api, new_book):
    """只改 price：200，title 保持不变"""
    resp = api.update_book(new_book, {"price": 99})
    data = resp.json()["data"]
    assert data["price"] == 99
    assert data["title"] == "待修改的书"


def test_update_empty_title_keeps_old(api, new_book):
    """title 传空字符串：200，原值保留（后端忽略空值）"""
    resp = api.update_book(new_book, {"title": ""})
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "待修改的书"


# ============ 删除接口 ============

def test_delete_success(api, new_book):
    """删除自己新建的书：200"""
    resp = api.delete_book(new_book)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


def test_delete_not_found(api):
    """删除不存在的 id：404"""
    resp = api.delete_book(999)
    assert resp.status_code == 404


def test_delete_without_token():
    """不带 token 删除：401"""
    resp = BookApi().delete_book(1)
    assert resp.status_code == 401


def test_delete_then_get_404(api, new_book):
    """删除后再查：404"""
    api.delete_book(new_book)
    resp = api.get_book(new_book)
    assert resp.status_code == 404


def test_delete_twice(api, new_book):
    """重复删除第二次：404"""
    api.delete_book(new_book)
    resp = api.delete_book(new_book)
    assert resp.status_code == 404
