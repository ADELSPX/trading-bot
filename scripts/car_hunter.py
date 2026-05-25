#!/usr/bin/env python3
"""
🏎️ صياد التورس — Car Hunter v2
يراقب حراج + سوم + سيارة بحثاً عن فورد تورس 2025/2026
يستخدم Jina AI لجلب الصفحات (يدعم JavaScript)
يرسل إشعارات تيليجرام للإعلانات الجديدة فقط
"""
import json, os, sqlite3, re, time, urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# ═══════════════ إعدادات ═══════════════
DB_PATH = Path("/root/trading-bot/data/cars.db")
BRIDGE_URL = "http://localhost:7890"
SEEN_HOURS = 48  # الإعلانات الأقدم من كذا ما نرسلها (نفترض شفناها)

# كلمات نستبعدها (مو بيع سيارة)
EXCLUDE_KEYWORDS = [
    "قطع غيار", "تشليح", "ريموت", "مفتاح", "مصدوم", "مصدومه",
    "صدمه", "تأجير", "للإيجار", "سواق", "سواقة",
    "شبك", "صدام", "مرايات", "شمعات", "كفرات", "جنط",
    "مطلوب", "مطلوبه", "مساعدات", "مكينة", "قير", "رفرف",
    "تظليل", "عازل", "حماية", "ممشى", "فحص",
]

# ═══════════════ مصادر البحث ═══════════════
SEARCHES = [
    {
        "name": "حراج",
        "url": "https://haraj.com.sa/search/{query}",
        "queries": ["2025+تورس", "2026+تورس", "2025+Taurus", "2026+Taurus"],
    },
]

# ═══════════════ SQLite ═══════════════
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            ad_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            price TEXT DEFAULT '',
            city TEXT DEFAULT '',
            year TEXT DEFAULT '',
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            sent INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_seen ON listings(sent, first_seen)")
    conn.commit()
    return conn

# ═══════════════ جلب الصفحات عبر Jina AI ═══════════════
def fetch_jina(url: str) -> str:
    """جلب صفحة ويب عبر Jina AI Reader (يدعم JavaScript)"""
    import subprocess
    jina_url = f"https://r.jina.ai/{url}"
    try:
        result = subprocess.run(
            ["curl", "-sL", jina_url, "-H", "Accept: text/markdown",
             "--max-time", "20", "-A", "CarHunter/2.0"],
            capture_output=True, text=True, timeout=25
        )
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"  ❌ curl exit {result.returncode}")
            return ""
    except Exception as e:
        print(f"  ❌ Jina: {e}")
        return ""

# ═══════════════ استخراج الإعلانات من Markdown ═══════════════
def extract_haraj_ads(markdown: str, source_name: str) -> list:
    """استخراج الإعلانات من markdown اللي رجعه Jina لحراج"""
    ads = []
    seen = set()
    lines = markdown.split('\n')
    
    for i, line in enumerate(lines):
        # نمط: ### [العنوان](الرابط)
        m = re.match(r'###\s*\[([^\]]+)\]\((https://haraj\.com\.sa/(\d+)/[^)]+)\)', line)
        if not m:
            continue
        
        title = m.group(1).strip()
        url = m.group(2).strip()
        ad_id = f"haraj_{m.group(3)}"
        
        if ad_id in seen:
            continue
        seen.add(ad_id)
        
        # استبعاد الإعلانات غير المرغوبة
        if any(kw in title for kw in EXCLUDE_KEYWORDS):
            continue
        
        # البحث عن المدينة والوقت في السطور اللي بعد العنوان
        city = ""
        time_str = ""
        for j in range(i + 1, min(i + 8, len(lines))):
            line_j = lines[j].strip()
            
            # وقت: "قبل X ساعات" أو "قبل X أيام" أو "أمس"
            if re.search(r'قبل\s|أمس|منذ', line_j) and not re.match(r'^\[|^!\[', line_j):
                time_str = line_j
                continue
            
            # مدينة: [اسم المدينة](رابط city/)
            city_m = re.match(r'\[([^\]]+)\]\(https://haraj\.com\.sa/city/', line_j)
            if city_m:
                city = city_m.group(1).strip()
        
        # حساب العمر التقريبي
        age_hours = parse_time_ar(time_str)
        if age_hours is None or age_hours > SEEN_HOURS:
            continue
        
        # استخراج السنة من العنوان
        year_match = re.search(r'(20\d{2})', title)
        year = year_match.group(1) if year_match else ""
        
        # استخراج السعر (من العنوان)
        price = ""
        price_patterns = [
            r'(\d{2,3}[,\d]*)\s*(?:الف|ألف|ريال|r\.?s|SAR|﷼)',
            r'(?:سعر|بـ)\s*(\d{2,3}[,\d]*)',
        ]
        for p in price_patterns:
            pm = re.search(p, title, re.IGNORECASE)
            if pm:
                price = pm.group(1)
                break
        
        ads.append({
            "ad_id": ad_id,
            "source": source_name,
            "title": title,
            "url": url,
            "price": price,
            "city": city,
            "year": year,
            "age": f"{age_hours}h" if age_hours < 24 else f"{age_hours//24}d",
        })
    
    return ads

