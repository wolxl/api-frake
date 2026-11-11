"""WSGI 入口 —— 给 CI / 生产环境用。

和 `python app.py` 的区别：
  - debug=False、use_reloader=False
    （debug 模式会开 reloader，一个进程变两个，后台跑时容易起不来或跑一半重启）
  - host / port 从环境变量读，方便换环境

本地开发仍然用 `python app.py`（默认 debug 开、改代码自动重启）。
"""

import os

from app import app

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
        use_reloader=False,
    )
