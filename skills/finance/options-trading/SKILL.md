---
name: options-trading
description: "Options trading — 10 strategies (incl. Gamma/Abu Fahd), Greeks, backtesting, bot architecture, n8n deployment. Built from 30+ analyzed videos + @bitcoin_way resources."
version: 2.0.0
category: finance
---

# خيارات التداول — Options Trading

## 🎯 متى تستخدم هذه المهارة

عندما يطلب المستخدم:
- "فديوهات التداول" / "استراتيجية التداول"
- "الدلتا" / "فبوناتشي" / "PUT" / "CALL" / "Greeks"
- بناء بوت تداول من محتوى تعليمي
- تحليل/تقييم صفقة options
- "فين وقفنا في التداول"
- باك تست استراتيجيات الأوبشن
- Iron Condor, Butterfly, Spreads

## 📊 حالة المشروع (آخر تحديث: 22 مايو 2026)

**10 استراتيجيات + n8n نشر + Telegram Bridge + خطة استعادة كاملة**

| المرحلة | الحالة | التفاصيل |
|---------|--------|---------|
| 🎥 تحليل الفيديوهات | ✅ مكتمل | 30 فيديو (دراية + دار التداول) |
| 🧠 Phase 1 | ✅ مكتمل | بوت أساسي (Put/Call + فيبوناتشي + دلتا) |
| 🚀 Phase 2 | ✅ مكتمل (17 مايو) | 9 استراتيجيات + Greeks + باك تست |
| 🚎 Phase 2.5 | ✅ مكتمل (22 مايو) | استراتيجية #10 قاما + تحويل قوس→خطوط |
| ⚡ Phase 2.6 | ✅ مكتمل (22 مايو) | n8n + Telegram Bridge + خطة استعادة |
| 🏗️ Phase 3 | ⏳ معلق | بيانات القاما الحية + أتمتة كاملة |
| 🔗 مصادر خارجية | ✅ مضافة | أدوات من @bitcoin_way |

## 🏗️ هيكل البوت (Phase 2)

```yaml
trading-bot/
├── bot/
│   ├── models.py         # هياكل البيانات (TradeConfig, Leg, StrategyResult)
│   ├── greeks.py          # Black-Scholes + Delta, Gamma, Theta, Vega, Rho, IV
│   ├── strategy.py        # 9 استراتيجيات أوبشن أصلية
│   ├── gamma_strategy.py  # 🚎 استراتيجية أبو فهد قاما (#10) — أبراج القاما
│   ├── core.py            # المحرك الرئيسي (signal → analyze → execute → monitor)
│   ├── indicators.py      # فيبوناتشي + دلتا
│   ├── risk.py            # إدارة مخاطر متقدمة + Kelly Criterion
│   └── execution.py       # تنفيذ الأوامر (Paper Trading حالياً)
├── backtest/
│   └── engine.py          # backtesting.py (MACD, RSI, Optimization)
├── scripts/
│   ├── backtest.py        # تشغيل باك تست حقيقي
│   ├── live_signals.py    # إشارات حية من yfinance
│   ├── signal_alert.py    # ⚡ إرسال إشارات فورية عبر Telegram Bridge
│   ├── telegram_bridge.py # جسر Webhook (منفذ 7890) — يحول JSON → تلغرام
│   └── n8n_signal.py      # توليد إشارات لـ n8n
├── deploy/                # 🔥 خطة استعادة كاملة (Disaster Recovery)
│   ├── recovery.sh        # سكربت يشغّل كل شيء من الصفر
│   ├── systemd/           # n8n.service + telegram-bridge.service
│   ├── n8n/               # تعليمات إعادة بناء تقرير الصباح
│   └── cron/              # مهام Hermes المجدولة
└── references/
    └── tools.py           # أدوات خارجية مفهرسة
```

## 📚 الاستراتيجيات المستخلصة (10)

