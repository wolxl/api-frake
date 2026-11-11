-- 种子数据（初始化账号和商品）
-- 说明：schema.sql 已删表重建，这里只需清空并重灌，顺序按外键依赖
USE mall;

DELETE FROM order_items;
DELETE FROM orders;
DELETE FROM cart_items;
DELETE FROM favorites;
DELETE FROM products;
DELETE FROM users;

-- 账号密码均为 123456（sha256 哈希存储）
INSERT INTO users (username, password) VALUES
('admin', SHA2('123456', 256)),
('test',  SHA2('123456', 256));

-- 商品：12 件（超过一页 8 件，才能测分页；id 1/2 与原有保持一致，保证接口用例可复用）
INSERT INTO products (name, price, stock) VALUES
('无线蓝牙耳机',      199.00, 100),
('机械键盘',          399.00,  50),
('智能手机 Pro',     3299.00,  20),
('笔记本电脑 14寸',  4599.00,  15),
('27寸显示器',        899.00,  30),
('无线鼠标',           89.00, 200),
('蓝牙音箱',          259.00,  60),
('充电宝 20000mAh',   129.00, 120),
('平板电脑',         2199.00,  25),
('智能手表',          899.00,  40),
('家用路由器',        199.00,  80),
('车载充电器',         49.00, 300);
