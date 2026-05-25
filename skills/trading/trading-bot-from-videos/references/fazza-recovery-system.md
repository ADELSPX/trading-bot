# 🛟 نظام النسخ الاحتياطي والاستعادة الكاملة

## نظرة عامة

المستخدم يريد نسخة من **كل شيء** على GitHub — لو السيرفر ضرب، يستنسخ ويسترجع كل شيء في دقائق.

## المستودعات الثلاثة

| المستودع | المحتوى | التحديث | النوع |
|----------|---------|---------|-------|
| [fazza-recovery](https://github.com/ADELSPX/fazza-recovery) 🔒 | config + skills + systemd + restore.sh | يومي 3 فجراً | خاص |
| [trading-bot](https://github.com/ADELSPX/trading-bot) | كود البوت + الاستراتيجيات + الإشارات | يومي + عند كل تعديل | عام |
| [hermes-backup](https://github.com/ADELSPX/hermes-backup) 🔒 | أرشيف .tar.gz للاستعادة السريعة | يومي 3 فجراً | خاص |

## fazza-recovery — الهيكل

```
fazza-recovery/
├── README.md
├── restore.sh              # سكربت الاستعادة الكامل
├── config/
│   ├── config.yaml         # إعدادات هرمس
│   ├── .env                # مفاتيح API
│   └── cron-jobs.json      # مهام cron المُصدرة
├── skills/
│   ├── trading/
│   └── hermes-agent/
├── systemd/
│   ├── n8n.service
│   └── telegram-bridge.service
├── scripts/
│   ├── hermes-backup.sh    # سكربت النسخ الاحتياطي نفسه
│   └── clear_cache.sh
└── projects/               # روابط وأكواد المشاريع المرتبطة
```

## سكربت النسخ الاحتياطي (`~/.hermes/scripts/hermes-backup.sh`)

يسوي 3 أشياء:

1. **أرشيف .tar.gz** ← config + skills + memory (حفظ محلي سريع)
2. **تحديث fazza-recovery** ← نسخ أحدث الملفات + git push
3. **Push trading-bot** ← إذا فيه تغييرات غير محفوظة

## الاستعادة

```bash
git clone https://github.com/ADELSPX/fazza-recovery.git
cd fazza-recovery
sudo bash restore.sh
```

يسوي:
1. تثبيت الحزم الأساسية
2. تثبيت Hermes Agent
3. استعادة config + skills + memory
4. Clone trading-bot + تثبيت المتطلبات
5. تثبيت n8n + Telegram Bridge كخدمات systemd
6. استعادة مهام cron

## المهام اليدوية بعد الاستعادة

1. راجع `~/.hermes/.env` — تأكد من مفاتيح API
2. `hermes auth add` للمزودات اللي تحتاج OAuth
3. شغّل مهام cron من `config/cron-jobs.txt`
4. `hermes doctor` — تأكد من كل شيء

## ⚠️ ملاحظة أمنية

مستودع fazza-recovery **خاص (private)** لأنه يحتوي على `.env` بمفاتيح API. لا تجعله عاماً أبداً.
