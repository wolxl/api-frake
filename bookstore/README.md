# 待测系统：图书管理 API

这是一个故意写得很简单的图书管理系统，**专门用来给你练接口测试**。
它只有 6 个接口，包含真实项目最常见的要素：登录、鉴权（token）、增删改查、异常返回。

## 怎么跑起来（第 1 课核心动作）

### 1. 装 Python 依赖（只需要装一次）

打开命令行（Windows 按 `Win+R` 输入 `cmd`），进入本目录：

```bash
cd 你的路径\test-dev-camp\bookstore
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python app.py
```

看到下面这行就说明成功了：

```
Running on http://127.0.0.1:5000
```

**注意：启动后这个窗口不要关**，关了服务就停了。测试完要关闭就按 `Ctrl+C`。

### 3. 验证

打开浏览器访问 [http://127.0.0.1:5000/api/books](http://127.0.0.1:5000/api/books)，会看到：

```json
{"code": 401, "message": "未登录或token失效"}
```

这是**正确的**——因为访问图书列表需要登录。这就叫"鉴权"，是接口测试要测的第一件事。

## 接口文档（6 个接口全在这）

| 方法 | 地址 | 说明 | 是否要登录 |
|---|---|---|---|
| POST | /api/login | 登录，返回 token | 否 |
| GET | /api/books | 获取图书列表 | 是 |
| GET | /api/books/1 | 获取 id=1 的图书 | 是 |
| POST | /api/books | 新增图书 | 是 |
| PUT | /api/books/1 | 修改 id=1 的图书 | 是 |
| DELETE | /api/books/1 | 删除 id=1 的图书 | 是 |

登录账号（写死在系统里）：

```
用户名：admin   密码：123456
```

## 常见问题

- **端口被占用**：换个端口，运行 `python app.py` 前先杀掉占用 5000 端口的程序，或把 `app.py` 最后一行改成 `app.run(port=5001)`。
- **pip 报错**：先升级 `python -m pip install --upgrade pip` 再装。
- **中文乱码**：Windows 命令行先执行 `chcp 65001`。

