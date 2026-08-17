# 1. 基础镜像：自带 Python 3.11 环境的"空房子"（用 1ms.run 加速器，绕开 Docker Hub）
FROM docker.1ms.run/library/python:3.11-slim

# 2. 设置容器里的工作目录（进去就在这个目录）
WORKDIR /app

# 3. 先复制依赖清单，再安装依赖（利用缓存，改代码不用重装）
COPY requirements.txt .
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 复制代码进容器
COPY app.py .

# 5. 告诉 Docker 这个容器要开 5000 端口
EXPOSE 5000

# 6. 容器启动时执行的命令
CMD ["python", "app.py"]
