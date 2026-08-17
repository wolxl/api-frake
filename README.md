# 电商下单链路接口自动化测试框架

基于 Python + pytest 的接口自动化测试框架，覆盖"登录 → 图书管理 → 购物车 → 下单 → 订单查询"完整业务链路。

## 技术栈

Python · pytest · requests · yaml · Allure · Docker · GitHub Actions · Jenkins

## 目录结构

```
├── base/          # 请求封装层：get/post/put/delete、token 注入
├── api/           # 接口层：每个接口一个方法
├── data/          # 测试数据（yaml 数据驱动）
├── testcases/     # 用例层：业务场景 + 四层断言
├── bookstore/     # 待测系统（Flask 图书商城 API）
└── .github/       # CI 工作流
```

## 快速开始

### 方式一：Docker 启动待测系统（推荐）

```bash
docker build -t bookstore bookstore/
docker run -d -p 5000:5000 --name bookstore bookstore
```

### 方式二：本地启动

```bash
cd bookstore
pip install -r requirements.txt
python app.py
```

### 运行测试

```bash
python -m pytest testcases -v --reruns 2
```

## 测试覆盖（53 条用例）

每个接口按四个维度设计：**正常流 / 异常流 / 边界值 / 权限校验**。

| 接口 | 覆盖场景 |
|---|---|
| 登录 | 正确/错误密码/用户不存在/空值/空请求体 |
| 图书管理 | 增删改查、字段校验、非法价格、数据闭环 |
| 购物车 | 加购累加、非法数量、图书不存在 |
| 订单 | 下单总价校验、下单清空购物车、订单查询 |

特点：

- **数据驱动**：测试数据存 yaml，数据与代码分离，改数据不改代码
- **数据隔离**：修改/删除类用例只操作自己新建的数据，互不污染
- **四层断言**：状态码 → 业务码 → 关键字段 → 错误信息
- **失败重试**：偶发失败自动重跑，避免误报

## 发现的真实 Bug

通过空值边界用例发现登录接口鉴权漏洞：

> 请求体传 `{"username": null, "password": null}` 时，后端 `users.get(None) != None` 判断为 False，被当作登录成功返回 token。

修复：登录前增加空值校验，空值统一返回 401。

## CI/CD

- **GitHub Actions**：代码 push 到 main 分支自动执行测试
- **Jenkins**：本地 Jenkins 定时构建（每天凌晨 2 点），自动拉代码 → 启动待测系统 → 执行 53 条用例
