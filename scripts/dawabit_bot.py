#!/usr/bin/env python3
"""بوت ضوابط المؤتمرات — RAG فوق ضوابط جامعة طيبة (29 صفحة OCR)
الاستخدام: python3 dawabit_bot.py "سؤالك هنا"
"""
import os, re, json, urllib.request, urllib.error, sys

# ─── 1) قاعدة المعرفة (النص الكامل للضوابط) ───
import unicodedata
DOC_PATH = '/tmp/dawabit_final.txt'
with open(DOC_PATH, encoding='utf-8') as f:
    doc = f.read()
# تنظيف شامل: إزالة رموز bidi + تحويل الأرقام العربية لإنجليزية
doc = ''.join(c for c in doc if not unicodedata.combining(c))
doc = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]', '', doc)
doc = re.sub(r'[\u0660-\u0669]', lambda m: str(ord(m.group())-0x660), doc)
doc = doc.replace('‏', '').replace('‎', '').replace('٠', '0')

# ─── 2) تقسيم النص إلى فقرات (chunks) ───
def chunk_text(text, max_len=500):
    # قطع حسب الفقرات/البنود
    chunks = []
    lines = text.split('\n')
    current = []
    cur_len = 0
    for line in lines:
        line = line.strip()
        if not line:
            if current:
                chunks.append('\n'.join(current))
                current, cur_len = [], 0
            continue
        if cur_len + len(line) > max_len and current:
            chunks.append('\n'.join(current))
            current, cur_len = [], 0
        current.append(line)
        cur_len += len(line)
    if current:
        chunks.append('\n'.join(current))
    return [c for c in chunks if len(c) > 20]

chunks = chunk_text(doc)
print(f"📚 قاعدة المعرفة: {len(chunks)} فقرة", file=sys.stderr)

# ─── 3) البحث: اختيار الفقرات الأقرب للسؤال ───
def retrieve(question, top_k=10):
    import unicodedata
    def norm(t):
        # إزالة التشكيل والتنوين
        t = ''.join(c for c in t if not unicodedata.combining(c))
        t = t.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
        t = t.replace('ى', 'ي').replace('ة', 'ه')
        return t

    def tokens(t):
        t = norm(t)
        # إزالة علامات الترقيم والالتصاق
        t = re.sub(r'[؟?،,.;:!()\[\]{}"\']', ' ', t)
        words = set(re.findall(r'[\w\u0600-\u06FF]+', t.lower()))
        stems = set()
        for w in words:
            stems.add(w)
            if len(w) > 4:
                for suf in ['ون', 'ات', 'ين', 'ها', 'هم', 'كما', 'ه', 'ي', 'ا']:
                    if w.endswith(suf) and len(w) - len(suf) >= 3:
                        stems.add(w[:-len(suf)])
                        break
        return words, stems

    q_words, q_stems = tokens(question)
    scored = []
    for i, chunk in enumerate(chunks):
        c_words, c_stems = tokens(chunk)
        overlap = (q_words & c_words) | (q_stems & c_stems)
        score = len(overlap)
        # وزن إضافي للكلمات المفتاحية
        kw_hits = 0
        for kw in ['مؤتمر', 'ندوة', 'حضور', 'مشاركة', 'استضافة', 'سفر', 'تذكرة', 'داخل', 'خارج', 'تخصص', 'خمسة', 'أيام', 'اختبار', 'تقرير', 'مالية', 'ترخيص', 'رعاية', 'ميزانية', 'لجنة', 'موافقة', 'طلب', 'مدة', 'أقصى', 'الحد', 'تجاوز', 'مصروفات', 'بدل', 'انتداب']:
            if kw in question and kw in chunk:
                score += 3
                kw_hits += 1
        # الفقرة الغنية بمفاتيح متعددة = محتوى حقيقي (تفوق جدول المحتويات)
        if kw_hits >= 2:
            score += 5
        scored.append((score, i, chunk))
    scored.sort(key=lambda x: (-x[0], x[1]))  # تعادل = الأقدم أولاً (استقرار)
    # الفقرات العالية أولاً ثم جيرانها كسياق
    result = []
    seen = set()
    for s, i, c in scored[:top_k]:
        if s > 0:
            if i not in seen:
                seen.add(i)
                result.append(chunks[i])
    for s, i, c in scored[:5]:
        for j in range(max(0, i-2), min(len(chunks), i+3)):
            if j not in seen:
                seen.add(j)
                result.append(chunks[j])
    return result[:15]

