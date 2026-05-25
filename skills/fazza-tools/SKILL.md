---
name: fazza-tools
description: "منظومة الأدوات المجانية: TinyFish (بحث+جلب) + Jina AI (قراءة مواقع سعودية وتغريدات X) + Gemini (رؤية الصور)"
version: 1.2.0
category: devops
---

# منظومة فزّاع — أدوات مجانية متكاملة

## قاعدة رئيسية: الأدوات لفزّاع أولاً

عند إضافة أو استخدام أداة جديدة — **ركّبها في Hermes (فزّاع) أولاً**، مو في OpenClaw/Nashmi.
Nashmi له استخداماته الخاصة (Ollama على A6)، لكن أدوات الويب والتصفح والمصادر تكون في فزّاع.
فكّر كأن Nashmi ما عنده متصفح — إذا احتجت متصفح، استخدم إما Hermes browser tools أو Browse.sh أو Kimi WebBridge.

## الأدوات

| الأداة | الوظيفة | التكلفة | المفتاح |
|--------|---------|---------|---------|
| **TinyFish Search** | بحث ويب كامل (عربي + إنجليزي) | 500 رصيد مجاني | `X-API-Key` |
| **TinyFish Fetch** | جلب محتوى المواقع | من الرصيد | `X-API-Key` |
| **Jina AI** | قراءة تغريدات X + مواقع سعودية محظورة | مجاني مفتوح | بدون |
| **faster-whisper** | تفريغ فيديوهات عربية محلياً | مجاني (جهازك) | بدون |
| **Gemini Vision** | قراءة الصور (model: gemini-2.5-flash) | مجاني | `GOOGLE_API_KEY` |
| **Techmeme via Jina** | أخبار تقنية و AI شاملة (بديل تويتر) | مجاني | بدون |
| **Gemini Vision** | قراءة الصور (model: gemini-2.5-flash) | مجاني | `GOOGLE_API_KEY` ⚠️ |
| **Tesseract OCR** | قراءة النص العربي من الصور (احتياطي) | مجاني (جهازك) | بدون |

## متى تستخدم كل أداة

