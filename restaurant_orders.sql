-- ========================================================
-- 智慧餐饮订单与 BI 结算系统真实数据 DDL 及 DML (MySQL/SQLite兼容)
-- 生成时间: 2026-09-19 12:49:53
-- ========================================================


-- 1. 订单主表
CREATE TABLE IF NOT EXISTS t_order (
    order_sn VARCHAR(64) PRIMARY KEY,
    store_id VARCHAR(32) NOT NULL,
    table_id VARCHAR(32) NOT NULL,
    period VARCHAR(16) NOT NULL,              -- BREAKFAST, LUNCH, DINNER, NIGHT
    people_count INT NOT NULL DEFAULT 1,
    original_total DECIMAL(10, 2) NOT NULL,   -- 菜品原价合计
    discount_amount DECIMAL(10, 2) NOT NULL,  -- 优惠券抵扣
    coupon_name VARCHAR(64) DEFAULT '无',
    tableware_fee DECIMAL(10, 2) NOT NULL,    -- 餐位费 (每人3元)
    actual_pay DECIMAL(10, 2) NOT NULL,       -- 实付 = 原价 - 优惠 + 餐位费
    status VARCHAR(20) NOT NULL,              -- PENDING_PAY, PAID, PRINTED, COMPLETED, CANCELLED
    pay_channel VARCHAR(32) NOT NULL,         -- 微信支付, 支付宝, 会员卡余额, 待支付, 已取消
    kitchen_printed TINYINT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    paid_at DATETIME NULL
);

-- 2. 订单菜品明细表
CREATE TABLE IF NOT EXISTS t_order_item (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_sn VARCHAR(64) NOT NULL,
    dish_id VARCHAR(32) NOT NULL,
    dish_name VARCHAR(64) NOT NULL,
    spec_name VARCHAR(32) NOT NULL,           -- 大份, 中份, 标准份, 一笼(6只)
    attributes VARCHAR(64) DEFAULT '',        -- 微辣, 去冰, 少糖
    extras VARCHAR(64) DEFAULT '',            -- 加金针菇, 加香醋
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_sn) REFERENCES t_order (order_sn)
);

-- 3. BI 日营收与对账聚合快照表
CREATE TABLE IF NOT EXISTS t_bi_settlement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stat_date DATE NOT NULL,
    period VARCHAR(16) NOT NULL,
    total_orders INT NOT NULL,                -- 总下单数
    valid_orders INT NOT NULL,                -- 有效入账单数 (PAID/PRINTED/COMPLETED)
    gmv DECIMAL(10, 2) NOT NULL,              -- 实际入账 GMV
    total_discounts DECIMAL(10, 2) NOT NULL,  -- 商家优惠减免
    cancelled_orders INT NOT NULL,            -- 取消/超时单数
    aov DECIMAL(10, 2) NOT NULL               -- 平均客单价
);

-- 创建索引加速查询
CREATE INDEX IF NOT EXISTS idx_order_status ON t_order (status);
CREATE INDEX IF NOT EXISTS idx_order_created_at ON t_order (created_at);
CREATE INDEX IF NOT EXISTS idx_order_item_sn ON t_order_item (order_sn);


