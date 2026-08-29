# 📌 Reference.md — البيانات الثابتة (نادراً ما تتغير)
> ملف مرجعي منفصل عن MEMORY.md. ارجع له عند الحاجة للمواصفات/المسارات/المفاتيح.
> آخر تحديث: 2026-08-29

---

## 🖥️ البنية التحتية

### السيرفر (هيرتزنر — هاذا الجهاز)
- **نظام:** Linux 6.8.0-117-generic، قرص 75GB (يميل للامتلاء)
- **تنظيف القرص:** `rm -f /var/log/geekom-monitor.log` + `journalctl --vacuum-time=3d` + `apt-get clean`
- **ملف ثقيل معروف:** `/var/log/geekom-monitor.log` ~3.8GB
- **خدمات systemd شغالة:** fazza-bridge (:8795), fazza-serve (:8765), fazza-web, omniroute (:20128), qiyas-activate, telegram-bridge (:7890), nginx

### A6 (ويندوز بعيد — GEEKOM)
- Ryzen 7 6800H، 12GB RAM، ~875GB SSD، AMD Radeon
- Win11 Pro، Tailscale: `a6-2.tail42aae4.ts.net`
- Chrome CDP: 9222 | IB Gateway: 4002 | RDP: 3389 | SSH: `adel.966`
- **مشكلة طفيان مزمنة:** الحل `/root/fix-a6-sleep.ps1` (يمنع sleep + AutoLogon + FazzaKeepAwake) + BIOS Restore on AC Power Loss
- افحص التايلسكيل أولاً قبل أي تدخل

### الماك M1 8GB (macbook-air-adel-1)
- IP: `100.116.133.41` | SSH: `adel/1010` | VNC: 5900
- Hermes v0.20.4 (Desktop+CLI) + حل IB Gateway
- عليه: Berd/Manus/Codex/Copilot/AnyDesk
- ⚠️ تطبيق X مسجل بحساب ثاني (سعد الضاوى) — **لا ننشر منه!**
- Chrome مسجل `shoooter966` | الماك خفيف (Ollama/Qwen جربناه وحذفناه — بطيء)
- SSH يشتغل بعد تعطيل Remote Management
- macOS يمنع screencapture من SSH — التصوير عبر VNC
- **قاعدة 25/8:** حد أقصى 2-3 محاولات تحكم عن بعد — بعدها خطوة يد للمالك
- **CAPTCHA = توقف فوري**

---

## 📁 المشاريع والمسارات

### مستودعات GitHub
- **ADELSPX/fazza-ai** = المستودع المقدس (روح فزاع SOUL.md + كل النسخ)
- **ADELSPX/trading-bot** = كل أدوات التداول + المهارات الجديدة
- التوكن في `~/.git-credentials` (تنظيف القرص يفرّغه — تحقق بعد أي تنظيف)

### مجلدات محلية
- `/root/fazza-ai/` — SOUL.md + المرجع + النسخ
- `/root/trading-bot/` — السكربتات + `knowledge/` (قاما/مطر/مطر/القنوات)
- `/root/hermes-browser-profile/` — بروفايل Chrome للسيرفر (CDP 9222)
- `/root/serve-files/` — مجلد خادم الملفات (:8765)

### مشاريع ويب حية
- **FazzaTrade** (fazza-trader): http://95.217.162.116:8796 — Vanilla JS SPA عربي RTL (Black-Scholes + محفظة + Payoff + الربط الحي)
- **الجسر الذكي** (fazza-bridge): :8795 (Hermes :8642 + IBKR Paper)
- **خادم الملفات:** :8765 — رفع: `python3 ~/.hermes/scripts/serve_upload.py <path>`
- **HermesOffice** على A6: `C:\projects\HermesOffice` — AI :8642/v1 `fazza-api-key-2026`

---

## 🔑 الأسرار والمفاتيح (محفوظة محلياً)

