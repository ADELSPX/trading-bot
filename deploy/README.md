# 📦 مجلد الاستعادة (Deploy)

كل ما تحتاجه لتشغيل النظام من الصفر على سيرفر جديد.

## الملفات

| الملف | الغرض |
|---|---|
| `recovery.sh` | 🔥 **سكربت الاستعادة الكامل** — يشغّل كل شيء بنقرة |
| `systemd/n8n.service` | خدمة n8n (تشغيل تلقائي 24/7) |
| `systemd/telegram-bridge.service` | جسر إشارات التداول الفورية (منفذ 7890) |
| `n8n/morning-report-flow.md` | تعليمات إعادة بناء تقرير الصباح في n8n |
| `cron/hermes-cron-jobs.txt` | مهام Hermes المجدولة (نشرات + نسخ احتياطي) |

## طريقة الاستخدام

```bash
# بعد تنصيب سيرفر جديد:
git clone https://github.com/ADELSPX/trading-bot.git
cd trading-bot/deploy
chmod +x recovery.sh
sudo ./recovery.sh
```

السكربت يسوي كل شيء تلقائياً — ما يحتاج تدخل يدوي إلا خطوتين بسيطة في النهاية.
