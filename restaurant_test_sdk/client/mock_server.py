"""
餐饮业务后端全真模拟服务器 (DiningMockServer)
封装门店、桌台、菜单、购物车协同、库存扣减、价格快照、防重提单、DB唯一约束与超时关单。
"""
import copy
import threading
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any

from restaurant_test_sdk.models import (
    TableStatus, MealPeriod, OrderStatus, Dish, Cart, CartItem,
    PriceSnapshot, Order, MQOrderMessage
)


class DiningMockServer:
    """餐饮业务中台模拟器，支持线程安全的并发业务处理"""

    def __init__(self):
        self._lock = threading.RLock()
        
        # 门店桌台状态表: {store_id: {table_id: TableStatus}}
        self.tables: Dict[str, Dict[str, TableStatus]] = {
            "store_888": {
                "table_01": TableStatus.IDLE,
                "table_02": TableStatus.DINING,
                "table_06": TableStatus.IDLE,
                "table_99": TableStatus.CLEARING, # 模拟正在清台的桌台
            }
        }
        
        # 菜品库: {dish_id: Dish}
        self.dishes: Dict[str, Dish] = {
            "dish_001": Dish(
                dish_id="dish_001",
                name="招牌老坛酸菜鱼",
                category="热销主菜",
                base_price=88.0,
                available_periods=[MealPeriod.LUNCH, MealPeriod.DINNER],
                specs={"大份": 20.0, "中份": 0.0, "小份": -15.0},
                attributes=["微辣", "特辣", "免麻"],
                extras={"加金针菇": 5.0, "加宽粉": 4.0},
                stock=50,
                is_on_sale=True
            ),
            "dish_002": Dish(
                dish_id="dish_002",
                name="限量特价手抓羊排",
                category="秒杀特惠",
                base_price=9.9,
                available_periods=[MealPeriod.LUNCH, MealPeriod.DINNER],
                specs={"标配": 0.0},
                attributes=["香辣", "原味"],
                extras={},
                stock=1,  # 仅剩1份，用于测试并发超卖拦截
                is_on_sale=True,
                is_special_offer=True
            ),
            "dish_003": Dish(
                dish_id="dish_003",
                name="早市鲜虾小笼包",
                category="早市点心",
                base_price=22.0,
                available_periods=[MealPeriod.BREAKFAST], # 仅早市
                specs={"一笼(6只)": 0.0},
                attributes=["配香醋", "不要醋"],
                extras={},
                stock=100,
                is_on_sale=True
            ),
            "dish_004": Dish(
                dish_id="dish_004",
                name="季节限定杨梅冰汤圆",
                category="甜品冷饮",
                base_price=16.0,
                available_periods=[MealPeriod.LUNCH, MealPeriod.DINNER],
                specs={"标准碗": 0.0},
                attributes=["少糖", "去冰", "正常冰"],
                extras={"加小圆子": 2.0},
                stock=20,
                is_on_sale=True
            )
        }

        # 购物车缓存: {f"{store_id}:{table_id}": Cart}
        self.carts: Dict[str, Cart] = {}
        
        # 订单数据库: {order_sn: Order}
        self.orders: Dict[str, Order] = {}
        
        # 数据库唯一索引模拟: {(store_id, table_id, "ACTIVE_UNPAID"): order_sn}
        # 模拟 DB 的 uk_store_table_status 唯一约束，防止未付款订单重复生成
        self.db_unique_table_active_order: Dict[Tuple[str, str, str], str] = {}
        
        # 已处理过的幂等令牌池: {token: order_sn}
        self.idempotency_tokens: Dict[str, str] = {}
        
        # 优惠券库: {coupon_id: {"min_spend": float, "discount": float}}
        self.coupons = {
            "COUPON_100_MINUS_20": {"min_spend": 100.0, "discount": 20.0},
            "COUPON_50_MINUS_10": {"min_spend": 50.0, "discount": 10.0}
        }
        
        # 餐位费标准（元/人）
        self.tableware_fee_per_person = 3.0
        
        # 门店起送/起做门槛金额 (堂食默认0元，外卖或特殊时段可配置)
        self.min_order_amount = 0.0

    # ---------------- 1. 扫码与开台 ---------------- #
    def scan_table(self, store_id: str, table_id: str, customer_id: str) -> Dict[str, Any]:
        """扫码开台 / 进单校验"""
        with self._lock:
            if store_id not in self.tables:
                return {"code": 404, "msg": f"门店不存在: {store_id}"}
            store_tables = self.tables[store_id]
            if table_id not in store_tables:
                return {"code": 404, "msg": f"桌台不存在: {table_id}"}
            
            status = store_tables[table_id]
            if status == TableStatus.CLEARING:
                return {"code": 4001, "msg": "服务员正在清台，请稍候或联系服务员更换桌台", "status": status}
            elif status == TableStatus.DISABLED:
                return {"code": 4002, "msg": "当前桌台已停用", "status": status}
            elif status == TableStatus.CHANGED:
                return {"code": 4003, "msg": "桌台状态已变更，请重新扫码关联新桌台", "status": status}
            elif status == TableStatus.MERGED:
                return {"code": 4004, "msg": "该桌已并桌，请扫描主桌二维码", "status": status}
            
            # 空闲开台 -> 转为 DINING
            if status == TableStatus.IDLE:
                store_tables[table_id] = TableStatus.DINING
                mode = "OPEN_TABLE"
            else:
                mode = "JOIN_TABLE"  # 用餐中加菜
            
            # 初始化或加入协同购物车
            cart_key = f"{store_id}:{table_id}"
            if cart_key not in self.carts:
                self.carts[cart_key] = Cart(store_id=store_id, table_id=table_id, participants=[customer_id])
            else:
                if customer_id not in self.carts[cart_key].participants:
                    self.carts[cart_key].participants.append(customer_id)
            
            return {
                "code": 200,
                "msg": "扫码成功",
                "mode": mode,
                "table_status": store_tables[table_id],
                "store_id": store_id,
                "table_id": table_id,
                "cart_version": self.carts[cart_key].version
            }

    # ---------------- 2. 菜单加载 ---------------- #
    def get_menu(self, store_id: str, period: MealPeriod) -> Dict[str, Any]:
        """根据当前时段获取上架菜单"""
        with self._lock:
            available_dishes = []
            for dish in self.dishes.values():
                if dish.is_on_sale and period in dish.available_periods:
                    available_dishes.append({
                        "dish_id": dish.dish_id,
                        "name": dish.name,
                        "category": dish.category,
                        "base_price": dish.base_price,
                        "specs": dish.specs,
                        "attributes": dish.attributes,
                        "extras": dish.extras,
                        "stock": dish.stock,
                        "is_special_offer": dish.is_special_offer
                    })
            return {"code": 200, "period": period, "dishes": available_dishes}

    # ---------------- 3. 购物车协同与算价 ---------------- #
    def sync_cart(self, store_id: str, table_id: str, customer_id: str,
                  items: List[CartItem], client_version: int) -> Dict[str, Any]:
        """多人同桌扫码实时同步购物车"""
        with self._lock:
            cart_key = f"{store_id}:{table_id}"
            if cart_key not in self.carts:
                self.carts[cart_key] = Cart(store_id=store_id, table_id=table_id)
            
            cart = self.carts[cart_key]
            cart.items = copy.deepcopy(items)
            cart.version += 1
            cart.updated_at = time.time()
            if customer_id not in cart.participants:
                cart.participants.append(customer_id)
            
            return {
                "code": 200,
                "msg": "购物车同步成功",
                "version": cart.version,
                "total_items": len(cart.items),
                "participants_count": len(cart.participants)
            }

    def calculate_price_snapshot(self, store_id: str, table_id: str,
                                 customer_count: int, coupon_id: Optional[str] = None,
                                 items: Optional[List[CartItem]] = None) -> PriceSnapshot:
        """计算订单价格快照：实付 = 原价 - 优惠 + 餐位费"""
        with self._lock:
            if items is not None:
                calc_items = items
            else:
                cart_key = f"{store_id}:{table_id}"
                cart = self.carts.get(cart_key, Cart(store_id, table_id))
                calc_items = cart.items
            
            original_total = sum(item.subtotal for item in calc_items)
            tableware_fee = max(0, customer_count) * self.tableware_fee_per_person
            
            discount = 0.0
            if coupon_id and coupon_id in self.coupons:
                rule = self.coupons[coupon_id]
                if original_total >= rule["min_spend"]:
                    discount = rule["discount"]
            
            actual_pay = max(0.0, original_total - discount + tableware_fee)
            min_satisfied = (original_total >= self.min_order_amount)
            
            return PriceSnapshot(
                original_total=round(original_total, 2),
                discount_amount=round(discount, 2),
                tableware_fee=round(tableware_fee, 2),
                actual_pay_amount=round(actual_pay, 2),
                min_consume_satisfied=min_satisfied,
                coupon_id=coupon_id
            )

    # ---------------- 4. 提交订单与异常拦截 ---------------- #
    def submit_order(self, store_id: str, table_id: str, items: List[CartItem],
                     price_snapshot: PriceSnapshot, idempotency_token: str) -> Dict[str, Any]:
        """
        下单与结算接口（包含防重幂等、桌台状态校验、库存防超卖、改价下架拦截、DB唯一键兜底）
        """
        with self._lock:
            # 1. 幂等校验 (防止弱网重复点击)
            if idempotency_token in self.idempotency_tokens:
                existing_sn = self.idempotency_tokens[idempotency_token]
                return {
                    "code": 4091,
                    "msg": "重复下单请求被拦截 (Idempotent Token Matched)",
                    "order_sn": existing_sn
                }

            # 2. 桌台突变校验 (选菜期间服务员在 POS 机上清台/换桌/并桌)
            current_table_status = self.tables.get(store_id, {}).get(table_id)
            if current_table_status in [TableStatus.CLEARING, TableStatus.CHANGED, TableStatus.MERGED, TableStatus.DISABLED]:
                return {
                    "code": 4005,
                    "msg": f"桌台状态已变更 ({current_table_status})，无法下单，请联系服务员",
                    "table_status": current_table_status
                }

            # 3. 起做金额校验
            if not price_snapshot.min_consume_satisfied:
                return {
                    "code": 4006,
                    "msg": f"未达到门店起做金额 {self.min_order_amount} 元"
                }

            # 4. 商品状态、改价校验与库存扣减
            for item in items:
                dish = self.dishes.get(item.dish_id)
                if not dish or not dish.is_on_sale:
                    return {
                        "code": 4007,
                        "msg": f"商品 [{item.name}] 已下架，请刷新购物车",
                        "invalid_dish_id": item.dish_id
                    }
                
                # 重新计算最新真实单价，校验是否发生价格变动
                spec_delta = dish.specs.get(item.spec_name, 0.0)
                extras_delta = sum(dish.extras.get(ext, 0.0) for ext in item.chosen_extras)
                real_unit_price = round(dish.base_price + spec_delta + extras_delta, 2)
                
                if abs(real_unit_price - item.unit_price) > 0.001:
                    return {
                        "code": 4008,
                        "msg": f"菜品 [{item.name}] 价格发生变动 (现价:{real_unit_price})，请重新确认",
                        "invalid_dish_id": item.dish_id
                    }
                
                # 库存扣减校验
                if dish.stock < item.quantity:
                    return {
                        "code": 4009,
                        "msg": f"商品 [{item.name}] 库存不足，当前仅剩 {dish.stock} 份",
                        "invalid_dish_id": item.dish_id
                    }

            # 5. DB 唯一约束兜底检验 (同一桌台同一时刻只能存在一个待支付有效订单)
            db_unique_key = (store_id, table_id, "ACTIVE_UNPAID")
            if db_unique_key in self.db_unique_table_active_order:
                return {
                    "code": 4092,
                    "msg": "DB唯一索引冲突 (uk_store_table_status): 当前桌台已有未完成的待支付订单"
                }

            # 6. 执行原子扣减库存
            for item in items:
                dish = self.dishes[item.dish_id]
                dish.stock -= item.quantity

            # 7. 创建订单与入库
            order_sn = f"ORD_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
            new_order = Order(
                order_sn=order_sn,
                store_id=store_id,
                table_id=table_id,
                items=copy.deepcopy(items),
                price_snapshot=copy.deepcopy(price_snapshot),
                status=OrderStatus.PENDING_PAY,
                idempotency_token=idempotency_token
            )
            
            self.orders[order_sn] = new_order
            self.idempotency_tokens[idempotency_token] = order_sn
            self.db_unique_table_active_order[db_unique_key] = order_sn
            
            # 清空当前桌购物车
            cart_key = f"{store_id}:{table_id}"
            if cart_key in self.carts:
                self.carts[cart_key].items = []

            return {
                "code": 200,
                "msg": "下单成功，等待支付",
                "order_sn": order_sn,
                "actual_pay_amount": price_snapshot.actual_pay_amount
            }

    # ---------------- 5. 支付与异步回调 ---------------- #
    def pay_callback(self, order_sn: str, channel: str = "WECHAT_PAY", success: bool = True) -> Dict[str, Any]:
        """支付完成回调接口 (更新状态、解绑唯一约束、返回 MQ 订单打印消息)"""
        with self._lock:
            order = self.orders.get(order_sn)
            if not order:
                return {"code": 404, "msg": f"订单不存在: {order_sn}"}
            
            if order.status == OrderStatus.CANCELLED:
                # 用户扣款但订单此前已超时关闭 -> 触发对账补单或自动原路退款
                return {
                    "code": 40010,
                    "msg": "订单已超时取消，触发对账补单/退款流程",
                    "order_sn": order_sn,
                    "need_refund": True
                }
            
            if order.status == OrderStatus.PAID:
                return {"code": 200, "msg": "订单已处于支付状态 (幂等响应)", "order_sn": order_sn}
            
            if success:
                order.status = OrderStatus.PAID
                order.paid_at = time.time()
                order.pay_channel = channel
                
                # 释放待支付的 DB 唯一锁定约束
                db_unique_key = (order.store_id, order.table_id, "ACTIVE_UNPAID")
                self.db_unique_table_active_order.pop(db_unique_key, None)
                
                # 构建 MQ 消息待发送至 RabbitMQ
                items_summary = "; ".join([f"{it.name}x{it.quantity}({it.spec_name})" for it in order.items])
                mq_msg = MQOrderMessage(
                    msg_id=f"MSG_{uuid.uuid4().hex[:8]}",
                    order_sn=order.order_sn,
                    store_id=order.store_id,
                    table_id=order.table_id,
                    items_summary=items_summary,
                    total_amount=order.price_snapshot.actual_pay_amount,
                    pay_time=order.paid_at
                )
                
                return {
                    "code": 200,
                    "msg": "支付成功，已进入后厨出票流程",
                    "order_sn": order_sn,
                    "mq_message": mq_msg
                }
            else:
                return {"code": 500, "msg": "支付失败回调"}

    # ---------------- 6. 超时关单与对账补单 ---------------- #
    def cancel_expired_order(self, order_sn: str, timeout_sec: float) -> bool:
        """超时未支付自动关单并回滚库存"""
        with self._lock:
            order = self.orders.get(order_sn)
            if not order:
                return False
            
            if order.status == OrderStatus.PENDING_PAY:
                now = time.time()
                if (now - order.created_at) >= timeout_sec:
                    order.status = OrderStatus.CANCELLED
                    order.cancelled_at = now
                    
                    # 回滚库存
                    for item in order.items:
                        dish = self.dishes.get(item.dish_id)
                        if dish:
                            dish.stock += item.quantity
                    
                    # 释放 DB 唯一键
                    db_unique_key = (order.store_id, order.table_id, "ACTIVE_UNPAID")
                    self.db_unique_table_active_order.pop(db_unique_key, None)
                    return True
            return False

    def reconcile_and_repair_order(self, order_sn: str, channel_payment_status: bool) -> Dict[str, Any]:
        """对账补偿：若渠道扣款成功但回调延迟丢失，主动向支付渠道对账补单"""
        with self._lock:
            order = self.orders.get(order_sn)
            if not order:
                return {"code": 404, "msg": "订单不存在"}
            
            if order.status == OrderStatus.CANCELLED and channel_payment_status:
                # 重新激活订单，扣减库存或发起补单
                order.status = OrderStatus.PAID
                order.paid_at = time.time()
                return {"code": 200, "msg": "对账成功：已为延时支付订单完成补单", "order_sn": order_sn}
            return {"code": 200, "msg": "对账一致，无须补单"}
