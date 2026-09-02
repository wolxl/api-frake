# 商城系统全流程接口自动化测试框架

基于 Python + pytest 的接口自动化测试框架，覆盖"登录 → 商品管理 → 购物车 → 下单（含库存校验）→ 订单查询"完整电商业务链路。

## 技术栈

Python · pytest · requests · yaml · Allure · Docker · GitHub Actions · Jenkins

## 目录结构

```
├── base/          # 请求封装层：get/post/put/delete、token 注入
├── api/           # 接口层：每个接口一个方法（MallApi）
├── data/          # 测试数据（yaml 数据驱动）
├── testcases/     # 用例层：商品 / 购物车 / 订单 / 全流程
├── mall_server/   # 待测系统（Flask 在线商城 API）
└── .github/       # CI 工作流
```

## 待测系统接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/login | 登录，返回 token |
| GET/POST | /api/products | 商品列表 / 新增商品 |
| GET/PUT/DELETE | /api/products/{id} | 商品详情 / 修改 / 删除 |
| POST/GET | /api/cart | 加购（校验库存）/ 查看购物车 |
| POST | /api/orders | 提交订单（校验并扣减库存） |
| GET | /api/orders/{id} | 查询订单 |

## 快速开始

### 方式一：Docker 启动待测系统（推荐）

```bash
docker build -t mall mall_server/
docker run -d -p 5000:5000 --name mall mall_server
```

### 方式二：本地启动

```bash
cd mall_server
pip install -r requirements.txt
python app.py
```

### 运行测试

```bash
python -m pytest testcases -v
```

## 测试覆盖（55+ 条用例）

每个接口按四个维度设计：**正常流 / 异常流 / 边界值 / 权限校验**。

| 模块 | 覆盖场景 |
|---|---|
| 登录 | 正确/错误密码/用户不存在/空值/空请求体 |
| 商品管理 | 增删改查、字段校验、非法价格/库存、数据闭环 |
| 购物车 | 加购累加、非法数量、商品不存在、**超库存加购** |
| 订单 | 总价校验、下单清空购物车、**下单扣库存**、订单查询 |

特点：

- **数据驱动**：测试数据存 yaml，数据与代码分离，改数据不改代码
- **数据隔离**：修改/删除类用例只操作自己新建的数据，互不污染
- **四层断言**：状态码 → 业务码 → 关键字段 → 错误信息
- **库存闭环**：加购/下单均校验库存，下单成功自动扣减库存

## 发现的真实 Bug

通过空值边界用例发现登录接口鉴权漏洞：

> 请求体传 `{"username": null, "password": null}` 时，后端 `users.get(None) != None` 判断为 False，被当作登录成功返回 token。

修复：登录前增加空值校验，空值统一返回 401。

## CI/CD

- **GitHub Actions**：代码 push 到 main 分支自动执行测试
- **Jenkins**：本地 Jenkins 定时构建，自动拉代码 → 启动待测系统 → 执行全部用例
