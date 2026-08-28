"""
待测系统：在线商城 API（教学用）

运行方式：python app.py
默认地址：http://127.0.0.1:5000

接口一览：
- POST   /api/login             登录，返回 token
- GET    /api/products          商品列表
- POST   /api/products          新增商品
- GET    /api/products/<id>     商品详情
- PUT    /api/products/<id>     修改商品
- DELETE /api/products/<id>     删除商品
- POST   /api/cart              加入购物车（校验库存）
- GET    /api/cart              查看购物车
- POST   /api/orders            提交订单（校验并扣减库存）
- GET    /api/orders/<id>       查询订单
"""

import uuid

from flask import Flask, jsonify, request

app = Flask(__name__)

# ============ 模拟数据库（内存存储，重启清空）============

products = {
    1: {"name": "无线蓝牙耳机", "price": 199.0, "stock": 100},
    2: {"name": "机械键盘", "price": 399.0, "stock": 50},
}
next_product_id = 3

users = {
    "admin": "123456",
    "test": "123456",
}

valid_tokens = set()
cart = {}        # {product_id: 数量}
orders = {}      # {order_id: 订单详情}
next_order_id = 1


# ============ 工具函数 ============

def get_token():
    """从请求头里取出 token，没有就返回 None"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    return None


def check_auth():
    """校验请求是否已登录"""
    return get_token() in valid_tokens


def unauthorized():
    """未登录的统一返回"""
    return jsonify({"code": 401, "message": "未登录或token失效"}), 401


# ============ 接口 1：登录 ============

@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    # 用户名或密码为空 → 401
    if not username or not password:
        return jsonify({"code": 1, "message": "用户名或密码错误"}), 401

    # 用户名或密码错误（包括用户不存在），统一返回 401
    if users.get(username) != password:
        return jsonify({"code": 1, "message": "用户名或密码错误"}), 401

    token = uuid.uuid4().hex
    valid_tokens.add(token)
    return jsonify({"code": 0, "message": "success", "token": token})


# ============ 接口 2：获取商品列表 ============

@app.get("/api/products")
def list_products():
    if not check_auth():
        return unauthorized()
    return jsonify({"code": 0, "data": products})


# ============ 接口 3：获取单个商品 ============

@app.get("/api/products/<int:product_id>")
def get_product(product_id):
    if not check_auth():
        return unauthorized()
    product = products.get(product_id)
    if product is None:
        return jsonify({"code": 404, "message": "商品不存在"}), 404
    return jsonify({"code": 0, "data": product})


# ============ 接口 4：新增商品 ============

@app.post("/api/products")
def add_product():
    if not check_auth():
        return unauthorized()

    data = request.get_json(silent=True) or {}
    name = data.get("name")
    price = data.get("price")
    stock = data.get("stock", 0)

    # 业务规则：商品名必填，价格必须是非负数字，库存必须是非负整数
    if not name:
        return jsonify({"code": 400, "message": "name不能为空"}), 400
    if not isinstance(price, (int, float)) or price < 0:
        return jsonify({"code": 400, "message": "price必须是非负数字"}), 400
    if not isinstance(stock, int) or stock < 0:
        return jsonify({"code": 400, "message": "stock必须是非负整数"}), 400

    global next_product_id
    product = {"name": name, "price": price, "stock": stock}
    products[next_product_id] = product
    result = {"id": next_product_id, **product}
    next_product_id += 1
    return jsonify({"code": 0, "message": "添加成功", "data": result}), 201


# ============ 接口 5：修改商品 ============

@app.put("/api/products/<int:product_id>")
def update_product(product_id):
    if not check_auth():
        return unauthorized()

    product = products.get(product_id)
    if product is None:
        return jsonify({"code": 404, "message": "商品不存在"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"]:
        product["name"] = data["name"]
    if "price" in data:
        price = data["price"]
        if not isinstance(price, (int, float)) or price < 0:
            return jsonify({"code": 400, "message": "price必须是非负数字"}), 400
        product["price"] = price
    if "stock" in data:
        stock = data["stock"]
        if not isinstance(stock, int) or stock < 0:
            return jsonify({"code": 400, "message": "stock必须是非负整数"}), 400
        product["stock"] = stock

    return jsonify({"code": 0, "message": "修改成功", "data": product})


# ============ 接口 6：删除商品 ============

@app.delete("/api/products/<int:product_id>")
def delete_product(product_id):
    if not check_auth():
        return unauthorized()

    if product_id not in products:
        return jsonify({"code": 404, "message": "商品不存在"}), 404

    del products[product_id]
    return jsonify({"code": 0, "message": "删除成功"})


# ============ 接口 7：加入购物车 ============

@app.post("/api/cart")
def add_to_cart():
    if not check_auth():
        return unauthorized()

    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity")

    # 业务规则：商品必须存在，数量必须是正整数，且不能超过库存
    if product_id not in products:
        return jsonify({"code": 400, "message": "商品不存在"}), 400
    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"code": 400, "message": "quantity必须是正整数"}), 400
    if quantity > products[product_id]["stock"]:
        return jsonify({"code": 400, "message": "库存不足"}), 400

    cart[product_id] = cart.get(product_id, 0) + quantity
    return jsonify({"code": 0, "message": "加购成功", "data": cart})


# ============ 接口 8：查看购物车 ============

@app.get("/api/cart")
def get_cart():
    if not check_auth():
        return unauthorized()
    return jsonify({"code": 0, "data": cart})


# ============ 接口 9：提交订单 ============

@app.post("/api/orders")
def create_order():
    if not check_auth():
        return unauthorized()

    data = request.get_json(silent=True) or {}
    items = data.get("items") or []

    # 业务规则：items 不能为空，每项商品必须存在、数量为正整数且不超过库存
    if not items:
        return jsonify({"code": 400, "message": "items不能为空"}), 400

    total = 0
    for item in items:
        product_id = item.get("product_id")
        quantity = item.get("quantity")
        if product_id not in products:
            return jsonify({"code": 400, "message": "商品不存在"}), 400
        if not isinstance(quantity, int) or quantity <= 0:
            return jsonify({"code": 400, "message": "quantity必须是正整数"}), 400
        if quantity > products[product_id]["stock"]:
            return jsonify({"code": 400, "message": "库存不足"}), 400
        total += products[product_id]["price"] * quantity

    # 校验全部通过：扣减库存、生成订单、清空购物车
    for item in items:
        products[item["product_id"]]["stock"] -= item["quantity"]

    global next_order_id
    order = {
        "id": next_order_id,
        "items": items,
        "total_price": total,
        "status": "created",
    }
    orders[next_order_id] = order
    next_order_id += 1

    cart.clear()
    return jsonify({"code": 0, "message": "下单成功", "data": order}), 201


# ============ 接口 10：查询订单 ============

@app.get("/api/orders/<int:order_id>")
def get_order(order_id):
    if not check_auth():
        return unauthorized()

    order = orders.get(order_id)
    if order is None:
        return jsonify({"code": 404, "message": "订单不存在"}), 404
    return jsonify({"code": 0, "data": order})


if __name__ == "__main__":
    app.run(debug=True)
