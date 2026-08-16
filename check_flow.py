"""验证电商下单链路：登录 → 加购 → 看购物车 → 下单 → 查订单"""
import requests

BASE = "http://127.0.0.1:5000"

# 1. 登录拿 token
resp = requests.post(f"{BASE}/api/login", json={"username": "admin", "password": "123456"})
print("1. 登录:", resp.status_code)
token = resp.json()["token"]
headers = {"Authorization": "Bearer " + token}

# 2. 加购：2 本《软件测试的艺术》(id=1, 单价 59)
resp = requests.post(f"{BASE}/api/cart", json={"book_id": 1, "quantity": 2}, headers=headers)
print("2. 加购:", resp.status_code, resp.json())

# 3. 看购物车
resp = requests.get(f"{BASE}/api/cart", headers=headers)
print("3. 购物车:", resp.status_code, resp.json())

# 4. 下单：2 本 id=1 → 总价应为 118
resp = requests.post(
    f"{BASE}/api/orders",
    json={"items": [{"book_id": 1, "quantity": 2}]},
    headers=headers,
)
print("4. 下单:", resp.status_code, resp.json())
order_id = resp.json()["data"]["id"]

# 5. 查订单
resp = requests.get(f"{BASE}/api/orders/{order_id}", headers=headers)
print("5. 查订单:", resp.status_code, resp.json())

# 6. 验证下单后购物车被清空
resp = requests.get(f"{BASE}/api/cart", headers=headers)
print("6. 下单后购物车:", resp.status_code, resp.json())
