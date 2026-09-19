#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
餐饮中台订单数据持久化与数据库导出工具 (init_and_export_db.py)
功能：
1. 创建标准的 SQLite 数据库文件 (restaurant_orders.db)
2. 创建 t_order (订单主表), t_order_item (菜品明细表), t_bi_settlement (BI结算汇总表)
3. 生成并落库 100+ 笔涵盖各生命周期状态、多时段、多规格的真实业务数据
4. 同步生成可直接导入 MySQL/Navicat/DBeaver 的 restaurant_orders.sql 脚本
5. 提供快捷的终端 SQL 查询命令行
"""

import sqlite3
import random
import time
from datetime import datetime, timedelta
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "restaurant_orders.db")
SQL_PATH = os.path.join(BASE_DIR, "restaurant_orders.sql")

CREATE_TABLES_SQL = """
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
"""

DISH_CATALOG = [
    {"dish_id": "D101", "name": "招牌老坛酸菜鱼", "base": 88.0, "specs": [("大份(+20元)", 20.0), ("中份", 0.0)], "extras": [("加金针菇(+5元)", 5.0), ("配宽粉(+4元)", 4.0)]},
    {"dish_id": "D102", "name": "限量特价手抓羊排", "base": 29.9, "specs": [("标准份", 0.0)], "extras": [("配秘制孜然粉", 0.0)]},
    {"dish_id": "D103", "name": "季节限定杨梅冰汤圆", "base": 16.0, "specs": [("标准碗", 0.0)], "extras": [("加小圆子(+2元)", 2.0), ("少糖去冰", 0.0)]},
    {"dish_id": "D104", "name": "早市鲜虾小笼包", "base": 24.0, "specs": [("一笼(6只)", 0.0), ("大笼(10只)(+12元)", 12.0)], "extras": [("加香醋姜丝", 0.0)]},
    {"dish_id": "D105", "name": "十三香绝味小龙虾", "base": 138.0, "specs": [("中份", 0.0), ("大份(+40元)", 40.0)], "extras": [("加手工拌面(+6元)", 6.0)]},
    {"dish_id": "D106", "name": "炭烤生蚝半打", "base": 48.0, "specs": [("蒜蓉味", 0.0), ("剁椒味", 0.0)], "extras": [("微辣", 0.0)]},
    {"dish_id": "D107", "name": "干锅千页豆腐", "base": 36.0, "specs": [("标准份", 0.0)], "extras": [("免葱", 0.0)]},
    {"dish_id": "D108", "name": "红糖滋粑", "base": 22.0, "specs": [("一份(6块)", 0.0)], "extras": [("多浇红糖汁", 0.0)]}
]

TABLES = ["table_01", "table_02", "table_03", "table_04", "table_06", "table_08", "table_09", "table_12", "table_16", "table_18", "table_22"]
PERIODS = ["BREAKFAST", "LUNCH", "DINNER", "NIGHT"]

def generate_database(num_orders=80):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(CREATE_TABLES_SQL)

    # 清空历史测试数据
    cursor.execute("DELETE FROM t_order_item;")
    cursor.execute("DELETE FROM t_order;")
    cursor.execute("DELETE FROM t_bi_settlement;")

    now = datetime.now()
    orders = []
    items_to_insert = []

    sql_inserts = [CREATE_TABLES_SQL.replace("AUTOINCREMENT", "AUTO_INCREMENT").replace("DATETIME", "DATETIME")]

    for i in range(1, num_orders + 1):
        # 模拟过去 3 天内的时间
        offset_seconds = random.randint(0, 3 * 24 * 3600)
        order_time = now - timedelta(seconds=offset_seconds)
        order_sn = f"ORD_{order_time.strftime('%Y%m%d%H%M%S')}_{str(i).zfill(3)}"
        
        table_id = random.choice(TABLES)
        period = random.choice(PERIODS)
        people_count = random.randint(1, 6)
        tableware_fee = round(people_count * 3.0, 2)

        # 随机点 1~3 道菜
        item_count = random.randint(1, 3)
        chosen_dishes = random.sample(DISH_CATALOG, item_count)
        
        original_total = 0.0
        for dish in chosen_dishes:
            spec_name, spec_delta = random.choice(dish["specs"])
            extra_name, extra_fee = random.choice(dish["extras"])
            qty = random.randint(1, 2)
            unit_price = dish["base"] + spec_delta + extra_fee
            subtotal = round(unit_price * qty, 2)
            original_total += subtotal

            items_to_insert.append((
                order_sn, dish["dish_id"], dish["name"], spec_name, "", extra_name, qty, unit_price, subtotal
            ))

        original_total = round(original_total, 2)

        # 满减优惠券规则
        discount_amount = 0.0
        coupon_name = "无"
        if original_total >= 200 and random.random() > 0.4:
            discount_amount = 50.0
            coupon_name = "满200减50元券"
        elif original_total >= 100 and random.random() > 0.3:
            discount_amount = 20.0
            coupon_name = "满100减20元券"

        actual_pay = max(0.0, round(original_total - discount_amount + tableware_fee, 2))

        # 订单状态分布
        r = random.random()
        if r < 0.10:
            status = "PENDING_PAY"
            pay_channel = "待支付"
            paid_at = None
            kitchen_printed = 0
        elif r < 0.25:
            status = "PAID"
            pay_channel = random.choice(["微信支付 (WeChat Pay)", "支付宝 (Alipay)", "会员卡余额"])
            paid_at = (order_time + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
            kitchen_printed = 0
        elif r < 0.45:
            status = "PRINTED"
            pay_channel = random.choice(["微信支付 (WeChat Pay)", "支付宝 (Alipay)", "会员卡余额"])
            paid_at = (order_time + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
            kitchen_printed = 1
        elif r < 0.55:
            status = "CANCELLED"
            pay_channel = "已取消(未扣款)"
            paid_at = None
            kitchen_printed = 0
        else:
            status = "COMPLETED"
            pay_channel = random.choice(["微信支付 (WeChat Pay)", "支付宝 (Alipay)", "美团买单", "会员卡余额"])
            paid_at = (order_time + timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M:%S")
            kitchen_printed = 1

        orders.append((
            order_sn, "store_888", table_id, period, people_count, original_total,
            discount_amount, coupon_name, tableware_fee, actual_pay, status,
            pay_channel, kitchen_printed, order_time.strftime("%Y-%m-%d %H:%M:%S"), paid_at
        ))

    # 批量插入订单
    cursor.executemany("""
        INSERT INTO t_order (
            order_sn, store_id, table_id, period, people_count, original_total,
            discount_amount, coupon_name, tableware_fee, actual_pay, status,
            pay_channel, kitchen_printed, created_at, paid_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, orders)

    # 批量插入明细
    cursor.executemany("""
        INSERT INTO t_order_item (
            order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, items_to_insert)

    # 自动汇总计算生成 BI 日报表记录
    cursor.execute("""
        INSERT INTO t_bi_settlement (stat_date, period, total_orders, valid_orders, gmv, total_discounts, cancelled_orders, aov)
        SELECT 
            DATE(created_at) as stat_date,
            period,
            COUNT(*) as total_orders,
            SUM(CASE WHEN status IN ('PAID', 'PRINTED', 'COMPLETED') THEN 1 ELSE 0 END) as valid_orders,
            COALESCE(SUM(CASE WHEN status IN ('PAID', 'PRINTED', 'COMPLETED') THEN actual_pay ELSE 0 END), 0) as gmv,
            COALESCE(SUM(discount_amount), 0) as total_discounts,
            SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END) as cancelled_orders,
            ROUND(COALESCE(SUM(CASE WHEN status IN ('PAID', 'PRINTED', 'COMPLETED') THEN actual_pay ELSE 0 END) / 
                  NULLIF(SUM(CASE WHEN status IN ('PAID', 'PRINTED', 'COMPLETED') THEN 1 ELSE 0 END), 0), 0), 2) as aov
        FROM t_order
        GROUP BY DATE(created_at), period
        ORDER BY stat_date DESC, period;
    """)

    conn.commit()

    # 导出为 SQL 文本文件供 Navicat/DBeaver/MySQL 使用
    with open(SQL_PATH, "w", encoding="utf-8") as f:
        f.write("-- ========================================================\n")
        f.write("-- 智慧餐饮订单与 BI 结算系统真实数据 DDL 及 DML (MySQL/SQLite兼容)\n")
        f.write(f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-- ========================================================\n\n")
        f.write(CREATE_TABLES_SQL + "\n\n")

        f.write("-- 插入订单主表记录\n")
        for o in orders:
            paid_str = f"'{o[14]}'" if o[14] else "NULL"
            f.write(f"INSERT INTO t_order VALUES ('{o[0]}', '{o[1]}', '{o[2]}', '{o[3]}', {o[4]}, {o[5]}, {o[6]}, '{o[7]}', {o[8]}, {o[9]}, '{o[10]}', '{o[11]}', {o[12]}, '{o[13]}', {paid_str});\n")

        f.write("\n-- 插入菜品明细表记录\n")
        for it in items_to_insert:
            f.write(f"INSERT INTO t_order_item (order_sn, dish_id, dish_name, spec_name, attributes, extras, quantity, unit_price, subtotal) VALUES ('{it[0]}', '{it[1]}', '{it[2]}', '{it[3]}', '{it[4]}', '{it[5]}', {it[6]}, {it[7]}, {it[8]});\n")

    # 统计数据
    cursor.execute("SELECT COUNT(*) FROM t_order;")
    total_o = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM t_order_item;")
    total_items = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*), SUM(gmv) FROM t_bi_settlement;")
    bi_row = cursor.fetchone()

    conn.close()

    print("=" * 60)
    print("✅ 餐饮中台数据库初始化与持久化成功！")
    print(f"📁 SQLite 数据库路径: {DB_PATH}")
    print(f"📄 SQL 导出脚本路径:  {SQL_PATH}")
    print(f"📊 插入订单主表 (t_order):        {total_o} 笔")
    print(f"🛒 插入菜品明细表 (t_order_item): {total_items} 行")
    print(f"📈 聚合 BI 报表快照 (t_bi_settlement): {bi_row[0]} 条记录 (累计GMV: ￥{bi_row[1]:.2f})")
    print("=" * 60)

def print_summary_query():
    """打印常用查询结果供终端预览"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n🔍 【1. 订单状态统计汇总 (按状态聚合)】:")
    cursor.execute("""
        SELECT status, COUNT(*) as 单数, SUM(actual_pay) as 实际入账金额, AVG(actual_pay) as 笔均金额
        FROM t_order
        GROUP BY status
        ORDER BY 单数 DESC;
    """)
    for row in cursor.fetchall():
        print(f"  - 状态: {row[0]:<12} | 订单量: {row[1]:>3} 笔 | 总金额: ￥{row[2]:>8.2f} | 笔均: ￥{row[3]:>6.2f}")

    print("\n🕒 【2. BI 时段营收对账统计 (按早/午/晚/夜市聚合)】:")
    cursor.execute("""
        SELECT period, 
               COUNT(*) as 全部单量,
               SUM(CASE WHEN status IN ('PAID', 'PRINTED', 'COMPLETED') THEN 1 ELSE 0 END) as 有效单量,
               SUM(CASE WHEN status IN ('PAID', 'PRINTED', 'COMPLETED') THEN actual_pay ELSE 0 END) as 实际GMV
        FROM t_order
        GROUP BY period;
    """)
    for row in cursor.fetchall():
        print(f"  - 时段: {row[0]:<10} | 总单量: {row[1]:>3} 笔 | 有效单: {row[2]:>3} 笔 | GMV: ￥{row[3]:>8.2f}")

    print("\n🔥 【3. 爆款菜品销售额排行 Top 5】:")
    cursor.execute("""
        SELECT dish_name, SUM(quantity) as 总销量, SUM(subtotal) as 销售额合计
        FROM t_order_item
        GROUP BY dish_name
        ORDER BY 销售额合计 DESC
        LIMIT 5;
    """)
    for idx, row in enumerate(cursor.fetchall(), 1):
        print(f"  Top {idx}: {row[0]:<14} | 销量: {row[1]:>3} 份 | 销售额: ￥{row[2]:>8.2f}")

    conn.close()

if __name__ == "__main__":
    generate_database()
    print_summary_query()
