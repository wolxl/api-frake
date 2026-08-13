

import requests
BASE_URL = "http://127.0.0.1:5000"

class BaseRequest:
    def __init__(self,token=""):

        if token:
            self.headers = {"Authorization": "Bearer " + token}
        else:
            self.headers = {}
    def get(self,path):
        url=f"{BASE_URL}{path}"
        resp=requests.get(url,headers=self.headers,timeout=10)
        return resp
    def post(self,path,data=None):
        url=f"{BASE_URL}{path}"
        resp=requests.post(url,json=data,headers=self.headers,timeout=10)
        return resp
    def put(self,path,data=None):
        url=f"{BASE_URL}{path}"
        resp=requests.put(url,json=data,headers=self.headers,timeout=10)
        return resp
    def delete(self,path):
        url=f"{BASE_URL}{path}"
        resp=requests.delete(url,headers=self.headers,timeout=10)
        return resp