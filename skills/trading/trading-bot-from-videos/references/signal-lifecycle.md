# 🔄 دورة الإشارة — Signal Lifecycle

الهيكل الكامل لتوليد الإشارة ومتابعتها من البداية للنهاية.

## المكونات

| الملف | الوظيفة |
|-------|---------|
| `scripts/gen_signal.py` | توليد إشارة + حفظ في active_signal.json |
| `scripts/signal_watcher.py` | مراقبة السعر + إرسال تنبيهات |
| `scripts/signal_alert.py` | إرسال إشارات فردية للتلغرام |
| `data/active_signal.json` | الإشارة النشطة الحالية |
| `bot/signal_builder.py` | SignalBuilder — يبني TradeSignal من EntrySignal |

## التدفق الكامل

```
⏰ 4:35 عصراً (أحد-خميس)
   ↓
📡 gen_signal.py
   ├─ yfinance → SPY × 10 = SPX
   ├─ SupplyDemandStrategy → zones + decide()
   ├─ SignalBuilder → ContractSpec + TradeSignal
   └─ 💾 data/active_signal.json
   ↓
⏱️ signal_watcher.py (كل 10 دقائق)
   ├─ يقرأ active_signal.json
   ├─ يجيب سعر SPX الحالي
   └─ يفحص:
       ├─ stage=pending + price ∈ entry_zone
       │   → stage=active → 🚀 تنبيه "تفعّلت الإشارة"
       ├─ stage=active + price ≥ target1 (CALL) or ≤ target1 (PUT)
       │   → stage=target1_hit → 💸 "تم تحقيق الهدف الأول"
       ├─ stage=target1_hit + price ≥ target2 or ≤ target2
       │   → stage=target2_hit → 🏆 "تم تحقيق الهدف الثاني"
       └─ stage=active + price ≥ stop (PUT) or ≤ stop (CALL)
           → stage=stopped → 🛑 "تم تفعيل الوقف"
```

## هيكل active_signal.json

```json
{
  "entry_zone": [7429.1, 7443.9],
  "stop_loss": 7495.3,
  "target1": 7377.7,
  "target2": 7318.9,
  "direction": "PUT",
  "contract": "SPXW 260526 P 7420",
  "strike": 7420,
  "expiry": "260526",
  "confidence": 0.25,
  "reason": "منطقة عرض | Base | 2/8",
  "stage": "pending",
  "generated_at": "2026-05-25 12:54"
}
```

مراحل `stage`:
- `pending` — تم توليد الإشارة، بانتظار دخول السعر للمنطقة
- `active` — السعر دخل المنطقة، الصفقة شغالة
- `target1_hit` — تم تحقيق الهدف الأول
- `target2_hit` — تم تحقيق الهدف الثاني (الصفقة انتهت)
- `stopped` — تم تفعيل وقف الخسارة

## التنبيهات

المراقب يرسل عبر `signal_alert.py` → Telegram Bridge (منفذ 7890) → تلغرام المستخدم.

التنبيه يصل خلال ~0.5 ثانية من تفعيل الشرط.

## ⚠️ ملاحظات

- المراقب يستخدم yfinance (بيانات متأخرة 15-20 دقيقة). للبيانات الحية، يحتاج مصدر مدفوع.
- المراقب لا يعمل خارج أيام التداول (Sat/Sun) — Cron مضبوط على `0-4` (أحد-خميس).
- إذا ما فيه ملف active_signal.json، المراقب يخرج بهدوء (يرسل شي).
