# ⚡ Live Watcher — إعداد وتشغيل

## المشكلة

Cron-based monitoring (كل 10 دقائق) بطيء جداً للتداول اللحظي على SPX. المستخدم يحتاج تنبيه خلال **ثواني** من وصول السعر لمنطقة الدخول.

## الحل: `scripts/live_watcher.py`

سكربت Python مستمر يراقب السعر كل 5 ثواني — يشغّل كـ background process على السيرفر.

### التشغيل

```bash
# مباشر (خلفية):
/usr/bin/python3 -u /root/trading-bot/scripts/live_watcher.py &

# عبر Hermes terminal tool:
terminal(background=true, command="/usr/bin/python3 -u /root/trading-bot/scripts/live_watcher.py")
```

### ملاحظات مهمة

1. **استخدم `-u` flag** — بدونها، stdout لا يظهر بسبب Python buffering
2. **yfinance بطيء نسبياً** — كل استدعاء `yf.download()` يأخذ ~3-10 ثواني. في المستقبل، استخدم WebSocket أو API أسرع.
3. **الاعتماد على `active_signal.json`** — السكربت يقرأ الإشارة من هذا الملف. تأكد أن `gen_signal.py` يكتبه أولاً.
4. **مسارين للمراقبة** — الـ live watcher (سريع) + cron watcher (احتياطي). إذا توقف الـ live watcher، cron يغطي الفجوة.

### دورة الحياة

```
١. يقرأ active_signal.json
٢. إذا stage=pending ← يفحص السعر كل 5s
٣. السعر دخل المنطقة ← يرسل تنبيه + يغير stage=active
٤. يتابع: target1_hit → target2_hit → stopped
```

### الفرق عن signal_watcher.py

| | signal_watcher.py | live_watcher.py |
|---|---|---|
| التشغيل | مرة واحدة (cron) | مستمر (while True) |
| الفحص | كل 10 دقائق | كل 5 ثواني |
| الإخراج | صامت | يطبع للسجل |
| الاستخدام | احتياطي | أساسي |
