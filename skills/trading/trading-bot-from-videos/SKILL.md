---
name: trading-bot-from-videos
description: "مشروع فديوهات التداول — استراتيجيات الأوبشن الكاملة من دورة الأسهم الأمريكية"
version: 6.2.0
category: trading
---

# 🤖 بوت التداول الذكي — من الفديوهات إلى التنفيذ

## 🆕 Signal Builder — مولد الإشارات الكامل — مايو 2026

أضيف `bot/signal_builder.py` لتوليد إشارات تداول جاهزة بتنسيق احترافي:

- 🎯 **توليد العقد تلقائياً**: `SPXW 260526 C 7495` (يضرب SPY × 10 للوصول لسعر SPX)
- 📐 **منطقة دخول (Range)**: بدل نقطة وحدة
- 🎯 **هدفين**: أول جزئي + ثاني كامل
- 📊 **متابعة الصفقة**: حفظ في `data/positions.json`
- ⚠️ **SPX = SPY × 10**: لا تنسى الضرب في 10 عند بناء شموع SPX

### 🎯 اختيار الـ Strike — المعادلة

Strike يُختار تلقائياً في `SignalBuilder.generate_contract()`:

```python
strike = current_price * (1 + offset_pct/100)  # لـ CALL
strike = current_price * (1 - offset_pct/100)  # لـ PUT
strike = round(strike / 5) * 5  # تدوير لأقرب 5
```

| المعامل | القيمة | السبب |
|---------|--------|-------|
| `strike_offset_pct` | 0.5% | عقد قريب = أرخص + يتحرك أسرع |
| التدوير | 5 نقاط | Strikes SPX تُسعّر بمضاعفات 5 |

**مثال (SPX=7456):**
- CALL: `7456 × 1.005 = 7493 → 7495`
- PUT: `7456 × 0.995 = 7419 → 7420`

**مقارنة بالمنافس:** Strike 7590 = 1.8% OTM (أبعد، أرخص لكن يحتاج حركة أكبر). اختيار 0.5% = توازن بين التكلفة وسرعة الحركة.

راجع `references/signal-builder-guide.md` للتوثيق الكامل.

## 🔄 دورة الإشارة الكاملة — Signal Lifecycle

الإشارة تمر بـ 5 مراحل من التوليد للتنفيذ:
`pending → active → target1_hit → target2_hit (or stopped)`

**مراقبين (مسارين):**
- ⚡ **Live Watcher** (`scripts/live_watcher.py`): سكربت مستمر يفحص السعر كل **5 ثواني**. يشغّل كـ background process: `terminal(background=true, command="/usr/bin/python3 -u /root/trading-bot/scripts/live_watcher.py")`. الحل الأسرع — أنسب للتداول اللحظي.
- 📡 **Cron Watcher** (`scripts/signal_watcher.py`): يفحص كل 10 دقائق. احتياطي في حال توقف الـ live watcher. موجود في مهمة Cron `⚡ مراقبة الصفقات`.

راجع `references/signal-lifecycle.md` للتفاصيل + هيكل `active_signal.json`.

### ⚡ Live Watcher — تشغيل وإدارة

**البنية الفعلية (مايو 2026):** yfinance بطيء جداً للمراقبة كل 5 ثواني (يأخذ 10-15s للاستدعاء). الحل = فصل الجالب عن المراقب:

- `scripts/price_fetcher.py` — يجيب السعر كل 30 ثانية ويحفظه في `data/current_price.txt`
- يفحص الإشارة النشطة (`active_signal.json`) مع كل تحديث
- إذا دخل السعر المنطقة ← ينبه فوراً عبر Telegram Bridge

```bash
# تشغيل الجالب في الخلفية (يحتاج PYTHONUNBUFFERED=1 و stdin piping):
PYTHONUNBUFFERED=1 /root/trading-bot/venv/bin/python3 /root/trading-bot/scripts/price_fetcher.py &

# أو عبر Hermes terminal:
terminal(background=true, command="PYTHONUNBUFFERED=1 /root/trading-bot/venv/bin/python3 /root/trading-bot/scripts/price_fetcher.py")
```

**ملاحظات مهمة:**
- `PYTHONUNBUFFERED=1` ضروري — بدونه المخرجات ما تظهر أبداً (حتى مع `-u` flag في subprocess)
- استخدم venv python: `/root/trading-bot/venv/bin/python3` (الـ venv موجود، عكس ما كُتب سابقاً)
- المخرج يُكتب لـ `/tmp/fetcher.log` للمراقبة
- السعر الحالي متاح في `data/current_price.txt` لأي سكربت آخر

## 🛟 نظام الاستعادة الكامل — fazza-recovery

3 مستودعات GitHub تحمي النظام بالكامل: `fazza-recovery` (استعادة شاملة)، `trading-bot` (كود البوت)، `hermes-backup` (أرشيف سريع).

في حال تعطل السيرفر: `git clone → bash restore.sh` يعيد كل شيء.

راجع `references/fazza-recovery-system.md` للتفاصيل.

## ⚠️ دروس من الفشل: n8n → Hermes Cron

n8n فشل كاملاً في أول 24 ساعة — التدفقات لم تشتغل بعد 22 مايو.
الحل: كل المهام المجدولة للتداول الآن في Hermes Cron (موثوق 100%).

راجع `references/cron-vs-n8n-pitfalls.md` للتفاصيل الكاملة.

## ⚠️ yfinance في بيئة هرمس

`yfinance` غير مثبت في venv هرمس. استخدم `/usr/bin/python3` لتشغيل تحليلات yfinance.

```bash
# التثبيت:
/usr/bin/python3 -m pip install --break-system-packages yfinance numpy scipy pandas
```

### ⚠️ `python3 -c` يعلق على السيرفر (PITFALL — مايو 2026)

`python3 -c "..."` يعلق indefinitely على هذا السيرفر (timeout بدون مخرجات).
**الحل:** استخدم stdin piping — `echo 'code' | python3` — وهذي الطريقة تشتغل بشكل موثوق.

```bash
# ❌ يعلق:
python3 -c "import yfinance as yf; s=yf.download('SPY',period='1d',progress=False); print(s['Close'].values[-1]*10)"

# ✅ شغال:
echo 'import yfinance as yf; s=yf.download("SPY",period="1d",progress=False); print(s["Close"].values[-1]*10)' | /usr/bin/python3
```