| # | الاستراتيجية | الأرجل | الربح |
|---|------------|--------|-------|
| 1 | **PUT/CALL مفرد** | 1 | غير محدود |
| 2 | **Debit Spread** | 2 (buy + sell) | محدود |
| 3 | **Credit Spread** | 2 (sell + buy) | محدود (علاوة) |
| 4 | **Iron Condor 🦅** | 4 | السوق يبقى بين strike الوسطى |
| 5 | **Butterfly 🦋** | 3 | السعر بالضبط عند ATM |
| 6 | **Strangle** | 2 (Put بعيد + Call بعيد) | حركة كبيرة بأي اتجاه |
| 7 | **Straddle** | 2 (Call ATM + Put ATM) | حركة كبيرة (أغلى من Strangle) |
| 8 | **Earnings** | 2 | حول إعلانات الأرباح |
| 9 | **Hedge 🛡️** | 1 | حماية المحفظة |
| 10 | **أبو فهد قاما (Gamma) 🚎** | 1 | تتبع سيولة الصانع عبر أبراج القاما |

## 🧮 اليونانيات (Greeks)

| اليوناني | الوظيفة | الاستخدام |
|---------|---------|-----------|
| **Delta** | حساسية سعر العقد لحركة السهم | اختيار Strike (0.5 Delta ATM) |
| **Gamma** | تغير الدلتا نفسها | إدارة المخاطر قرب expiry |
| **Theta** | تآكل قيمة العقد يومياً | ⏱️ لا تتداول آخر ساعة |
| **Vega** | حساسية لتغير التقلب (IV) | Iron Condor ينفع في IV منخفض |
| **Rho** | حساسية لتغير سعر الفائدة | العقود الطويلة (أشهر+) |

**المعادلة الذهبية (الدلتا):**
```
سعر العقد بعد الحركة = سعر العقد الحالي - (الدلتا × مقدار حركة السهم)
```

### Black-Scholes
- `option_price(S, K, T, r, sigma, type)` — سعر العقد
- `calculate_iv(market_price, ...)` — حساب التقلب الضمني من سعر السوق
- `GreeksCalculator.calculate_all(S, K, days, ...)` — جميع اليونانيات مرة وحدة
- `GreeksCalculator.calculate_spread(legs)` — اليونانيات لاستراتيجية متعددة الأرجل

## 🔬 باك تست (backtesting.py)

```
من: pip install backtesting yfinance scipy
```

| الاستراتيجية | الأداء (QQQ 2025) |
|-------------|------------------|
| MACD Crossover | -4% عائد، 3 صفقات |
| RSI (مُحسّن) | -4.8% عائد، 10 صفقات، 60% Win Rate |

**التحسين:** `bt.optimize(fast_ma=range(5,30,5), slow_ma=range(20,60,10))`

**مكتبة باك تست:** backtesting.py — تدعم المؤشرات الفنية فقط. لاستراتيجيات الأوبشن (Iron Condor, Spreads) نبني طبقة فوقها.

## 🚎 استراتيجية أبو فهد قاما (Gamma #10)

منهجية تداول مبنية على تتبع **سيولة الصانع (Market Maker)** من خلال أبراج القاما.

### المنهجية الأساسية

```
بيانات GAMMA Exposure حقيقية (SEC/CFTC) → منحنى (قوس) → تحويل → خطوط أفقية (أبراج)
```

**المصدر:** هيئة سوق المال الأمريكية تبيع بيانات القاما لشركات البيانات.
القاما الخام **منحنى** (شكل الجرس). دور المحلل: تحويله إلى **خطوط أفقية** عند النقاط الحرجة.

### الأبراج — الترتيب حسب القوة

| البرج | المعنى | الوزن |
|-------|--------|-------|
| 🔴 **أحمر** | نقطة انقلاب القاما (Zero Gamma/Flip Point) — الصانع ينقلب | الأقوى |
| 🟡 **أصفر** | أعلى جدار قاما (Gamma Wall) — أعلى تركيز سيولة | قوي |
| 🔵 **أزرق** | ثاني أعلى تركيز قاما | متوسط |
| ⚪ **أبيض** | نقاط ثانوية — مضاربي لحظي | أضعف |

