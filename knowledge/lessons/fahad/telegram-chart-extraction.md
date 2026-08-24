# استخراج شارتات تليجرام — مرجع فني

مستخلص من جلسات مراقبة قناة FAHAD_GAMMA1.

## مسار التصحيح الكامل

### المحاولة 1: صفحة /s/ مباشرة ❌
```bash
curl -sL "https://t.me/s/FAHAD_GAMMA1" | python3 -c "..."
```
**النتيجة:** Tirith security scanner منع pipe-to-interpreter

### المحاولة 2: حفظ HTML ثم بايثون ✅
```bash
curl -sL -o /tmp/fahad_raw.html "https://t.me/s/FAHAD_GAMMA1" ...
python3 /tmp/script.py
```
**النتيجة:** نجح — استخرج النصوص بنجاح

### المحاولة 3: استخراج الصور من /s/ page ❌
بحثت عن `<img src=...>` — وجدت فقط 160×160 صورة البروفايل تتكرر
بحثت عن `background-image: url(...)` على `tgme_widget_message_photo` — روابط resolve إلى 161 بايت
**النتيجة:** الروابط = placeholders — لا فائدة

### المحاولة 4: صفحات الرسائل الفردية ✅
`https://t.me/FAHAD_GAMMA1/76001`
**النتيجة:** وُجدت og:image — هذه هي الشارتات الحقيقية

### المحاولة 5: Vision API ❌
API key غير صالح (401 Unauthorized)

### المحاولة 6: OCR عبر pytesseract ⚠️
الأبعاد صغيرة (320×208 / 320×320) — OCR يعطي نتائج محدودة

## هيكل صفحة الرسالة الفردية

صفحة `https://t.me/FAHAD_GAMMA1/76001`:
- **Static HTML**: فقط meta tags + JavaScript redirect
- **og:image**: رابط الشارت الفعلي
- **og:description**: غير متاح (نص مختفي خلف JS)
- **لا يوجد** `<div class="tgme_widget_message_text">` — الرسالة مختفية وراء الـ JS
- حجم الصفحة: ~37KB (معظمه meta وسكريبتات)

## تنسيق og:image URL

```
https://cdn4.telesco.pe/file/<base64-hash>.jpg
```

## التمييز بين الشارت الحقيقي والـ thumbnail المكرر

كل رسائل الإعلان (SPX Ann, NDX Ann, SPY Ann, QQQ Ann) تشترك في **نفس og:image URL بالضبط** — هذه صورة القناة العامة (320×320، ~20KB).
رسائل الشارت الفعلية لها URLs مختلفة تماماً (320×208، ~11-13KB).

| الرسالة | النص | og:image URL | نوعها |
|---------|------|-------------|-------|
| 76001 | 🎯 تحديث SPX : | ...dnV9A.jpg | 🟡 صورة القناة |
| 76002 | SPX | ...rywg.jpg | 🟢 **شارت SPX** |
| 76006 | 🎯 تحديث NDX : | ...dnV9A.jpg | 🟡 صورة القناة |
| 76019 | NDX | ...obw.jpg | 🟢 **شارت NDX** |
| 76020 | 🎯 تحديث SPY : | ...dnV9A.jpg | 🟡 صورة القناة |
| 76025 | SPY | ...bbZag.jpg | 🟢 **شارت SPY** |
| 76026 | 🎯 تحديث QQQ : | ...dnV9A.jpg | 🟡 صورة القناة (بس إعلان، مافيه شارت) |

**طريقة الكشف:** قارن og:image URL كاملاً. إذا تطابق مع أي إعلان آخر = صورة القناة. إذا مختلف = شارت جديد.

## نمط التحديثات (آخر تحديث: 25 يونيو 2026)

كل مجموعة تحديثات تبدأ بـ **"🎯 بسم الله تحديثات جديدة"** (مثبت).

تأتي التحديثات بالترتيب:
1. SPX: إعلان → شارت
2. NDX: إعلان → شارت
3. SPY: إعلان → شارت
4. QQQ: إعلان فقط (قد يأتي شارت لاحقاً)

## أوامر سريعة للتكرار

```bash
# 1. تحميل صفحة القناة
curl -sL -o /tmp/raw.html "https://t.me/s/FAHAD_GAMMA1" -H "UA: Mozilla"

# 2. ربط النصوص بالأرقام
python3 << 'PYEOF'
import re
with open('/tmp/raw.html') as f: html = f.read()
pattern = r'<div[^>]*data-post="FAHAD_GAMMA1/(\d+)"[^>]*>.*?<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>'
for mid, txt in re.findall(pattern, html, re.DOTALL):
    c = re.sub(r'<[^>]+>','',txt).strip()
    if c: print(f'ID {mid}: {c[:120]}')
ids = sorted(set(re.findall(r'FAHAD_GAMMA1/(\d+)', html)), key=int)
print(f'Last 15 IDs: {ids[-15:]}')
PYEOF

# 3. تحميل رسالة فردية
curl -sL -o /tmp/msg.html "https://t.me/FAHAD_GAMMA1/76002" -H "UA: Mozilla"

# 4. استخراج og:image
OG=$(grep -oP 'og:image" content="\K[^"]+' /tmp/msg.html)
echo "$OG"

# 5. تحميل الشارت
curl -sL -o /tmp/chart.jpg "$OG"

# 6. فحص الأبعاد
python3 -c "from PIL import Image; print(Image.open('/tmp/chart.jpg').size)"

# 7. مقارنة الشارتات (md5 للتأكد من التفرد)
python3 -c "from PIL import Image; import hashlib; print(hashlib.md5(Image.open('/tmp/chart.jpg').tobytes()).hexdigest())"
```
