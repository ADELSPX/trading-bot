# 🤖 Trading Bot — بوت تداول ذكي

بوت تداول أوبشن + باك تست مبني على تحليل 30 فيديو تدريبي + Bitcoin Power Law.

## 📊 الرؤية

تحويل المعرفة من فيديوهات تدريبية إلى **بوت تداول آلي** يفهم السوق وينفذ الصفقات بناءً على:
- **فيبوناتشي** لتوقع حركة السعر
- **معادلة الدلتا** لحساب سعر العقد بعد الحركة
- **إدارة المخاطر** لكل صفقة
- **باك تست** لاختبار الاستراتيجيات تاريخياً

## 🏗️ هيكل المشروع

```
trading-bot/
├── bot/
│   ├── core.py           # المحرك الرئيسي
│   ├── strategy.py       # 9 استراتيجيات أوبشن
│   ├── indicators.py     # المؤشرات الفنية
│   ├── greeks.py         # اليونانيات
│   ├── risk.py           # إدارة المخاطر
│   └── execution.py      # تنفيذ الصفقات
├── backtest/
│   ├── engine.py         # باك تست (backtesting.py)
│   └── __init__.py
├── config/               # إعدادات البوت
├── data/                 # بيانات الإشارات
├── scripts/              # سكربتات التشغيل
├── requirements.txt
└── README.md
```

## 📦 التثبيت

```bash
pip install -r requirements.txt
```

## 🔧 الاستخدام

### باك تست المؤشرات الفنية

```python
from backtest import run_backtest, fetch_data

# جلب بيانات SPY
data = fetch_data("SPY", "2024-01-01")

# تشغيل الباك تست
results = run_backtest(data)
print(f"العائد: {results['return_pct']}%")
print(f"الصفقات: {results['total_trades']}")
print(f"Sharpe: {results['sharpe']}")
```

### تطوير استراتيجية مخصصة

```python
from backtesting import Strategy
from backtest import run_backtest, fetch_data

class MyStrategy(Strategy):
    ma_period = 30
    def init(self):
        self.sma = self.I(lambda x: pd.Series(x).rolling(self.ma_period).mean(), self.data.Close)
    def next(self):
        if not self.position and self.data.Close[-1] > self.sma[-1]:
            self.buy()
        elif self.position:
            self.position.close()

data = fetch_data("QQQ", "2024-01-01")
results = run_backtest(data, MyStrategy)
```

## 🎯 الاستراتيجيات المستخلصة

| # | الاستراتيجية | المصدر |
|---|------------|--------|
| 1 | العقود المفردة (Put/Call) | الفيديوهات |
| 2 | الديبت سبريد (Debit Spread) | الفيديوهات |
| 3 | الكريدت سبريد (Credit Spread) | الفيديوهات |
| 4 | الآيرون كندور (Iron Condor) 🦅 | الفيديوهات |
| 5 | البترفلاي (Butterfly) 🦋 | الفيديوهات |
| 6 | السترانجل (Strangle) | الفيديوهات |
| 7 | السترادل (Straddle) | الفيديوهات |
| 8 | إعلانات الأرباح | الفيديوهات |
| 9 | التحوط (Hedging) | الفيديوهات |

## 📡 الأسهم المستهدفة

- QQQ (NASDAQ 100)
- META
- TSLA
- SPX (S&P 500)

## 📝 المصادر

- **30 فيديو تدريبي** (منصة دراية + دورة دار التداول)
- **@bitcoin_way** — Bitcoin Power Law Model
- **[backtesting.py](https://github.com/kernc/backtesting.py)** — مكتبة الباك تست

## 🚀 البداية

```bash
# تثبيت المتطلبات
pip install -r requirements.txt
```
