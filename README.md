# 🤖 Trading Bot — بوت تداول ذكي

بوت تداول **9 استراتيجيات أوبشن** مع باك تست وإدارة مخاطر متقدمة، مبني على تحليل 30 فيديو تدريبي.

## 📊 الاستراتيجيات

| # | الاستراتيجية | الوصف |
|---|------------|-------|
| 1 | **عقد مفرد** | Put/Call بسيط |
| 2 | **Debit Spread** | Bull Call / Bear Put |
| 3 | **Credit Spread** | Bull Put / Bear Call |
| 4 | **Iron Condor** 🦅 | 4 أرجل — ربح من السوق الهادئ |
| 5 | **Butterfly** 🦋 | 3 أرجل — ربح عند السعر المستهدف |
| 6 | **Strangle** | Put + Call بعيدين |
| 7 | **Straddle** | Put + Call ATM |
| 8 | **Earnings** | حول إعلانات الأرباح |
| 9 | **Hedge** 🛡️ | حماية المحفظة |

## 🏗️ الهيكل

```
trading-bot/
├── bot/
│   ├── core.py           # المحرك الرئيسي
│   ├── strategy.py       # 9 استراتيجيات أوبشن
│   ├── greeks.py         # Black-Scholes + جميع اليونانيات
│   ├── indicators.py     # المؤشرات الفنية (Fibonacci, Delta)
│   ├── risk.py           # إدارة المخاطر المتقدمة
│   └── execution.py      # تنفيذ الصفقات
├── backtest/
│   ├── engine.py         # باك تست (backtesting.py)
│   └── __init__.py
├── config/               # إعدادات التداول
├── data/                 # بيانات الإشارات
├── scripts/
│   ├── backtest.py       # تشغيل باك تست
│   └── live_signals.py   # إشارات حية
└── requirements.txt
```

## 🚀 التشغيل

```bash
pip install -r requirements.txt

# باك تست MACD على QQQ
python -m scripts.backtest

# إشارات حية
python -m scripts.live_signals
```

## 📡 الأسهم المستهدفة

- QQQ (NASDAQ 100)
- META
- TSLA
- SPY (S&P 500)

## 🧮 اليونانيات (Greeks)

| اليوناني | الوصف | الاستخدام |
|---------|-------|-----------|
| **Delta** | حساسية لحركة السهم | اختيار Strike |
| **Gamma** | تغير الدلتا | إدارة المخاطر |
| **Theta** | تآكل الوقت | وقت الدخول |
| **Vega** | حساسية للتقلب | Iron Condor |
| **Rho** | حساسية للفائدة | طويل الأمد |

## 🔬 المصادر

- 30 فيديو تدريبي (منصة دراية + دار التداول)
- [backtesting.py](https://github.com/kernc/backtesting.py) — مكتبة الباك تست
- Black-Scholes Option Pricing Model

## 📝 ملاحظات

- البوت حالياً **Paper Trading** (محاكي)
- الـ strike المثالي: **أقرب 0.5 Delta ATM** (من الفيديوهات)
- أفضل وقت للدخول: **8:30–9:30 صباحاً Eastern** (بعد الافتتاح بـ 30 دقيقة)
