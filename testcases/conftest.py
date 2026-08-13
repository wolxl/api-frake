"""公共 fixture：登录一次，返回带 token 的 BookApi"""
import pytest
from api.book_api import BookApi


@pytest.fixture
def api():
    """先登录拿 token，再用 token 创建 BookApi"""
    book_api = BookApi()
    resp = book_api.login("admin", "123456")
    token = resp.json()["token"]
    return BookApi(token)