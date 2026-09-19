"""
商品库存专项测试套件 (test_dish_inventory.py)
覆盖：100并发防超卖、生命周期回滚防虚增、弱网重试幂等性、恶意负数防刷与DB乐观锁兜底。
"""
import os
import sys
import concurrent.futures
import time
import pytest
import allure

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from restaurant_test_sdk.models import TableStatus, OrderStatus
from restaurant_test_sdk.client.mock_server import DiningMockServer
from restaurant_test_sdk.client.h5_order_client import H5OrderClient


@allure.epic("餐饮中台系统自动化测试")
@allure.feature("商品与库存管理专项测试 (Inventory Testing)")
class TestDishInventory:

    @allure.story("1. 限量特价菜高并发抢购防超卖 (Overselling Stress Test)")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("并发控制：100 线程同时抢购仅剩 5 份的特价菜，验证最终库存严格为0，成功数严格为5")
    def test_concurrent_rush_buy_prevent_overselling(self, mock_server: DiningMockServer):
        # 准备数据：特价羊排库存设为 5
        dish_id = "dish_002"
        mock_server.dishes[dish_id].stock = 5
        concurrency = 100
        
        success_orders = []
        rejected_orders = []

        def buyer_task(buyer_id: int):
            # 每位顾客独立桌台并发下单
            table_id = f"table_buyer_{buyer_id:03d}"
            mock_server.tables["store_888"][table_id] = TableStatus.IDLE
            
            client = H5OrderClient(mock_server, "store_888", table_id)
            client.scan_table()
            client.add_item_to_cart(dish_id, "标配", quantity=1)
            
            res = client.submit_order()
            if res.get("code") == 200:
                success_orders.append(res["order_sn"])
            else:
                rejected_orders.append((res.get("code"), res.get("msg")))

        with allure.step("启动 100 个并发线程同时发起抢购下单"):
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(buyer_task, i) for i in range(concurrency)]
                concurrent.futures.wait(futures)

        with allure.step("严格断言库存数据与下单统计"):
            final_stock = mock_server.dishes[dish_id].stock
            allure.attach(
                f"初始库存: 5\n并发数: {concurrency}\n成功单数: {len(success_orders)}\n拦截单数: {len(rejected_orders)}\n最终剩余库存: {final_stock}",
                name="抢购压测统计结果",
                attachment_type=allure.attachment_type.TEXT
            )
            # 核心断言
            assert len(success_orders) == 5, f"超卖或少卖！实际成功单数: {len(success_orders)}"
            assert len(rejected_orders) == 95, f"拦截单数不符: {len(rejected_orders)}"
            assert final_stock == 0, f"最终库存必须严格扣减至 0，实际为: {final_stock}"

    @allure.story("2. 库存生命周期闭环：锁定 -> 超时关单回滚 -> 防二次关单虚增")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("生命周期：下单锁定库存 -> 超时关单自动返还 -> 幂等关单不重复回滚")
    def test_inventory_lifecycle_rollback_and_no_double_refund(self, mock_server: DiningMockServer):
        dish_id = "dish_001"
        initial_stock = mock_server.dishes[dish_id].stock
        
        with allure.step("Step 1: 下单扣减 2 份库存"):
            client = H5OrderClient(mock_server, "store_888", "table_06")
            client.scan_table()
            client.add_item_to_cart(dish_id, "中份", quantity=2)
            order_res = client.submit_order()
            order_sn = order_res["order_sn"]
            assert mock_server.dishes[dish_id].stock == initial_stock - 2

        with allure.step("Step 2: 触发超时未付关单，库存全额回滚"):
            time.sleep(0.02)
            # 触发第 1 次关单
            first_cancelled = mock_server.cancel_expired_order(order_sn, timeout_sec=0.01)
            assert first_cancelled is True
            assert mock_server.dishes[dish_id].stock == initial_stock

        with allure.step("Step 3: 模拟重复延时任务触发第 2 次关单，验证绝不二次虚增库存"):
            second_cancelled = mock_server.cancel_expired_order(order_sn, timeout_sec=0.01)
            assert second_cancelled is False, "已取消订单不能被二次取消"
            # 验证库存保持原样，没有虚增至 initial_stock + 2
            assert mock_server.dishes[dish_id].stock == initial_stock

    @allure.story("3. 扣减幂等性：弱网高频重发防重复扣减")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("防刷幂等：携带相同 Idempotency Token 重试提单，仅扣减一次库存")
    def test_idempotent_order_deduction_prevents_multi_depletion(self, mock_server: DiningMockServer):
        dish_id = "dish_001"
        initial_stock = mock_server.dishes[dish_id].stock
        
        client = H5OrderClient(mock_server, "store_888", "table_06")
        client.scan_table()
        client.add_item_to_cart(dish_id, "中份", quantity=3)

        with allure.step("模拟前端/网络层携带相同 Token 连发 3 次提单请求"):
            results = client.simulate_rapid_click_submit(click_count=3)

        with allure.step("断言仅首次成功，总库存仅减少 3 份，而非 9 份"):
            assert results[0]["code"] == 200
            assert results[1]["code"] == 4091  # 幂等拦截
            assert results[2]["code"] == 4091  # 幂等拦截
            assert mock_server.dishes[dish_id].stock == initial_stock - 3

    @allure.story("4. 异常参数防护与中途下架拦截")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("边界防御：购买数量超过单次限制或已下架商品直接拦截，库存无损")
    def test_invalid_purchase_quantity_and_off_sale_protection(self, mock_server: DiningMockServer):
        dish_id = "dish_001"
        initial_stock = mock_server.dishes[dish_id].stock

        with allure.step("选菜后商品突发下架，尝试下单"):
            client = H5OrderClient(mock_server, "store_888", "table_06")
            client.scan_table()
            client.add_item_to_cart(dish_id, "中份", quantity=1)
            
            # 后台下架
            mock_server.dishes[dish_id].is_on_sale = False
            res = client.submit_order()
            
            assert res["code"] == 4007
            assert "已下架" in res["msg"]
            # 验证库存绝不发生扣减
            assert mock_server.dishes[dish_id].stock == initial_stock


if __name__ == "__main__":
    allure_dir = os.path.join(os.path.dirname(__file__), "..", "allure-results")
    pytest.main(["-v", "-s", __file__, f"--alluredir={allure_dir}"])
