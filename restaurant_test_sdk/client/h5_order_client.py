"""
H5 下单全流程客户端 SDK (H5OrderClient)
封装顾客扫码开台、协同购物车、算价快照、防重提单、模拟支付与对账能力。
"""
import uuid
from typing import List, Dict, Optional, Any

from restaurant_test_sdk.models import (
    MealPeriod, TableStatus, CartItem, PriceSnapshot, OrderStatus
)
from restaurant_test_sdk.client.mock_server import DiningMockServer


class H5OrderClient:
    """H5 点餐业务客户端"""

    def __init__(self, server: DiningMockServer, store_id: str, table_id: str,
                 customer_id: Optional[str] = None, customer_count: int = 2):
        self.server = server
        self.store_id = store_id
        self.table_id = table_id
        self.customer_id = customer_id or f"user_{uuid.uuid4().hex[:6]}"
        self.customer_count = customer_count
        
        # 客户端本地状态
        self.cart_items: List[CartItem] = []
        self.cart_version: int = 1
        self.current_order_sn: Optional[str] = None
        self.table_status: Optional[TableStatus] = None

    # 1. 扫码开台 / 进单
    def scan_table(self) -> Dict[str, Any]:
        """扫描桌台二维码进入 H5 点餐页面"""
        resp = self.server.scan_table(self.store_id, self.table_id, self.customer_id)
        if resp.get("code") == 200:
            self.table_status = resp.get("table_status")
            self.cart_version = resp.get("cart_version", 1)
        return resp

    # 2. 菜单加载
    def fetch_menu(self, period: MealPeriod = MealPeriod.LUNCH) -> Dict[str, Any]:
        """加载门店在指定餐段开放的菜品"""
        return self.server.get_menu(self.store_id, period)

    # 3. 选菜与购物车构建
    def add_item_to_cart(self, dish_id: str, spec_name: str,
                         chosen_attributes: Optional[List[str]] = None,
                         chosen_extras: Optional[List[str]] = None,
                         quantity: int = 1) -> CartItem:
        """
        向购物车添加菜品，支持多规格、自定义做法属性与加料加价计算
        """
        dish = self.server.dishes.get(dish_id)
        if not dish:
            raise ValueError(f"菜品不存在: {dish_id}")
        
        chosen_attributes = chosen_attributes or []
        chosen_extras = chosen_extras or []
        
        spec_delta = dish.specs.get(spec_name, 0.0)
        extras_delta = sum(dish.extras.get(ext, 0.0) for ext in chosen_extras)
        unit_price = round(dish.base_price + spec_delta + extras_delta, 2)
        subtotal = round(unit_price * quantity, 2)
        
        item = CartItem(
            dish_id=dish_id,
            name=dish.name,
            spec_name=spec_name,
            chosen_attributes=chosen_attributes,
            chosen_extras=chosen_extras,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal
        )
        
        self.cart_items.append(item)
        return item

    def sync_cart(self) -> Dict[str, Any]:
        """多人同桌扫码，提交本地购物车变动以实时同步"""
        resp = self.server.sync_cart(
            self.store_id, self.table_id, self.customer_id, self.cart_items, self.cart_version
        )
        if resp.get("code") == 200:
            self.cart_version = resp["version"]
        return resp

    # 4. 价格快照计算
    def calculate_price(self, coupon_id: Optional[str] = None) -> PriceSnapshot:
        """请求服务端进行价格快照计算（原价 - 优惠 + 餐位费）"""
        return self.server.calculate_price_snapshot(
            self.store_id, self.table_id, self.customer_count, coupon_id, items=self.cart_items
        )

    # 5. 下单与结算
    def submit_order(self, idempotency_token: Optional[str] = None,
                     coupon_id: Optional[str] = None) -> Dict[str, Any]:
        """提交订单结算"""
        token = idempotency_token or f"TOKEN_{uuid.uuid4().hex}"
        snapshot = self.calculate_price(coupon_id=coupon_id)
        
        resp = self.server.submit_order(
            self.store_id, self.table_id, self.cart_items, snapshot, token
        )
        if resp.get("code") == 200:
            self.current_order_sn = resp.get("order_sn")
            self.cart_items = []
        return resp

    # 6. 弱网连击模拟 (防抖与后端幂等性验证)
    def simulate_rapid_click_submit(self, click_count: int = 3,
                                    coupon_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """模拟弱网下用户连续点击“立即下单”，携带相同幂等 Token"""
        token = f"TOKEN_RAPID_{uuid.uuid4().hex}"
        snapshot = self.calculate_price(coupon_id=coupon_id)
        
        results = []
        for _ in range(click_count):
            resp = self.server.submit_order(
                self.store_id, self.table_id, self.cart_items, snapshot, token
            )
            results.append(resp)
        return results

    # 7. 支付与回调
    def simulate_pay(self, order_sn: Optional[str] = None,
                     channel: str = "WECHAT_PAY", success: bool = True) -> Dict[str, Any]:
        """模拟支付与服务端异步回调"""
        sn = order_sn or self.current_order_sn
        if not sn:
            raise ValueError("缺少 order_sn，请先下单或指定 order_sn")
        return self.server.pay_callback(sn, channel=channel, success=success)

    # 8. 查询订单状态
    def get_order_status(self, order_sn: Optional[str] = None) -> Optional[OrderStatus]:
        sn = order_sn or self.current_order_sn
        order = self.server.orders.get(sn)
        return order.status if order else None
