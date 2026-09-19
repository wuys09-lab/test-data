# -*- coding: utf-8 -*-
"""
智慧餐饮订单管理与 BI 结算看板 Page Object (dashboard_page.py)
对页面上的所有元素定位 (By)、操作流程与断言获取方法进行集中封装
"""
from typing import List, Dict, Any
from selenium.webdriver.common.by import By
from .base_page import BasePage


class DashboardPage(BasePage):
    """餐饮订单管理与 BI 结算对账看板页面对象"""

    # 默认页面 URL
    PAGE_URL = "file:///Users/wu/Documents/test%20data/order_bi_dashboard.html"

    # ==================== 1. 顶部 Header 与 KPI 仪表盘定位符 ====================
    LOC_BRAND_TITLE = (By.CSS_SELECTOR, ".brand-title h1")
    LOC_STORE_NAME = (By.ID, "currentStoreName")
    LOC_BTN_QUICK_CREATE = (By.XPATH, "//button[contains(@onclick, 'openCreateOrderModal')]")
    LOC_BTN_TOP_AUDIT = (By.XPATH, "//header//button[contains(@onclick, 'runBIAudit')]")

    LOC_KPI_GMV = (By.ID, "kpiGmv")
    LOC_KPI_VALID_ORDERS = (By.ID, "kpiValidOrders")
    LOC_KPI_PENDING_COUNT = (By.ID, "kpiPendingCount")
    LOC_KPI_AOV = (By.ID, "kpiAov")
    LOC_KPI_DISCOUNTS = (By.ID, "kpiDiscounts")
    LOC_KPI_CANCELLED_COUNT = (By.ID, "kpiCancelledCount")
    LOC_KPI_CANCEL_RATIO = (By.ID, "kpiCancelRatio")

    # ==================== 2. 标签页切换定位符 ====================
    LOC_TAB_ORDERS = (By.XPATH, "//button[contains(@onclick, \"switchTab('orders')\")]")
    LOC_TAB_BI = (By.XPATH, "//button[contains(@onclick, \"switchTab('bi')\")]")
    LOC_TAB_AUDIT = (By.XPATH, "//button[contains(@onclick, \"switchTab('audit')\")]")
    LOC_TAB_DB = (By.XPATH, "//button[contains(@onclick, \"switchTab('db')\")]")

    # ==================== 3. 订单列表管理定位符 ====================
    LOC_FILTER_KEYWORD = (By.ID, "filterKeyword")
    LOC_FILTER_STATUS = (By.ID, "filterStatus")
    LOC_FILTER_PERIOD = (By.ID, "filterPeriod")
    LOC_BTN_EXPORT_CSV = (By.XPATH, "//button[contains(@onclick, 'exportOrdersCSV')]")
    LOC_TABLE_ROWS = (By.CSS_SELECTOR, "#ordersTableBody tr")

    # ==================== 4. 订单详情模态框定位符 ====================
    LOC_MODAL_ORDER_DETAIL = (By.ID, "orderDetailModal")
    LOC_MODAL_ORDER_SN = (By.ID, "modalOrderSn")
    LOC_MODAL_ACTUAL_PAY = (By.ID, "modalActualPay")
    LOC_MODAL_STATUS = (By.ID, "modalStatus")
    LOC_BTN_CLOSE_DETAIL = (By.XPATH, "//div[@id='orderDetailModal']//button[contains(@class, 'modal-close')]")

    LOC_BTN_SET_PAID = (By.XPATH, "//div[@id='orderDetailModal']//button[contains(@onclick, \"'PAID'\")]")
    LOC_BTN_SET_PRINTED = (By.XPATH, "//div[@id='orderDetailModal']//button[contains(@onclick, \"'PRINTED'\")]")
    LOC_BTN_SET_COMPLETED = (By.XPATH, "//div[@id='orderDetailModal']//button[contains(@onclick, \"'COMPLETED'\")]")
    LOC_BTN_SET_CANCELLED = (By.XPATH, "//div[@id='orderDetailModal']//button[contains(@onclick, \"'CANCELLED'\")]")

    # ==================== 5. 快速模拟下单模态框定位符 ====================
    LOC_MODAL_CREATE_ORDER = (By.ID, "createOrderModal")
    LOC_SELECT_NEW_TABLE = (By.ID, "newTable")
    LOC_SELECT_NEW_PERIOD = (By.ID, "newPeriod")
    LOC_SELECT_NEW_COMBO = (By.ID, "newDishCombo")
    LOC_INPUT_NEW_PEOPLE = (By.ID, "newPeopleCount")
    LOC_SELECT_NEW_COUPON = (By.ID, "newCoupon")
    LOC_SELECT_NEW_STATUS = (By.ID, "newStatus")
    LOC_BTN_SUBMIT_ORDER = (By.CSS_SELECTOR, "#newOrderForm button[type='submit']")

    # ==================== 6. BI 报表图表定位符 ====================
    LOC_CHART_PERIOD = (By.ID, "periodRevenueChart")
    LOC_CHART_STATUS = (By.ID, "statusPieChart")
    LOC_CHART_DISHES = (By.ID, "topDishesChart")
    LOC_CHART_CHANNEL = (By.ID, "paymentChannelChart")

    # ==================== 7. 财务对账定位符 ====================
    LOC_AUDIT_BI_GMV = (By.ID, "auditBiGmv")
    LOC_AUDIT_RAW_GMV = (By.ID, "auditRawGmv")
    LOC_AUDIT_DIFF = (By.ID, "auditDiff")
    LOC_AUDIT_BADGE = (By.ID, "auditBadge")
    LOC_AUDIT_FORMULA_CHECK = (By.ID, "auditFormulaCheck")

    LOC_BTN_AUDIT_RUN = (By.XPATH, "//div[@id='tab-audit']//button[contains(@onclick, 'runBIAudit')]")
    LOC_BTN_AUDIT_INJECT = (By.XPATH, "//div[@id='tab-audit']//button[contains(@onclick, 'injectDiscrepancyAnomaly')]")
    LOC_BTN_AUDIT_REPAIR = (By.XPATH, "//div[@id='tab-audit']//button[contains(@onclick, 'repairAllDiscrepancies')]")
    LOC_DISCREPANCY_SECTION = (By.ID, "discrepancySection")
    LOC_DISCREPANCY_ROWS = (By.CSS_SELECTOR, "#discrepancyTableBody tr")

    # ==================== 8. 数据库与 SQL 查询定位符 ====================
    LOC_BTN_DB_TABLE_ORDER = (By.ID, "btnTableOrder")
    LOC_BTN_DB_TABLE_ITEM = (By.ID, "btnTableItem")
    LOC_BTN_DB_TABLE_BI = (By.ID, "btnTableBi")
    LOC_SQL_INPUT = (By.ID, "sqlQueryInput")
    LOC_BTN_EXECUTE_SQL = (By.XPATH, "//button[contains(@onclick, 'executeCustomSql')]")
    LOC_BTN_PRESET_STATUS_GMV = (By.XPATH, "//button[contains(@onclick, \"runPresetQuery('status_gmv')\")]")
    LOC_DB_RESULT_ROWS = (By.CSS_SELECTOR, "#dbResultTbody tr")

    # ---------------- 业务操作方法封装 ----------------

    def load(self):
        """加载看板页面"""
        self.open(self.PAGE_URL)

    def get_brand_title(self) -> str:
        """获取品牌标题"""
        return self.get_text(*self.LOC_BRAND_TITLE)

    def get_current_store(self) -> str:
        """获取当前门店名称"""
        return self.get_text(*self.LOC_STORE_NAME)

    def get_kpi_summary(self) -> Dict[str, str]:
        """获取顶部所有核心 KPI 数据快照"""
        return {
            "gmv": self.get_text(*self.LOC_KPI_GMV),
            "valid_orders": self.get_text(*self.LOC_KPI_VALID_ORDERS),
            "pending_count": self.get_text(*self.LOC_KPI_PENDING_COUNT),
            "aov": self.get_text(*self.LOC_KPI_AOV),
            "discounts": self.get_text(*self.LOC_KPI_DISCOUNTS),
            "cancelled_count": self.get_text(*self.LOC_KPI_CANCELLED_COUNT),
            "cancel_ratio": self.get_text(*self.LOC_KPI_CANCEL_RATIO)
        }

    def switch_to_tab(self, tab_name: str):
        """切换标签页: 'orders', 'bi', 'audit', 'db'"""
        tab_map = {
            "orders": self.LOC_TAB_ORDERS,
            "bi": self.LOC_TAB_BI,
            "audit": self.LOC_TAB_AUDIT,
            "db": self.LOC_TAB_DB
        }
        if tab_name in tab_map:
            self.click(*tab_map[tab_name])

    def search_orders(self, keyword: str):
        """根据关键词检索订单"""
        self.type_text(*self.LOC_FILTER_KEYWORD, keyword)

    def filter_by_status(self, status: str):
        """根据状态筛选订单"""
        self.select_by_value(*self.LOC_FILTER_STATUS, status)

    def filter_by_period(self, period: str):
        """根据时段筛选订单"""
        self.select_by_value(*self.LOC_FILTER_PERIOD, period)

    def get_rendered_order_count(self) -> int:
        """获取当前列表展示的订单行数"""
        rows = self.find_elements(*self.LOC_TABLE_ROWS)
        return len(rows)

    def open_first_order_detail(self) -> str:
        """打开列表第一笔订单的核销抽屉并返回该单号"""
        btn_detail = (By.XPATH, "//tbody[@id='ordersTableBody']/tr[1]//button[contains(@onclick, 'viewOrderDetail')]")
        first_sn_elem = (By.XPATH, "//tbody[@id='ordersTableBody']/tr[1]/td[1]//strong")
        sn = self.get_text(*first_sn_elem)
        self.click(*btn_detail)
        return sn

    def transition_order_status_in_modal(self, target_status: str):
        """在模态框内快速流转状态: 'PAID', 'PRINTED', 'COMPLETED', 'CANCELLED'"""
        action_map = {
            "PAID": self.LOC_BTN_SET_PAID,
            "PRINTED": self.LOC_BTN_SET_PRINTED,
            "COMPLETED": self.LOC_BTN_SET_COMPLETED,
            "CANCELLED": self.LOC_BTN_SET_CANCELLED
        }
        if target_status in action_map:
            self.click(*action_map[target_status])

    def close_order_detail_modal(self):
        """关闭订单详情模态框"""
        self.click(*self.LOC_BTN_CLOSE_DETAIL)

    def create_mock_order(self, table="table_08", period="DINNER", combo="COMBO_FEAST", people="4", coupon="50", status="PAID"):
        """通过快速下单弹窗新增一笔测试订单"""
        self.click(*self.LOC_BTN_QUICK_CREATE)
        self.select_by_value(*self.LOC_SELECT_NEW_TABLE, table)
        self.select_by_value(*self.LOC_SELECT_NEW_PERIOD, period)
        self.select_by_value(*self.LOC_SELECT_NEW_COMBO, combo)
        self.type_text(*self.LOC_INPUT_NEW_PEOPLE, str(people))
        self.select_by_value(*self.LOC_SELECT_NEW_COUPON, str(coupon))
        self.select_by_value(*self.LOC_SELECT_NEW_STATUS, status)
        self.click(*self.LOC_BTN_SUBMIT_ORDER)
        # 处理可能的 alert 提示
        self.accept_alert()

    def run_bi_audit(self):
        """触发自动平账对账"""
        self.click(*self.LOC_BTN_AUDIT_RUN)

    def inject_audit_anomaly(self):
        """注入对账异常单"""
        self.click(*self.LOC_BTN_AUDIT_INJECT)
        self.accept_alert()

    def repair_audit_discrepancies(self):
        """一键平账修复"""
        self.click(*self.LOC_BTN_AUDIT_REPAIR)
        self.accept_alert()

    def get_audit_badge_text(self) -> str:
        """获取对账状态 Badge 文本"""
        return self.get_text(*self.LOC_AUDIT_BADGE)

    def execute_sql(self, sql: str):
        """在 DB 选项卡输入并执行自定义 SQL"""
        self.type_text(*self.LOC_SQL_INPUT, sql)
        self.click(*self.LOC_BTN_EXECUTE_SQL)
        self.accept_alert()
