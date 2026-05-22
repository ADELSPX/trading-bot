"""إعدادات التداول — منفصلة لتجنب circular imports"""
from dataclasses import dataclass, field
from datetime import time


@dataclass
class TradeConfig:
    """إعدادات التداول الأساسية"""
    symbol: str = "SPX"
    max_position_size: float = 1000.0
    target_profit_pct: float = 50.0
    stop_loss_pct: float = 100.0
    market_open: time = time(9, 30)
    market_close: time = time(16, 0)