ينطبق هذا على `subprocess.run([python3, '-c', ...])` أيضاً — استخدم `subprocess.run([python3], input=code, ...)` بدلاً منها.

### ⚠️ yfinance يرجع القيم بأقواس (PITFALL — مايو 2026)

عند طباعة `s['Close'].values[-1]`، المخرج يكون `[7456.4]` (بين قوسين — numpy array).
استخدم `.strip('[]')` قبل `float()`:

```python
price = float(result.stdout.strip().strip('[]'))
```

### ⚠️ yfinance بطيء — لا يصلح لمراقبة أقل من 30 ثانية

`yfinance.download` يأخذ 10-15 ثانية لكل استدعاء. لا تحاول تشغيله كل 5 ثواني.
البنية الصحيحة: **Price Fetcher** منفصل (كل 30 ثانية) + **Signal Checker** (كل 5 ثواني يقرأ من ملف).

## ⚠️⚠️ SPX vs SPY — مقياس السعر (PITFALL خطير)

**SPY (ETF) ≠ SPX (المؤشر). SPY ≈ SPX ÷ 10.**

عند توليد عقود SPXW، يجب ضرب أسعار SPY في 10:

| | SPY (ETF) | SPX (المؤشر) |
|---|---|---|
| السعر | ~$745 | ~$7456 |
| الـ Strike الصحيح | ❌ 750 | ✅ 7495 |
| العقد الكامل | ❌ `SPXW 260526 C 750` | ✅ `SPXW 260526 C 7495` |

```python
# ✅ الصح: ضرب في 10 عند بناء الشموع لـ SPX
# ⚠️ استخدم .values[-1] مو .iloc[-1] — الأخير deprecated في yfinance (FutureWarning)
spy_price = float(spy['Close'].values[-1])
spx_price = spy_price * 10
for i in range(len(close)):
    candles.append({
        'open': float(spy['Open'].iloc[i]) * 10,
        'high': float(spy['High'].iloc[i]) * 10,
        'low': float(spy['Low'].iloc[i]) * 10,
        'close': float(spy['Close'].values[i]) * 10,
        'index': i
    })
# ثم استخدم spx_price مع SignalBuilder
signal = sb.build_signal(decision, spx_price, symbol='SPX')
```

**yfinance لا يدعم SPX مباشرة — استخدم SPY × 10.** إذا استخدمت SPY مباشرة مع SignalBuilder لـ SPX، Strike يطلع غلط (750 بدل 7500).

**سكربت جاهز:** `scripts/gen_signal.py` — يستخدم SPY × 10 ويولد إشارة SPX كاملة.

تمت إضافة استراتيجية **العرض والطلب** من ٦ محاضرات "العرض والطلب مع ابوليلى" بقناة Abo Mazen Trade (@abo_mazen) بتاريخ 23 مايو 2026.

**المصدر:** YouTube Playlist — `PLnMGGUNsnv8hXcFRFlxacW9Lt7-s31112`

**الملفات المضافة:**
- `bot/supply_demand_strategy.py` — 500+ سطر، المحرك الكامل (منهجية أبو ليلى كاملة)
- `bot/strategy.py` — مُحدّث ليشمل `evaluate_supply_demand()` + مدمج في `best_strategy()`
- `strategy.py` يدعم الآن 11 استراتيجية كاملة

**المحاضرات الستة:**
| # | المحاضرة | المحتوى |
|---|---------|---------|
| 1 | اساسيات المضاربة | 8 معايير تقييم المناطق + 4 أنواع شموع + حالات المناطق (فريش/ملموسة/مستهلكة/مكسورة) |
| 2 | رسم الترندات | W/M Pattern + أنواع الترند + شروط الكسر |
| 3 | اثبات المناطق | تأكيد المناطق قبل الرسم |
| 4 | أوامر الدخول والوقف | تحديد نقاط الدخول + وقف الخسارة + التداخل |
| 5 | الواو تريد | W Trade — منطقة كسرت الترند وعاد لها السعر |
| 6 | آلية اتخاذ القرار | منهجية القرار النهائي: الدخول/الانتظار/الفليب |

**مكونات الاستراتيجية:**
1. **كشف المناطق:** Swing High/Low → مناطق عرض/طلب + تصنيف الشموع (Base/Marubozu/Engulfing/Inside Bar)
2. **تقييم 8 معايير:** فريش + شموع 1-6 + R:R ≥ 2:1 + خروج 2x + شمعة كاملة + قوة + شكل + موقع
3. **تحليل الترند:** W/M Pattern + أنواع (صاعد/هابط/مكسور)
4. **الواو تريد:** منطقة كسرت ترند → السعر عاد لها
5. **مناطق الفليب:** عرض → طلب / طلب → عرض

**ملف الكود:** `bot/supply_demand_strategy.py` (500+ سطر)
- `SupplyDemandZone` — هيكل المنطقة (distal/proximal/state)
- `SupplyDemandStrategy.detect_zones()` — كشف المناطق من الشموع
- `SupplyDemandStrategy.evaluate_zone()` — تقييم ٨ معايير
- `SupplyDemandStrategy.detect_trends()` — كشف الترندات
- `SupplyDemandStrategy.detect_w_trade()` — كشف الواو تريد
- `SupplyDemandStrategy.decide()` — آلية اتخاذ القرار
- `StrategyEngine.evaluate_supply_demand()` — مدمج في strategy.py

**الاستدعاء:**

```python
# الاستدعاء المباشر (SupplyDemandStrategy):
from bot.supply_demand_strategy import SupplyDemandStrategy, EntryDecision
sd = SupplyDemandStrategy(symbol="SPY")
sd.detect_zones(candles)          # كشف المناطق
sd.detect_trends(candles)         # كشف الترندات
for z in sd.zones:
    score = sd.evaluate_zone(z, current_price, recent_candles)  # → int (0-8)
signal = sd.decide(candles, current_price)  # → EntrySignal dataclass
# signal.decision ∈ {BUY, SELL, WAIT, FLIP_BUY, FLIP_SELL}
# signal.confidence: float, signal.entry_price, signal.stop_loss, signal.risk_reward

# عبر StrategyEngine:
from bot.strategy import StrategyEngine
from bot.models import TradeConfig
engine = StrategyEngine(config=TradeConfig(symbol="SPY"))
result = engine.evaluate_supply_demand(candles, current_price)
# → StrategyResult dataclass: result.strategy_name, result.direction, result.approved, ...

# عبر best_strategy() — تقييم كل الاستراتيجيات:
best = engine.best_strategy(
    signal={'price': price, 'direction': 'call', 'confidence': 0.6},
    fib_levels={...}, delta=0.3,
    supply_demand_data={'candles': candles, 'current_price': price},
    gamma_data=None  # يمرر إذا توفرت بيانات القاما
)
# → StrategyResult dataclass: best.strategy_name, best.direction, best.reason, best.confidence
# ⚠️ StrategyResult هو dataclass — استخدم attribute access (.direction) وليس .get()
```

