"""公共 fixture：登录一次，返回带 token 的 MallApi"""
import pytest
from api.mall_api import MallApi


@pytest.fixture
def api():
    """先登录拿 token，再用 token 创建 MallApi"""
    mall_api = MallApi()
    resp = mall_api.login("admin", "123456")
    token = resp.json()["token"]
    return MallApi(token)
