"""用例层：只写业务场景和断言"""
from api.book_api import BookApi


def test_list_books(api):
    """带 token 查列表，应该成功"""
    resp = api.list_books()
    assert resp.status_code == 200


def test_add_book(api):
    """新增图书，应该 201"""
    resp = api.add_book({"title": "测试框架的书", "author": "我", "price": 39.9})
    assert resp.status_code == 201


def test_get_book(api):
    """查 id=1 的书，应该成功"""
    resp = api.get_book(1)
    assert resp.status_code == 200


def test_books_without_token():
    """不带 token 查列表，应该 401"""
    api = BookApi()  # 故意不带 token
    resp = api.list_books()
    assert resp.status_code == 401