---

## 🆕 استراتيجية #10: أبو فهد قاما (GAMMA) — مايو 2026

تمت إضافة استراتيجية **أبو فهد قاما** من وثيقة `شرح استرتيجية ابو فهد قاما 1.docx` بتاريخ 22 مايو 2026.

**الملفات المضافة:**
- `bot/gamma_strategy.py` — 650+ سطر، المحرك الكامل لاستراتيجية القاما
- `bot/strategy.py` — مُحدّث ليشمل `evaluate_gamma()` + `best_strategy()`
- `strategy.py` يدعم الآن 11 استراتيجية كاملة

## 📋 مصدر المعرفة

**إجمالي الفيديوهات المفرغة والمحللة:**
- دفعة 1 (مايو 12): 10 فيديوهات منصة دراية + دار التداول
- دفعة 2 (مايو 13): 20 فيديو — دورة الأسهم الأمريكية والأوبشن كاملة (10 أيام)
- دفعة 3 (مايو 23): 6 فيديوهات — دورة العرض والطلب مع ابوليلى (Abo Mazen Trade)
- **المجموع: 36 فيديو محلل** ✅

### التقرير الشامل:
التقرير الكامل موجود في `references/تحليل-كامل-الدورة.md` — 523 سطر، 9 استراتيجيات، كل القواعد والمؤشرات.

---

## 🎯 الاستراتيجيات المستخلصة (9 استراتيجيات)

### 1. العقود المفردة (Single Call/Put)
| الاتجاه | العقد | التوقيت |
|---------|-------|---------|
| صاعد | شراء Call | عند التصحيح لمنطقة الدعم |
| هابط | شراء Put | عند الارتداد لمنطقة المقاومة |
| المشكلة | تأثير ثيتا سلبي عالي، تكلفة أعلى |

### 2. الديبت سبريد (Debit/Vertical Spread) ✅
**الهيكل:** شراء عقد قريب + بيع عقد أبعد
- **التكلفة:** أقل 45% من العقد المفرد
- **الثيتا:** أقل 28% تآكل
- **مناسب لـ:** صاعد (Bull Call) / هابط (Bear Put)

### 3. الكريدت سبريد (Credit Spread) 🔥
**الهيكل:** بيع عقد قريب + شراء عقد أبعد (للتغطية)
- **تحصل على الكريدت** مقدماً
- **اشترط الدخول:** IV عالي جداً (300%+)
- **الدلتا:** احتمالية وصول ≤ 5-15%
- **التغطية إلزامية** — لا تترك مكشوفاً

### 4. الآيرون كندور (Iron Condor) 🦅
**الهيكل:** 4 عقود — بيع Call بعيد + شراء Call أبعد + بيع Put بعيد + شراء Put أبعد
- **الهدف:** دخل عندما يبقى السهم في نطاق
- **مناسب لـ:** إعلانات الأرباح، الأسهم عالية IV
- **مثال:** فيسبوك بين 250 و 350

### 5. البترفلاي (Butterfly) 🦋
**الهيكل:** شراء طرف + بيع عقدين وسط + شراء طرف
- **التكلفة:** $0.80 بدل $2.42 (67% أوفر)
- **الربح اليومي:** ~16% يومياً
- **نسبة ربح/خسارة:** 3:1
- **ثيتا إيجابية** ✅

### 6. السترانجل (Strangle)
**الهيكل:** شراء Call باسترايك أعلى + شراء Put باسترايك أقل
- **الهدف:** حركة قوية في أي اتجاه
- **التكلفة:** أقل من السترادل
- **مناسب لـ:** TSLA, NVDA, AMD

### 7. السترادل (Straddle)
**الهيكل:** شراء Call + شراء Put بنفس الاسترايك (ATM)
- **التكلفة:** أعلى من السترانجل
- **يحتاج حركة قوية جداً**

### 8. استراتيجية إعلانات الأرباح
1. آخر ساعة قبل الإغلاق للدخول
2. حدد نطاق الحركة المتوقع (±3% مثلاً)
3. استخدم Iron Condor أو Credit Spread
4. الحركة النموذجية: ±3% إلى ±6%

### 9. التحوط (Hedging)
**الهيكل:** شراء Call أساسي + شراء Put استرايك بعيد (تأمين)
- يحمي من الانهيار المفاجئ
- مثل: سباي 450 مع بوت 435

### 10. استراتيجية أبو فهد قاما (GAMMA) 🚎 🆕
**المصدر:** وثيقة شرح استراتيجية أبو فهد قاما — مايو 2026
**النوع:** سكالبنج يومي (Scalping) — صفقة واحدة باليوم

**الأعمدة الثلاثة:**
| العمود | الوصف |
|--------|-------|
| 🗼 **أبراج القاما** | سيولة الصانع الحقيقية — بيانات من هيئة سوق المال الأمريكية (SEC/CFTC). المنهجية: تحويل منحنى القاما (قوس) إلى خطوط أفقية (أبراج). أحمر (Flip Point) > أصفر (Gamma Wall) > أزرق > أبيض (ثانوي) |
| 📦 **مناطق العرض والطلب** | بالأوزان: شهرية (3.0) > أسبوعية (2.0) > يومية (1.5) > ساعة (0.5 ⛔ تأكيد فقط — ما تدخل منها لحالها) |
| 🕯️ **الشموع البالعة** | 15 دقيقة للاتجاه، 5 دقائق للدخول |

**🚎 استعارة الباص:**
- كل برج عليه علامة 🚎 = محطة نقل ركاب
- تركب مع الباص عند المحطة، تبيع عند ربح 30%
- صفقة واحدة باليوم — حقق التارقت وأغلق الشاشة

