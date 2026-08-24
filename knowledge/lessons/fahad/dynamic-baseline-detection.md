# Dynamic Baseline Detection — التمييز الديناميكي بين الشارت والرمز (29 يونيو 2026)

## المشكلة

طريقة الـ hardcoded hash (`is_channel = "aP7ux" in hash_part`) تعتمد على hash ثابت يتغير كل جلسة. الحل الأفضل: بناء baseline ديناميكي في كل جلسة.

## الحل: Baseline ديناميكي من أول رسالة معلنة

### المبدأ
- أول رسالة إعلان (مثل `🎯 تحديث SPX :`) يكون og:image = **صورة القناة** — استخدمها كـ baseline
- كل الـ IDs اللي تشترك في نفس الـ URL بالضبط = إعلانات/نصوص فقط 🟡
- الـ IDs اللي لها URLs مختلفة = شارتات فريدة 🟢🔥

### السكربت

```python
import subprocess, re, sys

# IDs مستخرجة من /s/ page (chart-only suspected)
ids_to_check = sys.argv[1:]  # تمرير IDs من سطر الأوامر
# أو ID range
# ids_to_check = [str(i) for i in range(76172, 76193)]

channel_icon_url = None

for msg_id in ids_to_check:
    url = f"https://t.me/FAHAD_GAMMA1/{msg_id}"
    result = subprocess.run(
        ['curl', '-sL', url, '-H', 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'],
        capture_output=True, text=True, timeout=15
    )
    og_images = re.findall(r'og:image" content="([^"]+)"', result.stdout)
    og_desc = re.findall(r'og:description" content="([^"]*)"', result.stdout)
    
    if og_images:
        img = og_images[0]
        desc = og_desc[0][:80] if og_desc else ''
        
        # First ID with og:image = establish baseline
        if channel_icon_url is None:
            channel_icon_url = img
            print(f"ID {msg_id} | 🟡 صورة القناة (baseline) | desc={desc}")
        elif img == channel_icon_url:
            print(f"ID {msg_id} | 🟡 صورة القناة (مكرر) | desc={desc}")
        else:
            print(f"ID {msg_id} | 🟢 **شارت فريد 🔥** | desc={desc}")
    else:
        print(f"ID {msg_id} | ⚪ لا توجد og:image")
```

## الاكتشاف: "نص + شارت معًا" (ID 76203)

**نمط جديد مكتشف في جلسة 29 يونيو:**

بعض الرسائل قد يكون لها **نص تعليمي مهم + شارت فريد في نفس الرسالة**:
- ID 76203: نص = `"بس طبق الاستراتيجيه مهب مطلوب منك شيء ثاني . كول بوت وقف عند مركز سيولة الصانع"` + og:image = شارت فريد 🔥
- ID 76221: نص = `"شرح العلامات على الشارت: ✅️ ✅️..."` + og:image = صورة القناة (نص فقط مع رسم توضيحي)

### قاعدة التصنيف الجديدة للرسائل ذات النص:

| og:image | نوع النص | التصنيف |
|----------|----------|---------|
| فريد 🔥 | نص تعليمي قصير | **شارت + مبدأ** ← اقرأ النص واستخرج المبدأ |
| فريد 🔥 | نص طويل/تعليمي | **شارت + شرح** ← النص قد يحوي مبادئ مهمة (مثل ID 76222) |
| صورة القناة 🟡 | نص طويل | **نص فقط** ← اقرأ واستخرج المبادئ |
| صورة القناة 🟡 | نص قصير (رمز فقط) | إعلان ← تجاهل |

### الفرق عن الأنماط السابقة

| النمط | IDs مثال | og:image | النص |
|-------|----------|----------|------|
| إعلان + شارت منفصل | 76001→76002 | قناة / شارت | طويل / قصير |
| شارت فقط | 76215-76218 | فريد | (لا يوجد) |
| **نص + شارت معًا 🔥** | **76203** | **فريد** | **نص تعليمي** |
| نص تعليمي فقط | 76210 | قناة | نص طويل |

## نمط جديد: Update announcements بدون شارت

في جلسة 29 يونيو 2026 ظهر نمط جديد:
- `🎯 بسم الله تحديثات الإثنين 29 / 6 🎯` (ID 76223) — إعلان عن تحديثات قادمة وليس شارت
- هذا يختلف عن `🎯 تحديث SPX :` (اللي يتبعه شارت فوري)
- **طريقة التعامل:** إذا كان الإعلان بصيغة "بسم الله تحديثات [اليوم]" بدون رمز سهم — تجاهل
