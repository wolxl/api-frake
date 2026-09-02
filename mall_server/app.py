"""
待测系统：在线商城 API（Flask + MySQL）

运行前准备：
1. 建库建表：mysql -u root -p < schema.sql
2. 种子数据：mysql -u root -p < seed.sql
3. 装依赖：  pip install -r requirements.txt（含 pymysql）

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

import hashlib
import uuid

from flask import Flask, jsonify, request

import db

app = Flask(__name__)

# token -> user_id（进程内存；真实项目应换 Redis 或 JWT）
tokens = {}


# ============ 工具函数 ============

def get_token():
    """从请求头取出 token"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    return None


def current_user_id():
    """已登录返回 user_id，未登录返回 None"""
    return tokens.get(get_token())


def unauthorized():
    """未登录的统一返回"""
    return jsonify({"code": 401, "message": "未登录或token失效"}), 401


def hash_password(password):
    """密码哈希存储，数据库里不存明文"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def product_to_dict(row):
    """数据库行 -> 响应字典（DECIMAL 转 float，否则 JSON 序列化会失败）"""
    return {
        "id": row["id"],
        "name": row["name"],
        "price": float(row["price"]),
        "stock": row["stock"],
    }


def cart_dict(user_id):
    """该用户的购物车，格式 {str(product_id): quantity}"""
    rows = db.query(
        "SELECT product_id, quantity FROM cart_items WHERE user_id=%s", (user_id,)
    )
    return {str(r["product_id"]): r["quantity"] for r in rows}


# ============ 接口 1：登录 ============

@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    # 用户名或密码为空 → 401
    if not username or not password:
        return jsonify({"code": 1, "message": "用户名或密码错误"}), 401

    # 查数据库：用户不存在或密码不匹配，统一返回 401
    row = db.query_one(
        "SELECT id, password FROM users WHERE username=%s", (username,)
    )
    if row is None or row["password"] != hash_password(password):
        return jsonify({"code": 1, "message": "用户名或密码错误"}), 401

    token = uuid.uuid4().hex
    tokens[token] = row["id"]
    return jsonify({"code": 0, "message": "success", "token": token})


# ============ 接口 2：商品列表 ============

@app.get("/api/products")
def list_products():
    if current_user_id() is None:
        return unauthorized()

    rows = db.query("SELECT id, name, price, stock FROM products ORDER BY id")
    data = {str(r["id"]): product_to_dict(r) for r in rows}
    return jsonify({"code": 0, "data": data})


# ============ 接口 3：商品详情 ============

@app.get("/api/products/<int:product_id>")
def get_product(product_id):
    if current_user_id() is None:
        return unauthorized()

    row = db.query_one(
        "SELECT id, name, price, stock FROM products WHERE id=%s", (product_id,)
    )
    if row is None:
        return jsonify({"code": 404, "message": "商品不存在"}), 404
    return jsonify({"code": 0, "data": product_to_dict(row)})


# ============ 接口 4：新增商品 ============

@app.post("/api/products")
def add_product():
    if current_user_id() is None:
        return unauthorized()

    data = request.get_json(silent=True) or {}
    name = data.get("name")
    price = data.get("price")
    stock = data.get("stock", 0)

    if not name:
        return jsonify({"code": 400, "message": "name不能为空"}), 400
    if not isinstance(price, (int, float)) or price < 0:
        return jsonify({"code": 400, "message": "price必须是非负数字"}), 400
    if not isinstance(stock, int) or stock < 0:
        return jsonify({"code": 400, "message": "stock必须是非负整数"}), 400

    product_id = db.execute(
        "INSERT INTO products (name, price, stock) VALUES (%s, %s, %s)",
        (name, price, stock),
    )
    return jsonify({
        "code": 0,
        "message": "添加成功",
        "data": {"id": product_id, "name": name, "price": price, "stock": stock},
    }), 201


# ============ 接口 5：修改商品 ============

@app.put("/api/products/<int:product_id>")
def update_product(product_id):
    if current_user_id() is None:
        return unauthorized()

    row = db.query_one(
        "SELECT id, name, price, stock FROM products WHERE id=%s", (product_id,)
    )
    if row is None:
        return jsonify({"code": 404, "message": "商品不存在"}), 404

    data = request.get_json(silent=True) or {}
    name = row["name"]
    price = row["price"]
    stock = row["stock"]

    if "name" in data and data["name"]:
        name = data["name"]
    if "price" in data:
        p = data["price"]
        if not isinstance(p, (int, float)) or p < 0:
            return jsonify({"code": 400, "message": "price必须是非负数字"}), 400
        price = p
    if "stock" in data:
        s = data["stock"]
        if not isinstance(s, int) or s < 0:
            return jsonify({"code": 400, "message": "stock必须是非负整数"}), 400
        stock = s

    db.execute(
        "UPDATE products SET name=%s, price=%s, stock=%s WHERE id=%s",
        (name, price, stock, product_id),
    )
    return jsonify({
        "code": 0,
        "message": "修改成功",
        "data": {"id": product_id, "name": name, "price": float(price), "stock": stock},
    })


# ============ 接口 6：删除商品 ============

@app.delete("/api/products/<int:product_id>")
def delete_product(product_id):
    if current_user_id() is None:
        return unauthorized()

    row = db.query_one("SELECT id FROM products WHERE id=%s", (product_id,))
    if row is None:
        return jsonify({"code": 404, "message": "商品不存在"}), 404

    db.execute("DELETE FROM products WHERE id=%s", (product_id,))
    return jsonify({"code": 0, "message": "删除成功"})


# ============ 接口 7：加入购物车 ============

@app.post("/api/cart")
def add_to_cart():
    user_id = current_user_id()
    if user_id is None:
        return unauthorized()

    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity")

    row = db.query_one(
        "SELECT id, stock FROM products WHERE id=%s", (product_id,)
    )
    if row is None:
        return jsonify({"code": 400, "message": "商品不存在"}), 400
    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"code": 400, "message": "quantity必须是正整数"}), 400
    if quantity > row["stock"]:
        return jsonify({"code": 400, "message": "库存不足"}), 400

    # 唯一键 (user_id, product_id) 保证同一商品只一行，重复加购累加数量
    db.execute(
        """
        INSERT INTO cart_items (user_id, product_id, quantity)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE quantity = quantity + %s
        """,
        (user_id, product_id, quantity, quantity),
    )
    return jsonify({"code": 0, "message": "加购成功", "data": cart_dict(user_id)})


# ============ 接口 8：查看购物车 ============

@app.get("/api/cart")
def get_cart():
    user_id = current_user_id()
    if user_id is None:
        return unauthorized()
    return jsonify({"code": 0, "data": cart_dict(user_id)})


# ============ 接口 9：提交订单（事务） ============

@app.post("/api/orders")
def create_order():
    user_id = current_user_id()
    if user_id is None:
        return unauthorized()

    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    if not items:
        return jsonify({"code": 400, "message": "items不能为空"}), 400

    conn = db.get_conn()
    try:
        # 第一遍：只校验不写库（商品存在、数量合法、库存足够），FOR UPDATE 锁行
        validated = []
        total = 0.0
        for item in items:
            product_id = item.get("product_id")
            quantity = item.get("quantity")
            row = db.query_one(
                "SELECT id, price, stock FROM products WHERE id=%s FOR UPDATE",
                (product_id,),
                conn,
            )
            if row is None:
                return jsonify({"code": 400, "message": "商品不存在"}), 400
            if not isinstance(quantity, int) or quantity <= 0:
                return jsonify({"code": 400, "message": "quantity必须是正整数"}), 400
            if quantity > row["stock"]:
                return jsonify({"code": 400, "message": "库存不足"}), 400
            validated.append((product_id, quantity, float(row["price"])))
            total += float(row["price"]) * quantity

        # 第二遍：扣库存 + 写订单 + 写订单明细
        for product_id, quantity, _price in validated:
            db.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s",
                (quantity, product_id),
                conn,
            )

        order_id = db.execute(
            "INSERT INTO orders (user_id, total_price, status) VALUES (%s, %s, 'created')",
            (user_id, total),
            conn,
        )
        for product_id, quantity, price in validated:
            db.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, price)"
                " VALUES (%s, %s, %s, %s)",
                (order_id, product_id, quantity, price),
                conn,
            )

        # 下单成功后清空该用户购物车
        db.execute("DELETE FROM cart_items WHERE user_id = %s", (user_id,), conn)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    order = {
        "id": order_id,
        "items": [
            {"product_id": pid, "quantity": qty} for pid, qty, _ in validated
        ],
        "total_price": total,
        "status": "created",
    }
    return jsonify({"code": 0, "message": "下单成功", "data": order}), 201


# ============ 接口 10：查询订单 ============

@app.get("/api/orders/<int:order_id>")
def get_order(order_id):
    user_id = current_user_id()
    if user_id is None:
        return unauthorized()

    row = db.query_one(
        "SELECT id, user_id, total_price, status FROM orders"
        " WHERE id=%s AND user_id=%s",
        (order_id, user_id),
    )
    if row is None:
        return jsonify({"code": 404, "message": "订单不存在"}), 404

    rows = db.query(
        "SELECT product_id, quantity FROM order_items WHERE order_id=%s",
        (order_id,),
    )
    order = {
        "id": row["id"],
        "items": [
            {"product_id": r["product_id"], "quantity": r["quantity"]} for r in rows
        ],
        "total_price": float(row["total_price"]),
        "status": row["status"],
    }
    return jsonify({"code": 0, "data": order})


if __name__ == "__main__":
    app.run(debug=True)
