"""接口层：商城每个接口封装成一个方法"""
from base.base_request import BaseRequest


class MallApi:
    def __init__(self, token=""):
        self.req = BaseRequest(token)

    # 登录
    def login(self, username, password):
        return self.req.post(
            "/api/login",
            {"username": username, "password": password},
        )

    # 商品：列表 / 详情 / 新增 / 修改 / 删除
    def list_products(self):
        return self.req.get("/api/products")

    def get_product(self, product_id):
        return self.req.get(f"/api/products/{product_id}")

    def add_product(self, data):
        """新增商品：data 形如 {"name": "...", "price": 99.0, "stock": 10}"""
        return self.req.post("/api/products", data)

    def update_product(self, product_id, data):
        """修改商品：data 可含 name/price/stock"""
        return self.req.put(f"/api/products/{product_id}", data)

    def delete_product(self, product_id):
        return self.req.delete(f"/api/products/{product_id}")

    # 购物车
    def add_to_cart(self, product_id, quantity):
        return self.req.post("/api/cart", {"product_id": product_id, "quantity": quantity})

    def get_cart(self):
        return self.req.get("/api/cart")

    # 订单
    def create_order(self, items):
        """提交订单：items 形如 [{"product_id": 1, "quantity": 2}]"""
        return self.req.post("/api/orders", {"items": items})

    def get_order(self, order_id):
        return self.req.get(f"/api/orders/{order_id}")
