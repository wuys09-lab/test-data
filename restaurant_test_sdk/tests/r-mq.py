# -*- coding: utf-8 -*-
"""
RabbitMQ 死信队列 (DLX/DLQ) 单元测试用例
"""
import json
import pytest


class MockMethodFrame:
    """模拟 RabbitMQ 基础属性帧"""
    def __init__(self, delivery_tag: int = 1):
        self.delivery_tag = delivery_tag


class MockRabbitMQChannel:
    """
    RabbitMQ Channel (Pika 接口标准模拟)
    支持交换机/队列声明、绑定、投递、拉取消费、NACK 拒绝与死信转发路由 (DLX)
    """
    def __init__(self):
        self.exchanges = {}
        self.queues = {}
        self.queue_args = {}
        self.bindings = {}
        self.unacked = {}
        self._delivery_counter = 0

    def exchange_declare(self, exchange: str, exchange_type: str = 'direct', **kwargs):
        self.exchanges[exchange] = {"type": exchange_type}

    def queue_declare(self, queue: str, arguments: dict = None, **kwargs):
        if queue not in self.queues:
            self.queues[queue] = []
        if arguments:
            self.queue_args[queue] = arguments

    def queue_bind(self, queue: str, exchange: str, routing_key: str = "", **kwargs):
        self.bindings[(exchange, routing_key)] = queue

    def queue_purge(self, queue: str):
        if queue in self.queues:
            self.queues[queue].clear()

    def basic_publish(self, exchange: str, routing_key: str, body: str, **kwargs):
        payload = body.encode('utf-8') if isinstance(body, str) else body
        if exchange == "":
            target_queue = routing_key
        else:
            target_queue = self.bindings.get((exchange, routing_key))

        if target_queue and target_queue in self.queues:
            self.queues[target_queue].append(payload)

    def basic_get(self, queue: str, auto_ack: bool = False):
        if queue not in self.queues or not self.queues[queue]:
            return None, None, None

        payload = self.queues[queue].pop(0)
        self._delivery_counter += 1
        tag = self._delivery_counter

        if not auto_ack:
            self.unacked[tag] = (queue, payload)

        return MockMethodFrame(delivery_tag=tag), None, payload

    def basic_nack(self, delivery_tag: int, requeue: bool = False):
        if delivery_tag not in self.unacked:
            return

        src_queue, payload = self.unacked.pop(delivery_tag)
        if requeue:
            self.queues[src_queue].insert(0, payload)
        else:
            # 触发死信流转 (x-dead-letter-exchange)
            args = self.queue_args.get(src_queue, {})
            dlx_exchange = args.get('x-dead-letter-exchange')
            dlx_routing_key = args.get('x-dead-letter-routing-key', '')

            if dlx_exchange:
                target_dlx_queue = self.bindings.get((dlx_exchange, dlx_routing_key))
                if target_dlx_queue and target_dlx_queue in self.queues:
                    self.queues[target_dlx_queue].append(payload)


@pytest.fixture
def mq_channel():
    """提供 RabbitMQ 通道测试固件"""
    return MockRabbitMQChannel()


def test_failed_message_enter_dead_letter_queue(mq_channel):
    """测试用例 2: 验证业务处理失败拒绝后，消息流向死信队列"""

    DLX_EXCHANGE = "dlx.exchange"
    DLX_QUEUE = "order.dlx.queue"
    NORMAL_QUEUE = "order.retry.queue"

    # 1. 配置死信交换机和死信队列
    mq_channel.exchange_declare(exchange=DLX_EXCHANGE, exchange_type='direct')
    mq_channel.queue_declare(queue=DLX_QUEUE)
    mq_channel.queue_bind(queue=DLX_QUEUE, exchange=DLX_EXCHANGE, routing_key="dlx.key")

    # 2. 声明正常队列，并绑定死信参数（x-dead-letter-exchange）
    queue_args = {
        'x-dead-letter-exchange': DLX_EXCHANGE,
        'x-dead-letter-routing-key': "dlx.key"
    }
    mq_channel.queue_declare(queue=NORMAL_QUEUE, arguments=queue_args)
    mq_channel.queue_purge(queue=NORMAL_QUEUE)
    mq_channel.queue_purge(queue=DLX_QUEUE)

    # 3. 往正常队列投递一条消息
    mq_channel.basic_publish(
        exchange="",
        routing_key=NORMAL_QUEUE,
        body=json.dumps({"order_id": "ERROR_ORDER_999"})
    )

    # 4. 模拟消费者处理异常：拉取消息并 NACK 拒绝，且 requeue=False (不重回原队列)
    method_frame, _, body = mq_channel.basic_get(queue=NORMAL_QUEUE, auto_ack=False)
    assert method_frame is not None

    # 拒绝消息
    mq_channel.basic_nack(delivery_tag=method_frame.delivery_tag, requeue=False)

    # 5. 验证死信队列：死信队列中应当收到了这条被拒绝的消息
    dlx_method, _, dlx_body = mq_channel.basic_get(queue=DLX_QUEUE, auto_ack=True)
    assert dlx_method is not None, "消息未成功转入死信队列！"
    assert json.loads(dlx_body.decode('utf-8'))["order_id"] == "ERROR_ORDER_999"


if __name__ == "__main__":
    channel = MockRabbitMQChannel()
    test_failed_message_enter_dead_letter_queue(channel)
    print("✅ [r-mq.py] 执行成功：消息被 NACK 拒绝后，已成功通过 DLX 流入死信队列 order.dlx.queue！")