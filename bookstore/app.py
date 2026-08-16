"""
待测系统：图书管理 API（教学用，故意从简）

运行方式：python app.py
默认地址：http://127.0.0.1:5000

说明：这个系统故意不连接数据库，数据存在内存里，重启会清空。
这是为了让"被测系统"尽量简单，你把精力花在测试上，而不是研究系统。
"""

import uuid

from flask import Flask, jsonify, request

app = Flask(__name__)

# ============ 模拟数据库（用字典，教学够用）============

books = {
    1: {"title": "软件测试的艺术", "author": "Glenford Myers", "price": 59.0},
    2: {"title": "Python编程快速上手", "author": "Al Sweigart", "price": 89.0},
}
next_book_id = 3

users = {
    "admin": "123456",
    "test": "123456",
}

# 已登录的 token 集合（登录成功后把 token 加进来）
valid_tokens = set()


# ============ 工具函数 ============

def get_token():
    """从请求头里取出 token，没有就返回 None"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    return None


def check_auth():
    """校验请求是否已登录。返回 True/False"""
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

    # 用户名或密码为空 → 401（修复空值登录漏洞）
    if not username or not password:
        return jsonify({"code": 1, "message": "用户名或密码错误"}), 401

    # 用户名或密码错误（包括用户不存在），统一返回 401
    if users.get(username) != password:
        return jsonify({"code": 1, "message": "用户名或密码错误"}), 401

    # 登录成功：生成一个随机 token 并记录
    token = uuid.uuid4().hex
    valid_tokens.add(token)
    return jsonify({"code": 0, "message": "success", "token": token})

# ============ 接口 2：获取图书列表 ============

@app.get("/api/books")
def list_books():
    if not check_auth():
        return unauthorized()
    return jsonify({"code": 0, "data": books})


# ============ 接口 3：获取单本图书 ============

@app.get("/api/books/<int:book_id>")
def get_book(book_id):
    if not check_auth():
        return unauthorized()
    book = books.get(book_id)
    if book is None:
        return jsonify({"code": 404, "message": "图书不存在"}), 404
    return jsonify({"code": 0, "data": book})


# ============ 接口 4：新增图书 ============

@app.post("/api/books")
def add_book():
    if not check_auth():
        return unauthorized()

    data = request.get_json(silent=True) or {}
    title = data.get("title")
    author = data.get("author")
    price = data.get("price")

    # 业务规则：书名和作者必填，价格必须是非负数字
    if not title or not author:
        return jsonify({"code": 400, "message": "title和author不能为空"}), 400
    if price is not None and (not isinstance(price, (int, float)) or price < 0):
        return jsonify({"code": 400, "message": "price必须是非负数字"}), 400

    global next_book_id
    book = {"title": title, "author": author, "price": price}
    books[next_book_id] = book
    result = {"id": next_book_id, **book}
    next_book_id += 1
    return jsonify({"code": 0, "message": "添加成功", "data": result}), 201


# ============ 接口 5：修改图书 ============

@app.put("/api/books/<int:book_id>")
def update_book(book_id):
    if not check_auth():
        return unauthorized()

    book = books.get(book_id)
    if book is None:
        return jsonify({"code": 404, "message": "图书不存在"}), 404

    data = request.get_json(silent=True) or {}
    if "title" in data and data["title"]:
        book["title"] = data["title"]
    if "author" in data and data["author"]:
        book["author"] = data["author"]
    if "price" in data:
        price = data["price"]
        if not isinstance(price, (int, float)) or price < 0:
            return jsonify({"code": 400, "message": "price必须是非负数字"}), 400
        book["price"] = price

    return jsonify({"code": 0, "message": "修改成功", "data": book})


# ============ 接口 6：删除图书 ============

@app.delete("/api/books/<int:book_id>")
def delete_book(book_id):
    if not check_auth():
        return unauthorized()

    if book_id not in books:
        return jsonify({"code": 404, "message": "图书不存在"}), 404

    del books[book_id]
    return jsonify({"code": 0, "message": "删除成功"})


# ============ 模拟数据：购物车 & 订单 ============
cart = {}          # {book_id: 数量}
orders = {}        # {order_id: 订单详情}
next_order_id = 1


# ============ 接口 7：加入购物车 ============
@app.post("/api/cart")
def add_to_cart():
    if not check_auth():
        return unauthorized()

    data = request.get_json(silent=True) or {}
    book_id = data.get("book_id")
    quantity = data.get("quantity")

    # 业务规则：book_id 必须存在，quantity 必须是正整数
    if book_id not in books:
        return jsonify({"code": 400, "message": "图书不存在"}), 400
    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"code": 400, "message": "quantity必须是正整数"}), 400

    cart[book_id] = cart.get(book_id, 0) + quantity
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

    # 业务规则：items 不能为空，每项 book 必须存在且数量为正整数
    if not items:
        return jsonify({"code": 400, "message": "items不能为空"}), 400

    total = 0
    for item in items:
        book_id = item.get("book_id")
        quantity = item.get("quantity")
        if book_id not in books:
            return jsonify({"code": 400, "message": "图书不存在"}), 400
        if not isinstance(quantity, int) or quantity <= 0:
            return jsonify({"code": 400, "message": "quantity必须是正整数"}), 400
        total += books[book_id]["price"] * quantity

    global next_order_id
    order = {
        "id": next_order_id,
        "items": items,
        "total_price": total,
        "status": "created",
    }
    orders[next_order_id] = order
    next_order_id += 1

    # 下单成功，清空购物车
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
