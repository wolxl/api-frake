"""公共 fixture。

两个改动（对面试都有话可讲）：
1) token 提升到 session 级：57 条用例原来每条都登录一次，现在整个会话登录一次，
   用例数不变、登录请求从 57 次降到 1 次，跑得更快、日志也更干净；
2) 失败自动附日志：任何用例挂掉，pytest 会调 dump_response 把响应挂到报告里。
"""

import pytest

from api.mall_api import MallApi


@pytest.fixture(scope="session")
def token():
    """整个测试会话只登录一次"""
    resp = MallApi().login("admin", "123456")
    assert resp.status_code == 200, f"登录失败：{resp.status_code} {resp.text[:300]}"
    return resp.json()["token"]


@pytest.fixture
def api(token):
    """每个用例拿一个带 token 的客户端；token 不再重复登录"""
    return MallApi(token)


@pytest.fixture
def anon():
    """不带 token 的客户端，专门测鉴权"""
    return MallApi()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """用例失败时，把该用例用到的响应挂到报告上（Allure 在 steps 里已有）"""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        resp = item.funcargs.get("resp")
        if resp is not None:
            item.add_report_section(
                "call",
                "response",
                f"status={resp.status_code}\n{resp.text[:800]}",
            )
