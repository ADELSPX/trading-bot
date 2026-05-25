# Signal Builder — دليل الاستخدام

## الملف: `bot/signal_builder.py`

يحوّل تحليل `SupplyDemandStrategy` إلى إشارة تداول جاهزة بتنسيق احترافي.

### الفئات الرئيسية:

| الفئة | الوصف |
|-------|-------|
| `ContractSpec` | مواصفات العقد (رمز + Strike + تاريخ + اتجاه) |
| `TradeSignal` | الإشارة الكاملة (عقد + منطقة + هدفين + ثقة) |
| `Position` | صفقة نشطة للمتابعة |
| `SignalBuilder` | المولد الرئيسي |

### الاستخدام:

```python
from bot.supply_demand_strategy import SupplyDemandStrategy
from bot.signal_builder import SignalBuilder

# ١. التحليل
sd = SupplyDemandStrategy()
sd.detect_zones(candles)
sd.detect_trends(candles)
decision = sd.decide(candles, spx_price)

# ٢. بناء الإشارة
sb = SignalBuilder()
signal = sb.build_signal(decision, spx_price, symbol='SPX')
# → TradeSignal: contract, entry_zone, stop, target1, target2, confidence

# ٣. تنسيق وعرض
print(sb.format_signal(signal))
```

### توليد العقد فقط:

```python
c = sb.generate_contract('SPX', current_price=7456, direction='CALL', strike_offset_pct=0.5)
print(c.full_symbol)  # SPXW 260526 C 7495
```

### متابعة الصفقة:

```python
pos = Position(signal=signal, entry_price=3.40, entered_at=datetime.now().isoformat())
sb.save_position(pos)  # → /root/trading-bot/data/positions.json

# فحص الصفقة
hit = sb.check_position(current_price=7500, position=pos_dict)
# → "target1" | "target2" | "stopped" | None
```

### ⚠️ SPX = SPY × 10:

SignalBuilder يتوقع أسعار SPX الحقيقية (≈7456). عند استخدام SPY:
```python
spx_price = spy_price * 10
# ثم مرر spx_price لـ build_signal() و generate_contract()
```

### هيكل الإشارة (تنسيق تلغرام):

```
🤖 إشارة تداول SPX
🔴/🟢 الاتجاه: PUT/CALL
🔴/🟢 العقد: SPXW YYMMDD P/C XXXX

🟡 نوع الفرصة: سوينق/مضاربة
🟡 درجة الثقة: عالية/متوسطة/منخفضة

⚙️ خطة التنفيذ:
🔹 نوع الدخول: اختراق/إعادة اختبار
🔹 منطقة الدخول: XXXX – XXXX
🔹 مستوى الوقف: XXXX
🔹 الهدف الأول: XXXX
🔹 الهدف الثاني: XXXX

📋 العقد المقترح:
CALL/PUT | SPXW YYMMDD P/C XXXXX
Strike: XXXXX | انتهاء: YYMMDD

⚠️ للتحليل فقط — ليست توصية مالية
💡 التزم بإدارة رأس المال
```
