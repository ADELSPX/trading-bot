"""
إعدادات التداول
"""
from bot.core import TradeConfig

# إعدادات SPX
SPX_CONFIG = TradeConfig(
    symbol="SPX",
    max_position_size=1000.0,
    target_profit_pct=50.0,
    stop_loss_pct=100.0,
)

# إعدادات QQQ
QQQ_CONFIG = TradeConfig(
    symbol="QQQ",
    max_position_size=800.0,
    target_profit_pct=40.0,
    stop_loss_pct=100.0,
)

# إعدادات META
META_CONFIG = TradeConfig(
    symbol="META",
    max_position_size=500.0,
    target_profit_pct=60.0,
    stop_loss_pct=100.0,
)

# إعدادات TSLA
TSLA_CONFIG = TradeConfig(
    symbol="TSLA",
    max_position_size=600.0,
    target_profit_pct=70.0,
    stop_loss_pct=100.0,
)

SYMBOLS = {
    "SPX": SPX_CONFIG,
    "QQQ": QQQ_CONFIG,
    "META": META_CONFIG,
    "TSLA": TSLA_CONFIG,
}
