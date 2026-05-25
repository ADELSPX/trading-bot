# أنبوب تحويل الفيديو إلى نص (Video → Text Pipeline)

## لماذا هذا الأنبوب؟

عند الحاجة لتحليل فيديوهات تعليمية (دورات، محاضرات، دروس) واستخراج معلومات أو قواعد منها — دون استهلاك توكنز vision باهظة.

## المشكلة مع Voice-Pro

الأداة اللي انتشرت في مايو 2026 (**Voice-Pro** — `abus-aikorea/voice-pro`):
- ❌ تطويرها متوقف (الفريق منشغل بمشروع WeConnect)
- ❌ 9 جيجا تحميل أولي (موديل CosyVoice)
- ❌ لينكس مو مدعوم رسمياً — مصممة لـ Windows + NVIDIA GPU
- ❌ ثقيلة جداً لخوادم السحابة الصغيرة

## البديل الخفيف (152MB فقط)

| الأداة | الحجم | الوظيفة |
|--------|-------|---------|
| `yt-dlp` | ~2MB | تحميل فيديوهات يوتيوب واستخراج الصوت |
| `faster-whisper` | ~150MB (base) | تحويل الصوت إلى نص (يدعم العربية) |

## التثبيت

```bash
# yt-dlp — تحميل الفيديو
pip install --break-system-packages yt-dlp

# faster-whisper — تفريغ النص
pip install --break-system-packages faster-whisper
```

موديل whisper بيتحمل تلقائياً (~150MB) أول مرة تستخدمه.

## خطوات الاستخدام الكاملة

### 1. تحميل الفيديو واستخراج الصوت

```bash
yt-dlp -x --audio-format mp3 -o "%(title)s.%(ext)s" "رابط_اليوتيوب"
```

- `-x`: استخراج الصوت فقط
- `--audio-format mp3`: تحويل إلى MP3
- `-o`: اسم الملف الناتج

### 2. تحويل الصوت إلى نص

```python
from faster_whisper import WhisperModel

model = WhisperModel("base", device="cpu", compute_type="int8")
segments, _ = model.transcribe("audio.mp3", language="ar")

for segment in segments:
    print(f"[{segment.start:.1f}s → {segment.end:.1f}s] {segment.text}")
```

## وقت المعالجة المتوقع

| حجم الفيديو | yt-dlp | Whisper (CPU) | المجموع |
|-------------|--------|---------------|---------|
| 5 دقائق | ~15s | ~30s | ~45s |
| 10 دقائق | ~30s | ~60s | ~90s |
| ساعة | ~3min | ~6min | ~9min |

## مقارنة التكلفة: هذا الأنبوب vs Vision

| الطريقة | 11 فيديو × 7 دقائق |
|---------|---------------------|
| Vision (تحليل كل إطار) | آلاف التوكنز ❌ |
| yt-dlp + Whisper (صوت → نص) | 0 توكنز ✅ |

## تطبيق عملي: استخراج استراتيجيات تداول من فيديوهات

1. حمّل كل الفيديوهات: `yt-dlp -x --audio-format mp3 "URL"`
2. حوّل كل ملف صوتي لنص: `faster-whisper`
3. حلل النص واستخرج القواعد:
   - نقاط الدخول (Entry conditions)
   - نقاط الخروج (Exit conditions)
   - أنواع العقود (strike/expiry)
   - إدارة المخاطر (position sizing)
4. ابنِ السكريبت على القواعد المستخرجة

## قيود

- whisper base ممتاز للإنجليزي — للعربية استخدم `medium` (~1.5GB)
- يحتاج ffmpeg مثبت: `apt install ffmpeg`
- على CPU: أبطأ من GPU بس عملي للفيديوهات القصيرة
