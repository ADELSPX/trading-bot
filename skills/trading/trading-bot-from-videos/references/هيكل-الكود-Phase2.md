# 🏗️ هيكل الكود — بوت التداول Phase 2

## نظرة عامة

```
trading-bot/
├── bot/
│   ├── __init__.py       # استيراد
│   ├── models.py         # 🆕 TradeConfig, Leg, StrategyResult
│   ├── core.py           # المحرك الرئيسي — يستورد من models.py
│   ├── strategy.py       # 9 استراتيجيات — يستورد Leg/StrategyResult من models.py
│   ├── greeks.py         # 🆕 Black-Scholes + Greeks
│   ├── indicators.py     # Fibonacci + Delta
│   ├── risk.py           # إدارة المخاطر — يستورد TradeConfig من models.py
│   └── execution.py      # تنفيذ الصفقات (محاكي)
├── backtest/
│   ├── __init__.py
│   └── engine.py         # باك تست (backtesting.py)
├── config/
│   ├── __init__.py
│   └── settings.py       # Config لكل سهم
├── scripts/
│   ├── backtest.py       # باك تست + تحليل بيئة الأوبشن
│   └── live_signals.py   # إشارات حية
├── requirements.txt
└── README.md
```

## مسار الاستيراد (لتفادي circular import)

```
models.py ← TradeConfig, Leg, StrategyResult
    ↑            ↑
    │            │
core.py ─────────┤
risk.py ─────────┤
strategy.py ─────┘
```

## 9 استراتيجيات (strategy.py)

| # | اسم الميثود | عدد الأرجل | الربح | الخسارة |
|---|------------|-----------|-------|---------|
| 1 | `_simple_option()` | 1 | غير محدود | premium × 100 |
| 2 | `_debit_spread()` | 2 | (spread - net_debit) × 100 | net_debit × 100 |
| 3 | `_credit_spread()` | 2 | net_credit × 100 | (spread - net_credit) × 100 |
| 4 | `_iron_condor()` 🦅 | 4 | net_credit × 100 | (max_width - net_credit) × 100 |
| 5 | `_butterfly()` 🦋 | 3 | (width - debit) × 100 | debit × 100 |
| 6 | `_strangle()` | 2 | غير محدود | (put + call) × 100 |
| 7 | `_straddle()` | 2 | غير محدود | (call_atm + put_atm) × 100 |
| 8 | `_earnings_play()` 📊 | 2 | غير محدود | (call+put) × 100 at IV=40% |
| 9 | `_hedging()` 🛡️ | 1 | غير محدود | premium × 100 |

### معيار اختيار الأفضل

```python
score = confidence * 10 + (max_profit / max(abs(max_loss), 1))
```

## اليونانيات (greeks.py)

- `option_price(S, K, T, r, sigma, type)` — سعر Black-Scholes
- `calculate_delta(S, K, T, r, sigma, type)` — دلتا
- `calculate_gamma(S, K, T, r, sigma)` — جاما
- `calculate_theta(S, K, T, r, sigma, type)` — ثيتا (يومي)
- `calculate_vega(S, K, T, r, sigma)` — فيجا (لكل 1% IV)
- `calculate_rho(S, K, T, r, sigma, type)` — روه
- `calculate_iv(market_price, S, K, T, r, type)` — IV (Newton-Raphson)
- `GreeksCalculator.calculate_all()` — كل اليونانيات لعقد واحد
- `GreeksCalculator.calculate_spread(legs)` — كل اليونانيات لـ multi-leg

## إدارة المخاطر (risk.py)

```python
# القيم الافتراضية
MAX_DELTA = 0.50
MAX_GAMMA = 0.10
MAX_VEGA = 0.05
MAX_POSITION_PCT = 0.05  # 5%
MAX_PORTFOLIO_HEAT = 0.25  # 25%
```

## باك تست (scripts/backtest.py)

### استراتيجيات جاهزة
1. `MACrossoverStrategy` — fast_ma / slow_ma تقاطع
2. `RSIStrategy` — شراء عند oversold، بيع عند overbought

### واجهة
```python
run_technical_backtest(symbol="QQQ", start="2025-01-01",
                       strategy_type="rsi", cash=10000, optimize=True)
analyze_options_environment(symbol="SPY", start="2026-01-01")
```

### النتائج الفعلية (مايو 2026)
```
QQQ RSI optimized: Win Rate 60%, PF 1.50, Trades 10
QQQ MACD: Win Rate 33%, PF 0.54, Trades 3
```

## إشارات حية (scripts/live_signals.py)

```python
# الأسهم المستهدفة
TARGET_SYMBOLS = ["SPX", "QQQ", "META", "TSLA"]
# ⚠️ SPX لا يعمل مع yfinance — استخدم SPY بدلاً
```

### Pipeline التحليل
1. `fetch_price_data(symbol, period="3mo")` ← yfinance
2. `analyze_market(data)` ← RSI, MACD, MA, Bollinger, ATR
3. `generate_strikes(price, spread=0.03, count=6)` ← حول السعر
4. `engine.analyze(signal, price_data, strikes)` ← جميع الاستراتيجيات
5. `engine.best_strategy(...)` ← اختيار الأفضل
