# -*- coding: utf-8 -*-
"""
智慧餐饮订单管理与 BI 结算看板 Web UI 自动化测试用例 (ui_test.py)
技术栈: Python + Selenium + Pytest + POM (Page Object Model) + Allure
"""
import os
import sys
import pytest
import allure

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from restaurant_test_sdk.tests.web_tesing.pages.dashboard_page import DashboardPage


@allure.epic("智慧餐饮中台系统 Web UI 自动化测试")
@allure.feature("订单管理与 BI 结算对账看板端到端回归测试")
class TestOrderBiDashboardUI:
    """看板核心功能 UI 自动化测试套件"""

    @allure.story("1. 页面基本元素与 KPI 概览卡片验证")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("验证看板标题、当前门店以及 6 大核心 KPI 指标卡数据呈现")
    def test_01_dashboard_title_and_kpi_overview(self, dashboard_page: DashboardPage):
        with allure.step("1. 检查页面 Title 和主标题"):
            assert "智慧餐饮订单管理与 BI 结算对账看板" in dashboard_page.get_title()
            brand_title = dashboard_page.get_brand_title()
            assert "智慧餐饮中台 · 订单与 BI 结算看板" in brand_title

        with allure.step("2. 检查当前门店标签"):
            store_name = dashboard_page.get_current_store()
            assert "store_888" in store_name

        with allure.step("3. 校验顶部 6 大核心 KPI 指标卡初始值有效性"):
            kpis = dashboard_page.get_kpi_summary()
            assert kpis["gmv"].startswith("￥"), f"GMV 格式不正确: {kpis['gmv']}"
            assert int(kpis["valid_orders"]) > 0, "有效出单总量应大于 0"
            assert int(kpis["pending_count"]) >= 0, "待支付单量应合法"
            assert kpis["aov"].startswith("￥"), "客单价 AOV 应带货币符号"
            assert "%" in kpis["cancel_ratio"], "取消率应带百分比符号"

    @allure.story("2. 订单列表检索与状态多维筛选")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("验证按关键字检索桌号以及按 CANCELLED / PAID 状态筛选过滤订单列表")
    def test_02_order_filter_by_keyword_and_status(self, dashboard_page: DashboardPage):
        with allure.step("1. 按桌号关键字 'table_01' 进行检索过滤"):
            dashboard_page.search_orders("table_01")
            count_table_01 = dashboard_page.get_rendered_order_count()
            assert count_table_01 > 0, "应能检索到包含 table_01 的订单"

        with allure.step("2. 清空搜索词，并按状态筛选 'CANCELLED' (已取消) 订单"):
            dashboard_page.search_orders("")
            dashboard_page.filter_by_status("CANCELLED")
            cancelled_count = dashboard_page.get_rendered_order_count()
            assert cancelled_count > 0, "应能筛选出已取消的订单"

        with allure.step("3. 恢复全部订单筛选状态"):
            dashboard_page.filter_by_status("ALL")
            all_count = dashboard_page.get_rendered_order_count()
            assert all_count >= cancelled_count, "恢复全部状态后单量应更多"

    @allure.story("3. 订单详情核销抽屉与状态快速流转")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("验证打开订单结算详情抽屉、校验核销金额，并在弹窗内直接流转订单状态")
    def test_03_order_detail_drawer_and_status_transition(self, dashboard_page: DashboardPage):
        with allure.step("1. 点击第一笔订单的【查看核销详情】打开抽屉"):
            order_sn = dashboard_page.open_first_order_detail()
            assert order_sn != "", "订单编号不应为空"
            assert dashboard_page.is_displayed(*dashboard_page.LOC_MODAL_ORDER_DETAIL), "订单抽屉模态框应成功弹出"

        with allure.step("2. 验证抽屉内金额快照核销实付项"):
            actual_pay = dashboard_page.get_text(*dashboard_page.LOC_MODAL_ACTUAL_PAY)
            assert actual_pay.startswith("￥"), "实付金额快照应正常渲染"

        with allure.step("3. 模拟测试：点击按钮将订单状态流转为【后厨已出纸】(PRINTED)"):
            dashboard_page.transition_order_status_in_modal("PRINTED")
            status_text = dashboard_page.get_text(*dashboard_page.LOC_MODAL_STATUS)
            assert "出纸" in status_text or "PRINTED" in status_text, f"状态流转失败，当前状态: {status_text}"

        with allure.step("4. 关闭订单详情抽屉"):
            dashboard_page.close_order_detail_modal()
            assert not dashboard_page.is_displayed(*dashboard_page.LOC_MODAL_ORDER_DETAIL, timeout=1), "抽屉应已关闭"

    @allure.story("4. 快速模拟下单与 KPI 动态联动")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("验证通过【快速模拟下单】提交新订单，验证顶部 GMV 与有效订单量增量联动")
    def test_04_quick_simulate_order_and_dynamic_kpi_update(self, dashboard_page: DashboardPage):
        with allure.step("1. 记录下单前的有效订单数"):
            init_kpis = dashboard_page.get_kpi_summary()
            init_valid_count = int(init_kpis["valid_orders"])

        with allure.step("2. 打开快速模拟提单弹窗并提交一笔已支付单"):
            dashboard_page.create_mock_order(
                table="table_08",
                period="DINNER",
                combo="COMBO_FEAST",
                people="4",
                coupon="50",
                status="PAID"
            )

        with allure.step("3. 断言提交后顶部有效出单量 +1 且列表立即呈现新订单"):
            new_kpis = dashboard_page.get_kpi_summary()
            new_valid_count = int(new_kpis["valid_orders"])
            assert new_valid_count == init_valid_count + 1, f"订单提交后有效单数应+1 (原: {init_valid_count}, 现: {new_valid_count})"

    @allure.story("5. BI 多维动态报表看板呈现")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("验证切换至 BI 多维报表 Tab，四大 Chart.js Canvas 图表正常挂载与呈现")
    def test_05_bi_charts_rendering(self, dashboard_page: DashboardPage):
        with allure.step("1. 切换至【📈 BI 多维报表看板】选项卡"):
            dashboard_page.switch_to_tab("bi")

        with allure.step("2. 校验四大核心分析图表 Canvas 画布是否存在且可见"):
            assert dashboard_page.is_displayed(*dashboard_page.LOC_CHART_PERIOD, timeout=2), "时段营收图表未正常显示"
            assert dashboard_page.is_displayed(*dashboard_page.LOC_CHART_STATUS, timeout=2), "状态漏斗图表未正常显示"
            assert dashboard_page.is_displayed(*dashboard_page.LOC_CHART_DISHES, timeout=2), "菜品销售排行图表未正常显示"
            assert dashboard_page.is_displayed(*dashboard_page.LOC_CHART_CHANNEL, timeout=2), "支付渠道分布图表未正常显示"

    @allure.story("6. 财务结算与 BI 自动化对账引擎")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("验证平账校验通过、模拟注入账面异常单报警，以及一键平账修复功能")
    def test_06_bi_audit_and_anomaly_detection(self, dashboard_page: DashboardPage):
        with allure.step("1. 切换至【⚖️ 财务结算与自动化对账】选项卡"):
            dashboard_page.switch_to_tab("audit")

        with allure.step("2. 执行对账核验，断言初始状态为 100% 账实相符"):
            dashboard_page.run_bi_audit()
            badge_text = dashboard_page.get_audit_badge_text()
            assert "平账" in badge_text or "相符" in badge_text, f"初始状态应平账，当前文本: {badge_text}"

        with allure.step("3. 模拟 QA 测试注入对账异常单"):
            dashboard_page.inject_audit_anomaly()
            anomaly_badge = dashboard_page.get_audit_badge_text()
            assert "警告" in anomaly_badge or "偏差" in anomaly_badge, f"注入异常后应报警，当前文本: {anomaly_badge}"
            assert dashboard_page.is_displayed(*dashboard_page.LOC_DISCREPANCY_SECTION), "异常订单差异定位表应当展开呈现"

        with allure.step("4. 点击【一键平账修复】，断言账面恢复一致"):
            dashboard_page.repair_audit_discrepancies()
            repaired_badge = dashboard_page.get_audit_badge_text()
            assert "平账" in repaired_badge or "相符" in repaired_badge, f"修复后应恢复平账，当前文本: {repaired_badge}"

    @allure.story("7. 数据库与在线 SQL 执行控制台")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("验证切换至【🗄️ 数据库与 SQL 查询】选项卡，在线执行 SQL 聚合对账并在页面展示结果")
    def test_07_database_sql_console_query(self, dashboard_page: DashboardPage):
        with allure.step("1. 切换至【🗄️ 数据库与 SQL 查询】选项卡"):
            dashboard_page.switch_to_tab("db")

        with allure.step("2. 点击预设 SQL 按钮执行各状态订单金额聚合查询"):
            dashboard_page.click(*dashboard_page.LOC_BTN_PRESET_STATUS_GMV)
            dashboard_page.click(*dashboard_page.LOC_BTN_EXECUTE_SQL)
            dashboard_page.accept_alert()

        with allure.step("3. 校验数据库查询结果表格已成功渲染数据行"):
            result_rows = dashboard_page.find_elements(*dashboard_page.LOC_DB_RESULT_ROWS)
            assert len(result_rows) > 0, "SQL 查询结果表格不应为空"


if __name__ == "__main__":
    # 支持直接运行本文件调试
    pytest.main([__file__, "-v", "-s"])
