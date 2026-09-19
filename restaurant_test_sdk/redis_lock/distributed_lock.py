"""
Redis 分布式锁核心实现 (distributed_lock.py)
实现 Redisson 规范：原子加锁 (SET NX PX)、看门狗自动续期 (Watchdog)、Lua 脚本防误删释放。
"""
import threading
import time
import uuid
from typing import Optional, Dict, Any


LUA_RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class RedisEngineSimulator:
    """
    全真模拟 Redis 核心指令：原子 SET NX PX、PTTL、PEXPIRE 与 Lua 脚本执行环境
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._store: Dict[str, str] = {}
        self._expire_at: Dict[str, float] = {}  # {key: timestamp_in_sec}
        
        # 监控指标
        self.metrics = {
            "set_nx_attempts": 0,
            "set_nx_successes": 0,
            "set_nx_failures": 0,
            "watchdog_renewals": 0,
            "lua_release_successes": 0,
            "lua_release_rejections": 0,
        }

    def _purge_expired(self, key: str):
        if key in self._expire_at:
            if time.time() >= self._expire_at[key]:
                self._store.pop(key, None)
                self._expire_at.pop(key, None)

    def set(self, key: str, value: str, nx: bool = False, px: Optional[int] = None) -> bool:
        """模拟 SET key value NX PX ttl_ms 原子指令"""
        with self._lock:
            self.metrics["set_nx_attempts"] += 1
            self._purge_expired(key)
            
            if nx and key in self._store:
                self.metrics["set_nx_failures"] += 1
                return False
            
            self._store[key] = value
            if px is not None:
                self._expire_at[key] = time.time() + (px / 1000.0)
            
            self.metrics["set_nx_successes"] += 1
            return True

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            self._purge_expired(key)
            return self._store.get(key)

    def pttl(self, key: str) -> int:
        """获取剩余毫秒 TTL"""
        with self._lock:
            self._purge_expired(key)
            if key not in self._store:
                return -2
            if key not in self._expire_at:
                return -1
            remaining = int((self._expire_at[key] - time.time()) * 1000)
            return max(0, remaining)

    def pexpire(self, key: str, px: int) -> bool:
        """为 Key 重设/续期过期时间 (毫秒)"""
        with self._lock:
            self._purge_expired(key)
            if key in self._store:
                self._expire_at[key] = time.time() + (px / 1000.0)
                self.metrics["watchdog_renewals"] += 1
                return True
            return False

    def eval_lua_release(self, script: str, key: str, expected_val: str) -> int:
        """模拟 Redis 执行 Lua 脚本安全释放锁"""
        with self._lock:
            self._purge_expired(key)
            current_val = self._store.get(key)
            if current_val == expected_val:
                self._store.pop(key, None)
                self._expire_at.pop(key, None)
                self.metrics["lua_release_successes"] += 1
                return 1
            else:
                self.metrics["lua_release_rejections"] += 1
                return 0


class RedisDistributedLock:
    """
    符合工业标准的 Redis 分布式锁，内建 Redisson 看门狗续期后台线程
    """

    def __init__(self, redis_engine: RedisEngineSimulator, lock_key: str,
                 ttl_ms: int = 30000, watchdog_interval_ms: int = 10000):
        self.engine = redis_engine
        self.lock_key = lock_key
        self.ttl_ms = ttl_ms
        self.watchdog_interval_ms = watchdog_interval_ms
        
        self.random_val: str = f"TOKEN_{uuid.uuid4().hex}"
        self.is_locked: bool = False
        
        # 看门狗守护线程控制
        self._stop_watchdog_event = threading.Event()
        self._watchdog_thread: Optional[threading.Thread] = None

    def acquire(self, wait_timeout_ms: int = 0) -> bool:
        """
        加锁尝试：使用原子 SET key random_val NX PX ttl
        """
        start = time.time()
        while True:
            # 执行原子 SET NX PX
            ok = self.engine.set(self.lock_key, self.random_val, nx=True, px=self.ttl_ms)
            if ok:
                self.is_locked = True
                self._start_watchdog()
                return True
            
            if wait_timeout_ms <= 0:
                return False
            
            elapsed = (time.time() - start) * 1000
            if elapsed >= wait_timeout_ms:
                return False
            
            time.sleep(0.01)

    def _start_watchdog(self):
        """启动看门狗守护线程自动续期"""
        self._stop_watchdog_event.clear()

        def _watchdog_loop():
            interval_sec = self.watchdog_interval_ms / 1000.0
            while not self._stop_watchdog_event.wait(timeout=interval_sec):
                if not self.is_locked:
                    break
                # 看门狗续期：重设 TTL 为初始 ttl_ms
                success = self.engine.pexpire(self.lock_key, self.ttl_ms)
                if not success:
                    # 锁已丢失或异常
                    break

        self._watchdog_thread = threading.Thread(target=_watchdog_loop, daemon=True)
        self._watchdog_thread.start()

    def release(self) -> bool:
        """
        安全释放锁：必须使用 Lua 脚本校验 random_val 是否等于自身持有值
        """
        # 先停止看门狗
        self._stop_watchdog_event.set()
        self.is_locked = False
        
        result = self.engine.eval_lua_release(
            LUA_RELEASE_LOCK_SCRIPT, self.lock_key, self.random_val
        )
        return result == 1

    def simulate_crash_without_release(self):
        """模拟进程崩溃（杀进程/严重异常中断）：看门狗立即死亡，锁不执行释放，由 Redis TTL 自然兜底防死锁"""
        self._stop_watchdog_event.set()
        self.is_locked = False

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(f"无法获取分布式锁: {self.lock_key}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