**شروط دخول CALL (4 حالات — الأولوية للأبراج):**
1. شمعة خضراء فوق برج (غير ملامسة) — الشرط الأساسي
2. ارتداد من منطقة طلب (يومية/أسبوعية/شهرية فقط ⛔ بدون الساعة) + شمعة خضراء
3. اختراق برج بشمعة خضراء كاملة (بالعة)
4. اختراق ترند القاما

**شروط دخول PUT (4 حالات — الأولوية للأبراج):**
1. شمعة حمراء تحت برج (غير ملامسة) — الشرط الأساسي
2. ارتداد من منطقة عرض (يومية/أسبوعية/شهرية فقط ⛔ بدون الساعة) + شمعة حمراء
3. كسر برج بشمعة حمراء كاملة (بالعة)
4. كسر ترند القاما

**الوقف والـ Flip:**
- الوقف = نفس البرج اللي دخلت منه
- إذا كسر الوقف → اعكس الصفقة (Flip: CALL→PUT أو PUT→CALL)

**عقد رضا الوالدين 🕌:**
- عقد CALL دائماً عند أعمق برج قاع
- نصف سعر العقد (Limit Order)
- مدة يومين على الأقل

**أفضل الرموز (حسب أبو فهد):** QQQ, LLY, CRWD, COST, ASML, MDB

**ملف الكود:** `bot/gamma_strategy.py` (750+ سطر)
- `extract_towers_from_gamma_curve()` — 🆕 تحويل منحنى القاما الخام (من SEC) إلى خطوط أفقية (أبراج). يكتشف: Flip Point (🔴) + Gamma Walls (🟡🔵⚪)
- `detect_towers()` — مسارين: أساسي (gamma_curve من SEC) + احتياطي (Volume Profile/Swing Points)
- `ZONE_WEIGHT` — 🆕 أوزان المناطق: شهرية 3.0 > أسبوعية 2.0 > يومية 1.5 > ساعة 0.5 (⛔ مستبعدة من شروط الدخول)
- `GammaStrategy.analyze()` — تحليل كامل
- `StrategyEngine.evaluate_gamma()` — مدمج في strategy.py
- `parents_blessing_contract()` — عقد رضا الوالدين
- `should_flip()` — منطق Flip التلقائي

**الاستدعاء (GammaStrategy):**
```python
from bot.gamma_strategy import GammaStrategy, Direction, TowerStrength
gs = GammaStrategy(symbol="SPY", target_profit_pct=30.0)

# ١. استخراج الأبراج من منحنى القاما:
towers = gs.extract_towers_from_gamma_curve(gamma_curve, current_price)
# gamma_curve = [{price, gamma, open_interest}, ...]

# ٢. التحليل الكامل:
# ⚠️ analyze() يحتاج شموع 5 دقائق و 15 دقيقة!
# عند استخدام بيانات يومية فقط (yfinance)، قم بمحاكاة intraday candles
analysis = gs.analyze(
    price_data={'close': price, 'high': h, 'low': l, 'ma200': ma200},
    candles_5m=candles_5m,     # list[dict] — فريم 5 دقائق
    candles_15m=candles_15m,   # list[dict] — فريم 15 دقيقة
    volume_profile=None,
)
# → GammaAnalysis dataclass:
#   analysis.towers: list[GammaTower]
#   analysis.entry: GammaEntry | None (entry.direction, entry.entry_price, entry.stop_loss, ...)
#   analysis.nearest_tower_above / _below
#   analysis.notes: list[str]

# عبر StrategyEngine:
result = engine.evaluate_gamma(price_data, candles_5m, candles_15m)
# → StrategyResult dataclass
```

**مصدر بيانات القاما:**
- البيانات الحقيقية من هيئة سوق المال الأمريكية (SEC/CFTC) تباع لشركات البيانات
- القاما الخام = منحنى (قوس/شكل الجرس). دور المستخدم: تحويله إلى خطوط أفقية
- المدخل: `price_data['gamma_curve']` — قائمة `[{price, gamma, open_interest}, ...]`
- البوت يحوّلها تلقائياً: قوس → أبراج

**قواعد أبو فهد الصارمة:**
1. لا تعاكس شمعة بالعة إلا بعد تجاوزها (فريم ربع ساعة وفوق)
2. فريم 5 دقائق للدخول فقط — لا للتحليل
3. إذا تأخرت شمعتين عرضية وما شد → اطلع من الصفقة
4. آخر ساعة تداول = الساعة الذهبية (تقلبات قوية)
5. لا تشتري يوم الإعلان (تضخم العقود)
6. التعزيز يقلل متوسط العقد إلى الثلث — وإلا لا تعزز
7. العقد إذا عدا عليه أسبوع → ضعيف، تخارج وادخل جديد

---

## 📊 المؤشرات الفنية

| المؤشر | الاستخدام |
|--------|-----------|
| **MA 50** | مدى قصير |
| **MA 200** | المدى الطويل — الأهم (فوق = إيجابي، تحت = سلبي) |
| **MACD** | تأكيد فقط، ليس لاتخاذ القرار |
| **بولينجر باند** | تحديد النطاق — الضيق = انفجار متوقع |
| **حجم التداول** | تأكيد الحركة — الحجم العالي مع الاختراق = حقيقي |
| **فيبوناتشي 50%** | أهم مستوى ارتداد |
| **فيبوناتشي 61.8%** | النسبة الذهبية |

## 🧮 اليونانيات (The Greeks)

| اليوناني | المعنى | الاستخدام |
|----------|--------|-----------|
| **الدلتا (0-100%)** | حساسية العقد لحركة السهم | العلاقة بين السهم والعقد |
| **الثيتا** | تآكل الزمن | سلبي للمشتري، إيجابي للبائع |
| **IV (Implied Volatility)** | التقلب الضمني | >100% → بيع، <100% → شراء |

## 🎯 القواعد الصارمة

### تفضيلات المستخدم — نوع التداول
- ✅ **SPX (عقود أسبوعية SPXW)** — التركيز الأساسي
- ✅ **العملات (Forex)** — يمكن إضافتها لاحقاً
- ❌ **أسواق التنبؤ (Polymarket)** — المستخدم لا يفضلها صراحةً (25 مايو 2026)
- ❌ **المراهنات (Weather markets/Betting)** — مرفوضة

