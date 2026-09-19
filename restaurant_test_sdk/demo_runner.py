"""
餐饮系统测试 SDK 演示与讲解启动脚本 (demo_runner.py)
一键执行全流程业务、Redis 并发锁与 RabbitMQ 消息容灾测试，并附带控制台时序讲解。
"""
import sys
import os
import time

# 将当前根目录加入 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from restaurant_test_sdk.models import TableStatus, MealPeriod, OrderStatus
from restaurant_test_sdk.client.mock_server import DiningMockServer
from restaurant_test_sdk.client.h5_order_client import H5OrderClient
from restaurant_test_sdk.redis_lock.distributed_lock import RedisEngineSimulator
from restaurant_test_sdk.redis_lock.lock_tester import RedisLockTester
from restaurant_test_sdk.mq.mq_broker import RabbitMQBrokerSimulator
from restaurant_test_sdk.mq.kitchen_printer import KitchenPrinterWorker
from restaurant_test_sdk.mq.mq_tester import MQTester


class Color:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def log_step(step_name: str, desc: str = ""):
    print(f"\n{Color.CYAN}👉 [STEP] {step_name}{Color.END} {desc}")


def log_pass(msg: str):
    print(f"  {Color.GREEN}✔ {msg}{Color.END}")


def log_warn(msg: str):
    print(f"  {Color.WARNING}⚠ {msg}{Color.END}")


def log_banner(title: str):
    print(f"\n{Color.BOLD}{Color.HEADER}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{Color.END}\n")


def run_h5_workflow_demo():
    log_banner("一、H5 点餐全流程测试演示（业务正向与四大异常边界）")
    server = DiningMockServer()
    client = H5OrderClient(server, store_id="store_888", table_id="table_06", customer_count=2)

    # 1. 扫码开台
    log_step("1. 扫码开台", "桌台ID: table_06")
    scan_res = client.scan_table()
    log_pass(f"扫码成功，开台模式: {scan_res['mode']}，桌台状态: {scan_res['table_status']}")

    # 2. 菜单时段过滤
    log_step("2. 加载午市菜单", "过滤不在午市销售的早餐与夜宵菜品")
    menu_res = client.fetch_menu(MealPeriod.LUNCH)
    dish_names = [d["name"] for d in menu_res["dishes"]]
    log_pass(f"午市开放菜品 ({len(dish_names)}种): {', '.join(dish_names)}")

    # 3. 选菜与规格/属性/加料组合
    log_step("3. 购物车加菜与属性算价", "规格:大份(+20), 做法:微辣, 加料:金针菇(+5)")
    item1 = client.add_item_to_cart("dish_001", "大份", chosen_attributes=["微辣"], chosen_extras=["加金针菇"], quantity=1)
    item2 = client.add_item_to_cart("dish_004", "标准碗", chosen_attributes=["去冰"], chosen_extras=["加小圆子"], quantity=1)
    log_pass(f"已加入: {item1.name}({item1.spec_name}) 单价={item1.unit_price}元, {item2.name} 单价={item2.unit_price}元")

    # 4. 价格快照核销
    log_step("4. 价格快照校验", "原价 - 满100减20优惠券 + 2位餐位费(3元/位)")
    snapshot = client.calculate_price(coupon_id="COUPON_100_MINUS_20")
    log_pass(f"原价合计: {snapshot.original_total}元 | 优惠抵扣: -{snapshot.discount_amount}元 | 餐位费: +{snapshot.tableware_fee}元")
    log_pass(f"--> 最终实付金额: {snapshot.actual_pay_amount}元 (起送/起做条件验证: {snapshot.min_consume_satisfied})")

    # 5. 防重提单
    log_step("5. 提交订单结算", "携带防重 Idempotency Token 下单")
    order_res = client.submit_order(coupon_id="COUPON_100_MINUS_20")
    order_sn = order_res["order_sn"]
    log_pass(f"下单成功! 生成单号: {order_sn}, 初始状态: {client.get_order_status(order_sn)}")

    # 6. 弱网连击防重测试
    log_step("6. 边界异常：弱网防抖与连击幂等测试", "模拟用户连续高频点击 3 次立即下单 (相同 Token)")
    c_rapid = H5OrderClient(server, "store_888", "table_02")
    c_rapid.scan_table()
    c_rapid.add_item_to_cart("dish_001", "中份", quantity=1)
    rapid_res = c_rapid.simulate_rapid_click_submit(click_count=3)
    log_pass(f"第1次提单: code={rapid_res[0]['code']} (成功创建订单: {rapid_res[0].get('order_sn')})")
    log_warn(f"第2次提单: code={rapid_res[1]['code']} ({rapid_res[1]['msg']})")
    log_warn(f"第3次提单: code={rapid_res[2]['code']} ({rapid_res[2]['msg']})")

    # 7. 限量特价菜防超卖
    log_step("7. 边界异常：限量特价菜抢购防超卖", "商品仅剩 1 份，2 位顾客同时抢购")
    c_buyer1 = H5OrderClient(server, "store_888", "table_01")
    c_buyer1.scan_table()
    c_buyer1.add_item_to_cart("dish_002", "标配", quantity=1)
    res_b1 = c_buyer1.submit_order()

    c_buyer2 = H5OrderClient(server, "store_888", "table_02")
    c_buyer2.scan_table()
    c_buyer2.add_item_to_cart("dish_002", "标配", quantity=1)
    res_b2 = c_buyer2.submit_order()
    log_pass(f"顾客1抢购成功: code={res_b1['code']} | 顾客2抢购拦截: code={res_b2['code']} ({res_b2['msg']})")

    # 8. 支付与回调
    log_step("8. 调起支付与异步回调", "微信支付成功通知后更改订单状态为 PAID，生成厨打消息")
    pay_res = client.simulate_pay(order_sn, channel="WECHAT_PAY", success=True)
    log_pass(f"支付回调成功: 订单 {order_sn} 当前状态: {client.get_order_status(order_sn)}")
    log_pass(f"触发厨打 MQ 事件: msg_id={pay_res['mq_message'].msg_id}")