| الخدمة | القيمة | المكان |
|---|---|---|
| Gmail app password (adel966) | `zlxkhrbvyplbxrnr` | `~/.config/himalaya/config.toml` |
| بريد طيبة (Ardadi@taibahu.edu.sa) | `a1m2j3d4m5h6@` (ADFS tufs.taibahu.edu.sa) | — |
| X: @shoooter966 | كلمة السر في USER | — |
| GLM Merge Gateway | `mg_u7gVus-v08z4MDauwfaO1avflVEWakcx1sq05MyasUs` | `/root/.hermes/secrets/glm_merge.key` |
| gmi (MiniMax) | — | `/root/.hermes/secrets/gmi_api.key` |
| Colony (fazza) | `col_Ypr62b...` | `/root/.hermes/secrets/colony_key.txt` |
| Hugging Face | `adel.966@gmail.com` / `SSaa123456@@` | — |
| DuckDNS تفعيل | https://fazza-adel.duckdns.org/activate/ (حد جهازين) | — |
| جوال أبو جهاد | `0506317673` (+966) — للتحقق | — |

⚠️ **لا تشارك/ترسل/تنشر أي مفتاح خارجياً بدون إذن صريح**

---

## 🛠️ الأدوات والمهارات المثبّتة

### تصفح
- **browser-harness** (teknium1): CDP حقيقي. تشغيل:
  ```bash
  google-chrome --remote-debugging-port=9222 --user-data-dir=/root/hermes-browser-profile --no-sandbox --headless=new
  BU_CDP_URL=http://127.0.0.1:9222 browser-harness <<'PY'
  new_tab("https://..."); wait_for_load(); print(js("document.body.innerText"))
  PY
  ```
  ⚠️ ما يكتشف Chrome تلقائياً (لازم BU_CDP_URL)، واستخدم `js()` (مو import js)
- **browser-use** (قديم) + **OmniParser** (HF microsoft/OmniParser-v2) للمواقع المحمية
- **Real Profile Browsing:** Chrome الماك (100.116.133.41:9222 عبر CDP SSH) = حل Payhip/Cloudflare
  ⚠️ Payhip يمنع الرفع الآلي — يدوي

### تحليل التداول (مجاني)
- `yfinance` + `scripts/stock_snapshot.py` (RSI/MA/دعم/مقاومة)
- `scripts/spx_futures.py` (SPX + عقود ES/NQ + خيارات SPX بمراكز OI)
- `scripts/spx_hud_analyzer.py` — شارت احترافي (دعم/مقاومة + فيبوناتشي + RSI + حجم + MA)
- ⭐ أولوية أبو جهاد: السوق الأمريكي SPX والعقود

### نماذج/مزودات
- **GLM 5.3 Flash** (Merge Gateway) = الأساسي حالياً — `ask_glm()` في `/root/trading-bot/scripts/ask_glm.py`
- **hy3-free / deepseek** = fallback
- **Nous Portal** (portal.nousresearch.com) = 300+ مودل باشتراك واحد
- **gmi** (MiniMax مجاني حتى 6/9)

### وكيل/مجتمعات
- **Userbot تليجرام:** @Ardadi966 — جلسة `/root/trading-bot/fazza_userbot.session` — مراقبة 5 قنوات (مطر/كنترول/سامي/فواز/فهد)
- **The Colony:** مراقبة أسبوعية صامتة (cron d6b10f8c1414)
- **Hugging Face:** عبر CDP الماك — `curl -X PUT 'http://127.0.0.1:9222/json/new?{"url":"..."}'`

---

## 🔄 الاسترجاع والنسخ
- **backup-fazza.sh:** ينسخ state.db.gz + المهارات + config → backup/ على GitHub
- **restore-fazza.sh:** كبسة استرجاع كامل لأي سيرفر (git clone + bash restore-fazza.sh)
- نسخ احتياطي يومي تلقائي كل 24h
- SOUL.md **محمي** — لا يعدّله أي برنامج (إلا بأمر صريح من أبو جهاد)