```
قراءة صورة            → vision_analyze (تلقائي)
فشل vision_analyze    → Tesseract OCR (عربي: ara, إنجليزي: eng)
فشل Tesseract         → ارفع تباين + كبّر ×2 أو ×3 وأعد المحاولة
فشل بعد 3 محاولات    → اطلب من المستخدم وصف الصورة أو رابطها
```
قراءة موقع سعودي      → Jina AI (تخترق الحجب الحكومي)
قراءة تغريدة X        → Jina AI (حيلة http://) ⚠️ فقط
قراءة صورة            → Gemini Vision
أخبار تقنية يومية     → Techmeme عبر Jina (بديل X للقراءة)
تفريغ فيديو عربي      → arabic-video-transcription مهارة
تصفح موقع بخطوات كثيرة → Browse.sh Skill (أسرع + أقل توكنز)
سحب بيانات من موقع محدد  → Browse.sh Skill (Pre-built script للموقع)
أداء متصفح جوال + تسجيل دخول → Kimi WebBridge على A6
```

## Browse.sh — Skills متصفح جاهزة

Browse.sh (باكند Browserbase) — كتالوج مفتوح فيه مئات Skills المتصفح الجاهزة لمواقع محددة.
كل Skill مبنية خصيصاً للموقع (API endpoints, selectors, anti-bot bypass) — أسرع وأدق من المتصفح اليدوي.

## متى تستخدم Browse.sh Skills vs أدوات المتصفح العادية

| Browse.sh Skill | Hermes browser (navigate/click) |
|----------------|-------------------------------|
| Pre-built script للموقع | LLM يقرر كل خطوة |
| أقل بـ 50× توكنز | يستهلك توكنز كثيرة |
| يتجاوز anti-bot (CDP خفي) | يفشل مع CAPTCHA/logins |
| ما يصلح لتجارب مخصصة | مرن لأي موقع عشوائي |

## الأوامر

```bash
# البحث في الكتالوج
browse skills find <query>            # مثال: amazon, hotels, flights

# تثبيت Skill لموقع معين
browse skills add <slug>              # مثال: amazon.com/search-products-5170mf

# فتح متصفح محلي (بدون Browserbase Cloud)
browse open <url> --local

# قائمة الـ Skills المتاحة
browse skills list
```

## ⚠️ مشاكل وحلول

- **vision_analyze يفشل برسالة API key not valid**: المفتاح انتهى. لا تكرر المحاولة — انتقل مباشرة لـ Tesseract OCR.
- **Tesseract غير مثبت**: `apt-get install -y tesseract-ocr tesseract-ocr-ara && pip3 install pytesseract Pillow --break-system-packages`
- **النص العربي مشوّه في OCR**: استخدم `--psm 6` أو `--psm 4`، وارفع حجم الصورة ×2 أو ×3 مع تباين أعلى:
  ```python
  from PIL import Image
  img = Image.open("path.jpg")
  img = img.resize((w*2, h*2), Image.LANCZOS)
  gray = img.convert("L")
  bw = gray.point(lambda x: 0 if x < 140 else 255)
  bw.save("/tmp/ocr_input.png")
  ```
- **OCR يطلع لاتيني بس؟**: جرب `-l ara+eng`

- **تعارض اسم `browse`**: بعض أنظمة لينكس عندهم `/usr/bin/browse` (xdg-open). احذفه قبل تثبيت Browse.sh CLI: `rm /usr/bin/browse && npm install -g browse`
- **Daemon**: الـ CLI يحتاج daemon للبث المباشر. `browse doctor` يفحص الحالة.
- **API Key**: محلياً (`--local`) بدون مفتاح. للسحابة (بروكسيات + CAPTCHA) يحتاج `BROWSERBASE_API_KEY`.

**X/Twitter يرفض كل أدوات الجلب المباشرة (HTTP 426 Upgrade Required).**
**web_extract و browser_navigate و TinyFish Fetch كلها تفشل مع X.**
**الطريقة الوحيدة اللي تشتغل: Jina AI Reader بالحيلة:**

```bash
curl -sL 'https://r.jina.ai/http://x.com/USER/status/TWEET_ID'
```

السر: `http://` داخل الرابط — مش `https://`.

انظر مهارة `nashmi-x-reader` للتفاصيل الكاملة.

## الأوامر

```bash
# TinyFish CLI (أسرع وأقوى من curl)
export TINYFISH_API_KEY="sk-tinyfish-..."
tinyfish search query "..." --language ar --pretty
tinyfish fetch content get --format markdown "URL1" "URL2"
tinyfish agent run --url "URL" "استخرج البيانات كـ JSON"
```
# Jina AI — قراءة تغريدات X ومواقع محظورة
curl -sL 'https://r.jina.ai/http://x.com/USER/status/ID'
# Techmeme — أخبار تقنية شاملة
curl -sL 'https://r.jina.ai/https://www.techmeme.com' -H 'Accept: text/markdown'

# Gemini Vision — قراءة الصور (إذا vision_analyze فشل 503)
python -c "import base64,urllib.request,json; img=base64.b64encode(open('path','rb').read()).decode(); req=urllib.request.Request(url, json.dumps({'contents':[{'parts':[{'text':'prompt'},{'inline_data':{'mime_type':'image/jpeg','data':img}}]}]}).encode(), {'Content-Type':'application/json'}); print(json.loads(urllib.request.urlopen(req).read())['candidates'][0]['content']['parts'][0]['text'])"
- **قراءة صورة** — `vision_analyze` مباشرة. لو فشل 503 → Gemini Vision fallback

## المفاتيح

محفوظة في `/root/.hermes/.env`:
- `TINYFISH_API_KEY`
- `GOOGLE_API_KEY`
- `GEMINI_API_KEY`

## البحث عن كيانات سعودية/عربية غير معروفة

عندما يطلب المستخدم العثور على شخص أو قناة أو كيان عربي غير واضح المعالم:

### خطوات البحث المتدرجة

1. **TinyFish Search** (الأفضل والأسرع):
   ```bash
   tinyfish search query "اسم الكيان + سياق" --language ar --pretty
   # مثال: tinyfish search query "ظل الجزيرة الديني شخصية" --language ar --pretty
   ```
   ⚠️ `--top-k` غير موجود في tinyfish CLI — النتائج ترجع بالعدد الافتراضي.

2. **فحص حسابات X** عبر Jina AI (إذا TinyFish أعطى نتيجة):
   ```bash
   curl -sL 'https://r.jina.ai/http://x.com/الحساب_المحتمل'
   # استخدم http:// (ليس https://) — هذا هو السر
   ```

3. **جرب هجاءات مختلفة للحساب** (إذا الأولى فشلت):
   - ظل_الجزيرة, zilaljazeera, zeel_aljazeera, dhal_aljazeera, ظلالجزيرة
   - الحساب قد لا يكون موجوداً أصلاً

4. **استخدم عدة أدوات بالتوازي** (في نفس الوقت):
   - TinyFish (للبحث العام) + Jina AI (للمواقع المحظورة/المحددة)
   - لا تعتمد على أداة واحدة

5. **تأكد من نطاق البحث** — "ظل الجزيرة" قد يعني:
   - شخص / حساب على X
   - مسلسل درامي (على قناة ماسة / شبكة المجد)
   - شركة (ظل الجزيرة للسيارات)
   - قناة يوتيوب دعوية

   اسأل المستخدم للتوضيح إذا بقيت النتائج غامضة.

### ما لا يعمل عادة
- **x_search** — يتطلب رصيد X API (غير متوفر حالياً)
- **Jina AI → Google** — محظور (451 SecurityCompromiseError)
- **DuckDuckGo HTML** — غالباً بدون نتائج للعربية
- **browser_navigate** — لا يفيد في البحث العربي

انظر `references/arabic-entity-search.md` لمزيد من التفصيل والسيناريوهات.

## المراجع

- `references/web-monitor-pattern.md` — نمط مراقبة المواقع العربية: Jina AI + SQLite + cron + Telegram (مثال: حراج)
- `references/vision-fallback-chain.md` — سلسلة احتياط الرؤية: ماذا تفعل عندما تفشل كل مزودات vision
- `references/twexapi-pricing.md` — أسعار واجهات X/Twitter
- `references/travel-tools.md` — أدوات السفر والحجوزات
- `references/video-to-text-pipeline.md` — تحويل الفيديو إلى نص (بديل Voice-Pro الخفيف)
- `references/memory-management.md` — بروتوكول إشعار الذاكرة: لا تعدّل ذاكرة المستخدم بدون استئذانه
