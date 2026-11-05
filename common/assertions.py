"""断言封装层。

为什么要这一层：
1) 用例层只写"期望什么"，不写"怎么断言" —— 改断言风格只改这一处；
2) 失败时一次性给出：接口、期望、实际、响应体前 500 字 —— 排障不用再复现；
3) 每条断言自动进 Allure 的 step + 附件，报告里能直接看到请求/响应。
"""
import json

import allure


def _detail(resp):
    """把响应压成一段可读文本，避免日志里出现几万字符的 HTML。"""
    body = resp.text or ""
    if len(body) > 500:
        body = body[:500] + "...(truncated)"
    return {
        "url": getattr(resp, "url", ""),
        "status": resp.status_code,
        "body": body,
    }


def _attach(resp):
    try:
        allure.attach(
            json.dumps(_detail(resp), ensure_ascii=False, indent=2),
            name="response",
            attachment_type=allure.attachment_type.JSON,
        )
    except Exception:
        pass


def _fail(msg, resp):
    _attach(resp)
    detail = _detail(resp)
    raise AssertionError(
        f"{msg}\n  url   : {detail['url']}\n  status: {detail['status']}\n  body  : {detail['body']}"
    )


def assert_status(resp, expected):
    """HTTP 状态码断言"""
    with allure.step(f"断言 status == {expected}（实际 {resp.status_code}）"):
        if resp.status_code != expected:
            _fail(f"状态码不符：期望 {expected}，实际 {resp.status_code}", resp)


def assert_code(resp, expected=0):
    """业务码断言：本项目约定 success 时 body.code == 0"""
    with allure.step(f"断言 body.code == {expected}"):
        try:
            actual = resp.json().get("code")
        except Exception:
            _fail("响应不是合法 JSON，无法取 code", resp)
        if actual != expected:
            _fail(f"业务码不符：期望 {expected}，实际 {actual}", resp)


def assert_ok(resp, status=200):
    """成功语义的合并断言：HTTP 200 + 业务码 0 + 有 data"""
    assert_status(resp, status)
    assert_code(resp, 0)
    with allure.step("断言 body 含 data 字段"):
        if "data" not in resp.json():
            _fail("响应缺少 data 字段", resp)


def assert_error(resp, status, message=None):
    """失败语义的合并断言：指定状态码 + 可选错误文案"""
    assert_status(resp, status)
    if message is not None:
        with allure.step(f"断言 message == {message}"):
            actual = (resp.json() or {}).get("message")
            if actual != message:
                _fail(f"错误文案不符：期望 {message}，实际 {actual}", resp)


def assert_field(resp, field, expected):
    """data 里某个字段等于期望值"""
    with allure.step(f"断言 data.{field} == {expected}"):
        data = (resp.json() or {}).get("data") or {}
        if data.get(field) != expected:
            _fail(f"字段不符：data.{field} 期望 {expected}，实际 {data.get(field)}", resp)


def assert_has_keys(resp, *keys):
    """data 必须包含这些字段（契约测试用）"""
    with allure.step("断言 data 字段齐全：" + "/".join(keys)):
        data = (resp.json() or {}).get("data") or {}
        missing = [k for k in keys if k not in data]
        if missing:
            _fail(f"data 缺字段：{missing}（实际字段 {list(data.keys())}）", resp)


def assert_type(resp, field, typ):
    """data 字段类型断言：契约比"有值"更严，能抓到 1 → "1" 这类退化"""
    with allure.step(f"断言 data.{field} 是 {typ.__name__}"):
        data = (resp.json() or {}).get("data") or {}
        value = data.get(field)
        if not isinstance(value, typ):
            _fail(f"类型不符：data.{field} 期望 {typ.__name__}，实际 {type(value).__name__}（{value!r}）", resp)
