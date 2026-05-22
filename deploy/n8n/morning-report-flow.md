# n8n Morning Report Flow — تفاصيل

## الاسم
📊 تقرير الصباح — فزاع للتداول

## الجدول
- الأحد → الخميس
- الساعة 4:30 عصراً بتوقيت مكة (UTC+3)
- يعادل: 13:30 UTC

## الوصف
n8n يشغّل البوت كل صباح تداول، يحلل السوق، ويرسل تقرير تلغرام.

## العقد (Nodes)
1. **Schedule Trigger** — 13:30 UTC, Sun-Thu (Cron: `30 13 * * 0-4`)
2. **Execute Command** — يشغّل: `cd /root/trading-bot && python scripts/live_signals.py`
3. **Telegram Node** — يرسل التقرير للبوت

## إعادة البناء
في حال تعطل السيرفر، افتح n8n على http://IP:5678 وسوّي:
1. Create Workflow → Schedule Trigger (Cron: 30 13 * * 0-4)
2. Execute Command Node: `cd /root/trading-bot && python scripts/live_signals.py`
3. Telegram Node: Bot Token + Chat ID
4. Activate workflow