### قواعد التداول
1. **5% كحد أقصى** من رأس المال للصفقة الواحدة
2. **الاتجاه أولاً** — لا تعاكس السوق أبداً
3. **اشترِ من الدعم، بِع من المقاومة**
4. **غطِّ عقودك دائماً** — لا عقود مكشوفة
5. **آخر ساعة قبل الإغلاق** = أفضل توقيت
6. **لا تشتري IV > 60%**
7. **لا تتداول عقود اليوم نفسه**
8. **خطط + ورق + قلم** قبل كل صفقة

## 🌐 المنصات والأدوات

| المنصة/الأداة | الاستخدام |
|--------------|-----------|
| **Thinkorswim (TOS)** | التداول والتحليل الرئيسي |
| **TradingView** | الرسوم البيانية |
| **Barchart.com** | فلترة العقود — الأعلى نشاطاً |
| **Market Chameleon** | IV وإعلانات الأرباح |
| **Finviz.com** | Heatmap ونظرة عامة |
| **StockCharts.com** | رسوم مجانية |
| **IBKR** | منصة بديلة |

## 📁 هيكل البوت (Phase 1 — أساسي)

```\ntrading-bot/\n├── bot/\n│   ├── core.py                    # المحرك الرئيسي\n│   ├── strategy.py                # 11 استراتيجيات (Single, IC, Butterfly, Gamma, Supply/Demand)\n│   ├── supply_demand_strategy.py  # 🆕 استراتيجية العرض والطلب — أبو ليلى\n│   ├── gamma_strategy.py          # 🆕 استراتيجية القاما — أبو فهد\n│   ├── indicators.py              # المؤشرات الفنية\n│   ├── greeks.py                  # اليونانيات\n│   ├── risk.py                    # إدارة المخاطر\n│   └── execution.py               # تنفيذ الصفقات
├── backtest/             # باك تست (مدمج مع backtesting.py) ✅
│   ├── engine.py         # TechnicalStrategy + run_backtest + fetch_data
│   └── __init__.py
├── config/
│   ├── settings.py
│   └── stocks.yaml
├── data/
├── scripts/
├── requirements.txt      # +backtesting, yfinance, scipy
└── README.md
```

## 📦 باك تست (backtesting.py)

