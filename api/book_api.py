from base.base_request import BaseRequest

class BookApi:
    def __init__(self,token=""):
        self.req=BaseRequest(token)

    def login(self,username,password):
        return self.req.post(
            "/api/login",
            {"username":username,"password":password})
    def list_books(self):
        return self.req.get(
            "/api/books",
        )
    def get_book(self,book_id):
        return self.req.get(
            f"/api/books/{book_id}",
        )

    def add_book(self, data):
        """新增图书"""
        return self.req.post("/api/books", data)

    def update_book(self, book_id, data):
        """修改图书"""
        return self.req.put(f"/api/books/{book_id}", data)

    def delete_book(self, book_id):
        """删除图书"""
        return self.req.delete(f"/api/books/{book_id}")

    def add_to_cart(self, book_id, quantity):
        """加入购物车"""
        return self.req.post("/api/cart", {"book_id": book_id, "quantity": quantity})

    def get_cart(self):
        """查看购物车"""
        return self.req.get("/api/cart")

    def create_order(self, items):
        """提交订单：items 形如 [{"book_id": 1, "quantity": 2}]"""
        return self.req.post("/api/orders", {"items": items})

    def get_order(self, order_id):
        """查询订单"""
        return self.req.get(f"/api/orders/{order_id}")
