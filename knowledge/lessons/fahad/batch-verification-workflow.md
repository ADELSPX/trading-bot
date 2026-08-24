# Batch Verification Workflow — جلسة 27 يونيو 2026

مستخلص من جلسة المراقبة الفعلية (session حيث تم فحص IDs 76172–76192).

## المشكلة

رسائل الشارتات الجديدة ليس لها نصوص وصفية في صفحة `/s/` (تظهر كـ `text_not_supported_wrap`). 
تحتاج إلى التحقق من كل ID على حدة لمعرفة إذا كان شارتاً حقيقياً أم لا.

## الحل: Batch Verification

### الخطوة 1: احصل على قائمة الـ IDs من `/s/`
```bash
grep -oP 'data-post="FAHAD_GAMMA1/\K[0-9]+' /tmp/fahad_raw.html | sort -u | tail -20
```

### الخطوة 2: افحص كل ID للـ og:image
أنشئ سكريبت `/tmp/check_ogs.py`:
```python
import subprocess, re

ids_to_check = ['76172', '76173', '76174', '76175']  # IDs الفعلية

for msg_id in ids_to_check:
    url = f"https://t.me/FAHAD_GAMMA1/{msg_id}"
    result = subprocess.run(
        ['curl', '-sL', '-o', f'/tmp/msg_{msg_id}.html', url,
         '-H', 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'],
        capture_output=True, text=True, timeout=15
    )
    
    with open(f'/tmp/msg_{msg_id}.html', 'r') as f:
        html = f.read()
    
    og_images = re.findall(r'og:image" content="([^"]+)"', html)
    og_desc = re.findall(r'og:description" content="([^"]*)"', html)
    
    img_url = og_images[0] if og_images else "(لا يوجد)"
    desc = og_desc[0] if og_desc else ""
    url_hash = img_url.split('/')[-1][:50] if img_url != "(لا يوجد)" else "N/A"
    
    print(f"ID {msg_id}: hash={url_hash} | desc={desc[:100]}")
```

### الخطوة 3: صنف النتائج
- **نفس الـ hash** المتكرر بين رسائل متعددة = صورة القناة (تجاهل)
- **hash فريد** = شارت جديد 🔥

### نمط التكرار في جلسة 27 يونيو 2026
- Channel photo hash: `aP7ux_Ljy1Eu0C9rxKSYHk0yLp52aDkzOzEdzMVeflFKZQ6ZSR`
- 12 رسالة شارت فريد: IDs 76172-76181, 76183-76185
- رسائل نص فقط (نفس hash القناة): 76182, 76186-76192
- ID 76183: استثناء — له hash فريد لكن النص المرفق كان دعاءً (قد يكون أخطأ المستخدم في إرفاق الشارت أو إعادة نشر)

## قاعدة التصنيف من الـ og:image وحدها

| og:image hash | ID | التصنيف |
|---------------|----|---------|
| فريد (لم يظهر في أي ID آخر) | 76172 | شارت LLY 🟢 |
| فريد | 76173 | شارت 🟢 |
| فريد | 76174 | شارت 🟢 |
| ... | 76175-76181 | شارتات 🟢 |
| مكرر (صورة القناة) | 76182 | نص تعليمي 🟡 |
| فريد | 76183 | شارت (استثناء مع دعاء) 🟢 |
| فريد | 76184-76185 | شارتات 🟢 |
| مكرر (صورة القناة) | 76187-76192 | نصوص/أدعية 🟡 |

## OCR Results الفعلية من هذه الجلسة

على شارت ID 76185 (320×208, 12KB):
- PSM 3: نتائج محدودة جداً
- PSM 6: استخرج "116.00" و "112.00" جزئياً
- PSM 11: استخرج "Tradngview" (TradingView watermark) وأرقام متفرقة
- PSM 12: مشابه لـ PSM 11

الخلاصة: OCR على 320×208 يعطي أرقاماً كبيرة فقط (مستويات السعر العريضة) ولا يقرأ الاسترايكات أو النصوص الصغيرة.
