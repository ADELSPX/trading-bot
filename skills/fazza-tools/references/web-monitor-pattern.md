# نمط مراقبة المواقع العربية — Web Monitor Pattern

## الملخص

نمط متكامل لمراقبة مواقع عربية تعتمد JavaScript (مثل حراج، سوم، سيارة) واستخراج البيانات منها، مع منع التكرار وإرسال إشعارات تيليجرام.

## المكونات

```
Jina AI Reader (curl) ← يجلب الصفحة مع JavaScript
        ↓
استخراج بالـ regex من markdown النظيف
        ↓
SQLite — يخزن الإعلانات + يمنع التكرار
        ↓
Telegram Bridge — يرسل الجديد فقط
        ↓
Cron — كل 30 دقيقة
```

## أسلوب الجلب: curl مو urllib

**المشكلة**: `urllib.request` يرجع 403 من Jina AI حتى مع User-Agent. curl يشتغل.

```python
# ✅ الصح — subprocess + curl
import subprocess
result = subprocess.run(
    ["curl", "-sL", jina_url, "-H", "Accept: text/markdown",
     "--max-time", "20", "-A", "CarHunter/2.0"],
    capture_output=True, text=True, timeout=25
)
return result.stdout

# ❌ الغلط — urllib دايم 403
# req = urllib.request.Request(url, headers={"Accept": "text/markdown"})
```

## استخراج البيانات من Jina markdown

حراج (وغيره من المواقع العربية) يستخدم React — الـ HTML الأصلي فاضي. Jina يشغّل JavaScript ويرجع markdown نظيف.

### شكل المخرجات:
```markdown
### [العنوان](https://haraj.com.sa/ID/title/)

[المدينة](https://haraj.com.sa/city/...)

قبل ٥ ساعات

[المستخدم](https://haraj.com.sa/users/...)
```

### استخراج بالـ regex:
```python
# كل إعلان يبدأ بـ:
m = re.match(r'###\s*\[([^\]]+)\]\((https://haraj\.com\.sa/(\d+)/[^)]+)\)', line)

# المدينة في السطور اللي بعد:
city_m = re.match(r'\[([^\]]+)\]\(https://haraj\.com\.sa/city/', line_j)

# الوقت في السطور اللي بعد:
if re.search(r'قبل\s|أمس|منذ', line_j):
    time_str = line_j
```

## منع التكرار — SQLite

```sql
CREATE TABLE IF NOT EXISTS listings (
    ad_id TEXT PRIMARY KEY,   -- haraj_11181257577
    source TEXT NOT NULL,     -- حراج
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    sent INTEGER DEFAULT 0
);
```

### Cold Start (أول تشغيل)
أول مرة تشغّل ← تخزّن كل الإعلانات بدون إرسال (مافي داعي 60 إشعار دفعة وحدة).

```bash
python3 car_hunter.py --init   # يخزن فقط، بدون إرسال
python3 car_hunter.py           # التشغيلات اللاحقة — يرسل الجديد
```

## PYTHONUNBUFFERED=1

سكريبتات Python اللي تشتغل في الخلفية (background/cron) تحتاج `PYTHONUNBUFFERED=1` عشان الـ print يطلع فوراً:

```bash
PYTHONUNBUFFERED=1 python3 script.py
```

بدونها، المخرجات تتأخر أو ما تطلع أبداً في background mode.

## استبعاد الإعلانات غير المرغوبة

فلترة بالكلمات المفتاحية — أي إعلان فيه كلمة من القائمة يُستبعد:

```python
EXCLUDE_KEYWORDS = [
    "قطع غيار", "تشليح", "ريموت", "مفتاح", "مصدوم",
    "صدمه", "شبك", "صدام", "مرايات", "شمعات", "مطلوب",
]
```

## تحويل الوقت العربي لساعات

```python
def parse_time_ar(time_str: str) -> int:
    arabic_nums = {'٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
                   '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'}
    for ar, en in arabic_nums.items():
        time_str = time_str.replace(ar, en)
    
    if m := re.search(r'(\d+)\s*ساع', time_str): return int(m.group(1))
    if m := re.search(r'(\d+)\s*دقيق', time_str): return 0
    if m := re.search(r'(\d+)\s*(?:يوم|ايام)', time_str): return int(m.group(1)) * 24
    if 'أمس' in time_str: return 24
    return 999
```

## ملفات مرجعية

السكريبت الكامل موجود في `trading-bot/scripts/car_hunter.py` على GitHub.