def run_redis_lock_demo():
    log_banner("二、Redis 分布式锁高并发与容灾专项测试演示")
    engine = RedisEngineSimulator()
    server = DiningMockServer()
    tester = RedisLockTester(engine, server)

    # 1. 100 并发同桌抢单
    log_step("1. 100 线程并发抢占同桌台分布式锁", "Key: lock:order:table:store_888:table_06")
    res_100 = tester.run_concurrency_clash_test(concurrency=100)
    log_pass(f"并发测试完成: 总线程数={res_100['total_concurrency']} | 加锁成功={res_100['acquired_count']} | 安全拒绝={res_100['rejected_count']}")
    log_pass(f"严格互斥验证结果: {res_100['is_strictly_mutex']} (绝无重复生成多张桌台单)")

    # 2. Watchdog 续期
    log_step("2. Redisson Watchdog 看门狗自动续期验证", "初始TTL=200ms，业务执行0.35s超过TTL")
    res_wd = tester.test_watchdog_auto_renewal(hold_duration_sec=0.35)
    log_pass(f"看门狗后台自动续期次数: {res_wd['renewals_count']} 次 | 业务完成前锁剩余TTL: {res_wd['remaining_ttl_ms']}ms")
    log_pass(f"看门狗机制有效: {res_wd['watchdog_effective']}")

    # 3. 崩溃防死锁自愈
    log_step("3. 进程异常崩溃防死锁与 TTL 自然到期自愈验证", "线程1崩溃不释放锁，线程2等待TTL后恢复加锁")
    res_crash = tester.test_crash_ttl_deadlock_prevention(short_ttl_ms=120)
    log_pass(f"崩溃发生时新请求被拦截: {res_crash['client_2_blocked_during_ttl']}")
    log_pass(f"TTL到期后新请求成功自愈加锁: {res_crash['client_2_recovered_after_ttl']}")
    log_pass(f"防死锁保护生效: {res_crash['deadlock_prevented']}")

    # 4. Lua 脚本防误删
    log_step("4. 安全释放锁：Lua 脚本校验 random_value 防误删", "防止因网络卡顿其他线程误删新锁")
    res_lua = tester.test_safe_release_lua()
    log_pass(f"非法/异主删除尝试被拒绝 (return 0): {res_lua['rogue_delete_rejected']}")
    log_pass(f"原锁所有权完好保留: {res_lua['lock_a_protected']}")
    log_pass(f"属主安全调用 Lua 释放: {res_lua['owner_released_cleanly']}")

    # 5. DB 唯一约束兜底
    log_step("5. 后端数据库唯一索引 (uk_store_table_status) 兜底防御", "模拟极端突破缓存锁时的最后一道防线")
    res_db = tester.test_db_unique_constraint_fallback()
    log_pass(f"订单1正常生成: {res_db['order_1_success']} | 订单2被DB唯一索引拦截: {res_db['order_2_intercepted_by_db_uk']}")


