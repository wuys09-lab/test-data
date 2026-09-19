"""
RabbitMQ 消息可靠性、积压与容灾专项测试器 (mq_tester.py)
执行发布确认、消息持久化、500单瞬时涌入慢出纸积压监控、宕机重试进死信与消费幂等防重打验证。
"""
import time
import uuid
from typing import Dict, Any, List

from restaurant_test_sdk.models import MQOrderMessage
from restaurant_test_sdk.mq.mq_broker import RabbitMQBrokerSimulator
from restaurant_test_sdk.mq.kitchen_printer import KitchenPrinterWorker
from restaurant_test_sdk.redis_lock.distributed_lock import RedisEngineSimulator
from restaurant_test_sdk.config import config


class MQTester:
    """RabbitMQ 消息中间件专项测试与监控器"""

    def __init__(self, broker: RabbitMQBrokerSimulator = None,
                 printer: KitchenPrinterWorker = None,
                 redis_engine: RedisEngineSimulator = None):
        self.broker = broker or RabbitMQBrokerSimulator()
        self.redis = redis_engine or RedisEngineSimulator()
        self.printer = printer or KitchenPrinterWorker(self.broker, self.redis)

    # 1. 消息可靠性：Publisher ConfirmCallback 与 ReturnCallback 验证
    def test_publisher_confirm_and_return(self) -> Dict[str, Any]:
        """
        验证发布确认机制：
        - 正常投递：收到 ConfirmCallback ACK
        - 路由键错误：触发 ReturnCallback (NO_ROUTE) 捕获异常
        """
        confirm_results = []
        return_results = []

        self.broker.set_confirm_callback(
            lambda ack, cause: confirm_results.append({"ack": ack, "cause": cause})
        )
        self.broker.set_return_callback(
            lambda msg, code, text, ex, rk: return_results.append({
                "msg_id": msg.msg_id, "code": code, "text": text, "routing_key": rk
            })
        )

        test_msg = MQOrderMessage(
            msg_id=f"MSG_CONFIRM_{uuid.uuid4().hex[:6]}",
            order_sn="ORD_TEST_CONFIRM_001",
            store_id="store_888",
            table_id="table_06",
            items_summary="酸菜鱼x1",
            total_amount=108.0,
            pay_time=time.time(),
            delivery_mode=2
        )

        # 场景 A: 正常发送到匹配队列
        ok_a = self.broker.basic_publish(config.order_exchange, config.order_routing_key, test_msg)
        
        # 场景 B: 交换机存在，但 routing_key 错误，无对应队列可达
        unroutable_msg = MQOrderMessage(
            msg_id=f"MSG_UNROUTE_{uuid.uuid4().hex[:6]}",
            order_sn="ORD_TEST_UNROUTE_002",
            store_id="store_888",
            table_id="table_06",
            items_summary="鲜虾小笼包x2",
            total_amount=44.0,
            pay_time=time.time(),
            delivery_mode=2
        )
        ok_b = self.broker.basic_publish(config.order_exchange, "invalid.routing.key", unroutable_msg)

        return {
            "test_name": "Publisher 确认与路由失败退回测试",
            "normal_publish_success": ok_a,
            "normal_confirm_acked": len(confirm_results) >= 1 and confirm_results[0]["ack"],
            "unroutable_caught_by_return_callback": len(return_results) == 1,
            "return_reply_code": return_results[0]["code"] if return_results else None,
            "return_reply_text": return_results[0]["text"] if return_results else None
        }

    # 2. Broker 持久化与节点重启恢复测试
    def test_durability_and_restart(self) -> Dict[str, Any]:
        """
        验证 Exchange、Queue durable=True 与 Message delivery_mode=2。
        模拟在投递中途重启 RabbitMQ 节点，验证消息不丢失。
        """
        # 构造 1 条持久化消息，1 条非持久化消息
        persistent_msg = MQOrderMessage(
            msg_id="MSG_DURABLE_01",
            order_sn="ORD_DURABLE_01",
            store_id="store_888",
            table_id="table_06",
            items_summary="酸菜鱼大份x1",
            total_amount=108.0,
            pay_time=time.time(),
            delivery_mode=2 # 持久化
        )
        non_persistent_msg = MQOrderMessage(
            msg_id="MSG_VOLATILE_02",
            order_sn="ORD_VOLATILE_02",
            store_id="store_888",
            table_id="table_06",
            items_summary="杨梅冰汤圆x1",
            total_amount=16.0,
            pay_time=time.time(),
            delivery_mode=1 # 非持久化
        )

        self.broker.basic_publish(config.order_exchange, config.order_routing_key, persistent_msg)
        self.broker.basic_publish(config.order_exchange, config.order_routing_key, non_persistent_msg)

        before_metrics = self.broker.get_queue_metrics(config.kitchen_queue)
        
        # 模拟 RabbitMQ 节点意外重启
        self.broker.simulate_broker_restart()
        
        after_metrics = self.broker.get_queue_metrics(config.kitchen_queue)
        remaining_messages = self.broker.queues[config.kitchen_queue]

        return {
            "test_name": "Broker持久化与节点重启容灾验证",
            "messages_before_restart": before_metrics["messages_ready"],
            "messages_after_restart": after_metrics["messages_ready"],
            "persistent_message_survived": any(m.msg_id == "MSG_DURABLE_01" for m in remaining_messages),
            "volatile_message_dropped": not any(m.msg_id == "MSG_VOLATILE_02" for m in remaining_messages),
            "durability_effective": (after_metrics["messages_ready"] == 1)
        }

    # 3. 500单瞬时涌入与慢消费者积压性能测试 (Backlog Testing)
    def test_500_order_burst_backlog_and_alert(self, burst_count: int = 500) -> Dict[str, Any]:
        """
        模拟后厨打印机物理出纸慢处理（每秒约1~2张），批量模拟 500 个订单瞬时涌入，
        监控队列 Ready 堆积水位与 5 分钟超时未出单警报。
        """
        # 清空测试队列
        self.broker.queues[config.kitchen_queue].clear()
        
        # 模拟瞬时 500 个订单涌入
        for i in range(burst_count):
            # 将后 5 单模拟为已支付超过 5 分钟未出单的超时消息，即使前 20 单被消费，仍留存队列触发报警
            is_timeout_order = (i >= (burst_count - 5))
            pay_time = time.time() - (310.0 if is_timeout_order else 10.0)
            
            msg = MQOrderMessage(
                msg_id=f"MSG_BURST_{i:04d}",
                order_sn=f"ORD_BURST_{i:04d}",
                store_id="store_888",
                table_id=f"table_{(i%20)+1:02d}",
                items_summary=f"套餐A x 1",
                total_amount=68.0,
                pay_time=pay_time,
                delivery_mode=2
            )
            self.broker.basic_publish(config.order_exchange, config.order_routing_key, msg)

        # 观测积压最高峰
        peak_metrics = self.broker.get_queue_metrics(config.kitchen_queue)
        
        # 启动慢消费者处理部分订单 (测试限速出纸与线程池稳定，处理 20 单)
        self.printer.print_duration_sec = 0.005  # 加速单测耗时
        processed = []
        for _ in range(20):
            res = self.printer.process_one_message(config.kitchen_queue)
            if res:
                processed.append(res)

        after_process_metrics = self.broker.get_queue_metrics(config.kitchen_queue)
        
        # 检查超时未出单报警（已支付超 5 分钟）
        timeout_orders = []
        for msg in self.broker.queues[config.kitchen_queue]:
            if (time.time() - msg.pay_time) > config.order_print_timeout_sec:
                timeout_orders.append(msg.order_sn)

        return {
            "test_name": "500单瞬时涌入消息积压与超时监控测试",
            "burst_count": burst_count,
            "peak_ready_messages": peak_metrics["messages_ready"],
            "messages_backlog_detected": peak_metrics["messages_ready"] == burst_count,
            "partial_processed_count": len(processed),
            "remaining_backlog_count": after_process_metrics["messages_ready"],
            "timeout_unprinted_orders_count": len(timeout_orders),
            "timeout_alert_triggered": len(timeout_orders) > 0
        }

    # 4. 消费者宕机、重试超限进死信 (DLQ) 与补偿重打
    def test_crash_retry_dlq_and_replay(self) -> Dict[str, Any]:
        """
        模拟后厨打印机断网宕机：
        - 消息进入 unacked，触发消费重试 (3次)
        - 重试耗尽后 basic.nack(requeue=False)，自动路由到死信交换机 (DLX) 与死信队列 (DLQ)
        - 触发企业微信/钉钉告警通知
        - 打印机网络恢复后，从 DLQ 拉取补偿重打
        """
        # 清空测试队列，确保用例隔离
        self.broker.queues[config.kitchen_queue].clear()
        self.broker.queues[config.dlq_queue].clear()
        self.printer.printed_tickets.clear()
        
        # 准备订单消息
        msg = MQOrderMessage(
            msg_id="MSG_CRASH_TEST_01",
            order_sn="ORD_CRASH_TEST_01",
            store_id="store_888",
            table_id="table_08",
            items_summary="手抓羊排x1",
            total_amount=9.9,
            pay_time=time.time(),
            delivery_mode=2
        )
        self.broker.basic_publish(config.order_exchange, config.order_routing_key, msg)

        # 模拟后厨打印机宕机/网络故障
        self.printer.is_online = False
        
        # 连续处理，触发重试与死信转移
        attempt_history = []
        for _ in range(self.printer.max_retries + 1):
            res = self.printer.process_one_message(config.kitchen_queue)
            if res:
                attempt_history.append(res)

        dlq_metrics = self.broker.get_queue_metrics(config.kitchen_queue)
        
        # 模拟打印机维修完毕恢复上线，从 DLQ 进行补偿拉取打印
        self.printer.is_online = True
        replayed_tickets = self.printer.replay_from_dlq()
        
        dlq_after_repair_metrics = self.broker.get_queue_metrics(config.kitchen_queue)

        return {
            "test_name": "消费者宕机重试、死信转运与补打容灾测试",
            "attempt_steps": [h["status"] for h in attempt_history],
            "dlq_message_count": dlq_metrics["dlq_messages_count"],
            "alert_triggered": dlq_metrics["alert_count"] > 0,
            "latest_alert_content": self.broker.alert_notifications[-1]["content"] if self.broker.alert_notifications else None,
            "replayed_tickets_count": len(replayed_tickets),
            "dlq_cleared_after_repair": (dlq_after_repair_metrics["dlq_messages_count"] == 0)
        }

    # 5. 消费幂等性防重打测试 (Redis 去重校验)
    def test_consumer_idempotency(self, duplicate_count: int = 5) -> Dict[str, Any]:
        """
        模拟同一条已支付订单消息因网络重传被重复投递 5 次，
        后厨打印机结合 Redis msg_id / order_sn 进行消费幂等去重，
        验证绝对不会打出多张相同订单。
        """
        # 清空测试队列与打印记录
        self.broker.queues[config.kitchen_queue].clear()
        self.printer.printed_tickets.clear()
        
        target_order_sn = f"ORD_IDEMPOTENT_{uuid.uuid4().hex[:6]}"
        
        # 发送 5 条相同 order_sn 的消息
        for i in range(duplicate_count):
            msg = MQOrderMessage(
                msg_id=f"MSG_DUP_{i}_{uuid.uuid4().hex[:4]}",
                order_sn=target_order_sn,
                store_id="store_888",
                table_id="table_06",
                items_summary="招牌老坛酸菜鱼(大份)x1",
                total_amount=108.0,
                pay_time=time.time(),
                delivery_mode=2
            )
            self.broker.basic_publish(config.order_exchange, config.order_routing_key, msg)

        # 打印机依次消费这 5 条消息
        self.printer.print_duration_sec = 0.001
        self.printer.is_online = True
        process_results = []
        for _ in range(duplicate_count):
            res = self.printer.process_one_message(config.kitchen_queue)
            if res:
                process_results.append(res)

        # 统计物理纸质打印件中该 order_sn 出现的次数
        physical_printed = [t for t in self.printer.printed_tickets if t["order_sn"] == target_order_sn]

        return {
            "test_name": "后厨消费幂等性防重复出纸测试",
            "total_received_messages": duplicate_count,
            "physical_printed_tickets_count": len(physical_printed),
            "duplicate_skipped_count": len([r for r in process_results if r["status"] == "DUPLICATE_IGNORED"]),
            "is_strictly_idempotent": (len(physical_printed) == 1)
        }
