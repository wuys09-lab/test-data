"""
全局测试与配置管理模块 (config.py)
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class SDKConfig:
    # 基础服务与门店配置
    base_url: str = "http://api.restaurant.local"
    default_store_id: str = "store_888"
    default_table_id: str = "table_06"
    
    # 支付与订单超时配置
    order_pay_timeout_sec: int = 15 * 60  # 生产 15 分钟，测试中可动态缩短
    test_order_pay_timeout_sec: float = 1.5  # 模拟环境快速关单验证时长
    
    # Redis 分布式锁配置
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    lock_key_prefix: str = "lock:order:table"
    lock_ttl_ms: int = 30000  # 30 秒默认 TTL
    watchdog_heartbeat_ms: int = 10000  # 看门狗每 10 秒续期一次
    
    # RabbitMQ 消息队列与容灾配置
    rabbitmq_host: str = "127.0.0.1"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_pass: str = "guest"
    
    order_exchange: str = "order.event.exchange"
    order_routing_key: str = "order.paid.kitchen"
    kitchen_queue: str = "kitchen.printer.queue"
    
    # 死信与重试配置
    dlx_exchange: str = "dlx.order.exchange"
    dlx_routing_key: str = "dlx.kitchen.print"
    dlq_queue: str = "dlq.kitchen.printer.queue"
    max_retry_times: int = 3
    
    # 慢消费者模拟配置 (后厨物理出纸限速)
    printer_speed_sec: float = 0.05  # 每张单打印耗时 (测试模拟加速，生产通常0.5~1.0s)
    printer_backlog_alert_threshold: int = 50  # 积压警报水位线
    order_print_timeout_sec: float = 300.0  # 5分钟未出单超时报警阈值
    
    # 告警通道模拟 Webhook
    alert_webhook_url: str = "https://oapi.dingtalk.com/robot/send?access_token=test_token"


# 单例默认配置
config = SDKConfig()
