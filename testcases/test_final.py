"""全流程冒烟：登录 → 查商品 → 加购 → 下单 → 查订单"""
import requests

BASE_URL = "http://127.0.0.1:5000"


def test_final():
    # 1. 登录拿 token
    resp = requests.post(
        f"{BASE_URL}/api/login",
        json={"username": "admin", "password": "123456"},
    )
    assert resp.status_code == 200
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 查商品列表
    resp = requests.get(f"{BASE_URL}/api/products", headers=headers)
    assert resp.status_code == 200

    # 3. 加购一件商品
    resp = requests.post(f"{BASE_URL}/api/cart", json={"product_id": 1, "quantity": 1}, headers=headers)
    assert resp.status_code == 200

    # 4. 下单
    resp = requests.post(f"{BASE_URL}/api/orders", json={"items": [{"product_id": 1, "quantity": 1}]}, headers=headers)
    assert resp.status_code == 201
    order_id = resp.json()["data"]["id"]

    # 5. 查订单
    resp = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "created"
