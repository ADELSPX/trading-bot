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
