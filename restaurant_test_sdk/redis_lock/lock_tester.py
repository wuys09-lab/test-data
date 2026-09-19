"""
Redis 分布式锁专项测试器 (lock_tester.py)
执行 100 线程并发竞争、Watchdog 自动续期、崩溃防死锁、Lua防误删与DB唯一索引兜底验证。
"""
import concurrent.futures
import time
from typing import Dict, Any, List

from restaurant_test_sdk.redis_lock.distributed_lock import (
    RedisEngineSimulator, RedisDistributedLock, LUA_RELEASE_LOCK_SCRIPT
)
from restaurant_test_sdk.client.mock_server import DiningMockServer
from restaurant_test_sdk.client.h5_order_client import H5OrderClient


class RedisLockTester:
    """Redis 分布式锁自动化专项验证器"""

    def __init__(self, redis_engine: RedisEngineSimulator = None, mock_server: DiningMockServer = None):
        self.engine = redis_engine or RedisEngineSimulator()
        self.server = mock_server or DiningMockServer()

    # 1. 100 并发线程抢锁与同桌下单防重复测试
    def run_concurrency_clash_test(self, store_id: str = "store_888",
                                   table_id: str = "table_06",
                                   concurrency: int = 100) -> Dict[str, Any]:
        """
        模拟同一桌台 100 个并发线程同时发起加锁与提交订单
        """
        lock_key = f"lock:order:table:{store_id}:{table_id}"
        success_list: List[str] = []
        fail_list: List[str] = []
        lock_held_times = 0
        
        # 准备桌台与菜品
        client_init = H5OrderClient(self.server, store_id, table_id, customer_count=2)
        client_init.scan_table()
        client_init.add_item_to_cart("dish_001", "中份", quantity=1)
        client_init.sync_cart()

        def worker_task(worker_id: int):
            nonlocal lock_held_times
            lock = RedisDistributedLock(self.engine, lock_key, ttl_ms=30000)
            acquired = lock.acquire(wait_timeout_ms=0)
            if acquired:
                lock_held_times += 1
                try:
                    # 模拟持有锁期间执行业务下单
                    time.sleep(0.02)
                    success_list.append(f"worker_{worker_id}")
                finally:
                    lock.release()
            else:
                fail_list.append(f"worker_{worker_id}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(worker_task, i) for i in range(concurrency)]
            concurrent.futures.wait(futures)

        return {
            "test_name": "100并发同桌抢锁互斥性测试",
            "lock_key": lock_key,
            "total_concurrency": concurrency,
            "acquired_count": len(success_list),
            "rejected_count": len(fail_list),
            "is_strictly_mutex": (len(success_list) == 1 and len(fail_list) == concurrency - 1),
            "success_workers": success_list
        }

    # 2. Redisson Watchdog 看门狗自动续期验证
    def test_watchdog_auto_renewal(self, store_id: str = "store_888",
                                   table_id: str = "table_06",
                                   hold_duration_sec: float = 0.35) -> Dict[str, Any]:
        """
        模拟业务耗时较长，验证看门狗后台线程自动发起 PEXPIRE 续期
        """
        lock_key = f"lock:order:table:{store_id}:{table_id}"
        # 设置短 TTL: 200ms，续期心跳: 80ms
        lock = RedisDistributedLock(
            self.engine, lock_key, ttl_ms=200, watchdog_interval_ms=80
        )
        
        acquired = lock.acquire()
        assert acquired, "初始获取锁失败"
        
        renewals_before = self.engine.metrics["watchdog_renewals"]
        # 保持业务执行一段时间（超过初始 TTL 200ms）
        time.sleep(hold_duration_sec)
        
        renewals_after = self.engine.metrics["watchdog_renewals"]
        remaining_ttl = self.engine.pttl(lock_key)
        
        # 释放锁
        released = lock.release()
        
        return {
            "test_name": "Redisson Watchdog 看门狗自动续期验证",
            "lock_key": lock_key,
            "hold_duration_sec": hold_duration_sec,
            "renewals_count": renewals_after - renewals_before,
            "remaining_ttl_ms": remaining_ttl,
            "is_lock_alive_before_release": remaining_ttl > 0,
            "watchdog_effective": (renewals_after > renewals_before),
            "released_safely": released
        }

    # 3. 进程异常崩溃防死锁与 TTL 自然到期恢复验证
    def test_crash_ttl_deadlock_prevention(self, store_id: str = "store_888",
                                           table_id: str = "table_06",
                                           short_ttl_ms: int = 150) -> Dict[str, Any]:
        """
        模拟持有锁的业务进程意外崩溃（看门狗死亡，未显式调用 release），
        验证锁在到达 TTL 后自动消亡，后续请求能正常加锁，避免系统永久死锁。
        """
        lock_key = f"lock:order:table:{store_id}:{table_id}"
        
        # 线程 1 获取锁
        client_1_lock = RedisDistributedLock(self.engine, lock_key, ttl_ms=short_ttl_ms)
        ok1 = client_1_lock.acquire()
        assert ok1, "线程1初次加锁失败"
        
        # 线程 1 发生致命异常 / 崩溃（停止续期，但不执行 release）
        client_1_lock.simulate_crash_without_release()
        
        # 此时线程 2 立即尝试加锁，预期失败（锁还在 TTL 内）
        client_2_lock = RedisDistributedLock(self.engine, lock_key, ttl_ms=1000)
        ok2_immediate = client_2_lock.acquire()
        
        # 等待锁的 TTL 到期
        time.sleep((short_ttl_ms + 50) / 1000.0)
        
        # 线程 2 再次尝试加锁，预期成功恢复
        ok2_after_ttl = client_2_lock.acquire()
        if ok2_after_ttl:
            client_2_lock.release()
            
        return {
            "test_name": "进程崩溃防死锁与TTL到期自愈验证",
            "lock_key": lock_key,
            "client_1_acquired": ok1,
            "client_2_blocked_during_ttl": not ok2_immediate,
            "client_2_recovered_after_ttl": ok2_after_ttl,
            "deadlock_prevented": (not ok2_immediate and ok2_after_ttl)
        }

    # 4. Lua 脚本防误删安全验证
    def test_safe_release_lua(self, store_id: str = "store_888",
                              table_id: str = "table_06") -> Dict[str, Any]:
        """
        验证释放锁时严格校验 random_value，严禁误删其他线程或客户端创建的锁
        """
        lock_key = f"lock:order:table:{store_id}:{table_id}"
        
        # 客户端 A 加锁
        lock_a = RedisDistributedLock(self.engine, lock_key, ttl_ms=10000)
        acquired_a = lock_a.acquire()
        assert acquired_a
        
        # 恶意/超时的客户端 B 企图用不同的 random_val 删除客户端 A 的锁
        rogue_random_val = "ROGUE_TOKEN_9999"
        del_res = self.engine.eval_lua_release(
            LUA_RELEASE_LOCK_SCRIPT, lock_key, rogue_random_val
        )
        
        # 验证此时锁依然安全属于客户端 A
        lock_a_still_holds = (self.engine.get(lock_key) == lock_a.random_val)
        
        # 客户端 A 正常释放
        released_a = lock_a.release()
        lock_now_cleared = (self.engine.get(lock_key) is None)
        
        return {
            "test_name": "Lua 脚本比对 random_value 防误删验证",
            "rogue_delete_rejected": (del_res == 0),
            "lock_a_protected": lock_a_still_holds,
            "owner_released_cleanly": (released_a and lock_now_cleared)
        }

    # 5. DB 唯一索引兜底验证 (当 Redis 锁被突破或失效时)
    def test_db_unique_constraint_fallback(self, store_id: str = "store_888",
                                           table_id: str = "table_06") -> Dict[str, Any]:
        """
        验证即使极端情况下绕过 Redis 分布式锁，数据库层的唯一索引约束 (uk_store_table_status)
        依然能够拦截并发脏写入，保证系统数据一致性。
        """
        client1 = H5OrderClient(self.server, store_id, table_id, customer_count=2)
        client1.scan_table()
        client1.add_item_to_cart("dish_001", "中份", quantity=1)
        client1.sync_cart()
        
        # 客户端 1 下单成功
        resp1 = client1.submit_order()
        
        # 客户端 2 绕过 Redis 锁，尝试向同桌台再下一单
        client2 = H5OrderClient(self.server, store_id, table_id, customer_count=2)
        client2.add_item_to_cart("dish_004", "标准碗", quantity=1)
        resp2 = client2.submit_order()
        
        return {
            "test_name": "数据库唯一索引兜底检验",
            "order_1_success": (resp1.get("code") == 200),
            "order_2_code": resp2.get("code"),
            "order_2_intercepted_by_db_uk": (resp2.get("code") == 4092),
            "fallback_effective": (resp2.get("code") == 4092)
        }