-- 插入订单主表记录
INSERT INTO t_order VALUES ('ORD_20260917002914_001', 'store_888', 'table_02', 'LUNCH', 3, 189.0, 0.0, '无', 9.0, 198.0, 'PAID', '支付宝 (Alipay)', 0, '2026-09-17 00:29:14', '2026-09-17 00:31:14');
INSERT INTO t_order VALUES ('ORD_20260916154421_002', 'store_888', 'table_18', 'NIGHT', 4, 304.0, 20.0, '满100减20元券', 12.0, 296.0, 'COMPLETED', '美团买单', 1, '2026-09-16 15:44:21', '2026-09-16 15:47:21');
INSERT INTO t_order VALUES ('ORD_20260917211950_003', 'store_888', 'table_06', 'LUNCH', 5, 72.0, 0.0, '无', 15.0, 87.0, 'COMPLETED', '美团买单', 1, '2026-09-17 21:19:50', '2026-09-17 21:22:50');
INSERT INTO t_order VALUES ('ORD_20260916180745_004', 'store_888', 'table_01', 'BREAKFAST', 5, 65.9, 0.0, '无', 15.0, 80.9, 'PRINTED', '微信支付 (WeChat Pay)', 1, '2026-09-16 18:07:45', '2026-09-16 18:08:45');
INSERT INTO t_order VALUES ('ORD_20260917173126_005', 'store_888', 'table_09', 'BREAKFAST', 1, 152.0, 20.0, '满100减20元券', 3.0, 135.0, 'COMPLETED', '会员卡余额', 1, '2026-09-17 17:31:26', '2026-09-17 17:34:26');
INSERT INTO t_order VALUES ('ORD_20260919085112_006', 'store_888', 'table_06', 'LUNCH', 5, 72.0, 0.0, '无', 15.0, 87.0, 'PENDING_PAY', '待支付', 0, '2026-09-19 08:51:12', NULL);
INSERT INTO t_order VALUES ('ORD_20260918225706_007', 'store_888', 'table_06', 'DINNER', 4, 76.0, 0.0, '无', 12.0, 88.0, 'PRINTED', '微信支付 (WeChat Pay)', 1, '2026-09-18 22:57:06', '2026-09-18 22:58:06');
INSERT INTO t_order VALUES ('ORD_20260917130109_008', 'store_888', 'table_08', 'DINNER', 3, 128.0, 0.0, '无', 9.0, 137.0, 'COMPLETED', '微信支付 (WeChat Pay)', 1, '2026-09-17 13:01:09', '2026-09-17 13:04:09');
INSERT INTO t_order VALUES ('ORD_20260917005015_009', 'store_888', 'table_01', 'NIGHT', 3, 324.0, 50.0, '满200减50元券', 9.0, 283.0, 'COMPLETED', '美团买单', 1, '2026-09-17 00:50:15', '2026-09-17 00:53:15');
INSERT INTO t_order VALUES ('ORD_20260918031821_010', 'store_888', 'table_03', 'NIGHT', 4, 36.0, 0.0, '无', 12.0, 48.0, 'PENDING_PAY', '待支付', 0, '2026-09-18 03:18:21', NULL);
INSERT INTO t_order VALUES ('ORD_20260917111202_011', 'store_888', 'table_22', 'DINNER', 4, 59.8, 0.0, '无', 12.0, 71.8, 'COMPLETED', '会员卡余额', 1, '2026-09-17 11:12:02', '2026-09-17 11:15:02');
INSERT INTO t_order VALUES ('ORD_20260918003951_012', 'store_888', 'table_16', 'BREAKFAST', 4, 244.0, 20.0, '满100减20元券', 12.0, 236.0, 'PRINTED', '支付宝 (Alipay)', 1, '2026-09-18 00:39:51', '2026-09-18 00:40:51');
INSERT INTO t_order VALUES ('ORD_20260919031054_013', 'store_888', 'table_03', 'BREAKFAST', 6, 105.9, 20.0, '满100减20元券', 18.0, 103.9, 'COMPLETED', '会员卡余额', 1, '2026-09-19 03:10:54', '2026-09-19 03:13:54');
INSERT INTO t_order VALUES ('ORD_20260917054350_014', 'store_888', 'table_03', 'NIGHT', 5, 332.0, 50.0, '满200减50元券', 15.0, 297.0, 'PRINTED', '支付宝 (Alipay)', 1, '2026-09-17 05:43:50', '2026-09-17 05:44:50');
INSERT INTO t_order VALUES ('ORD_20260919054108_015', 'store_888', 'table_02', 'BREAKFAST', 1, 235.9, 50.0, '满200减50元券', 3.0, 188.9, 'PAID', '微信支付 (WeChat Pay)', 0, '2026-09-19 05:41:08', '2026-09-19 05:43:08');
INSERT INTO t_order VALUES ('ORD_20260917085548_016', 'store_888', 'table_16', 'LUNCH', 6, 29.9, 0.0, '无', 18.0, 47.9, 'PRINTED', '微信支付 (WeChat Pay)', 1, '2026-09-17 08:55:48', '2026-09-17 08:56:48');
INSERT INTO t_order VALUES ('ORD_20260918213431_017', 'store_888', 'table_18', 'DINNER', 3, 18.0, 0.0, '无', 9.0, 27.0, 'PENDING_PAY', '待支付', 0, '2026-09-18 21:34:31', NULL);
INSERT INTO t_order VALUES ('ORD_20260916231511_018', 'store_888', 'table_06', 'BREAKFAST', 3, 32.0, 0.0, '无', 9.0, 41.0, 'PRINTED', '微信支付 (WeChat Pay)', 1, '2026-09-16 23:15:11', '2026-09-16 23:16:11');
INSERT INTO t_order VALUES ('ORD_20260917003752_019', 'store_888', 'table_09', 'BREAKFAST', 4, 22.0, 0.0, '无', 12.0, 34.0, 'PRINTED', '会员卡余额', 1, '2026-09-17 00:37:52', '2026-09-17 00:38:52');
INSERT INTO t_order VALUES ('ORD_20260918124934_020', 'store_888', 'table_12', 'LUNCH', 4, 161.9, 20.0, '满100减20元券', 12.0, 153.9, 'PAID', '微信支付 (WeChat Pay)', 0, '2026-09-18 12:49:34', '2026-09-18 12:51:34');
INSERT INTO t_order VALUES ('ORD_20260917185239_021', 'store_888', 'table_06', 'BREAKFAST', 5, 36.0, 0.0, '无', 15.0, 51.0, 'COMPLETED', '会员卡余额', 1, '2026-09-17 18:52:39', '2026-09-17 18:55:39');
INSERT INTO t_order VALUES ('ORD_20260918205220_022', 'store_888', 'table_22', 'DINNER', 2, 256.0, 50.0, '满200减50元券', 6.0, 212.0, 'PAID', '支付宝 (Alipay)', 0, '2026-09-18 20:52:20', '2026-09-18 20:54:20');
INSERT INTO t_order VALUES ('ORD_20260918105710_023', 'store_888', 'table_04', 'NIGHT', 6, 245.0, 50.0, '满200减50元券', 18.0, 213.0, 'COMPLETED', '会员卡余额', 1, '2026-09-18 10:57:10', '2026-09-18 11:00:10');
INSERT INTO t_order VALUES ('ORD_20260918000759_024', 'store_888', 'table_02', 'NIGHT', 4, 113.0, 0.0, '无', 12.0, 125.0, 'PRINTED', '微信支付 (WeChat Pay)', 1, '2026-09-18 00:07:59', '2026-09-18 00:08:59');
INSERT INTO t_order VALUES ('ORD_20260919025906_025', 'store_888', 'table_01', 'LUNCH', 5, 22.0, 0.0, '无', 15.0, 37.0, 'COMPLETED', '会员卡余额', 1, '2026-09-19 02:59:06', '2026-09-19 03:02:06');
INSERT INTO t_order VALUES ('ORD_20260919094141_026', 'store_888', 'table_12', 'BREAKFAST', 5, 125.9, 20.0, '满100减20元券', 15.0, 120.9, 'PRINTED', '会员卡余额', 1, '2026-09-19 09:41:41', '2026-09-19 09:42:41');
INSERT INTO t_order VALUES ('ORD_20260917144104_027', 'store_888', 'table_09', 'BREAKFAST', 4, 44.0, 0.0, '无', 12.0, 56.0, 'PAID', '会员卡余额', 0, '2026-09-17 14:41:04', '2026-09-17 14:43:04');
INSERT INTO t_order VALUES ('ORD_20260916144945_028', 'store_888', 'table_02', 'NIGHT', 1, 18.0, 0.0, '无', 3.0, 21.0, 'PRINTED', '微信支付 (WeChat Pay)', 1, '2026-09-16 14:49:45', '2026-09-16 14:50:45');
INSERT INTO t_order VALUES ('ORD_20260917050312_029', 'store_888', 'table_08', 'BREAKFAST', 2, 18.0, 0.0, '无', 6.0, 24.0, 'PRINTED', '微信支付 (WeChat Pay)', 1, '2026-09-17 05:03:12', '2026-09-17 05:04:12');
INSERT INTO t_order VALUES ('ORD_20260916134240_030', 'store_888', 'table_06', 'LUNCH', 3, 392.0, 50.0, '满200减50元券', 9.0, 351.0, 'COMPLETED', '美团买单', 1, '2026-09-16 13:42:40', '2026-09-16 13:45:40');
INSERT INTO t_order VALUES ('ORD_20260919054422_031', 'store_888', 'table_08', 'DINNER', 5, 132.0, 20.0, '满100减20元券', 15.0, 127.0, 'CANCELLED', '已取消(未扣款)', 0, '2026-09-19 05:44:22', NULL);
INSERT INTO t_order VALUES ('ORD_20260917050402_032', 'store_888', 'table_01', 'NIGHT', 6, 76.0, 0.0, '无', 18.0, 94.0, 'COMPLETED', '支付宝 (Alipay)', 1, '2026-09-17 05:04:02', '2026-09-17 05:07:02');
INSERT INTO t_order VALUES ('ORD_20260916162750_033', 'store_888', 'table_08', 'LUNCH', 2, 29.9, 0.0, '无', 6.0, 35.9, 'PAID', '微信支付 (WeChat Pay)', 0, '2026-09-16 16:27:50', '2026-09-16 16:29:50');
INSERT INTO t_order VALUES ('ORD_20260917094515_034', 'store_888', 'table_06', 'DINNER', 4, 358.0, 50.0, '满200减50元券', 12.0, 320.0, 'PRINTED', '微信支付 (WeChat Pay)', 1, '2026-09-17 09:45:15', '2026-09-17 09:46:15');
INSERT INTO t_order VALUES ('ORD_20260918185213_035', 'store_888', 'table_08', 'BREAKFAST', 1, 98.0, 0.0, '无', 3.0, 101.0, 'PENDING_PAY', '待支付', 0, '2026-09-18 18:52:13', NULL);
INSERT INTO t_order VALUES ('ORD_20260916200518_036', 'store_888', 'table_03', 'NIGHT', 4, 36.0, 0.0, '无', 12.0, 48.0, 'PENDING_PAY', '待支付', 0, '2026-09-16 20:05:18', NULL);
INSERT INTO t_order VALUES ('ORD_20260917202314_037', 'store_888', 'table_09', 'LUNCH', 5, 404.0, 20.0, '满100减20元券', 15.0, 399.0, 'PRINTED', '支付宝 (Alipay)', 1, '2026-09-17 20:23:14', '2026-09-17 20:24:14');
INSERT INTO t_order VALUES ('ORD_20260919012152_038', 'store_888', 'table_08', 'LUNCH', 5, 104.0, 20.0, '满100减20元券', 15.0, 99.0, 'COMPLETED', '会员卡余额', 1, '2026-09-19 01:21:52', '2026-09-19 01:24:52');
INSERT INTO t_order VALUES ('ORD_20260919123529_039', 'store_888', 'table_03', 'DINNER', 3, 245.9, 50.0, '满200减50元券', 9.0, 204.9, 'PAID', '会员卡余额', 0, '2026-09-19 12:35:29', '2026-09-19 12:37:29');
INSERT INTO t_order VALUES ('ORD_20260917031906_040', 'store_888', 'table_18', 'DINNER', 5, 72.0, 0.0, '无', 15.0, 87.0, 'COMPLETED', '支付宝 (Alipay)', 1, '2026-09-17 03:19:06', '2026-09-17 03:22:06');
INSERT INTO t_order VALUES ('ORD_20260919123101_041', 'store_888', 'table_01', 'DINNER', 2, 164.0, 20.0, '满100减20元券', 6.0, 150.0, 'PAID', '支付宝 (Alipay)', 0, '2026-09-19 12:31:01', '2026-09-19 12:33:01');
INSERT INTO t_order VALUES ('ORD_20260919121413_042', 'store_888', 'table_04', 'DINNER', 4, 96.0, 0.0, '无', 12.0, 108.0, 'COMPLETED', '微信支付 (WeChat Pay)', 1, '2026-09-19 12:14:13', '2026-09-19 12:17:13');
INSERT INTO t_order VALUES ('ORD_20260918143649_043', 'store_888', 'table_12', 'BREAKFAST', 2, 61.9, 0.0, '无', 6.0, 67.9, 'COMPLETED', '微信支付 (WeChat Pay)', 1, '2026-09-18 14:36:49', '2026-09-18 14:39:49');
INSERT INTO t_order VALUES ('ORD_20260919000100_044', 'store_888', 'table_01', 'BREAKFAST', 5, 113.0, 20.0, '满100减20元券', 15.0, 108.0, 'COMPLETED', '微信支付 (WeChat Pay)', 1, '2026-09-19 00:01:00', '2026-09-19 00:04:00');
INSERT INTO t_order VALUES ('ORD_20260918124848_045', 'store_888', 'table_12', 'LUNCH', 2, 184.0, 20.0, '满100减20元券', 6.0, 170.0, 'COMPLETED', '支付宝 (Alipay)', 1, '2026-09-18 12:48:48', '2026-09-18 12:51:48');
INSERT INTO t_order VALUES ('ORD_20260918214218_046', 'store_888', 'table_22', 'BREAKFAST', 3, 562.0, 20.0, '满100减20元券', 9.0, 551.0, 'PENDING_PAY', '待支付', 0, '2026-09-18 21:42:18', NULL);
INSERT INTO t_order VALUES ('ORD_20260918225325_047', 'store_888', 'table_16', 'LUNCH', 2, 92.0, 0.0, '无', 6.0, 98.0, 'PAID', '会员卡余额', 0, '2026-09-18 22:53:25', '2026-09-18 22:55:25');
INSERT INTO t_order VALUES ('ORD_20260916165701_048', 'store_888', 'table_03', 'DINNER', 1, 171.8, 20.0, '满100减20元券', 3.0, 154.8, 'CANCELLED', '已取消(未扣款)', 0, '2026-09-16 16:57:01', NULL);
INSERT INTO t_order VALUES ('ORD_20260918232412_049', 'store_888', 'table_22', 'NIGHT', 3, 414.0, 20.0, '满100减20元券', 9.0, 403.0, 'COMPLETED', '微信支付 (WeChat Pay)', 1, '2026-09-18 23:24:12', '2026-09-18 23:27:12');
INSERT INTO t_order VALUES ('ORD_20260916183231_050', 'store_888', 'table_04', 'DINNER', 3, 116.0, 0.0, '无', 9.0, 125.0, 'CANCELLED', '已取消(未扣款)', 0, '2026-09-16 18:32:31', NULL);
INSERT INTO t_order VALUES ('ORD_20260918224227_051', 'store_888', 'table_04', 'NIGHT', 4, 32.0, 0.0, '无', 12.0, 44.0, 'COMPLETED', '美团买单', 1, '2026-09-18 22:42:27', '2026-09-18 22:45:27');
INSERT INTO t_order VALUES ('ORD_20260918210821_052', 'store_888', 'table_18', 'LUNCH', 4, 268.0, 50.0, '满200减50元券', 12.0, 230.0, 'COMPLETED', '微信支付 (WeChat Pay)', 1, '2026-09-18 21:08:21', '2026-09-18 21:11:21');
INSERT INTO t_order VALUES ('ORD_20260917140949_053', 'store_888', 'table_02', 'LUNCH', 2, 59.8, 0.0, '无', 6.0, 65.8, 'COMPLETED', '会员卡余额', 1, '2026-09-17 14:09:49', '2026-09-17 14:12:49');
INSERT INTO t_order VALUES ('ORD_20260918160702_054', 'store_888', 'table_03', 'DINNER', 1, 142.0, 0.0, '无', 3.0, 145.0, 'PAID', '支付宝 (Alipay)', 0, '2026-09-18 16:07:02', '2026-09-18 16:09:02');
INSERT INTO t_order VALUES ('ORD_20260918065741_055', 'store_888', 'table_08', 'BREAKFAST', 4, 154.0, 20.0, '满100减20元券', 12.0, 146.0, 'COMPLETED', '美团买单', 1, '2026-09-18 06:57:41', '2026-09-18 07:00:41');
INSERT INTO t_order VALUES ('ORD_20260917110807_056', 'store_888', 'table_03', 'NIGHT', 3, 72.0, 0.0, '无', 9.0, 81.0, 'COMPLETED', '支付宝 (Alipay)', 1, '2026-09-17 11:08:07', '2026-09-17 11:11:07');
INSERT INTO t_order VALUES ('ORD_20260917190030_057', 'store_888', 'table_12', 'BREAKFAST', 5, 152.0, 20.0, '满100减20元券', 15.0, 147.0, 'PENDING_PAY', '待支付', 0, '2026-09-17 19:00:30', NULL);
INSERT INTO t_order VALUES ('ORD_20260918070919_058', 'store_888', 'table_08', 'DINNER', 6, 404.0, 50.0, '满200减50元券', 18.0, 372.0, 'COMPLETED', '美团买单', 1, '2026-09-18 07:09:19', '2026-09-18 07:12:19');
INSERT INTO t_order VALUES ('ORD_20260916212403_059', 'store_888', 'table_18', 'BREAKFAST', 2, 66.0, 0.0, '无', 6.0, 72.0, 'PRINTED', '会员卡余额', 1, '2026-09-16 21:24:03', '2026-09-16 21:25:03');
INSERT INTO t_order VALUES ('ORD_20260916231627_060', 'store_888', 'table_03', 'BREAKFAST', 6, 36.0, 0.0, '无', 18.0, 54.0, 'COMPLETED', '会员卡余额', 1, '2026-09-16 23:16:27', '2026-09-16 23:19:27');
INSERT INTO t_order VALUES ('ORD_20260918120821_061', 'store_888', 'table_02', 'NIGHT', 1, 44.0, 0.0, '无', 3.0, 47.0, 'COMPLETED', '微信支付 (WeChat Pay)', 1, '2026-09-18 12:08:21', '2026-09-18 12:11:21');
INSERT INTO t_order VALUES ('ORD_20260916213411_062', 'store_888', 'table_04', 'BREAKFAST', 1, 228.0, 50.0, '满200减50元券', 3.0, 181.0, 'PAID', '微信支付 (WeChat Pay)', 0, '2026-09-16 21:34:11', '2026-09-16 21:36:11');
INSERT INTO t_order VALUES ('ORD_20260917025155_063', 'store_888', 'table_18', 'DINNER', 2, 103.8, 0.0, '无', 6.0, 109.8, 'COMPLETED', '微信支付 (WeChat Pay)', 1, '2026-09-17 02:51:55', '2026-09-17 02:54:55');
INSERT INTO t_order VALUES ('ORD_20260917073900_064', 'store_888', 'table_03', 'LUNCH', 4, 253.9, 20.0, '满100减20元券', 12.0, 245.9, 'PENDING_PAY', '待支付', 0, '2026-09-17 07:39:00', NULL);
INSERT INTO t_order VALUES ('ORD_20260917205818_065', 'store_888', 'table_16', 'DINNER', 3, 140.0, 20.0, '满100减20元券', 9.0, 129.0, 'PRINTED', '会员卡余额', 1, '2026-09-17 20:58:18', '2026-09-17 20:59:18');
INSERT INTO t_order VALUES ('ORD_20260919011707_066', 'store_888', 'table_04', 'BREAKFAST', 3, 145.0, 20.0, '满100减20元券', 9.0, 134.0, 'PRINTED', '支付宝 (Alipay)', 1, '2026-09-19 01:17:07', '2026-09-19 01:18:07');
INSERT INTO t_order VALUES ('ORD_20260917201501_067', 'store_888', 'table_02', 'NIGHT', 6, 65.9, 0.0, '无', 18.0, 83.9, 'PENDING_PAY', '待支付', 0, '2026-09-17 20:15:01', NULL);
INSERT INTO t_order VALUES ('ORD_20260917122427_068', 'store_888', 'table_22', 'LUNCH', 1, 392.0, 0.0, '无', 3.0, 395.0, 'PENDING_PAY', '待支付', 0, '2026-09-17 12:24:27', NULL);
INSERT INTO t_order VALUES ('ORD_20260917014452_069', 'store_888', 'table_18', 'DINNER', 1, 92.0, 0.0, '无', 3.0, 95.0, 'COMPLETED', '微信支付 (WeChat Pay)', 1, '2026-09-17 01:44:52', '2026-09-17 01:47:52');
INSERT INTO t_order VALUES ('ORD_20260918070457_070', 'store_888', 'table_08', 'DINNER', 5, 206.0, 50.0, '满200减50元券', 15.0, 171.0, 'COMPLETED', '美团买单', 1, '2026-09-18 07:04:57', '2026-09-18 07:07:57');
INSERT INTO t_order VALUES ('ORD_20260918122335_071', 'store_888', 'table_04', 'NIGHT', 4, 372.0, 20.0, '满100减20元券', 12.0, 364.0, 'PAID', '支付宝 (Alipay)', 0, '2026-09-18 12:23:35', '2026-09-18 12:25:35');
INSERT INTO t_order VALUES ('ORD_20260917192302_072', 'store_888', 'table_08', 'DINNER', 2, 129.0, 0.0, '无', 6.0, 135.0, 'PAID', '微信支付 (WeChat Pay)', 0, '2026-09-17 19:23:02', '2026-09-17 19:25:02');
INSERT INTO t_order VALUES ('ORD_20260917055000_073', 'store_888', 'table_16', 'BREAKFAST', 5, 36.0, 0.0, '无', 15.0, 51.0, 'COMPLETED', '微信支付 (WeChat Pay)', 1, '2026-09-17 05:50:00', '2026-09-17 05:53:00');
INSERT INTO t_order VALUES ('ORD_20260917222809_074', 'store_888', 'table_02', 'BREAKFAST', 4, 424.0, 20.0, '满100减20元券', 12.0, 416.0, 'PAID', '会员卡余额', 0, '2026-09-17 22:28:09', '2026-09-17 22:30:09');
INSERT INTO t_order VALUES ('ORD_20260917053904_075', 'store_888', 'table_09', 'LUNCH', 1, 292.0, 50.0, '满200减50元券', 3.0, 245.0, 'CANCELLED', '已取消(未扣款)', 0, '2026-09-17 05:39:04', NULL);
INSERT INTO t_order VALUES ('ORD_20260919023941_076', 'store_888', 'table_12', 'DINNER', 6, 288.0, 50.0, '满200减50元券', 18.0, 256.0, 'COMPLETED', '微信支付 (WeChat Pay)', 1, '2026-09-19 02:39:41', '2026-09-19 02:42:41');
INSERT INTO t_order VALUES ('ORD_20260918094256_077', 'store_888', 'table_02', 'LUNCH', 1, 106.0, 0.0, '无', 3.0, 109.0, 'COMPLETED', '微信支付 (WeChat Pay)', 1, '2026-09-18 09:42:56', '2026-09-18 09:45:56');
INSERT INTO t_order VALUES ('ORD_20260918160341_078', 'store_888', 'table_16', 'NIGHT', 6, 116.0, 20.0, '满100减20元券', 18.0, 114.0, 'PAID', '会员卡余额', 0, '2026-09-18 16:03:41', '2026-09-18 16:05:41');
INSERT INTO t_order VALUES ('ORD_20260917111614_079', 'store_888', 'table_12', 'LUNCH', 4, 196.0, 20.0, '满100减20元券', 12.0, 188.0, 'COMPLETED', '微信支付 (WeChat Pay)', 1, '2026-09-17 11:16:14', '2026-09-17 11:19:14');
INSERT INTO t_order VALUES ('ORD_20260917085944_080', 'store_888', 'table_09', 'BREAKFAST', 6, 72.0, 0.0, '无', 18.0, 90.0, 'CANCELLED', '已取消(未扣款)', 0, '2026-09-17 08:59:44', NULL);