def run_rabbitmq_demo():
    log_banner("三、RabbitMQ 消息可靠性、积压与死信 (DLQ) 容灾测试演示")
    broker = RabbitMQBrokerSimulator()
    engine = RedisEngineSimulator()
    printer = KitchenPrinterWorker(broker, engine, print_duration_sec=0.005)
    tester = MQTester(broker, printer, engine)

    # 1. 生产者确认
    log_step("1. Publisher ConfirmCallback 与 ReturnCallback 验证", "确认 Broker 收到并捕获不可达路由")
    res_pub = tester.test_publisher_confirm_and_return()
    log_pass(f"正常投递 ConfirmCallback ACK: {res_pub['normal_confirm_acked']}")
    log_pass(f"错误 RoutingKey 触发 ReturnCallback: {res_pub['unroutable_caught_by_return_callback']} (Code={res_pub['return_reply_code']}, {res_pub['return_reply_text']})")

    # 2. Broker 重启持久化
    log_step("2. Broker 持久化与节点重启容灾验证", "Exchange/Queue durable=True 与 Message delivery_mode=2")
    res_durable = tester.test_durability_and_restart()
    log_pass(f"持久化消息节点重启后完好存活: {res_durable['persistent_message_survived']}")
    log_pass(f"非持久化易失消息自动淘汰: {res_durable['volatile_message_dropped']}")

    # 3. 500单瞬时涌入积压
    log_step("3. 500 单瞬时涌入与慢消费者出纸积压监控 (Backlog Testing)", "后厨打印物理受限，瞬时并发500单")
    res_backlog = tester.test_500_order_burst_backlog_and_alert(burst_count=500)
    log_pass(f"队列 Ready 消息峰值堆积: {res_backlog['peak_ready_messages']} 条 (监控大屏积压检测: {res_backlog['messages_backlog_detected']})")
    log_warn(f"触发 5 分钟超时未出单警报: {res_backlog['timeout_alert_triggered']} (超时订单数: {res_backlog['timeout_unprinted_orders_count']} 个)")

    # 4. 打印机宕机、重试与死信
    log_step("4. 消费者宕机、重试 3 次进死信队列 (DLQ) 与补打容灾", "断网宕机 -> 重试 -> DLQ -> 钉钉报警 -> 恢复补打")
    res_dlq = tester.test_crash_retry_dlq_and_replay()
    log_warn(f"重试轨迹: {' -> '.join(res_dlq['attempt_steps'])}")
    log_pass(f"死信队列 (DLQ) 成功接收堆积: {res_dlq['dlq_message_count']} 条")
    log_pass(f"系统触发企业告警: {res_dlq['alert_triggered']} (内容: {res_dlq['latest_alert_content']})")
    log_pass(f"打印机恢复后从 DLQ 补偿补打: 补打单数={res_dlq['replayed_tickets_count']}, DLQ清空={res_dlq['dlq_cleared_after_repair']}")

    # 5. 消费幂等性防重打
    log_step("5. 消费幂等性验证 (Redis 去重)", "同一订单因网络重发 5 次消息，绝不允许打印两张单")
    res_idempotent = tester.test_consumer_idempotency(duplicate_count=5)
    log_pass(f"收到消息数: {res_idempotent['total_received_messages']} 次")
    log_pass(f"实际物理出纸: {res_idempotent['physical_printed_tickets_count']} 张 | 幂等忽略: {res_idempotent['duplicate_skipped_count']} 次")
    log_pass(f"严格消费幂等验证结果: {res_idempotent['is_strictly_idempotent']}")


if __name__ == "__main__":
    print(f"\n{Color.BOLD}{Color.GREEN}🚀 启动餐饮测试 SDK (DiningTestSDK) 演示脚本...{Color.END}")
    start_all = time.time()
    run_h5_workflow_demo()
    run_redis_lock_demo()
    run_rabbitmq_demo()
    total_elapsed = round(time.time() - start_all, 2)
    print(f"\n{Color.BOLD}{Color.GREEN}✨ 全部三大专项测试演练执行完毕！耗时: {total_elapsed} 秒。{Color.END}\n")
