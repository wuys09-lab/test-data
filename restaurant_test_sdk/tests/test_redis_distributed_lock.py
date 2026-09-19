"""
测试套件二：Redis 并发控制与分布式锁专项测试
"""
import os
import sys
import pytest
import allure

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from restaurant_test_sdk.redis_lock.lock_tester import RedisLockTester


@allure.epic("餐饮中台系统自动化测试")
@allure.feature("Redis 分布式锁与高并发专项测试")
class TestRedisDistributedLock:

    @allure.story("1. 100 线程高并发同桌抢单锁互斥测试")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("并发控制：同桌台 100 个并发线程同时抢锁提单，严格仅允许 1 线程加锁成功")
    def test_100_concurrency_table_lock_mutex(self, lock_tester: RedisLockTester):
        with allure.step("启动 100 个线程对 store_888:table_06 执行并发抢锁"):
            res = lock_tester.run_concurrency_clash_test(
                store_id="store_888", table_id="table_06", concurrency=100
            )

        with allure.step("断言并发互斥指标：严格1单成功，99单被分布式锁拦截"):
            assert res["total_concurrency"] == 100
            assert res["acquired_count"] == 1, f"实际抢锁成功数: {res['acquired_count']}"
            assert res["rejected_count"] == 99
            assert res["is_strictly_mutex"] is True

    @allure.story("2. Redisson Watchdog 看门狗自动续期验证")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("锁续期：耗时业务下看门狗后台守护线程自动执行 PEXPIRE 续期，防止锁提前失效")
    def test_redisson_watchdog_auto_renewal(self, lock_tester: RedisLockTester):
        with allure.step("加锁并执行耗时业务（持续时间超过初始 TTL 设置）"):
            res = lock_tester.test_watchdog_auto_renewal(
                store_id="store_888", table_id="table_06", hold_duration_sec=0.25
            )

        with allure.step("验证看门狗后台续期次数与 TTL 存活状态"):
            assert res["watchdog_effective"] is True
            assert res["renewals_count"] >= 1, "看门狗未触发续期操作"
            assert res["is_lock_alive_before_release"] is True
            assert res["released_safely"] is True

    @allure.story("3. 进程崩溃防死锁与 TTL 自动释放")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("防死锁：持有锁进程突发崩溃无 release，验证 TTL 到期后锁自动释放自愈")
    def test_crash_ttl_deadlock_recovery(self, lock_tester: RedisLockTester):
        with allure.step("模拟线程 1 加锁后进程崩溃（看门狗终止，未显式释放锁）"):
            res = lock_tester.test_crash_ttl_deadlock_prevention(
                store_id="store_888", table_id="table_06", short_ttl_ms=100
            )

        with allure.step("验证 TTL 到期前其他线程被阻拦，到期后自动消亡并恢复加锁"):
            assert res["client_1_acquired"] is True
            assert res["client_2_blocked_during_ttl"] is True
            assert res["client_2_recovered_after_ttl"] is True
            assert res["deadlock_prevented"] is True

    @allure.story("4. Lua 脚本防误删安全验证")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("安全释放：验证必须使用 Lua 脚本校验 random_value，严禁误删其他客户端的锁")
    def test_lua_safe_release(self, lock_tester: RedisLockTester):
        with allure.step("客户端 A 持有锁，恶意客户端 B 尝试删除客户端 A 的锁"):
            res = lock_tester.test_safe_release_lua(store_id="store_888", table_id="table_06")

        with allure.step("断言恶意删除被拒绝，且属主客户端能正常原子释放"):
            assert res["rogue_delete_rejected"] is True
            assert res["lock_a_protected"] is True
            assert res["owner_released_cleanly"] is True

    @allure.story("5. 数据库唯一索引兜底防御")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("后端兜底：假定 Redis 锁极端失效/穿透，数据库 uk_store_table_status 唯一约束杜绝脏数据")
    def test_db_unique_index_fallback(self, lock_tester: RedisLockTester):
        with allure.step("绕过 Redis 分布式锁，尝试对同桌台同时生成两个待支付活动订单"):
            res = lock_tester.test_db_unique_constraint_fallback(store_id="store_888", table_id="table_06")

        with allure.step("断言数据库层唯一约束成功拦截第 2 张重复订单"):
            assert res["order_1_success"] is True
            assert res["order_2_intercepted_by_db_uk"] is True
            assert res["fallback_effective"] is True


if __name__ == "__main__":
    allure_dir = os.path.join(os.path.dirname(__file__), "..", "allure-results")
    pytest.main(["-v", "-s", __file__, f"--alluredir={allure_dir}"])
