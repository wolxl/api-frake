"""商城 Web 前端（服务端渲染）+ 页面路由

存在理由：接口测试只能证明「JSON 返回对不对」，证明不了「用户在页面上能不能走完一单」。
本模块给同一个被测系统补一条功能测试线，页面直接读写同一套表，因此可以做跨层校验：
    页面上加购 → 调 GET /api/cart 能查到 → 「前端操作 + 接口断言」两端对齐。

页面清单：
    GET  /                      首页（分类 + 商品列表 + 分页）
    GET  /search?q=&page=       搜索结果（分页）
    GET  /product/<pid>         商品详情
    GET  /register              注册页
    POST /register              提交注册
    GET  /login                 登录页
    POST /login                 提交登录
    GET  /logout                退出
    POST /cart/add              加入购物车
    GET  /cart                  购物车
    POST /cart/update           修改购物车数量
    POST /cart/remove           删除购物车行
    POST /order/submit          提交订单（事务）
    GET  /orders                我的订单
    POST /order/<oid>/pay       支付订单
    POST /order/<oid>/cancel    取消订单（回滚库存）
    POST /order/<oid>/refund    退款（回滚库存）
    GET  /favorites             我的收藏
    POST /favorite/toggle       收藏 / 取消收藏
    GET  /seller                卖家中心（商品与库存一览）

订单状态流转：
    created(待支付) --支付--> paid(已支付) --退款--> refunded(已退款)
    created(待支付) --取消--> cancelled(已取消)，取消与退款都会把库存加回去
"""

import hashlib
import re
from functools import wraps
from urllib.parse import urlencode

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)

import db

web_bp = Blueprint(
    "web", __name__, template_folder="templates", static_folder="static"
)

PAGE_SIZE = 8          # 每页商品数
MAX_CART_QTY = 99      # 单个商品单次最多购买数量
STATUS_CN = {
    "created": "待支付",
    "paid": "已支付",
    "cancelled": "已取消",
    "refunded": "已退款",
}

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


def fav_ids(user_id):
    """当前用户收藏的商品 id 集合，模板里用来切换「已收藏/收藏」"""
    if not user_id:
        return set()
    rows = db.query("SELECT product_id FROM favorites WHERE user_id=%s", (user_id,))
    return {r["product_id"] for r in rows}


