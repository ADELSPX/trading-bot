# Hermes Agent - المهارات والإعدادات
## آخر تحديث: 2026-05-25

### المهارات المثبتة:
1. **karpathy-discipline** — Karpathy-style agent discipline
   - ينفذ المطلوب فقط، لا يتوه، لا يبالغ
   - يحمّل دائماً (always_load)
   
2. **grill-with-docs** (من @JulianGoldieSEO)
   - يسأل أسئلة تفصيلية قبل أي مشروع
   - يمنع البناء قبل التخطيط

### مزودات:
- الأساسي: DeepSeek V4 Pro
- الرؤية: تحتاج مفتاح Google جديد (Gemini منتهي)

### إعدادات هامة:
- البوابة: systemd (hermes-gateway.service)
- المنصة: Telegram
- النسخ الاحتياطي: كل يوم 3 فجراً

## HUD Analyzer (28 أغسطس 2026)
- السكربت: `scripts/spx_hud_analyzer.py`
- الفكرة: مستوحاة من Hermes HUD Mode — تحليل مرئي لأي رمز
- الاستخدام: `python3 scripts/spx_hud_analyzer.py [SYMBOL] [PERIOD] [OUT]`
- المخرجات: شارت (دعم/مقاومة + فيبوناتشي + RSI + حجم + متوسطات) + ملخص نصي
- المصدر: تغريدة iamlukethedev عن Hermes HUD (28/8/2026) — طبقها أبو جهاد على SPX
