"""
领域模型与状态枚举定义 (models.py)
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
import time
import uuid


class TableStatus(str, Enum):
    """桌台状态枚举"""
    IDLE = "IDLE"           # 空闲未开台 (允许扫码开台)
    DINING = "DINING"       # 用餐中 (允许加菜)
    CLEARING = "CLEARING"   # 服务员正在清台 (拦截下单)
    MERGED = "MERGED"       # 已并桌 (拦截，引导至主桌)
    CHANGED = "CHANGED"     # 已换桌 (拦截，引导至新桌)
    DISABLED = "DISABLED"   # 停用维修 (拦截)


class MealPeriod(str, Enum):
    """用餐时段枚举"""
    BREAKFAST = "BREAKFAST" # 早市 07:00 - 10:00
    LUNCH = "LUNCH"         # 午市 11:00 - 14:00
    DINNER = "DINNER"       # 晚市 17:00 - 21:00
    NIGHT = "NIGHT"         # 夜宵 21:00 - 02:00
    CLOSED = "CLOSED"       # 非营业时段


class OrderStatus(str, Enum):
    """订单状态枚举"""
    PENDING_PAY = "PENDING_PAY" # 待支付
    PAID = "PAID"               # 已支付 (待厨打)
    PRINTED = "PRINTED"         # 已出纸打印
    CANCELLED = "CANCELLED"     # 超时未付/主动取消并释放库存
    COMPLETED = "COMPLETED"     # 已完成


@dataclass
class DishSpec:
    """规格（大份/中份/小份）"""
    spec_name: str
    price_delta: float = 0.0


@dataclass
class DishExtra:
    """加料（珍珠、加蛋等）"""
    name: str
    price: float = 0.0


@dataclass
class Dish:
    """菜品信息"""
    dish_id: str
    name: str
    category: str
    base_price: float
    available_periods: List[MealPeriod]
    specs: Dict[str, float] = field(default_factory=dict)       # 如: {"大份": 8.0, "中份": 0.0, "小份": -3.0}
    attributes: List[str] = field(default_factory=list)          # 如: ["微辣", "去冰", "免葱"]
    extras: Dict[str, float] = field(default_factory=dict)       # 如: {"加煎蛋": 3.0, "加面": 2.0}
    stock: int = 999                                            # 库存 (限量特价菜可能为1或少量)
    is_on_sale: bool = True                                     # 是否上架
    is_special_offer: bool = False                              # 是否限量特价菜


@dataclass
class CartItem:
    """购物车单品行"""
    dish_id: str
    name: str
    spec_name: str
    chosen_attributes: List[str]
    chosen_extras: List[str]
    quantity: int
    unit_price: float
    subtotal: float


@dataclass
class Cart:
    """多人同桌共享购物车"""
    store_id: str
    table_id: str
    items: List[CartItem] = field(default_factory=list)
    version: int = 1                                            # 协同版本号
    participants: List[str] = field(default_factory=list)       # 同桌扫码顾客ID
    updated_at: float = field(default_factory=time.time)


@dataclass
class PriceSnapshot:
    """订单价格快照计算模型"""
    original_total: float       # 菜品原价合计
    discount_amount: float      # 优惠券 / 满减抵扣金额
    tableware_fee: float        # 餐位费 (人数 * 单人餐位费)
    actual_pay_amount: float    # 最终实付金额 = 原价 - 优惠 + 餐位费
    min_consume_satisfied: bool # 是否达到起做/起送金额标准
    coupon_id: Optional[str] = None


@dataclass
class Order:
    """订单实体"""
    order_sn: str
    store_id: str
    table_id: str
    items: List[CartItem]
    price_snapshot: PriceSnapshot
    status: OrderStatus = OrderStatus.PENDING_PAY
    idempotency_token: str = ""
    created_at: float = field(default_factory=time.time)
    paid_at: Optional[float] = None
    cancelled_at: Optional[float] = None
    pay_channel: Optional[str] = None
    kitchen_printed: bool = False


@dataclass
class MQOrderMessage:
    """RabbitMQ 订单打印事件消息体"""
    msg_id: str
    order_sn: str
    store_id: str
    table_id: str
    items_summary: str
    total_amount: float
    pay_time: float
    retry_count: int = 0
    delivery_mode: int = 2      # 2 代表消息持久化 (Persistent)
    durable: bool = True        # 队列/交换机持久化标识
    created_at: float = field(default_factory=time.time)