### قواعد الدخول (منهجية أبو فهد)

1. **دخول CALL:** شمعة خضراء تفتح **فوق** البرج (غير ملامسة) → CALL
2. **دخول PUT:** شمعة حمراء تفتح **تحت** البرج (غير ملامسة) → PUT
3. **الوقف:** نفس البرج اللي دخلت منه
4. **Flip:** كسر البرج → اعكس الصفقة فوراً
5. **هدف:** 30% ربح
6. **صفقة واحدة باليوم** — حقق الهدف وأغلق الشاشة

### أوزان مناطق العرض والطلب

| الإطار الزمني | الوزن | الاستخدام |
|--------------|-------|-----------|
| 🟣 شهري | 3.0 | دخول رئيسي — سيولة مؤسسية |
| 🟡 أسبوعي | 2.0 | دخول رئيسي |
| 🔵 يومي | 1.5 | متوسط |
| 🟢 ساعة | 0.5 | ⛔ تأكيد ثانوي فقط — لا تدخل منها لحالها |

### التحويل البرمجي (extract_towers_from_gamma_curve)

المدخل: `gamma_curve[{price, gamma, open_interest}]`
المخرج: `list[GammaTower]` — خطوط أفقية مستخرجة من المنحنى

الخوارزمية:
1. البحث عن Flip Point (تقاطع القاما مع الصفر) → 🔴
2. البحث عن قمم القاما (Gamma Walls) → 🟡🔵⚪
3. إزالة المستويات المتقاربة جداً

## ⚡ البنية التحتية للنشر (Deployment)

### n8n — أتمتة التقارير
- خدمة systemd (`systemctl status n8n`) — منفذ 5678
- **تقرير الصباح:** n8n يشغّل `live_signals.py` كل أحد-خميس 4:30 عصراً بتوقيت مكة
- الإخراج: تقرير تلغرام مباشر

### Telegram Bridge — إشارات فورية
- خدمة systemd على منفذ 7890
- يستقبل JSON POST → رسالة تلغرام خلال **أقل من ثانية**
- `scripts/signal_alert.py` — واجهة CLI للإرسال

### خطة الاستعادة (Disaster Recovery)
```bash
git clone https://github.com/ADELSPX/trading-bot.git
cd trading-bot/deploy && chmod +x recovery.sh && sudo ./recovery.sh
```
يشغّل Hermes + n8n + Bridge + systemd تلقائياً. التفاصيل في `deploy/README.md`.

```
إشارة (Signal) → فيبوناتشي → توليد Strikes → 9 استراتيجيات → اختيار الأفضل
    ↓
إدارة المخاطر → Kelly Criterion → تنفيذ الأرجل → مراقبة P&L → إغلاق
```

**أفضل استراتيجية:** يحسب Profit/Risk Ratio ويختار الأعلى.

**الأسهم المستهدفة:** QQQ, META, TSLA, SPY

## 🔗 مصادر خارجية معتمدة (من @bitcoin_way)

