"""MySQL 连接与查询封装（pymysql）"""

import pymysql
from pymysql.cursors import DictCursor

from config import DB_CONFIG


def get_conn():
    """创建一个新连接，事务手动控制（autocommit=False）"""
    return pymysql.connect(
        **DB_CONFIG,
        cursorclass=DictCursor,
        autocommit=False,
    )


def query(sql, args=None, conn=None):
    """查询多行；不传 conn 时自动开/关连接"""
    c = conn or get_conn()
    try:
        with c.cursor() as cur:
            cur.execute(sql, args or ())
            return cur.fetchall()
    finally:
        if conn is None:
            c.close()


def query_one(sql, args=None, conn=None):
    """查询单行，没有则返回 None"""
    rows = query(sql, args, conn)
    return rows[0] if rows else None


def execute(sql, args=None, conn=None):
    """执行 INSERT/UPDATE/DELETE；不传 conn 时自动提交，返回 lastrowid"""
    c = conn or get_conn()
    try:
        with c.cursor() as cur:
            cur.execute(sql, args or ())
            if conn is None:
                c.commit()
            return cur.lastrowid
    finally:
        if conn is None:
            c.close()
