# سلسلة احتياط الرؤية — Vision Fallback Chain

آخر تحديث: 2026-05-25

## الترتيب الصحيح

```
1. vision_analyze (تلقائي — يختار المزود من config.yaml)
   ├─ Google Gemini → يحتاج GOOGLE_API_KEY ساري
   ├─ xAI/Grok     → يحتاج رصيد مدفوع (حتى مع SuperGrok OAuth!)
   ├─ DeepSeek     → لا يدعم image_url format
   └─ auto         → يختار أول مزود متاح

2. Tesseract OCR (احتياطي — محلي، مجاني)
   ├─ عربي: tesseract img.png stdout -l ara --psm 6
   ├─ إنجليزي: tesseract img.png stdout -l eng --psm 6
   └─ مختلط: tesseract img.png stdout -l ara+eng --psm 4

3. Preprocessing (إذا OCR مشوّه)
   ├─ تكبير 2x-3x مع LANCZOS
   ├─ تحويل لأبيض/أسود مع threshold 140
   └─ حفظ PNG مو JPG

4. استسلام
   └─ اطلب من المستخدم وصف الصورة أو رابطها
```

## أخطاء المزودات (2026-05-25)

| المزود | الحالة | السبب |
|--------|--------|-------|
| Google Gemini | ❌ مفتاح منتهي | `GOOGLE_API_KEY` في .env غير ساري |
| xAI/Grok | ❌ يبي رصيد | حتى مع OAuth، الرؤية تحتاج credits منفصلة |
| DeepSeek | ❌ لا يدعم | `unknown variant image_url` |
| auto | ❌ | ما لقى مزود شغّال |

## تثبيت Tesseract (مرة واحدة)

```bash
apt-get install -y tesseract-ocr tesseract-ocr-ara
pip3 install pytesseract Pillow --break-system-packages
tesseract --list-langs | grep ara  # تأكيد
```

## تذكير

- **لا تعلّق في حلقة debugging** — إذا فشلت 3 محاولات، انتقل للخطوة اللي بعدها
- **OCR مو مثالي** — النص بيطلع متقطع. استخدمه لتلميح (اسم حساب، أرقام) وليس نص كامل
- **اطلب مساعدة المستخدم** — إذا الصورة مهمة، وصفه لها أسرع من 10 محاولات OCR
