"""
测试套件一：H5 下单全流程测试（正向业务流与四大异常边界）
"""
import os
import sys
import time
import pytest
import allure

# 自动将项目根目录加入 sys.path，支持直接通过 python 脚本命令执行
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from restaurant_test_sdk.models import TableStatus, MealPeriod, OrderStatus
from restaurant_test_sdk.client.mock_server import DiningMockServer
from restaurant_test_sdk.client.h5_order_client import H5OrderClient


@allure.epic("餐饮中台系统自动化测试")
@allure.feature("H5 移动端点餐全流程与异常边界专项")
class TestH5OrderWorkflow:

    @allure.story("1. 正常业务流 (Happy Path)")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("正向流程：扫码开台 -> 协同加菜 -> 优惠券算价快照 -> 幂等下单 -> 微信支付 -> 触发厨打")
    def test_h5_happy_path_complete_workflow(self, mock_server):
        with allure.step("Step 1: 扫码开台并校验桌台状态"):
            client = H5OrderClient(mock_server, store_id="store_888", table_id="table_06", customer_count=2)
            scan_res = client.scan_table()
            assert scan_res["code"] == 200
            assert scan_res["mode"] == "OPEN_TABLE"
            assert scan_res["table_status"] == TableStatus.DINING

        with allure.step("Step 2: 依据午市餐段加载有效菜单"):
            menu_res = client.fetch_menu(MealPeriod.LUNCH)
            assert menu_res["code"] == 200
            dish_ids = [d["dish_id"] for d in menu_res["dishes"]]
            assert "dish_001" in dish_ids  # 酸菜鱼
            assert "dish_003" not in dish_ids  # 鲜虾小笼包仅早市，午市不应出现

        with allure.step("Step 3: 选菜配置多规格、属性做法与加料组合"):
            # 招牌酸菜鱼：基准 88 + 大份 20 + 加金针菇 5 = 113 元
            item1 = client.add_item_to_cart(
                dish_id="dish_001",
                spec_name="大份",
                chosen_attributes=["微辣", "免麻"],
                chosen_extras=["加金针菇"],
                quantity=1
            )
            assert item1.unit_price == 113.0
            assert item1.subtotal == 113.0

            # 甜品冰汤圆：基准 16 + 加小圆子 2 = 18 元
            item2 = client.add_item_to_cart(
                dish_id="dish_004",
                spec_name="标准碗",
                chosen_attributes=["少糖", "去冰"],
                chosen_extras=["加小圆子"],
                quantity=1
            )
            assert item2.unit_price == 18.0

        with allure.step("Step 4: 多人同桌协同共享购物车同步"):
            sync_res = client.sync_cart()
            assert sync_res["code"] == 200
            assert sync_res["total_items"] == 2

        with allure.step("Step 5: 价格快照计算 (原价 131 - 优惠券 20 + 2人餐位费 6 = 实付 117)"):
            snapshot = client.calculate_price(coupon_id="COUPON_100_MINUS_20")
            assert snapshot.original_total == 131.0
            
            assert snapshot.discount_amount == 20.0
            assert snapshot.tableware_fee == 6.0
            assert snapshot.actual_pay_amount == 117.0
            assert snapshot.min_consume_satisfied is True

        with allure.step("Step 6: 携带防重令牌提交订单与锁定库存"):
            order_res = client.submit_order(coupon_id="COUPON_100_MINUS_20")
            assert order_res["code"] == 200
            assert "order_sn" in order_res
            order_sn = order_res["order_sn"]
            assert client.get_order_status(order_sn) == OrderStatus.PENDING_PAY

        with allure.step("Step 7: 调起微信支付并接收异步回调，触发后厨出票 MQ 消息"):
            pay_res = client.simulate_pay(order_sn, channel="WECHAT_PAY", success=True)
            assert pay_res["code"] == 200
            assert client.get_order_status(order_sn) == OrderStatus.PAID
            assert "mq_message" in pay_res
            assert pay_res["mq_message"].order_sn == order_sn

    @allure.story("2. 异常场景 - 商品与库存变动")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("异常：选菜后菜品下架、改价或限量特价菜秒杀超卖拦截")
    def test_dish_stock_and_price_tampering_interception(self, mock_server):
        client = H5OrderClient(mock_server, store_id="store_888", table_id="table_06")
        client.scan_table()

        with allure.step("场景 A: 选菜后后台突发下架商品"):
            client.add_item_to_cart("dish_001", "中份", quantity=1)
            mock_server.dishes["dish_001"].is_on_sale = False  # 后台下架
            res = client.submit_order()
            assert res["code"] == 4007
            assert "已下架" in res["msg"]

        # 恢复上架，准备场景 B
        mock_server.dishes["dish_001"].is_on_sale = True

        with allure.step("场景 B: 选菜后后台修改价格"):
            client.cart_items = []
            client.add_item_to_cart("dish_001", "中份", quantity=1)  # 此时单价 88
            mock_server.dishes["dish_001"].base_price = 98.0  # 后台提价至 98
            res = client.submit_order()
            assert res["code"] == 4008
            assert "价格发生变动" in res["msg"]

        # 恢复价格，准备场景 C
        mock_server.dishes["dish_001"].base_price = 88.0

        with allure.step("场景 C: 限量特价菜仅剩1份，并发多人抢购防超卖"):
            # 特价羊排 dish_002 仅剩 1 份
            client_buyer_1 = H5OrderClient(mock_server, "store_888", "table_01")
            client_buyer_1.scan_table()
            client_buyer_1.add_item_to_cart("dish_002", "标配", quantity=1)
            
            client_buyer_2 = H5OrderClient(mock_server, "store_888", "table_02")
            client_buyer_2.scan_table()
            client_buyer_2.add_item_to_cart("dish_002", "标配", quantity=1)

            # 买家 1 率先下单成功
            res1 = client_buyer_1.submit_order()
            assert res1["code"] == 200

            # 买家 2 慢一步，库存已被扣尽，拦截并提示库存不足
            res2 = client_buyer_2.submit_order()
            assert res2["code"] == 4009
            assert "库存不足" in res2["msg"]
            assert mock_server.dishes["dish_002"].stock == 0  # 库存严格不超卖

    @allure.story("3. 异常场景 - 桌台状态突发变动")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("异常：顾客正在选菜，服务员在 POS 上操作清台/并桌/换桌拦截")
    def test_table_status_dynamic_change_interception(self, mock_server):
        client = H5OrderClient(mock_server, store_id="store_888", table_id="table_06")
        client.scan_table()
        client.add_item_to_cart("dish_001", "中份", quantity=1)

        with allure.step("服务员在 POS 机上对当前桌台执行清台操作"):
            mock_server.tables["store_888"]["table_06"] = TableStatus.CLEARING

        with allure.step("顾客点击立即下单，系统拦截并提示桌台状态已变更"):
            order_res = client.submit_order()
            assert order_res["code"] == 4005
            assert "桌台状态已变更" in order_res["msg"]

    @allure.story("4. 异常场景 - 弱网连击与防抖幂等")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("异常：弱网连续快速点击立即下单，防抖与幂等令牌拦截生成重复单")
    def test_weak_network_rapid_clicks_idempotency(self, mock_server):
        client = H5OrderClient(mock_server, store_id="store_888", table_id="table_06")
        client.scan_table()
        client.add_item_to_cart("dish_001", "中份", quantity=1)

        with allure.step("模拟前端/弱网连续点击 3 次立即下单"):
            results = client.simulate_rapid_click_submit(click_count=3)
            assert len(results) == 3
            
            # 第 1 次成功下单
            assert results[0]["code"] == 200
            order_sn_1 = results[0]["order_sn"]

            # 第 2、3 次被后端基于幂等 Token 严格拦截
            assert results[1]["code"] == 4091
            assert results[2]["code"] == 4091
            assert "重复下单" in results[1]["msg"]
            assert results[1]["order_sn"] == order_sn_1

    @allure.story("5. 异常场景 - 支付超时关单与主动对账补单")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("异常：待支付超时触发延时任务自动关单退还库存；延迟扣款触发对账补单")
    def test_payment_timeout_cancel_and_reconciliation(self, mock_server):
        client = H5OrderClient(mock_server, store_id="store_888", table_id="table_06")
        client.scan_table()
        
        initial_stock = mock_server.dishes["dish_001"].stock
        client.add_item_to_cart("dish_001", "中份", quantity=2)
        order_res = client.submit_order()
        order_sn = order_res["order_sn"]
        
        assert mock_server.dishes["dish_001"].stock == initial_stock - 2

        with allure.step("模拟超时未支付，延时任务关单并回滚库存"):
            # 延时 0.05 秒，设置超时阈值为 0.01 秒
            time.sleep(0.05)
            cancelled = mock_server.cancel_expired_order(order_sn, timeout_sec=0.01)
            assert cancelled is True
            assert client.get_order_status(order_sn) == OrderStatus.CANCELLED
            # 验证库存已全额回滚
            assert mock_server.dishes["dish_001"].stock == initial_stock

        with allure.step("模拟用户实则已扣款但因第三方延迟回调，系统对账并自动补单"):
            reconcile_res = mock_server.reconcile_and_repair_order(order_sn, channel_payment_status=True)
            assert reconcile_res["code"] == 200
            assert "补单" in reconcile_res["msg"]
            assert client.get_order_status(order_sn) == OrderStatus.PAID


if __name__ == "__main__":
    # 支持在终端直接通过 python test_h5_order_workflow.py 执行
    allure_dir = os.path.join(os.path.dirname(__file__), "..", "allure-results")
    pytest.main(["-v", "-s", __file__, f"--alluredir={allure_dir}"])