def page_window(total, page):
    """返回 (页码, 总页数)，页码越界自动夹紧"""
    pages = max(1, (int(total) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(int(page or 1), pages))
    return page, pages


def query_page(where_sql, params, page):
    """分页查询商品：先算总数，再按 LIMIT/OFFSET 取当页"""
    cond = f" WHERE {where_sql}" if where_sql else ""
    total = db.query_one(f"SELECT COUNT(*) AS n FROM products{cond}", params)["n"]
    page, pages = page_window(total, page)
    rows = db.query(
        f"SELECT id, name, price, stock FROM products{cond} ORDER BY id LIMIT %s OFFSET %s",
        tuple(params) + (PAGE_SIZE, (page - 1) * PAGE_SIZE),
    )
    return rows, page, pages, int(total)


def back_url(default="/"):
    """表单里带的 next，只允许站内路径，防开放重定向"""
    target = request.form.get("next") or default
    return target if target.startswith("/") else default


@web_bp.app_context_processor
def inject_globals():
    """所有模板都能拿到 user 与购物车数量"""
    user = current_user()
    return {
        "user": user,
        "cart_badge": cart_badge(user["id"]) if user else 0,
    }


@web_bp.app_template_global("page_url")
def page_url(n):
    """分页链接：保留当前查询参数（比如搜索词），只改 page"""
    args = request.args.to_dict()
    args["page"] = n
    return f"{request.path}?{urlencode(args)}"


@web_bp.app_template_filter("status_cn")
def status_filter(status: str) -> str:
    return STATUS_CN.get(status, status)


# 商品名 → emoji（没有图片资源，用色块 + emoji 当商品图，测试点不受影响）
_EMOJI = [
    ("耳机", "🎧"), ("键盘", "⌨️"), ("手机", "📱"), ("笔记本", "💻"),
    ("显示器", "🖥️"), ("鼠标", "🖱️"), ("音箱", "🔊"), ("音响", "🔊"),
    ("充电宝", "🔋"), ("平板", "📱"), ("手表", "⌚"), ("相机", "📷"),
    ("路由", "📶"), ("充电器", "🔌"),
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
    products, page, pages, total = query_page(
        "", (), request.args.get("page", 1, type=int)
    )
    user = current_user()
    return render_template(
        "index.html",
        products=products,
        page=page,
        pages=pages,
        total=total,
        favs=fav_ids(user["id"]) if user else set(),
        active="index",
    )


# ============ 搜索 ============


@web_bp.get("/search")
def search():
    q = (request.args.get("q") or "").strip()
    if q:
        products, page, pages, total = query_page(
            "name LIKE %s", (f"%{q}%",), request.args.get("page", 1, type=int)
        )
    else:
        products, page, pages, total = [], 1, 1, 0
    user = current_user()
    return render_template(
        "search.html",
        q=q,
        products=products,
        page=page,
        pages=pages,
        total=total,
        favs=fav_ids(user["id"]) if user else set(),
        active="search",
    )


# ============ 商品详情 ============


@web_bp.get("/product/<int:pid>")
def product_detail(pid):
    product = db.query_one(
        "SELECT id, name, price, stock FROM products WHERE id=%s", (pid,)
    )
    if product is None:
        return render_template("404.html", msg="商品不存在或已下架"), 404
    user = current_user()
    return render_template(
        "product.html",
        p=product,
        active="index",
        fav=(product["id"] in fav_ids(user["id"])) if user else False,
    )


# ============ 收藏 ============


@web_bp.get("/favorites")
@login_required
def favorites():
    uid = session["user_id"]
    rows = db.query(
        """
        SELECT f.product_id, p.name, p.price, p.stock
        FROM favorites f JOIN products p ON p.id = f.product_id
        WHERE f.user_id = %s ORDER BY f.id DESC
        """,
        (uid,),
    )
    return render_template("favorites.html", rows=rows, active="fav")


@web_bp.post("/favorite/toggle")
@login_required
def favorite_toggle():
    uid = session["user_id"]
    pid = request.form.get("product_id", type=int)
    product = db.query_one("SELECT id, name FROM products WHERE id=%s", (pid,))
    if product is None:
        flash("商品不存在", "error")
        return redirect(back_url())

    if pid in fav_ids(uid):
        db.execute(
            "DELETE FROM favorites WHERE user_id=%s AND product_id=%s", (uid, pid)
        )
        flash(f"已取消收藏「{product['name']}」", "ok")
    else:
        db.execute(
            "INSERT INTO favorites (user_id, product_id) VALUES (%s, %s)", (uid, pid)
        )
        flash(f"已收藏「{product['name']}」", "ok")
    return redirect(back_url())


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
    if quantity > MAX_CART_QTY:
        flash(f"单个商品单次最多购买 {MAX_CART_QTY} 件", "error")
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


@web_bp.post("/cart/update")
@login_required
def cart_update():
    """修改购物车数量：1 ~ min(库存, 99)"""
    uid = session["user_id"]
    cart_id = request.form.get("cart_id", type=int)
    quantity = request.form.get("quantity", type=int)

    row = db.query_one(
        """
        SELECT c.id, c.product_id, p.name, p.stock
        FROM cart_items c JOIN products p ON p.id = c.product_id
        WHERE c.id=%s AND c.user_id=%s
        """,
        (cart_id, uid),
    )
    if row is None:
        flash("购物车记录不存在", "error")
        return redirect(url_for("web.cart"))

    if quantity is None:
        flash("数量必须是数字", "error")
        return redirect(url_for("web.cart"))
    if quantity <= 0:
        flash("数量必须大于 0，想删除请点删除", "error")
        return redirect(url_for("web.cart"))
    if quantity > MAX_CART_QTY:
        flash(f"单个商品最多购买 {MAX_CART_QTY} 件", "error")
        return redirect(url_for("web.cart"))
    if quantity > row["stock"]:
        flash(f"「{row['name']}」库存不足，仅剩 {row['stock']} 件", "error")
        return redirect(url_for("web.cart"))

    db.execute(
        "UPDATE cart_items SET quantity=%s WHERE id=%s AND user_id=%s",
        (quantity, cart_id, uid),
    )
    flash("数量已更新", "ok")
    return redirect(url_for("web.cart"))


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

    flash(f"下单成功，订单号 {order_id}，合计 ￥{total:.2f}，请尽快支付", "ok")
    return redirect(url_for("web.orders"))


# ============ 订单状态操作 ============


def _own_order(order_id):
    """只允许操作自己的订单；别人的订单一律当不存在"""
    return db.query_one(
        "SELECT id, status, total_price FROM orders WHERE id=%s AND user_id=%s",
        (order_id, session["user_id"]),
    )


def _return_stock(order_id, conn):
    """把订单里的商品数量加回库存（取消/退款共用）"""
    items = db.query(
        "SELECT product_id, quantity FROM order_items WHERE order_id=%s",
        (order_id,),
        conn,
    )
    for it in items:
        db.execute(
            "UPDATE products SET stock = stock + %s WHERE id=%s",
            (it["quantity"], it["product_id"]),
            conn,
        )


@web_bp.post("/order/<int:oid>/pay")
@login_required
def order_pay(oid):
    order = _own_order(oid)
    if order is None:
        flash("订单不存在", "error")
        return redirect(url_for("web.orders"))
    if order["status"] != "created":
        flash(f"订单当前状态是「{STATUS_CN.get(order['status'])}」，不能支付", "error")
        return redirect(url_for("web.orders"))

    db.execute(
        "UPDATE orders SET status='paid', paid_at=NOW() WHERE id=%s AND user_id=%s",
        (oid, session["user_id"]),
    )
    flash(f"支付成功，订单 ￥{float(order['total_price']):.2f}", "ok")
    return redirect(url_for("web.orders"))


@web_bp.post("/order/<int:oid>/cancel")
@login_required
def order_cancel(oid):
    order = _own_order(oid)
    if order is None:
        flash("订单不存在", "error")
        return redirect(url_for("web.orders"))
    if order["status"] != "created":
        flash("只有待支付的订单能取消", "error")
        return redirect(url_for("web.orders"))

    conn = db.get_conn()
    try:
        _return_stock(oid, conn)
        db.execute(
            "UPDATE orders SET status='cancelled' WHERE id=%s AND user_id=%s",
            (oid, session["user_id"]),
            conn,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    flash("订单已取消，库存已退回", "ok")
    return redirect(url_for("web.orders"))


@web_bp.post("/order/<int:oid>/refund")
@login_required
def order_refund(oid):
    order = _own_order(oid)
    if order is None:
        flash("订单不存在", "error")
        return redirect(url_for("web.orders"))
    if order["status"] != "paid":
        flash("只有已支付的订单能退款", "error")
        return redirect(url_for("web.orders"))

    conn = db.get_conn()
    try:
        _return_stock(oid, conn)
        db.execute(
            "UPDATE orders SET status='refunded' WHERE id=%s AND user_id=%s",
            (oid, session["user_id"]),
            conn,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    flash("退款成功，库存已退回", "ok")
    return redirect(url_for("web.orders"))


@web_bp.get("/orders")
@login_required
def orders():
    uid = session["user_id"]
    rows = db.query(
        "SELECT id, total_price, status, created_at, paid_at FROM orders"
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


# ============ 卖家中心 ============


@web_bp.get("/seller")
@login_required
def seller():
    """卖家中心：只读的商品与库存一览（这个系统没有真正的后台权限模型）"""
    rows = db.query("SELECT id, name, price, stock FROM products ORDER BY id")
    return render_template("seller.html", rows=rows, active="seller")


# ============ 注册 / 登录 / 退出 ============

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


@web_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""

        if not USERNAME_RE.match(username):
            flash("用户名需 3-20 位，只能是字母、数字或下划线", "error")
        elif len(password) < 6 or len(password) > 20:
            flash("密码长度需 6-20 位", "error")
        elif not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
            flash("密码必须同时包含字母和数字", "error")
        elif password != confirm:
            flash("两次输入的密码不一致", "error")
        elif db.query_one("SELECT id FROM users WHERE username=%s", (username,)):
            flash("用户名已被占用", "error")
        else:
            db.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hash_password(password)),
            )
            flash(f"注册成功，请登录：{username}", "ok")
            return redirect(url_for("web.login"))

        return render_template("register.html"), 400

    return render_template("register.html")


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
