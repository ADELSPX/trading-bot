# AGENTS.md — بوت تداول SPX (فزاع)

> اقرأ هذا الملف قبل أي جلسة. اقرأ LESSONS.md بعده.

## المشروع
بوت تداول خيارات SPX — يولد إشارات PUT/CALL مع Strike صحيح، منطقة دخول، وقف، وأهداف. يرسل عبر تيليجرام بسرعة (ثواني).

## التقنيات
- Python 3 + yfinance (بيانات السوق)
- استراتيجية العرض والطلب + القاما
- إرسال: Telegram Bridge (localhost:7890)
- الاستضافة: Linux (3.7GB RAM)
- المرجع: `ADELSPX/trading-bot` على GitHub

## هيكل المشروع
```
trading-bot/
├── bot/                     # المكتبات الأساسية
│   ├── signal_builder.py    # بناء الإشارة كاملة
│   └── supply_demand_strategy.py  # استراتيجية العرض والطلب
├── scripts/                 # السكريبتات التنفيذية
│   ├── gen_signal.py        # توليد إشارة
│   ├── live_watcher.py      # مراقب حي (كل 5 ثواني)
│   ├── price_fetcher.py     # جالب السعر (كل 30 ثانية)
│   └── signal_watcher.py    # مراقب (كل 10 دقائق)
├── skills/                  # مهارات Hermes
├── LESSONS.md               # سجل الأخطاء (اقرأه!)
├── HERMES_SKILLS.md         # توثيق المهارات
├── setup.sh                 # سكريبت الاستعادة
└── README.md
```

## ⚠️ محظورات (لا تنتهكها أبداً)

1. **لا تعدل `bot/signal_builder.py` بدون تخطيط مسبق** — قلب النظام
2. **لا تحذف أي ملف بدون تأكيد** — البوت حي
3. **لا تغير صيغة الإشارة** — المستخدم يعتمد على الشكل الحالي
4. **لا تفترض الأسعار** — اسحب من yfinance (`^SPX`) مباشرة
5. **لا تبدأ تطوير بدون `grill-with-docs` أولاً**
6. **أي تطوير = git push فوراً** — GitHub هو المصدر الوحيد للحقيقة

## أوامر مهمة
```bash
# اختبار سريع
echo 'from bot.signal_builder import SignalBuilder; print("OK")' | python3

# تشغيل المراقب الحي
python3 scripts/live_watcher.py > logs/watcher.log 2>&1 &

# جالب السعر
python3 scripts/price_fetcher.py > logs/price.log 2>&1 &

# توليد إشارة
echo 'import sys; sys.path.insert(0,"."); from scripts.gen_signal import main; main()' | python3
```

## سير العمل
1. اقترح خطة (grill-with-docs)
2. ناقشها مع المستخدم
3. نفذ — خطوة خطوة
4. كل خطوة = اختبار + git commit + push
5. حدث LESSONS.md إذا صار خطأ

## قيود البيئة
- الرام: 3.7GB فقط — إذا نزل عن 400MB الصوت يفشل
- الرؤية: Gemini منتهي، xAI بدون رصيد — استخدم Tesseract للصور العربية
- python3 -c يعلق — استخدم echo pipe
- العمليات الخلفية تحتاج توجيه stdout لملف