def parse_time_ar(time_str: str) -> int:
    """تحويل الوقت العربي لعدد ساعات: 'قبل ٥ ساعات' → 5, 'أمس' → 24, 'قبل ٢ أيام' → 48"""
    time_str = time_str.strip()
    
    # تحويل الأرقام العربية لهندية
    arabic_nums = {'٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
                   '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'}
    for ar, en in arabic_nums.items():
        time_str = time_str.replace(ar, en)
    
    # ساعات
    m = re.search(r'(\d+)\s*ساع', time_str)
    if m: return int(m.group(1))
    
    # دقائق
    m = re.search(r'(\d+)\s*دقيق', time_str)
    if m: return 0  # أقل من ساعة
    
    # أيام
    m = re.search(r'(\d+)\s*(?:يوم|ايام|أيام)', time_str)
    if m: return int(m.group(1)) * 24
    
    # أمس
    if 'أمس' in time_str:
        return 24
    
    # شهر / شهور
    m = re.search(r'(\d+)\s*شهر', time_str)
    if m: return int(m.group(1)) * 30 * 24
    
    return 999  # غير معروف = قديم جداً

# ═══════════════ قاعدة البيانات — الجديد/المكرر ═══════════════
def get_new_ads(conn, ads: list) -> list:
    """إرجاع الإعلانات الجديدة فقط"""
    new = []
    for ad in ads:
        row = conn.execute(
            "SELECT ad_id FROM listings WHERE ad_id = ?", (ad["ad_id"],)
        ).fetchone()
        if not row:
            new.append(ad)
    return new

def save_ads(conn, ads: list):
    """حفظ الإعلانات في القاعدة"""
    now = datetime.now().isoformat()
    for ad in ads:
        conn.execute("""
            INSERT OR REPLACE INTO listings
            (ad_id, source, title, url, price, city, year, first_seen, last_seen, sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            ad["ad_id"], ad["source"], ad["title"], ad["url"],
            ad.get("price", ""), ad.get("city", ""), ad.get("year", ""),
            now, now
        ))
    conn.commit()

# ═══════════════ إرسال الإشعار ═══════════════
def send_telegram(ads: list) -> int:
    """إرسال الإعلانات الجديدة لتليجرام"""
    sent = 0
    for ad in ads:
        year_str = f"📅 {ad['year']}" if ad.get('year') else ""
        price_str = f"💰 {ad['price']} ريال" if ad.get('price') else ""
        city_str = f"📍 {ad.get('city')}" if ad.get('city') else ""
        age_str = f"⏰ قبل {ad.get('age', '?')}" if ad.get('age') else ""
        
        parts = [p for p in [year_str, price_str, city_str, age_str] if p]
        
        msg = f"""🏎️ **{ad['title']}**

{' | '.join(parts)}

🔗 {ad['url']}
📡 المصدر: {ad['source']}"""
        
        try:
            body = json.dumps({"message": msg}).encode()
            req = urllib.request.Request(BRIDGE_URL, data=body,
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
            sent += 1
        except Exception as e:
            print(f"  ❌ فشل إرسال {ad['ad_id']}: {e}")
    return sent

# ═══════════════ الدالة الرئيسية ═══════════════
def hunt(send_new: bool = True):
    """الصيد الرئيسي — إذا send_new=False، يخزن فقط بدون إرسال (للتشغيل الأول)"""
    now = datetime.now()
    mode = "📤 إرسال" if send_new else "🥶 تهيئة (بدون إرسال)"
    print(f"🏎️ {now.strftime('%Y-%m-%d %H:%M')} — صيد التورس ({mode})...")
    conn = init_db()
    all_ads = []
    
    for source in SEARCHES:
        for q in source["queries"]:
            url = source["url"].format(query=q)
            print(f"  🔍 {source['name']}: {q}")
            
            md = fetch_jina(url)
            if not md:
                continue
            
            ads = extract_haraj_ads(md, source["name"])
            print(f"    📋 وجدت {len(ads)} إعلان (بعد التصفية)")
            all_ads.extend(ads)
            time.sleep(2)  # احترام للسيرفر
    
    # الجديد فقط
    new = get_new_ads(conn, all_ads)
    
    if new:
        print(f"\n  🆕 **{len(new)} إعلان جديد!**")
        for ad in new[:10]:
            print(f"    • {ad['title'][:60]} | {ad.get('city','?')}")
        if len(new) > 10:
            print(f"    ... و {len(new) - 10} إعلان آخر")
        
        # إرسال فقط إذا مطلوب
        if send_new:
            sent = send_telegram(new)
            print(f"  ✅ أرسلت {sent} إشعار")
        
        save_ads(conn, new)
    else:
        print(f"\n  ⏳ لا يوجد جديد (إجمالي المخزن: {conn.execute('SELECT COUNT(*) FROM listings').fetchone()[0]})")
    
    conn.close()


if __name__ == "__main__":
    import sys
    # --init = تشغيل صامت (بدون إرسال) للتعبئة الأولية
    send = "--init" not in sys.argv
    hunt(send_new=send)
