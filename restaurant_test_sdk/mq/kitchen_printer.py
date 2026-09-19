"""
后厨打印机消费者服务与幂等去重引擎 (kitchen_printer.py)
实现出纸速率限制、消费幂等防重打、故障重试、死信转运与 DLQ 补偿重打。
"""
import threading
import time
from typing import List, Dict, Optional, Any

from restaurant_test_sdk.models import MQOrderMessage
from restaurant_test_sdk.mq.mq_broker import RabbitMQBrokerSimulator
from restaurant_test_sdk.redis_lock.distributed_lock import RedisEngineSimulator
from restaurant_test_sdk.config import config


class KitchenPrinterWorker:
    """后厨出纸打印消费者，模拟物理出纸限速与幂等性防护"""

    def __init__(self, broker: RabbitMQBrokerSimulator,
                 redis_engine: Optional[RedisEngineSimulator] = None,
                 print_duration_sec: float = 0.05,
                 max_retries: int = 3):
        self.broker = broker
        self.redis = redis_engine or RedisEngineSimulator()
        self.print_duration_sec = print_duration_sec
        self.max_retries = max_retries
        
        # 打印机运行状态
        self.is_online = True
        self.simulate_hardware_failure = False
        
        # 物理出纸记录
        self.printed_tickets: List[Dict[str, Any]] = []
        self.duplicate_skipped_count = 0
        self.retry_count_total = 0
        self._lock = threading.RLock()

    def process_one_message(self, queue_name: str = config.kitchen_queue) -> Optional[Dict[str, Any]]:
        """
        拉取单条消息并处理（含物理出纸、幂等校验、异常重试、死信转运）
        """
        with self._lock:
            msg = self.broker.basic_get(queue_name)
            if not msg:
                return None
            
            # 1. 模拟设备故障 / 宕机
            if not self.is_online or self.simulate_hardware_failure:
                self.retry_count_total += 1
                msg.retry_count += 1
                
                if msg.retry_count >= self.max_retries:
                    # 重试超限，进入死信队列 (DLQ)
                    self.broker.basic_nack(queue_name, msg.msg_id, requeue=False)
                    return {
                        "status": "DLQ_ROUTED",
                        "msg_id": msg.msg_id,
                        "order_sn": msg.order_sn,
                        "retry_count": msg.retry_count
                    }
                else:
                    # 重新入队重试
                    self.broker.basic_nack(queue_name, msg.msg_id, requeue=True)
                    return {
                        "status": "RETRY",
                        "msg_id": msg.msg_id,
                        "order_sn": msg.order_sn,
                        "retry_count": msg.retry_count
                    }

            # 2. 消费幂等性校验 (通过 Redis SETNX 校验 msg_id 或 order_sn)
            # 防止网络震荡或重试机制导致同一订单打印出两张相同纸质单
            idempotent_key = f"order:printed:{msg.order_sn}"
            acquired = self.redis.set(idempotent_key, "PRINTED", nx=True, px=86400 * 1000)
            
            if not acquired:
                # 重复投递的消息，拦截打印，直接 ACK
                self.duplicate_skipped_count += 1
                self.broker.basic_ack(queue_name, msg.msg_id)
                return {
                    "status": "DUPLICATE_IGNORED",
                    "msg_id": msg.msg_id,
                    "order_sn": msg.order_sn
                }

            # 3. 模拟后厨打印机物理出纸延时 (每秒约 1~2 张)
            if self.print_duration_sec > 0:
                time.sleep(self.print_duration_sec)

            # 4. 打印成功入库记录并 ACK
            ticket = {
                "ticket_no": f"TICKET_{len(self.printed_tickets)+1:04d}",
                "order_sn": msg.order_sn,
                "table_id": msg.table_id,
                "summary": msg.items_summary,
                "printed_at": time.time()
            }
            self.printed_tickets.append(ticket)
            self.broker.basic_ack(queue_name, msg.msg_id)

            return {
                "status": "PRINTED_SUCCESS",
                "ticket": ticket,
                "msg_id": msg.msg_id,
                "order_sn": msg.order_sn
            }

    def replay_from_dlq(self) -> List[Dict[str, Any]]:
        """
        后厨打印服务网络恢复后，从死信队列 (DLQ) 手动或定时拉取消息进行补打
        """
        repaired_results = []
        with self._lock:
            # 临时确保设备恢复正常
            orig_online = self.is_online
            orig_fail = self.simulate_hardware_failure
            self.is_online = True
            self.simulate_hardware_failure = False
            
            while True:
                res = self.process_one_message(queue_name=config.dlq_queue)
                if not res:
                    break
                repaired_results.append(res)
                
            self.is_online = orig_online
            self.simulate_hardware_failure = orig_fail
            
        return repaired_results
