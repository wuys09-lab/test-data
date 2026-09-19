"""
Pytest 共享 Fixtures 配置 (conftest.py)
"""
import pytest
from restaurant_test_sdk.client.mock_server import DiningMockServer
from restaurant_test_sdk.client.h5_order_client import H5OrderClient
from restaurant_test_sdk.redis_lock.distributed_lock import RedisEngineSimulator
from restaurant_test_sdk.redis_lock.lock_tester import RedisLockTester
from restaurant_test_sdk.mq.mq_broker import RabbitMQBrokerSimulator
from restaurant_test_sdk.mq.kitchen_printer import KitchenPrinterWorker
from restaurant_test_sdk.mq.mq_tester import MQTester


@pytest.fixture
def mock_server():
    """每个测试函数拥有独立干净的业务服务器实例"""
    return DiningMockServer()


@pytest.fixture
def h5_client(mock_server):
    """默认 H5 顾客端 Client"""
    return H5OrderClient(mock_server, store_id="store_888", table_id="table_06", customer_count=2)


@pytest.fixture
def redis_engine():
    """独立 Redis 核心模拟引擎"""
    return RedisEngineSimulator()


@pytest.fixture
def lock_tester(redis_engine, mock_server):
    """Redis 分布式锁专项测试器"""
    return RedisLockTester(redis_engine=redis_engine, mock_server=mock_server)


@pytest.fixture
def mq_broker():
    """RabbitMQ 核心模拟代理"""
    return RabbitMQBrokerSimulator()


@pytest.fixture
def mq_tester(mq_broker, redis_engine):
    """RabbitMQ 消息可靠性与容灾专项测试器"""
    printer = KitchenPrinterWorker(mq_broker, redis_engine=redis_engine, print_duration_sec=0.005)
    return MQTester(broker=mq_broker, printer=printer, redis_engine=redis_engine)
