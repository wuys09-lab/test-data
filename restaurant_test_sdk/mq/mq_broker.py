
"""
RabbitMQ 消息中间件全真模拟与可靠性引擎 (mq_broker.py)
实现 Publisher ConfirmCallback、ReturnCallback、持久化、死信交换机 (DLX/DLQ) 与监控指标统计。
"""
import copy
import threading
import time
from typing import Dict, List, Optional, Callable, Any

from restaurant_test_sdk.models import MQOrderMessage
from restaurant_test_sdk.config import config


class RabbitMQBrokerSimulator:
    """RabbitMQ 核心代理模拟器"""

    def __init__(self):
        self._lock = threading.RLock()
        
        # 交换机与队列元数据 (durable)
        self.exchanges: Dict[str, Dict[str, Any]] = {
            config.order_exchange: {"type": "direct", "durable": True},
            config.dlx_exchange: {"type": "direct", "durable": True}
        }
        
        # 队列存储: {queue_name: [MQOrderMessage]}
        self.queues: Dict[str, List[MQOrderMessage]] = {
            config.kitchen_queue: [],
            config.dlq_queue: []
        }
        
        # 队列元信息配置 (包含死信配置)
        self.queue_configs: Dict[str, Dict[str, Any]] = {
            config.kitchen_queue: {
                "durable": True,
                "x-dead-letter-exchange": config.dlx_exchange,
                "x-dead-letter-routing-key": config.dlx_routing_key,
                "max-length": 10000
            },
            config.dlq_queue: {
                "durable": True
            }
        }
        
        # 绑定关系: {exchange: {routing_key: target_queue}}
        self.bindings: Dict[str, Dict[str, str]] = {
            config.order_exchange: {
                config.order_routing_key: config.kitchen_queue
            },
            config.dlx_exchange: {
                config.dlx_routing_key: config.dlq_queue
            }
        }
        
        # Unacked 消费中的消息: {queue_name: {msg_id: MQOrderMessage}}
        self.unacked_messages: Dict[str, Dict[str, MQOrderMessage]] = {
            config.kitchen_queue: {},
            config.dlq_queue: {}
        }
        
        # 回调勾子
        self.confirm_callback: Optional[Callable[[bool, Optional[str]], None]] = None
        self.return_callback: Optional[Callable[[MQOrderMessage, int, str, str, str], None]] = None
        
        # 外部告警通道收集 (钉钉/企业微信 Webhook 记录)
        self.alert_notifications: List[Dict[str, Any]] = []

    # 1. 注册发布者确认与返回回调
    def set_confirm_callback(self, callback: Callable[[bool, Optional[str]], None]):
        self.confirm_callback = callback

    def set_return_callback(self, callback: Callable[[MQOrderMessage, int, str, str, str], None]):
        self.return_callback = callback

    # 2. 消息发送与路由
    def basic_publish(self, exchange: str, routing_key: str, message: MQOrderMessage) -> bool:
        """发送订单事件消息至 RabbitMQ"""
        with self._lock:
            # 校验 Exchange 是否存在
            if exchange not in self.exchanges:
                if self.confirm_callback:
                    self.confirm_callback(False, f"Exchange '{exchange}' 不存在")
                return False
            
            # 路由匹配校验
            target_queue = self.bindings.get(exchange, {}).get(routing_key)
            if not target_queue:
                # 路由不可达，触发 ReturnCallback
                if self.return_callback:
                    self.return_callback(
                        message,
                        312,
                        "NO_ROUTE",
                        exchange,
                        routing_key
                    )
                # 若设置了 mandatory，此时 ConfirmCallback 依然可以确认到达 Broker
                if self.confirm_callback:
                    self.confirm_callback(True, "到达Broker但路由不可达，已触发ReturnCallback")
                return False
            
            # 成功路由入队
            msg_copy = copy.deepcopy(message)
            self.queues[target_queue].append(msg_copy)
            
            # 触发 ConfirmCallback (ACK 成功)
            if self.confirm_callback:
                self.confirm_callback(True, None)
            
            return True

    # 3. 消费者拉取与 ACK / NACK 控制
    def basic_get(self, queue_name: str) -> Optional[MQOrderMessage]:
        """消费者拉取单条消息并置为 Unacked 状态"""
        with self._lock:
            q = self.queues.get(queue_name, [])
            if not q:
                return None
            msg = q.pop(0)
            self.unacked_messages[queue_name][msg.msg_id] = msg
            return msg

    def basic_ack(self, queue_name: str, msg_id: str) -> bool:
        """消费确认，从 unacked 中清除"""
        with self._lock:
            if msg_id in self.unacked_messages.get(queue_name, {}):
                del self.unacked_messages[queue_name][msg_id]
                return True
            return False

    def basic_nack(self, queue_name: str, msg_id: str, requeue: bool = False) -> bool:
        """消费异常拒绝：requeue=True 重回队列，requeue=False 进入死信交换机 (DLX)"""
        with self._lock:
            if msg_id not in self.unacked_messages.get(queue_name, {}):
                return False
            
            msg = self.unacked_messages[queue_name].pop(msg_id)
            if requeue:
                # 重回原队列头部
                self.queues[queue_name].insert(0, msg)
            else:
                # 路由到死信队列
                q_cfg = self.queue_configs.get(queue_name, {})
                dlx = q_cfg.get("x-dead-letter-exchange")
                dlk = q_cfg.get("x-dead-letter-routing-key")
                if dlx and dlk:
                    dlq = self.bindings.get(dlx, {}).get(dlk)
                    if dlq and dlq in self.queues:
                        self.queues[dlq].append(msg)
                        self._trigger_alert(
                            f"【死信告警】订单 {msg.order_sn} 打印消费重试失败，已转入死信队列 {dlq}！"
                        )
            return True

    # 4. 告警推送
    def _trigger_alert(self, content: str):
        notification = {
            "timestamp": time.time(),
            "content": content,
            "webhook": config.alert_webhook_url
        }
        self.alert_notifications.append(notification)

    # 5. 模拟 Broker 节点重启 (持久化校验)
    def simulate_broker_restart(self):
        """模拟 RabbitMQ 节点重启，校验持久化队列与消息能否存活"""
        with self._lock:
            # 清理非持久化队列和非持久化消息 (delivery_mode != 2)
            for q_name, msg_list in list(self.queues.items()):
                cfg = self.queue_configs.get(q_name, {})
                if not cfg.get("durable", False):
                    self.queues[q_name] = []
                else:
                    # 保留持久化消息 (delivery_mode == 2)
                    self.queues[q_name] = [m for m in msg_list if m.delivery_mode == 2]
            
            # 正在消费中的 unacked 消息未被 ACK，重启后重回 Ready 队列
            for q_name, unack_dict in self.unacked_messages.items():
                for msg in unack_dict.values():
                    if msg.delivery_mode == 2:
                        self.queues[q_name].append(msg)
                self.unacked_messages[q_name].clear()

    # 6. Management API 监控数据采集
    def get_queue_metrics(self, queue_name: str) -> Dict[str, Any]:
        with self._lock:
            ready_count = len(self.queues.get(queue_name, []))
            unacked_count = len(self.unacked_messages.get(queue_name, {}))
            return {
                "queue_name": queue_name,
                "messages_ready": ready_count,
                "messages_unacknowledged": unacked_count,
                "messages_total": ready_count + unacked_count,
                "dlq_messages_count": len(self.queues.get(config.dlq_queue, [])),
                "alert_count": len(self.alert_notifications)
            }
