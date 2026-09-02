-- 种子数据（初始化账号和商品）
USE mall;

-- 账号密码均为 123456（sha256 哈希存储）
INSERT IGNORE INTO users (username, password) VALUES
('admin', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92'),
('test',  '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92');

-- 商品（id 1/2 与原有内存版一致，保证测试用例可复用）
INSERT IGNORE INTO products (name, price, stock) VALUES
('无线蓝牙耳机', 199.00, 100),
('机械键盘',     399.00, 50);
