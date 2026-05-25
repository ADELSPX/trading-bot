# 🔊 TTS Voice Alerts for Trading Bot

> تمت التجربة: 21 مايو 2026
> المزود: xAI (Grok) — صوت `eve`

## كيفية توليد تنبيه صوتي

### 1. الاستخدام المباشر عبر الأداة

```python
from hermes_tools import text_to_speech

# توليد صوت وتحويله لـ MEDIA path
result = text_to_speech("نص التحذير بالعربي")
# → يعيد "/root/.hermes/audio_cache/tts_20260521_XXXXXX.ogg"
```

المسار الناتج يوضع في رسالة Telegram:
```
MEDIA:/root/.hermes/audio_cache/tts_20260521_XXXXXX.ogg
[[audio_as_voice]]
```

الـ `[[audio_as_voice]]` يخبر المنصة بإرساله كـ voice bubble (وليس ملف عادي).

### 2. Cron Job للفحص الدوري

```bash
hermes cron create "كل 30 دقيقة" \
  --name "مراقبة التداول" \
  --prompt "افحص صفقات التداول. إذا فيه Stop Loss تفعل أو خسارة فوق 5%، أرسل voice message تحذير على تليجرام. استخدم text_to_speech."
```

### 3. التكامل مع البوت مباشرة

داخل `bot/core.py` عند تنفيذ أمر طارئ:
```python
def send_alert(self, message: str):
    """إرسال تنبيه صوتي للمستخدم"""
    from hermes_tools import text_to_speech
    result = text_to_speech(message)
    # الـ MEDIA path يُمرر للـ send_message
    return result
```

## عينة صوتية مختبرة

النص التجريبي الذي نجح:
```
⚠️ تنبيه من نظام التداول. تم تفعيل أمر وقف الخسارة. السهم انخفض بنسبة 3.5 بالمئة. الخسارة المسجلة 450 دولار. راجع المحفظة فوراً.
```

الصوت: طبيعي، واضح، مناسب عربياً.

## مقدم الصوت

| المزود | الصوت | الجودة | التكلفة |
|--------|-------|--------|---------|
| xAI (Grok) | `eve` | ممتاز — طبيعي | مجاني (ضمن SuperGrok) |
| Edge TTS | `ar-SA-HamedNeural` | جيد — صوت ذكر | مجاني |
| ElevenLabs | حسب الـ voice_id | ممتاز | يتطلب API key |