[backtesting.py](https://github.com/kernc/backtesting.py) — مكتبة باك تست لمؤشرات السوق (MA, RSI, MACD).

```python
from backtest import run_backtest, fetch_data
data = fetch_data("SPY", "2024-01-01")
results = run_backtest(data)
print(f"العائد: {results['return_pct']}%")
```

للأوبشن: backtesting.py لا تدعم عقود الأوبشن مباشر. نبني طبقة فوقها for Greeks + multi-leg.

## 📡 مصادر إضافية

- **@bitcoin_way** — Bitcoin Power Law Model: Price ∝ Time^5.8 (Santostasi). Fair value ~$120K. Floor ~$56K. 2033 target: $1M.
- **[backtesting.py](https://github.com/kernc/backtesting.py)** by kernc — AGPL-3.0, 8.3K⭐, باك تست مؤشرات + تحسين معاملات.
  - ⚠️ مثبتة ومختبرة: import backtesting يعمل، Backtest() + run() + optimize() شغالة
  - ⚠️ تحتاج: numpy, pandas, bokeh (تثبت مع pip install backtesting)
  - ⚠️ لا تدعم الأوبشن مباشر — نبني طبقة فوقها للـ Greeks
  - ⚠️ بعض الرنات تترك trades مفتوحة → استخدم finalize_trades=True

## 🏗️ الهيكل البرمجي (Phase 2 — مايو 2026)

### ملفات أساسية:

| الملف | الوظيفة | ملاحظات |
|-------|--------|---------|
| `bot/models.py` | TradeConfig, Leg, StrategyResult | 🆕 لكسر circular import |
| `bot/strategy.py` | 11 استراتيجيات (StrategyEngine) | multi-leg + Gamma + Supply/Demand |
| `bot/greeks.py` | Black-Scholes: Delta, Gamma, Theta, Vega, Rho, IV | 🆕 |
| `bot/risk.py` | إدارة مخاطر متعددة الأرجل + Kelly Criterion | 🆕 |
| `bot/signal_builder.py` | مولد الإشارات: عقد + منطقة + هدفين + متابعة | SignalBuilder, TradeSignal, ContractSpec |
| `bot/core.py` | TradingBot pipeline | يستورد من models.py |
| `backtest/engine.py` | باك تست (MACD, RSI) مع تحسين | يستخدم backtesting.py |
| `scripts/backtest.py` | باك تست كامل + تحليل بيئة الأوبشن | HTML تقارير |
| `scripts/live_signals.py` | إشارات حية من yfinance | حفظ كـ JSON |

### ⚠️ مشكلة Circular Import (حلها)
المشكلة: `core.py` يستورد `RiskManager` من `risk.py`، و`risk.py` يستورد `TradeConfig` من `core.py` → دائرة.

الحل: إنشاء `config/models.py` يحتوي على `TradeConfig`. جميع الملفات تستورد منه (`from config.models import TradeConfig`):
- `bot/core.py`
- `bot/risk.py`
- `config/settings.py`

**أيضًا:** `@staticmethod` في `indicators.py` استخدم `self._norm_cdf()` وهذا خطأ لأن static method ليس لها `self` — صحّح إلى `TechnicalIndicators._norm_cdf(d1)`.

### Real-Time Signal Infrastructure
Detailed setup in `references/trading-signal-infrastructure.md`:
- **Telegram Bridge** (systemd, port 7890) — real-time signals in ~0.5s
- **signal_alert.py** — CLI/API script for bots to send signals
- **Hermes Cron Jobs** — daily reports + position monitoring (replaced n8n, see pitfall)
- **Architecture**: Python webhook bridge for speed + Hermes Cron for scheduled workflows
- **Circular import fix**: `config/models.py` for `TradeConfig`
- **Static method fix**: `TechnicalIndicators._norm_cdf(d1)` instead of `self._norm_cdf(d1)`

### ⚠️ n8n Pitfall — Scheduler Unreliable (May 2026)
n8n workflow scheduler failed silently: all trading workflows executed once then errored in <1s with no retries. The Sunday report never ran — user missed the first scheduled report. **Do not rely on n8n for scheduled trading tasks.** Use Hermes Cron instead — it has run backup/news/monitoring jobs without a single failure. n8n database at `/root/.n8n/database.sqlite` can be queried via Python sqlite3 when the `sqlite3` CLI is not installed.

**n8n failed workflows (May 22, 2026):**
- `📊 تقرير الصباح` — error, <1s, never retriggered
- `Morning Trading Report` — error, <1s, never retriggered
- `Signal Alert - Real Time` — error, <1s, never retriggered

**Working Hermes Cron replacement (actual, tested May 25):**
```bash
# Daily report — 4:30 PM Mecca (13:30 UTC), Sun-Thu:
hermes cron create "30 13 * * 0-4" \
  --name "📊 تقرير التداول اليومي" \
  --skills "trading-bot-from-videos" \
  --prompt "شغّل تحليل SPY: yfinance → supply/demand zones → gamma → report" \
  --toolsets terminal,file,web \
  --workdir /root/trading-bot

# Position monitoring — every 10 min, Sun-Thu:
hermes cron create "*/10 * * * 0-4" \
  --name "⚡ مراقبة الصفقات" \
  --skills "trading-bot-from-videos" \
  --prompt "Check positions.json → alert on stop/target via text_to_speech" \
  --toolsets terminal,file,web,tts \
  --workdir /root/trading-bot

# Trigger immediately (don't wait for schedule):
hermes cron run <job_id>
```

### اختيار الاستراتيجية الأنسب
`StrategyEngine.best_strategy()` تستخدم معيار:
```
score = confidence * 10 + (max_profit / max(abs(max_loss), 1))
```
الأعلى score يفوز. تستثنى الاستراتيجيات ذات `approved=False` (فشل الشرط).

### ⚠️⚠️ اختيار المنطقة — الأقرب أم الأعمق؟ (PITFALL خطير — مايو 2026)

المستخدم رفض إشارات البوت لأنها كانت تختار أعمق منطقة طلب (7088، تبعد 5%) بدل أقرب منطقة للسعر (7429، تبعد 0.3%). الإصلاح في `supply_demand_strategy.py`:

**1. ترتيب المرشحين — وزن القرب 70% (السطر 734):**
```python
# ✅ الجديد: وزن القرب = 70%، الثقة = 30%
s._final_score = (s.confidence * 0.30) + (s._proximity * 0.70)
# ❌ القديم: يرتب بالثقة فقط → يختار أعمق منطقة
```

**2. المناطق القريبة من السعر لا تكسر (السطر 341):**
```python
# إذا السعر داخل المنطقة أو قريب (< 2%) → لا توصل لحالة BROKEN
price_in_zone = zone.bottom <= current_price <= zone.top
near_zone = abs(current_price - zone.mid) / current_price < 0.02
if price_in_zone or near_zone:
    touches = min(touches, 2)  # أقصى حد = CONSUMED، مو BROKEN
```

**3. تخفيض الحد الأدنى للمناطق القريبة (السطر 674):**
```python
# المناطق القريبة (< 1%) تقبل score ≥ 1 بدل ≥ 3
near_price = abs(current_price - zone.mid) / current_price < 0.01
min_score = 1 if near_price else 3
```

**4. هدف SELL = تحت الدخول (السطر 683):**
```python
# ✅ PUT: الهدف = تحت الدخول بـ 2x المسافة
tp = entry - (stop - entry) * 2  # للـ SELL
tp = entry + (entry - stop) * 2  # للـ BUY
# ❌ القديم: tp = current_price (للـ SELL يطلع الهدف فوق الدخول!)
```

### ⚠️ Pitfalls مكتشفة

1. **توليد Strikes:** عند تصفية strikes للـ Strangle، استخدم list comprehension + guard:
   ```python
   below = [s for s in strikes if s <= price * 0.97]  # ✅
   put_k = min(below) if below else strikes[0]
   # ❌ لا تستخدم: min(...) or strikes[0]  ← ينهار على empty seq
   ```

2. **SPX لا يعمل مع yfinance:** مؤشر SPX (S&P 500) لا يمكن جلبه عبر yfinance. استخدم `SPY` بدلاً منه للباك تست وتحليل بيئة الأوبشن.

3. **Backtest توقف:** بعض الاستراتيجيات تترك trades مفتوحة → استخدم `Backtest(data, strat, finalize_trades=True)`

4. **n8n غير موثوق:** جدولة n8n فشلت بصمت — كل التدفقات نفذت مرة واحدة ثم توقفت. استخدم Hermes Cron للتقارير المجدولة.

6. **GammaStrategy يحتاج شموع 5m و 15m:** `GammaStrategy.analyze()` يتطلب `candles_5m` و `candles_15m` كـ list[dict]. عند استخدام بيانات يومية فقط من yfinance، قم بمحاكاة intraday candles من الشمعة اليومية (تقسيم النطاق اليومي إلى 4 شمعات 15m و 12 شمعة 5m). التوقيع الكامل: `analyze(price_data, candles_5m, candles_15m, volume_profile=None)`.

7. **yfinance في بيئة Hermes — التثبيت الصحيح (مايو 2026):** حزمة yfinance + scipy + numpy مثبتة نظامياً عبر:
   ```bash
   /usr/bin/python3 -m pip install --break-system-packages yfinance scipy numpy pandas
   ```
   يوجد venv في `/root/trading-bot/venv/bin/python3` — استخدمه للسكربتات الطويلة (subprocess عبر stdin مو `-c`). للتشغيل السريع من cron، استخدم `/usr/bin/python3` مباشرة.

8. **execute_code sandbox لا يدعم yfinance:** الساندبوكس (`/tmp/hermes_sandbox_*/`) لا يحتوي على yfinance أو numpy أو scipy. لتشغيل تحليل التداول، استخدم `terminal()` مع heredoc (`/usr/bin/python3 << 'PYEOF'`) وليس `execute_code()`.

8. **StrategyResult هو dataclass — لا تستخدم .get():** `StrategyEngine.best_strategy()` و `evaluate_supply_demand()` و `evaluate_gamma()` يرجعون `StrategyResult` (dataclass من `bot/strategy.py`). استخدم attribute access: `result.direction`، `result.strategy_name`، `result.confidence` — وليس `result.get('direction')`.

9. **StrategyResult مكرر — انتبه للـ import:** يوجد `StrategyResult` في ملفين: `bot/models.py` (للـ multi-leg strategies: .name, .legs, .max_profit) و `bot/strategy.py` (للـ trading signals: .strategy_name, .direction, .strike). الذي يرجع من `best_strategy()` هو نسخة `bot/strategy.py`.

### مقارنة Black-Scholes مع السوق الحقيقي (شاهد الـ reference)

`references/مقارنة-Black-Scholes-مع-السوق.md` — اختبرت BS على بيانات SPY الحقيقية (17 مايو 2026):
- **الفرق ~$2.3 (+/- 0.3%)** بين BS والسوق — طبيعي بسبب bid/ask spread
- **الدلتا والاتجاه صحيحين 100%** — الأهم للتحليل
- **Theta سالبة** — صحيح لكل مشتري عقد

### أدوات خارجية من @bitcoin_way (17 مايو 2026)

قيمت تغريدتين من @bitcoin_way تحتويان على 15+ أداة تداول مفتوحة المصدر. جميعها سليمة. الأهم:

| الأولوية | الأداة | الرابط | الفائدة |
|---------|-------|-------|---------|
| 🏆 عالية | **TradingAgents** | github.com/TradeMaster-NTU/TradeMaster | إطار تداول متعدد الوكلاء (UCLA/MIT) |
| 🏆 عالية | **OpenBB** | github.com/OpenBB-finance/OpenBBTerminal | بيانات مالية + خيارات (Options) |
| 🟡 متوسطة | **Vibe-Trading** | github.com/vibe-trading | لغة طبيعية → استراتيجية → باكتست |
| 🟡 متوسطة | **Microsoft qlib** | github.com/microsoft/qlib | منصة كوانت |
| 🔵 منخفضة | FinRL, QuantDinger, Freqtrade | — | للأطلاع |


### باك تست — نتائج فعلية (مايو 2026)

```
QQQ | MACD (2025-01 → اليوم):
  العائد: -3.98%  |  الصفقات: 3  |  Win Rate: 33.33%  |  PF: 0.54

QQQ | RSI (optimized, 2025-01 → اليوم):
  العائد: -4.79%  |  الصفقات: 10  |  Win Rate: 60.00%  |  PF: 1.50  ✅

QQQ | MACD (5 سنين — 2022-01 → اليوم) 🏆:
  العائد: +57.82%  |  أقصى خسارة: -20.76%  |  Sharpe: 0.69
  الصفقات: 17  |  Win Rate: 47.06%  |  PF: 2.07  ✅✅

QQQ | RSI (5 سنين — optimized):
  العائد: -3.92%  |  أقصى خسارة: -30.25%  |  Sharpe: -0.05
  الصفقات: 36  |  Win Rate: 63.89%  |  PF: 1.20
```

**الخلاصة:** MACD على QQQ ممتاز (+57% في 5 سنين). RSI يعطي نسبة فوز عالية (63.8%) لكن الخسائر أكبر من الأرباح — يحتاج تحسين إدارة المخاطر.

## ⚠️ قواعد العمل (مهمة — تصحيحات المستخدم)

### التزم بالمتابعة — لا تترك الوعود معلقة
المستخدم يتوقع متابعة المهام المجدولة. إذا وعدت بشيء (تقرير الأحد، مراقبة الصفقات، اختبار)، يجب:
1. التحقق من التنفيذ في الموعد
2. إبلاغ المستخدم بالنتيجة
3. إذا فشل — الإصلاح فوراً دون انتظار تذكير من المستخدم
خرقت هذه القاعدة: وعدت بتقرير الأحد ومراقبة الصفقات، ولم أتابع. المستخدم اضطر لتذكيري.

### ابنِ بشكل صحيح من البداية — لا تنتظر التصحيحات
المستخدم قالها صراحة: "مو المفترض يكون الشغل ما يحتاج اعطيك ملاحظات". إذا كان فيه نموذج عمل (بوت منافس مثلاً)، ادرس تفاصيله كاملة قبل البناء:
- ✅ Strike صحيح (SPX = SPY×10)
- ✅ منطقة دخول قريبة من السعر
- ✅ هدفين (جزئي + كامل)
- ✅ متابعة بعد الصفقة (entry → target1 → target2)
لا تبني شيئاً وتنتظر المستخدم يصحح الأخطاء الواضحة.

### ⚠️⚠️ لا تغرق التليجرام بالإشعارات (PITFALL — مايو 2026)

المستخدم يرفض رفضاً قاطعاً إغراق التليجرام بالإشعارات المتكررة.

**القواعد:**
1. إشعارات المراقبة = **عند الحدث فقط** (دخول منطقة، هدف، وقف). ليس كل دورة فحص.
2. أي نظام مراقبة جديد (مثل صياد الإعلانات) = **cold start أولاً** (تخزين بدون إرسال)، ثم إرسال الجديد فقط.
3. cron واسع (كل ساعة أو ساعتين) — مو كل نص ساعة.
4. التهيئة الأولى لا ترسل شيئاً أبداً. فقط تخزّن.
5. **اسأل المستخدم عن المعايير قبل ما تبني** — لا تبني ثم تتفاجأ برفضه.

خرقت هذه القاعدة مع صياد التورس (car_hunter) — أرسل 56 إشعار دفعة واحدة. المستخدم ألغى المهمة فوراً.

### لا تنفذ قبل التقرير — إلا بتفويض صريح
المستخدم يطلب: **تحليل → تقرير → موافقته → تنفيذ**. لا تكتب كود، لا تنزل مكتبات، لا تشغل سكربت قبل ما تقر وتعرض التقرير وتنتظر أمره. خرقت هذه القاعدة في جلسات سابقة.

**الاستثناء:** إذا قال المستخدم "الأمر متروك كامل لصلاحياتك" أو "ابدأ لا انتظر" — هذا تفويض صريح للمهمة الحالية فقط. بعد انتهائها، تعود القاعدة للعمل.

### المصادر أولاً
عند إضافة استراتيجية جديدة: استخرجها من المصدر (فيديو، X، مقال) → حللها → اعرضها → انتظر → نفذ.

## 🔄 طرق البحث عن الفرص

1. **المسح العام:** Finviz → قطاعات → Heatmap
2. **فلترة الأوبشن:** Barchart → Unusual Options Activity
3. **إعلانات الأرباح:** Market Chameleon → حركة متوقعة

## 📋 الملفات المفرغة (إجمالي 30 فيديو لكل ساذج يراجعها قبل التقرير)

**الدفعة 1 (10 فيديوهات):** `/root/videos_input/`
- دراية (4) + دار التداول (2) + قديمة (4)
- المحلّل: `references/تحليل-10-فيديوهات-كامل.md`

**الدفعة 2 (20 فيديو):** `/tmp/trading-transcripts/`
- دورة الأسهم الأمريكية والأوبشن كاملة
- جميعها مفرغة بالكامل ✅

| الملف | الأسطر | المدة |
|-------|--------|-------|
| 01-11-59.txt | 0 (ضوضاء) | - |
| 01-12-06.txt | 1,952 | 82 د |
| 01-12-11.txt | 230 | قصير |
| 01-12-16.txt | 724 | 62 د |
| 01-12-20.txt | 2,273 | 73 د |
| 01-12-25.txt + part2 | **2,395** | **90 د** |
| 01-12-29.txt | 78896 بايت | 78 د |
| 01-12-34.txt | **2,614** | **89 د** |
| 01-12-39.txt | 2,333 | 75 د |
| 01-12-44.txt | 819 | 18 د |
| 01-12-53.txt | 2,538 | 58 د |
| 01-13-07.txt | 1,566 | 37 د |
| 01-13-12.txt | 554 | - |
| 01-13-22.txt | 441 | - |
| 01-13-29.txt | 500 | - |
| 01-13-37.txt | **3,243** | **80 د** |
| 01-13-45.txt | **2,412** | **80 د** |
| 01-13-53.txt | **2,472** | **70 د** |
| 01-14-08.txt | 2,221 | 71 د |


## 🔊 التنبيهات الصوتية (TTS Voice Alerts) — مايو 2026

### متى تستخدمها
للتحذيرات الطارئة اللي المستخدم يحتاج يعرفها فوراً حتى لو ما يتابع الشاشة:
- 🛑 Stop Loss تم تفعيله
- 📉 خسارة تتجاوز نسبة محددة (مثلاً 5% من رأس المال)
- 🚀 أمر كبير تم تنفيذه
- 🏆 Take Profit تحقق

### كيف تشتغل
**TTS tool** في Hermes Agent تحوّل نص لصوت وتُرسله على Telegram كـ voice message:

```python
from hermes_tools import text_to_speech, send_message

# توليد صوت
result = text_to_speech("⚠️ تنبيه. تم تفعيل وقف الخسارة عند $450")

# إرسال كـ voice bubble على Telegram
send_message(target="telegram", message=f"MEDIA:{result}")
```

### الإعدادات الحالية للمستخدم
- **المزود:** xAI (Grok) — صوته طبيعي، يفضله المستخدم
- **الصوت:** `eve` (xAI TTS)
- **اللغة:** عربي
- **بديل:** يمكن استخدام Edge TTS (صوت `ar-SA-HamedNeural`)

### طرق التفعيل مع البوت

**❶ Cron Job — فحص دوري:**
```bash
hermes cron create "*/30 * * * *" \
  --name "مراقبة المحفظة" \
  --skills "trading-bot-from-videos" \
  --prompt "افحص صفقات التداول النشطة. إذا فيه وقف خسارة تفعل أو خسارة >5%، أرسل voice message تحذير للمستخدم. استخدم text_to_speech بالعربي."
```

**❷ Skill مخصص — نداء مباشر من البوت:**
في ملف الـ skill أو داخل البوت، تضيف شرط التحذير الصوتي وقت تنفيذ الصفقة.

### بدائل مستقبلية
| الطريقة | المنصة | التكلفة | الفائدة |
|---------|--------|---------|---------|
| **SMS** | Twilio | ~$0.05/رسالة للسعودية | توصل بدون إنترنت |
| **Voice Call** | Vapi.ai | ~$0.05/دقيقة | يتصل بك هاتفياً ويقرأ التحذير |
| **TTS Telegram** | xAI/Edge | مجاني (موجود حالياً) | صوت على التطبيق الحالي |

### ملاحظة
المستخدم حالياً شغال على Telegram كواجهة أساسية (نفس الجلسة الحالية). التنبيهات الإضافية تفيد فقط إذا احتاج اتصال بدون نت. لا تقترح Twilio/Vapi إلا إذا طلبها صراحة.

## 📌 ملاحظات فنية مهمة

- **مشكلة VAD:** faster-whisper مع VAD يتجمد على الملفات الطويلة — استخدم `--no-vad`
- **الذاكرة:** السيرفر 3.7GB RAM — تشغيل transcription واحد فقط في كل مرة
- **مشكلة التايم أوت:** الملفات الطويلة تتجاوز 600s — استخدم background=true
- **تقسيم الملفات:** إذا انقطعت، استخدم `ffmpeg -ss OFFSET -i input.wav part2.wav`
- **yfinance ⚠️:** SPX (مؤشر S&P 500) لا يمكن جلبه عبر yfinance، استخدم SPY (ETF) للباك تست
- **yfinance في Hermes:** مثبت نظامياً AND in venv. الـ venv في `/root/trading-bot/venv/` **موجود** (تم تأكيده 25 مايو 2026). استخدم `/root/trading-bot/venv/bin/python3` للسكربتات الطويلة. للتشغيل السريع من cron، استخدم `/usr/bin/python3` مباشرة.
- **باك تست يعمل:** `python3 -c "from backtest import run_technical_backtest; print_results(run_technical_backtest('QQQ', '2025-01-01', 'rsi'))"`

### 🤖 سكربت التقرير اليومي (Cron-Ready — عبر Hermes Cron Agent Prompt)

لا يوجد `scripts/daily_report.py` مستقل حالياً. التقرير يُشغّل عبر Hermes Cron Agent الذي ينفذ كود Python مباشرة باستخدام `/usr/bin/python3`:

```bash
# Hermes cron job — يشغّل البايثون مباشرة في التقرير:
hermes cron create "30 13 * * 0-4" \
  --name "📊 تقرير التداول اليومي" \
  --skills "trading-bot-from-videos" \
  --prompt "شغّل تحليل SPY: yfinance → supply/demand zones → gamma → تقرير عربي" \
  --deliver origin \
  --toolsets terminal,file,web \
  --workdir /root/trading-bot
```

الكود الذي يُشغّل: `from bot.supply_demand_strategy import SupplyDemandStrategy; sd.detect_zones(candles); sd.decide(candles, price)` باستخدام `/usr/bin/python3` (الحزم مثبتة نظامياً).
