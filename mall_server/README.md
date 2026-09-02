# 待测系统：在线商城 API

一个用于接口测试练习的 Flask 在线商城服务（内存存储，重启清空）。

## 启动

```bash
pip install -r requirements.txt
python app.py
```

## 接口一览

| 方法 | 路径 | 说明 | 需要登录 |
|---|---|---|---|
| POST | /api/login | 登录，返回 token | 否 |
| GET/POST | /api/products | 商品列表 / 新增商品 | 是 |
| GET/PUT/DELETE | /api/products/{id} | 商品详情 / 修改 / 删除 | 是 |
| POST/GET | /api/cart | 加购（校验库存）/ 查看购物车 | 是 |
| POST | /api/orders | 提交订单（校验并扣减库存） | 是 |
| GET | /api/orders/{id} | 查询订单 | 是 |

登录账号：`admin / 123456`
