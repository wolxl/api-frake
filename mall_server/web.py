"""商城 Web 前端（服务端渲染）+ 页面路由

存在理由：接口测试只能证明「JSON 返回对不对」，证明不了「用户在页面上能不能走完一单」。
本模块给同一个被测系统补一条功能测试线，页面直接读写同一套表，因此可以做跨层校验：
    页面上加购 → 调 GET /api/cart 能查到 → 「前端操作 + 接口断言」两端对齐。

页面清单：
    GET  /                      首页（分类 + 商品列表）
    GET  /search?q=             搜索结果
    GET  /product/<pid>         商品详情
    POST /cart/add              加入购物车（表单）
    GET  /cart                  购物车
    POST /cart/remove           删除购物车行
    POST /order/submit          提交订单（事务：校验库存 → 扣减 → 写订单 → 清购物车）
    GET  /orders                我的订单
    GET/POST /login             登录（session cookie，与 /api/login 的 token 机制并行）
    GET  /logout                退出
"""

import hashlib
from functools import wraps

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)

import db

web_bp = Blueprint(
    "web", __name__, template_folder="templates", static_folder="static"
)

# ============ 工具 ============


def hash_password(password: str) -> str:
    """与 app.py 保持一致：sha256 十六进制，库里不存明文"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def current_user():
    """从 session 取当前用户；未登录返回 None"""
    uid = session.get("user_id")
    if not uid:
        return None
    row = db.query_one("SELECT id, username FROM users WHERE id=%s", (uid,))
    if row is None:  # session 里的用户在库里被删了
        session.clear()
        return None
    return row


def login_required(view):
    """页面级登录校验：未登录跳登录页，记住来路"""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("web.login", next=request.path))
        return view(*args, **kwargs)

    return wrapper


def cart_rows(user_id):
    """购物车明细（连表拿商品名/单价/库存）"""
    return db.query(
        """
        SELECT c.id, c.product_id, c.quantity, p.name, p.price, p.stock
        FROM cart_items c JOIN products p ON p.id = c.product_id
        WHERE c.user_id = %s ORDER BY c.id
        """,
        (user_id,),
    )


def cart_badge(user_id):
    """顶部购物车角标数量"""
    if not user_id:
        return 0
    row = db.query_one(
        "SELECT COALESCE(SUM(quantity),0) AS n FROM cart_items WHERE user_id=%s",
        (user_id,),
    )
    return int(row["n"]) if row else 0


@web_bp.app_context_processor
def inject_globals():
    """所有模板都能拿到 user 与购物车数量"""
    user = current_user()
    return {
        "user": user,
        "cart_badge": cart_badge(user["id"]) if user else 0,
    }


# 商品名 → emoji（没有图片资源，用色块 + emoji 当商品图，测试点不受影响）
_EMOJI = [
    ("耳机", "🎧"), ("键盘", "⌨️"), ("手机", "📱"), ("笔记本", "💻"),
    ("显示器", "🖥️"), ("鼠标", "🖱️"), ("音箱", "🔊"), ("音响", "🔊"),
    ("充电宝", "🔋"), ("平板", "📱"), ("手表", "⌚"), ("相机", "📷"),
    ("路由", "📶"), ("耳机", "🎧"),
]


@web_bp.app_template_filter("emoji")
def emoji_filter(name: str) -> str:
    for key, emo in _EMOJI:
        if key in (name or ""):
            return emo
    return "📦"


@web_bp.app_template_filter("yuan")
def yuan_filter(value) -> str:
    """DECIMAL 过来是 Decimal，统一两位小数"""
    return f"{float(value):.2f}"


# ============ 首页 ============


@web_bp.get("/")
def index():
    products = db.query("SELECT id, name, price, stock FROM products ORDER BY id")
    return render_template(
        "index.html",
        products=products,
        active="index",
        hot=products[:4],
    )


# ============ 搜索 ============


@web_bp.get("/search")
def search():
    q = (request.args.get("q") or "").strip()
    if q:
        # 故意用 LIKE 模糊匹配：功能测试可以覆盖「搜不到」「特殊字符」「超长关键词」
        products = db.query(
            "SELECT id, name, price, stock FROM products WHERE name LIKE %s ORDER BY id",
            (f"%{q}%",),
        )
    else:
        products = []
    return render_template(
        "search.html", q=q, products=products, active="search"
    )


# ============ 商品详情 ============


@web_bp.get("/product/<int:pid>")
def product_detail(pid):
    product = db.query_one(
        "SELECT id, name, price, stock FROM products WHERE id=%s", (pid,)
    )
    if product is None:
        return render_template("404.html", msg="商品不存在或已下架"), 404
    return render_template("product.html", p=product, active="index")


# ============ 购物车 ============


@web_bp.post("/cart/add")
def cart_add():
    if not session.get("user_id"):
        return redirect(url_for("web.login", next=request.form.get("next") or "/"))

    uid = session["user_id"]
    product_id = request.form.get("product_id", type=int)
    quantity = request.form.get("quantity", type=int) or 1

    product = db.query_one(
        "SELECT id, stock FROM products WHERE id=%s", (product_id,)
    )
    if product is None:
        flash("商品不存在", "error")
        return redirect(url_for("web.index"))
    if quantity <= 0:
        flash("数量必须大于 0", "error")
        return redirect(url_for("web.product_detail", pid=product_id))

    already = db.query_one(
        "SELECT quantity FROM cart_items WHERE user_id=%s AND product_id=%s",
        (uid, product_id),
    )
    want = quantity + (already["quantity"] if already else 0)
    if want > product["stock"]:
        flash(f"库存不足，当前仅剩 {product['stock']} 件", "error")
        return redirect(url_for("web.product_detail", pid=product_id))

    db.execute(
        """
        INSERT INTO cart_items (user_id, product_id, quantity) VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE quantity = quantity + %s
        """,
        (uid, product_id, quantity, quantity),
    )
    flash("已加入购物车", "ok")
    return redirect(url_for("web.cart"))


@web_bp.get("/cart")
@login_required
def cart():
    uid = session["user_id"]
    rows = cart_rows(uid)
    total = sum(float(r["price"]) * r["quantity"] for r in rows)
    return render_template(
        "cart.html", rows=rows, total=total, active="cart"
    )


@web_bp.post("/cart/remove")
@login_required
def cart_remove():
    uid = session["user_id"]
    cart_id = request.form.get("cart_id", type=int)
    db.execute(
        "DELETE FROM cart_items WHERE id=%s AND user_id=%s", (cart_id, uid)
    )
    flash("已删除", "ok")
    return redirect(url_for("web.cart"))


# ============ 提交订单 ============


@web_bp.post("/order/submit")
@login_required
def order_submit():
    """事务：校验库存 → 扣减 → 写订单与明细 → 清购物车；任一步失败整体回滚"""
    uid = session["user_id"]
    rows = cart_rows(uid)
    if not rows:
        flash("购物车是空的", "error")
        return redirect(url_for("web.cart"))

    conn = db.get_conn()
    try:
        validated, total = [], 0.0
        for r in rows:
            p = db.query_one(
                "SELECT id, price, stock FROM products WHERE id=%s FOR UPDATE",
                (r["product_id"],),
                conn,
            )
            if p is None:
                conn.rollback()
                flash("商品不存在，请刷新购物车", "error")
                return redirect(url_for("web.cart"))
            if r["quantity"] > p["stock"]:
                conn.rollback()
                flash(f"「{r['name']}」库存不足，仅剩 {p['stock']} 件", "error")
                return redirect(url_for("web.cart"))
            validated.append((r["product_id"], r["quantity"], float(p["price"])))
            total += float(p["price"]) * r["quantity"]

        for pid, qty, _ in validated:
            db.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s",
                (qty, pid),
                conn,
            )

        order_id = db.execute(
            "INSERT INTO orders (user_id, total_price, status) VALUES (%s, %s, 'created')",
            (uid, total),
            conn,
        )
        for pid, qty, price in validated:
            db.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, price)"
                " VALUES (%s, %s, %s, %s)",
                (order_id, pid, qty, price),
                conn,
            )
        db.execute("DELETE FROM cart_items WHERE user_id = %s", (uid,), conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    flash(f"下单成功，订单号 {order_id}，合计 ￥{total:.2f}", "ok")
    return redirect(url_for("web.orders"))


@web_bp.get("/orders")
@login_required
def orders():
    uid = session["user_id"]
    rows = db.query(
        "SELECT id, total_price, status, created_at FROM orders"
        " WHERE user_id=%s ORDER BY id DESC",
        (uid,),
    )
    detail = {}
    for o in rows:
        detail[o["id"]] = db.query(
            """
            SELECT oi.product_id, oi.quantity, oi.price, p.name
            FROM order_items oi JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id=%s
            """,
            (o["id"],),
        )
    return render_template(
        "orders.html", orders=rows, detail=detail, active="orders"
    )


# ============ 登录 / 退出 ============


@web_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        # 注意：空值、用户不存在、密码错——页面上给同一句提示，避免用户枚举
        if not username or not password:
            flash("用户名或密码错误", "error")
            return render_template("login.html"), 401

        row = db.query_one(
            "SELECT id, password FROM users WHERE username=%s", (username,)
        )
        if row is None or row["password"] != hash_password(password):
            flash("用户名或密码错误", "error")
            return render_template("login.html"), 401

        session["user_id"] = row["id"]
        flash(f"欢迎回来，{username}", "ok")
        target = request.args.get("next") or url_for("web.index")
        # 只允许站内跳转，防开放重定向
        if not target.startswith("/"):
            target = url_for("web.index")
        return redirect(target)

    return render_template("login.html")


@web_bp.get("/logout")
def logout():
    session.clear()
    flash("已退出登录", "ok")
    return redirect(url_for("web.index"))