-- 插入菜品明细表记录
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917002914_001', 'D106', '炭烤生蚝半打', '剁椒味', '', '微辣', 2, 48.0, 96.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917002914_001', 'D101', '招牌老坛酸菜鱼', '中份', '', '加金针菇(+5元)', 1, 93.0, 93.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916154421_002', 'D104', '早市鲜虾小笼包', '大笼(10只)(+12元)', '', '加香醋姜丝', 2, 36.0, 72.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916154421_002', 'D105', '十三香绝味小龙虾', '大份(+40元)', '', '加手工拌面(+6元)', 1, 184.0, 184.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916154421_002', 'D106', '炭烤生蚝半打', '蒜蓉味', '', '微辣', 1, 48.0, 48.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917211950_003', 'D104', '早市鲜虾小笼包', '大笼(10只)(+12元)', '', '加香醋姜丝', 2, 36.0, 72.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916180745_004', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916180745_004', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 1, 29.9, 29.9);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917173126_005', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 2, 22.0, 44.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917173126_005', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '加小圆子(+2元)', 2, 18.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917173126_005', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 2, 36.0, 72.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919085112_006', 'D104', '早市鲜虾小笼包', '大笼(10只)(+12元)', '', '加香醋姜丝', 2, 36.0, 72.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918225706_007', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '加小圆子(+2元)', 1, 18.0, 18.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918225706_007', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918225706_007', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 1, 22.0, 22.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917130109_008', 'D101', '招牌老坛酸菜鱼', '中份', '', '配宽粉(+4元)', 1, 92.0, 92.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917130109_008', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917005015_009', 'D105', '十三香绝味小龙虾', '中份', '', '加手工拌面(+6元)', 2, 144.0, 288.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917005015_009', 'D104', '早市鲜虾小笼包', '大笼(10只)(+12元)', '', '加香醋姜丝', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918031821_010', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '加小圆子(+2元)', 2, 18.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917111202_011', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 2, 29.9, 59.8);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918003951_012', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 1, 22.0, 22.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918003951_012', 'D101', '招牌老坛酸菜鱼', '中份', '', '加金针菇(+5元)', 2, 93.0, 186.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918003951_012', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919031054_013', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 1, 29.9, 29.9);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919031054_013', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '少糖去冰', 2, 16.0, 32.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919031054_013', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 2, 22.0, 44.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917054350_014', 'D101', '招牌老坛酸菜鱼', '大份(+20元)', '', '配宽粉(+4元)', 2, 112.0, 224.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917054350_014', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917054350_014', 'D104', '早市鲜虾小笼包', '大笼(10只)(+12元)', '', '加香醋姜丝', 2, 36.0, 72.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919054108_015', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 1, 29.9, 29.9);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919054108_015', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 1, 22.0, 22.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919054108_015', 'D105', '十三香绝味小龙虾', '大份(+40元)', '', '加手工拌面(+6元)', 1, 184.0, 184.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917085548_016', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 1, 29.9, 29.9);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918213431_017', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '加小圆子(+2元)', 1, 18.0, 18.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916231511_018', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '少糖去冰', 2, 16.0, 32.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917003752_019', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 1, 22.0, 22.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918124934_020', 'D106', '炭烤生蚝半打', '剁椒味', '', '微辣', 2, 48.0, 96.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918124934_020', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 1, 29.9, 29.9);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918124934_020', 'D104', '早市鲜虾小笼包', '大笼(10只)(+12元)', '', '加香醋姜丝', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917185239_021', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918205220_022', 'D105', '十三香绝味小龙虾', '大份(+40元)', '', '加手工拌面(+6元)', 1, 184.0, 184.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918205220_022', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 2, 36.0, 72.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918105710_023', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918105710_023', 'D106', '炭烤生蚝半打', '剁椒味', '', '微辣', 2, 48.0, 96.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918105710_023', 'D101', '招牌老坛酸菜鱼', '大份(+20元)', '', '加金针菇(+5元)', 1, 113.0, 113.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918000759_024', 'D101', '招牌老坛酸菜鱼', '大份(+20元)', '', '加金针菇(+5元)', 1, 113.0, 113.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919025906_025', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 1, 22.0, 22.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919094141_026', 'D106', '炭烤生蚝半打', '剁椒味', '', '微辣', 2, 48.0, 96.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919094141_026', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 1, 29.9, 29.9);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917144104_027', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 2, 22.0, 44.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916144945_028', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '加小圆子(+2元)', 1, 18.0, 18.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917050312_029', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '加小圆子(+2元)', 1, 18.0, 18.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916134240_030', 'D104', '早市鲜虾小笼包', '一笼(6只)', '', '加香醋姜丝', 1, 24.0, 24.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916134240_030', 'D105', '十三香绝味小龙虾', '大份(+40元)', '', '加手工拌面(+6元)', 2, 184.0, 368.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919054422_031', 'D106', '炭烤生蚝半打', '剁椒味', '', '微辣', 2, 48.0, 96.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919054422_031', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917050402_032', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 1, 22.0, 22.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917050402_032', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917050402_032', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '加小圆子(+2元)', 1, 18.0, 18.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916162750_033', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 1, 29.9, 29.9);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917094515_034', 'D101', '招牌老坛酸菜鱼', '大份(+20元)', '', '加金针菇(+5元)', 2, 113.0, 226.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917094515_034', 'D106', '炭烤生蚝半打', '蒜蓉味', '', '微辣', 2, 48.0, 96.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917094515_034', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918185213_035', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 2, 22.0, 44.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918185213_035', 'D104', '早市鲜虾小笼包', '大笼(10只)(+12元)', '', '加香醋姜丝', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918185213_035', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '加小圆子(+2元)', 1, 18.0, 18.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916200518_036', 'D104', '早市鲜虾小笼包', '大笼(10只)(+12元)', '', '加香醋姜丝', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917202314_037', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917202314_037', 'D105', '十三香绝味小龙虾', '大份(+40元)', '', '加手工拌面(+6元)', 2, 184.0, 368.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919012152_038', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 2, 36.0, 72.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919012152_038', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '少糖去冰', 2, 16.0, 32.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919123529_039', 'D105', '十三香绝味小龙虾', '大份(+40元)', '', '加手工拌面(+6元)', 1, 184.0, 184.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919123529_039', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '少糖去冰', 2, 16.0, 32.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919123529_039', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 1, 29.9, 29.9);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917031906_040', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917031906_040', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '加小圆子(+2元)', 2, 18.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919123101_041', 'D106', '炭烤生蚝半打', '蒜蓉味', '', '微辣', 1, 48.0, 48.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919123101_041', 'D104', '早市鲜虾小笼包', '大笼(10只)(+12元)', '', '加香醋姜丝', 2, 36.0, 72.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919123101_041', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 2, 22.0, 44.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919121413_042', 'D106', '炭烤生蚝半打', '蒜蓉味', '', '微辣', 2, 48.0, 96.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918143649_043', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '少糖去冰', 2, 16.0, 32.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918143649_043', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 1, 29.9, 29.9);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919000100_044', 'D101', '招牌老坛酸菜鱼', '大份(+20元)', '', '加金针菇(+5元)', 1, 113.0, 113.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918124848_045', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '少糖去冰', 1, 16.0, 16.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918124848_045', 'D106', '炭烤生蚝半打', '蒜蓉味', '', '微辣', 2, 48.0, 96.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918124848_045', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 2, 36.0, 72.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918214218_046', 'D105', '十三香绝味小龙虾', '中份', '', '加手工拌面(+6元)', 2, 144.0, 288.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918214218_046', 'D101', '招牌老坛酸菜鱼', '大份(+20元)', '', '加金针菇(+5元)', 2, 113.0, 226.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918214218_046', 'D104', '早市鲜虾小笼包', '一笼(6只)', '', '加香醋姜丝', 2, 24.0, 48.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918225325_047', 'D101', '招牌老坛酸菜鱼', '中份', '', '配宽粉(+4元)', 1, 92.0, 92.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916165701_048', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 2, 29.9, 59.8);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916165701_048', 'D101', '招牌老坛酸菜鱼', '大份(+20元)', '', '配宽粉(+4元)', 1, 112.0, 112.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918232412_049', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 1, 22.0, 22.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918232412_049', 'D105', '十三香绝味小龙虾', '大份(+40元)', '', '加手工拌面(+6元)', 2, 184.0, 368.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918232412_049', 'D104', '早市鲜虾小笼包', '一笼(6只)', '', '加香醋姜丝', 1, 24.0, 24.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916183231_050', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 2, 22.0, 44.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916183231_050', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 2, 36.0, 72.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918224227_051', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '少糖去冰', 2, 16.0, 32.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918210821_052', 'D101', '招牌老坛酸菜鱼', '大份(+20元)', '', '配宽粉(+4元)', 2, 112.0, 224.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918210821_052', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 2, 22.0, 44.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917140949_053', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 2, 29.9, 59.8);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918160702_054', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 1, 22.0, 22.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918160702_054', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 2, 36.0, 72.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918160702_054', 'D106', '炭烤生蚝半打', '剁椒味', '', '微辣', 1, 48.0, 48.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918065741_055', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918065741_055', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 1, 22.0, 22.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918065741_055', 'D106', '炭烤生蚝半打', '剁椒味', '', '微辣', 2, 48.0, 96.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917110807_056', 'D104', '早市鲜虾小笼包', '大笼(10只)(+12元)', '', '加香醋姜丝', 2, 36.0, 72.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917190030_057', 'D104', '早市鲜虾小笼包', '大笼(10只)(+12元)', '', '加香醋姜丝', 2, 36.0, 72.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917190030_057', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 2, 22.0, 44.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917190030_057', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918070919_058', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '加小圆子(+2元)', 2, 18.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918070919_058', 'D105', '十三香绝味小龙虾', '大份(+40元)', '', '加手工拌面(+6元)', 2, 184.0, 368.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916212403_059', 'D106', '炭烤生蚝半打', '蒜蓉味', '', '微辣', 1, 48.0, 48.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916212403_059', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '加小圆子(+2元)', 1, 18.0, 18.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916231627_060', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918120821_061', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 2, 22.0, 44.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916213411_062', 'D105', '十三香绝味小龙虾', '大份(+40元)', '', '加手工拌面(+6元)', 1, 184.0, 184.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260916213411_062', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 2, 22.0, 44.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917025155_063', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 2, 29.9, 59.8);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917025155_063', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 2, 22.0, 44.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917073900_064', 'D101', '招牌老坛酸菜鱼', '大份(+20元)', '', '配宽粉(+4元)', 2, 112.0, 224.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917073900_064', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 1, 29.9, 29.9);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917205818_065', 'D106', '炭烤生蚝半打', '剁椒味', '', '微辣', 2, 48.0, 96.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917205818_065', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 2, 22.0, 44.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919011707_066', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '少糖去冰', 2, 16.0, 32.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919011707_066', 'D101', '招牌老坛酸菜鱼', '大份(+20元)', '', '加金针菇(+5元)', 1, 113.0, 113.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917201501_067', 'D102', '限量特价手抓羊排', '标准份', '', '配秘制孜然粉', 1, 29.9, 29.9);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917201501_067', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '加小圆子(+2元)', 2, 18.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917122427_068', 'D104', '早市鲜虾小笼包', '一笼(6只)', '', '加香醋姜丝', 1, 24.0, 24.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917122427_068', 'D105', '十三香绝味小龙虾', '大份(+40元)', '', '加手工拌面(+6元)', 2, 184.0, 368.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917014452_069', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 2, 22.0, 44.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917014452_069', 'D106', '炭烤生蚝半打', '剁椒味', '', '微辣', 1, 48.0, 48.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918070457_070', 'D105', '十三香绝味小龙虾', '大份(+40元)', '', '加手工拌面(+6元)', 1, 184.0, 184.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918070457_070', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 1, 22.0, 22.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918122335_071', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '加小圆子(+2元)', 2, 18.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918122335_071', 'D105', '十三香绝味小龙虾', '中份', '', '加手工拌面(+6元)', 2, 144.0, 288.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918122335_071', 'D106', '炭烤生蚝半打', '蒜蓉味', '', '微辣', 1, 48.0, 48.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917192302_072', 'D101', '招牌老坛酸菜鱼', '中份', '', '加金针菇(+5元)', 1, 93.0, 93.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917192302_072', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917055000_073', 'D104', '早市鲜虾小笼包', '大笼(10只)(+12元)', '', '加香醋姜丝', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917222809_074', 'D105', '十三香绝味小龙虾', '中份', '', '加手工拌面(+6元)', 1, 144.0, 144.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917222809_074', 'D106', '炭烤生蚝半打', '蒜蓉味', '', '微辣', 2, 48.0, 96.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917222809_074', 'D101', '招牌老坛酸菜鱼', '中份', '', '配宽粉(+4元)', 2, 92.0, 184.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917053904_075', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '少糖去冰', 2, 16.0, 32.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917053904_075', 'D101', '招牌老坛酸菜鱼', '大份(+20元)', '', '配宽粉(+4元)', 2, 112.0, 224.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917053904_075', 'D104', '早市鲜虾小笼包', '大笼(10只)(+12元)', '', '加香醋姜丝', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260919023941_076', 'D105', '十三香绝味小龙虾', '中份', '', '加手工拌面(+6元)', 2, 144.0, 288.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918094256_077', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 1, 22.0, 22.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918094256_077', 'D103', '季节限定杨梅冰汤圆', '标准碗', '', '加小圆子(+2元)', 2, 18.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918094256_077', 'D106', '炭烤生蚝半打', '蒜蓉味', '', '微辣', 1, 48.0, 48.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918160341_078', 'D108', '红糖滋粑', '一份(6块)', '', '多浇红糖汁', 2, 22.0, 44.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260918160341_078', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 2, 36.0, 72.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917111614_079', 'D106', '炭烤生蚝半打', '蒜蓉味', '', '微辣', 1, 48.0, 48.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917111614_079', 'D104', '早市鲜虾小笼包', '大笼(10只)(+12元)', '', '加香醋姜丝', 1, 36.0, 36.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917111614_079', 'D101', '招牌老坛酸菜鱼', '大份(+20元)', '', '配宽粉(+4元)', 1, 112.0, 112.0);
INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('ORD_20260917085944_080', 'D107', '干锅千页豆腐', '标准份', '', '免葱', 2, 36.0, 72.0);
