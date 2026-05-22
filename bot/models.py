"""
هياكل البيانات الأساسية — مشتركة بين جميع الملفات
لتفادي الـ circular imports
"""

from dataclasses import dataclass, field
from datetime import time
from typing import Optional, Literal


@dataclass
class TradeConfig:
    """إعدادات التداول الأساسية"""
    symbol: str = "SPX"
    max_position_size: float = 1000.0
    target_profit_pct: float = 50.0
    stop_loss_pct: float = 100.0
    market_open: time = time(9, 30)
    market_close: time = time(16, 0)
    account_balance: float = 10000.0


@dataclass
class Leg:
    """رجل واحد في الاستراتيجية"""
    strike: float
    option_type: Literal["call", "put"]
    action: Literal["buy", "sell"]
    quantity: int = 1


@dataclass
class StrategyResult:
    """نتيجة تحليل الاستراتيجية"""
    name: str
    legs: list[Leg] = field(default_factory=list)
    max_profit: Optional[float] = None
    max_loss: Optional[float] = None
    break_even: list[float] = field(default_factory=list)
    total_delta: float = 0.0
    total_gamma: float = 0.0
    total_theta: float = 0.0
    total_vega: float = 0.0
    total_premium: float = 0.0
    confidence: float = 0.0
    direction: str = "neutral"
    explanation: str = ""
    approved: bool = False
    reject_reason: str = ""
