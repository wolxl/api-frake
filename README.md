# 淘淘商城 · 接口自动化测试 + 功能测试

[![API Test](https://github.com/wolxl/api-frake/actions/workflows/test.yml/badge.svg)](https://github.com/wolxl/api-frake/actions/workflows/test.yml)

一个可完整跑通的电商测试项目：**自己写被测系统，自己写测试**。包含一条接口自动化测试线（pytest + requests，65 条用例）和一条功能测试线（仿淘宝/京东的服务端渲染前端，可直接点着测）。

- 被测系统：Flask + MySQL 8 实现的商城（10 个业务接口 + 18 个页面路由）
- 测试框架：三层分层（请求层 / 接口层 / 用例层），YAML 数据驱动，三层断言，Allure 报告
- 持续集成：GitHub Actions 11 步流水线，起 MySQL → 灌数据 → 起服务 → 探活 → 跑用例 → 出报告，每天定时执行

---

## 一、两条测试线

| | 接口自动化线 | 功能测试线 |
|---|---|---|
| 被测对象 | `mall_server/app.py`（JSON API） | `mall_server/web.py`（HTML 页面） |
| 测试手段 | pytest + requests | 浏览器手工 / 待补 Selenium |
| 产出 | 65 条用例、Allure 报告、CI 结果 | 测试计划、用例、缺陷报告、测试报告 |
| 覆盖 | 登录、商品 CRUD、购物车、下单、订单查询、契约 | 登录注册、搜索、详情、收藏、购物车、下单、支付/取消/退款、卖家中心 |

两条线共用一套被测系统与一套数据，省掉造数据的工作。

---

## 二、快速开始

### 1. 准备数据库（MySQL 8）

```bash
cd mall_server
mysql -u root -p < schema.sql     # 建库建表（6 张表，含 DROP 可重复执行）
mysql -u root -p < seed.sql       # 种子数据：admin/test 账号、12 件商品
cp config.example.py config.py    # 填入你的 MySQL 密码（config.py 不进仓库）
```

### 2. 装依赖并启动

```bash
pip install -r requirements.txt          # 运行被测系统所需
pip install -r ../requirements-dev.txt   # 跑测试所需（pytest / allure-pytest / cryptography）
python wsgi.py                           # 起服务 http://127.0.0.1:5000
```

> `wsgi.py` 是 CI 与生产入口（关掉 debug 与 reloader）；本地开发也可以用 `python app.py`。

### 3. 跑测试

```bash
python -m pytest testcases -v                 # 全部 65 条
python -m pytest testcases -q --alluredir=allure-results
```

### 4. 一键复现整条 CI（本地）

```powershell
powershell -File ci_local.ps1 -MysqlPassword "你的密码"
```

脚本会依次：装依赖 → 重建数据库 → 生成 config → 起服务并探活 → 跑用例 → 生成 Allure 报告。

---

## 三、目录结构

```
api-frake/
├── base/
│   └── base_request.py      # 请求层：统一 baseURL / 超时 / 日志 / token 注入
├── api/
│   └── mall_api.py          # 接口层：一个方法对应一个业务接口
├── testcases/
│   ├── conftest.py          # token(session) / api / anon 三个 fixture，失败自动挂响应
│   ├── test_product.py      # 商品模块 36 条
│   ├── test_cart_order.py   # 购物车 + 订单 20 条
│   ├── test_contract.py     # 契约测试 8 条（字段类型/必填/枚举）
│   └── test_final.py        # 全链路 1 条（登录→加购→下单→查订单）
├── data/                    # YAML 测试数据（正常值 / 异常值 / 边界值）
├── common/                  # 断言封装
├── mall_server/             # 被测系统
│   ├── app.py               # 业务接口（JSON API）+ /api/health
│   ├── web.py               # 页面路由（Blueprint，服务端渲染）
│   ├── wsgi.py              # 生产/CI 启动入口
│   ├── db.py                # PyMySQL 连接与查询封装
│   ├── schema.sql           # 建表（users/products/cart_items/orders/order_items/favorites）
│   ├── seed.sql             # 种子数据（12 件商品、admin/test 账号）
│   ├── templates/           # 11 个 Jinja2 模板
│   └── static/              # style.css
├── performance/             # JMeter 压测脚本
├── .github/workflows/test.yml  # CI：11 步
└── ci_local.ps1             # 本地复现 CI
```

---

## 四、被测系统

### 业务接口（10 个）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查（无鉴权，供 CI 探活） |
| POST | `/api/login` | 登录，返回 token |
| GET | `/api/products` | 商品列表 |
| GET | `/api/products/{id}` | 商品详情 |
| POST | `/api/products` | 新增商品 |
| PUT | `/api/products/{id}` | 修改商品 |
| DELETE | `/api/products/{id}` | 删除商品 |
| POST | `/api/cart` | 加入购物车（校验库存） |
| GET | `/api/cart` | 查看购物车 |
| POST | `/api/orders` | 提交订单（事务内校验并扣减库存） |
| GET | `/api/orders/{id}` | 查询订单 |

### 页面路由（18 个，用于功能测试）

首页（分页 8 件/页）、搜索、商品详情、注册、登录、登出、购物车（改数量/删除）、提交订单、订单列表、订单支付、取消、申请退款、收藏夹、收藏切换、卖家中心、404。

---

## 五、框架设计

### 三层分工

```
testcases/  →  只写断言和测试逻辑
   ↓
api/        →  业务接口，一个方法对应一个接口
   ↓
base/       →  只负责发请求：baseURL、超时、日志、token
```

改结构不动用例，改用例不动结构。

### fixture 设计

| fixture | 作用域 | 作用 |
|---|---|---|
| `token` | session | 登录一次，全流程复用 |
| `api` | function | 已带 token 的客户端 |
| `anon` | function | 不带 token 的客户端（测未授权场景） |

`pytest_runtest_makereport` 钩子会在用例失败时把请求/响应挂进报告，排查不用翻日志。

### 三层断言

```python
assert r.status_code == 200          # ① HTTP 层：通信是否成功
assert body["code"] == 0             # ② 业务层：业务是否成功
assert body["data"]["total"] == 12   # ③ 数据层：字段值是否正确
```

只断言状态码会被开发糊弄——接口返回 200 但业务码是 500 的情况真实存在。部分用例还有**第四层：数据库二次断言**，直接查 MySQL 确认落库结果。

### 数据驱动

异常与边界数据放在 `data/*.yaml`，用例用 `@pytest.mark.parametrize` 读取，一组数据一条用例：

```yaml
- name: 密码错误
  username: test
  password: wrong_pass
  expect_code: 401
```

---

## 六、测试覆盖（65 条）

| 模块 | 条数 | 覆盖场景 |
|---|---|---|
| 商品 | 36 | 增删改查、字段校验、非法价格/库存、数据闭环 |
| 购物车 + 订单 | 20 | 加购累加、超库存、非法数量、总价校验、下单扣库存、订单查询 |
| 契约 | 8 | 字段类型、必填项、枚举值、响应结构稳定性 |
| 全链路 | 1 | 登录 → 加购 → 下单 → 查订单 |

设计口径：每个接口按 **正常流 / 异常流 / 边界值 / 权限校验** 四维覆盖。

---

## 七、CI 流水线（11 步）

`.github/workflows/test.yml`：

1. 拉代码
2. 装 Python（带 pip 缓存）
3. 装依赖
4. 初始化 MySQL 并灌种子数据
5. 生成 `config.py`
6. 启动被测服务 + `/api/health` 探活（起不来直接 `exit 1`）
7. 跑 pytest（`--junitxml` + `--alluredir`）
8. 失败时打印断言详情与 app.log
9. 生成 Allure HTML 报告
10. 上传报告 artifact
11. 发布到 GitHub Pages

同时配了 `schedule: cron "0 1 * * *"`（北京时间每天 09:00 定时跑）。

### 一个真实踩过的坑

最初探活用的是业务接口 `/api/products`——它需要 token，未登录返回 401，`curl -sf` 判失败，循环空转 30 秒；而且脚本没有 `exit 1`，会继续跑到用例里（用例自己登录后能过），于是 CI **时红时绿**。

修法：加一个无鉴权的 `/api/health`，探活失败就 `exit 1`，把所有不稳定挡在测试之前。

---

## 八、发现过的真实缺陷

**登录接口空值鉴权绕过**

```
POST /api/login
{"username": null, "password": null}
→ 200 {"code": 0, "token": "..."}
```

原因：后端用 `users.get(None) != None` 判空，`None != None` 为 False，被当作校验通过。

**修复**：登录前显式判空，空值统一返回 401。

这个缺陷是用「边界值 + 异常值」两条用例找到的，也成了后来注册/登录接口必测的固定项。

---

## 九、已知限制

- 用例之间存在数据依赖（共用同一套种子数据），暂未做库级隔离，跑前需重置数据库
- `base_request.py` 的 baseURL 目前写死，未接多环境配置切换
- 功能测试线还没有 Selenium 自动化，当前靠手工执行
- GitHub Pages 需要在仓库 Settings → Pages 里把 Source 设为 `gh-pages` 分支，才能在线看 Allure 报告
