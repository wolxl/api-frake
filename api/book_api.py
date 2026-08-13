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