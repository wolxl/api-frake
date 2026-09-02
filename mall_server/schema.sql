-- 商城数据库建表脚本（MySQL 8.0）
-- 用法: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS mall DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE mall;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(50)  NOT NULL UNIQUE,
    password   VARCHAR(64)  NOT NULL COMMENT 'sha256 哈希，不存明文',
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- 商品表
CREATE TABLE IF NOT EXISTS products (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100)  NOT NULL,
    price      DECIMAL(10,2) NOT NULL,
    stock      INT           NOT NULL DEFAULT 0 COMMENT '库存',
    created_at TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

-- 购物车表（一个用户对一件商品只有一行，重复加购累加数量）
CREATE TABLE IF NOT EXISTS cart_items (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    product_id INT NOT NULL,
    quantity   INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_product (user_id, product_id),
    FOREIGN KEY (user_id)    REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 订单主表
CREATE TABLE IF NOT EXISTS orders (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    total_price  DECIMAL(10,2) NOT NULL COMMENT '订单总金额',
    status       VARCHAR(20) NOT NULL DEFAULT 'created',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 订单明细表（一个订单对应多个商品；price 存下单时价格快照）
CREATE TABLE IF NOT EXISTS order_items (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    order_id   INT NOT NULL,
    product_id INT NOT NULL,
    quantity   INT NOT NULL,
    price      DECIMAL(10,2) NOT NULL COMMENT '下单时单价快照',
    FOREIGN KEY (order_id)   REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