# ─── 4) DeepSeek يجيب مع المصدر ───
def read_key():
    with open('/root/.hermes/config.yaml') as f:
        content = f.read()
    m = re.search(r'deepseek-v4pro:\s*\n\s*api_key:\s*(\S+)', content)
    return m.group(1) if m else ""

def read_gmi_key():
    try:
        with open('/root/.hermes/secrets/gmi_api.key') as f:
            return f.read().strip()
    except:
        return ""

def read_omni_key():
    try:
        with open('/root/.hermes/config.yaml') as f:
            content = f.read()
        m = re.search(r'omniroute:.*?api_key:\s*(\S+)', content, re.DOTALL)
        return m.group(1).strip() if m else ""
    except:
        return ""

# المزودات: DeepSeek أولاً، ثم omniRoute (مجاني عبر مزودات متعددة)، ثم gmi كـ fallback أخير
PROVIDERS = [
    {"name": "DeepSeek", "url": "https://api.deepseek.com/v1/chat/completions",
     "model": "deepseek-v4-flash", "key": read_key()},
    {"name": "OmniRoute", "url": "http://127.0.0.1:20128/v1/chat/completions",
     "model": "auto/best-coding", "key": read_omni_key()},
    {"name": "GMI", "url": "https://api.gmi-serving.com/v1/chat/completions",
     "model": "MiniMaxAI/MiniMax-M3", "key": read_gmi_key()},
]

def ask(question):
    hits = retrieve(question)
    if not hits:
        return "❌ ما لقيت جواب في الضوابط — صيغ سؤالك بشكل أدق (مثال: 'ضوابط حضور المؤتمر خارج المملكة؟')"
    # حد السياق — 6 فقرات فقط (الموديل يرجّع فارغ مع الأطول) + تنظيف رموز bidi
    import unicodedata
    clean_hits = []
    for h in hits[:6]:
        h = ''.join(c for c in h if not unicodedata.combining(c))
        h = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]', '', h)
        h = re.sub(r'[\u0660-\u0669]', lambda m: str(ord(m.group())-0x660), h)  # أرقام عربية→إنجليزية
        clean_hits.append(h)
    context = "\n\n".join(f"[مصدر]\n{h}" for h in clean_hits)
    prompt = f"""أنت مساعد رسمي لضوابط إدارة المؤتمرات والندوات بجامعة طيبة.
أجب بدقة تامة من النص المعطى فقط. لا تخترع ولا تضيف من عندك.
إذا النص ما يغطي السؤال — قل بصراحة "غير مذكور في الضوابط".
اذكر رقم المادة/البند إذا موجود، ورقم الصفحة إذا ظهرت.

الضوابط (مقتطفات ذات صلة):
{context}

السؤال: {question}

الجواب:"""
    last_err = ""
    for p in PROVIDERS:
        if not p["key"]:
            continue
        payload = json.dumps({
            "model": p["model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500
        }).encode()
        req = urllib.request.Request(
            p["url"], data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {p['key']}"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read())
            content = data["choices"][0]["message"]["content"]
            if content and content.strip():
                return content
            last_err = f"{p['name']}: جواب فارغ"
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:150] if hasattr(e, 'read') else ''
            last_err = f"{p['name']}: HTTP {e.code}: {body[:80]}"
        except Exception as e:
            last_err = f"{p['name']}: {str(e)[:80]}"
    return f"⚠️ كل المزودات فشلت — آخر خطأ: {last_err}"

if __name__ == '__main__':
    q = sys.argv[1] if len(sys.argv) > 1 else "كم مدة الحضور القصوى للمؤتمر؟"
    print("س:", q)
    print("ج:", ask(q))