| الأداة | الرابط | الفائدة للبوت |
|-------|-------|--------------|
| **TradingAgents** 🏆 | [github.com/TradeMaster-NTU/TradeMaster](https://github.com/TradeMaster-NTU/TradeMaster) | إطار multi-agent (UCLA/MIT) — هندسة ممتازة |
| **OpenBB** 🏆 | [github.com/OpenBB-finance/OpenBBTerminal](https://github.com/OpenBB-finance/OpenBBTerminal) | بيانات خيارات شاملة — تكامل MCP |
| **Vibe-Trading** | [github.com/vibe-trading](https://github.com/vibe-trading) | Natural language → Strategy → Backtest |
| **FinRL** | [github.com/AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL) | تعلم تعزيزي للتداول |
| **qlib** | [github.com/microsoft/qlib](https://github.com/microsoft/qlib) | منصة Microsoft كوانت كاملة |

## ⛔ العناصر القابلة للبرمجة

1. ✅ فيبوناتشي — تحديد مستويات الدعم/المقاومة
2. ✅ اختيار Strike — بناءً على توقع السعر (الـ 0.5 Delta)
3. ✅ 9 استراتيجيات أوبشن كاملة
4. ✅ تنفيذ Market/Limit Order
5. ✅ مراقبة P&L — رصد الربح/الخسارة
6. ✅ Take Profit + Stop Loss
7. ✅ Delta, Gamma, Theta, Vega, Rho calculation
8. ✅ باك تست تاريخي (MACD, RSI)
9. ✅ إشارات حية (yfinance)
10. ✅ Kelly Criterion لإدارة حجم الصفقة
11. ✅ n8n أتمتة التقارير اليومية (تقرير الصباح)
12. ✅ Telegram Bridge — إشارات فورية (< 1 ثانية)
13. ✅ خطة استعادة كاملة (deploy/recovery.sh)
14. ✅ تحويل قوس القاما إلى خطوط (extract_towers_from_gamma_curve)
15. ⏰ Time check — منع التداول خارج السوق
16. ⏳ بيانات القاما الحية — بانتظار المصدر (أبو فهد)

## 🧠 العناصر الغير قابلة للبرمجة
- القرار الأساسي: هل السوق سينزل أم سيصعد؟ (Directional bias)
- اختيار فيبوناتشي ليفل المناسب (قد يختلف حسب السياق)

## 🎯 اختيار Strike المثالي
- **أقرب 0.5 Delta ATM** (من الفيديوهات)
- **أفضل وقت للدخول:** 8:30–9:30 صباحاً Eastern (بعد الافتتاح بـ 30 دقيقة)

## 🛠️ الأدوات

| الأداة | الاستخدام |
|--------|-----------|
| `backtesting` (pip) | باك تست MACD, RSI مع تحسين |
| `yfinance` (pip) | جلب بيانات السوق الحية |
| `scipy` (pip) | الحسابات العددية |
| `Jina AI` (r.jina.ai) | قراءة X/Twitter (تغريدات @bitcoin_way) |
| `GitHub PAT` | رفع التحديثات للمستودع |

## ⚠️ معوقات + Pitfalls

1. **Voice-Pro** رفضناه: 9GB + توقف التطوير + لا يدعم لينكس
2. **YouTube** محجوب — الحل: Google Drive
3. **Telegram gateway** يستهلك تحديثات — الحل: Google Drive
4. **SSH إلى A6** اشتغل لكن المستخدم فضّل درايف
5. **circular import** بين core.py و risk.py — الحل: models.py منفصل
6. **GitHub PAT في URL** ينتهي بصمت (git push يعلق بدون خطأ) — لازم يجدد التوكن
7. **strikes** في الـ Strangle لازم تدقق لو strikes بعيدة عن السعر
8. **backtesting.py** ما تدعم الأوبشن مباشر — نبني طبقة فوقها
9. **مناطق الساعة** ⛔ لا تدخل منها لحالها — تأكيد ثانوي فقط (توجيه أبو جهاد 22 مايو)
10. **القاما الخام منحنى** — لازم تحويل إلى خطوط قبل استخدامه كأبراج (extract_towers_from_gamma_curve)
11. **بيانات القاما** تنتظر المصدر (أبو فهد) — الكود جاهز لكن بدون بيانات حية

## 📁 ملفات مرتبطة

- `references/tools.py` — أدوات خارجية مفهرسة مع تقييم أولوية
- `references/video-5-summary.md` — تحليل أول 5 فيديوهات
- `references/delta-formula-examples.md` — أمثلة الدلتا
- `references/derayah-notes.md` — ملاحظات منصة دراية
- `references/gamma-methodology.md` — منهجية أبو فهد قاما: تحويل القوس إلى خطوط (تفصيل كامل)
