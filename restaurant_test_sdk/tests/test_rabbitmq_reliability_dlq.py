"""
测试套件三：RabbitMQ 多端同步、积压与容灾专项测试
"""
import os
import sys
import pytest
import allure

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from restaurant_test_sdk.mq.mq_tester import MQTester


@allure.epic("餐饮中台系统自动化测试")
@allure.feature("RabbitMQ 消息可靠性、积压与容灾专项测试")
class TestRabbitMQReliabilityAndDLQ:

    @allure.story("1. 消息生产端可靠性验证")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("可靠投递：验证 ConfirmCallback 发布确认与 ReturnCallback 路由不可达异常捕获")
    def test_publisher_confirm_and_return_callback(self, mq_tester: MQTester):
        with allure.step("测试生产者发送消息并接收 ConfirmCallback 与 ReturnCallback 回调"):
            res = mq_tester.test_publisher_confirm_and_return()

        with allure.step("断言消息投递与路由异常捕获行为"):
            assert res["normal_publish_success"] is True
            assert res["normal_confirm_acked"] is True
            assert res["unroutable_caught_by_return_callback"] is True
            assert res["return_reply_code"] == 312

    @allure.story("2. 消息持久化与 Broker 重启容灾")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("持久化验证：Exchange/Queue durable=True 与 delivery_mode=2，节点重启消息不丢失")
    def test_broker_durability_and_restart(self, mq_tester: MQTester):
        with allure.step("投递持久化与非持久化消息，并模拟 Broker 宕机重启"):
            res = mq_tester.test_durability_and_restart()

        with allure.step("断言重启后持久化消息完好存活，非持久化消息被淘汰"):
            assert res["persistent_message_survived"] is True
            assert res["volatile_message_dropped"] is True
            assert res["durability_effective"] is True

    @allure.story("3. 500单瞬时涌入与慢消费者积压监控 (Backlog Testing)")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("积压与告警：模拟后厨物理出纸受限（1~2张/秒），500单瞬时涌入监控堆积与超时告警")
    def test_500_order_burst_backlog_and_alert(self, mq_tester: MQTester):
        with allure.step("瞬时注入 500 个订单消息，观察队列 Ready 堆积与消费限速"):
            res = mq_tester.test_500_order_burst_backlog_and_alert(burst_count=500)

        with allure.step("断言队列监控指标与5分钟未出单警报触发"):
            assert res["burst_count"] == 500
            assert res["peak_ready_messages"] == 500
            assert res["messages_backlog_detected"] is True
            assert res["partial_processed_count"] == 20
            assert res["timeout_alert_triggered"] is True
            assert res["timeout_unprinted_orders_count"] > 0

    @allure.story("4. 消费者宕机、死信 (DLQ) 流转与容灾补打")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("容灾闭环：打印机宕机 -> Unacked 重试 3 次 -> 转移 DLQ -> 钉钉告警 -> 恢复补打")
    def test_consumer_crash_retry_dlq_and_replay(self, mq_tester: MQTester):
        with allure.step("模拟打印机故障，触发 3 次重试失败后路由至 DLQ 并推送告警"):
            res = mq_tester.test_crash_retry_dlq_and_replay()

        with allure.step("断言死信队列接收到消息并触发了告警通知"):
            assert res["dlq_message_count"] == 1
            assert res["alert_triggered"] is True
            assert "死信告警" in res["latest_alert_content"]

        with allure.step("恢复打印机服务，验证从死信队列完成补偿补打并清空 DLQ"):
            assert res["replayed_tickets_count"] == 1
            assert res["dlq_cleared_after_repair"] is True

    @allure.story("5. 后厨消费幂等性防重打验证")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("消费幂等：同一订单重复投递 5 次，结合 Redis msg_id/order_sn 去重绝不出双张单")
    def test_consumer_idempotency_duplicate_prevention(self, mq_tester: MQTester):
        with allure.step("同一订单连续投递 5 次重复消息至打印机队列"):
            res = mq_tester.test_consumer_idempotency(duplicate_count=5)

        with allure.step("断言物理打印件数量严格为 1，其余 4 次重复消费被幂等拦截"):
            assert res["total_received_messages"] == 5
            assert res["physical_printed_tickets_count"] == 1
            assert res["duplicate_skipped_count"] == 4
            assert res["is_strictly_idempotent"] is True


if __name__ == "__main__":
    allure_dir = os.path.join(os.path.dirname(__file__), "..", "allure-results")
    pytest.main(["-v", "-s", __file__, f"--alluredir={allure_dir}"])
