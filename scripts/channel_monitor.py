#!/usr/bin/env python3
"""مراقب القنوات التعليمية الصامت — صفر توكنات
يراقب 5 قنوات، يحفظ الرسائل النصية الجديدة في المخ الذكي.
التشغيل: python3 channel_monitor.py --fetch   (سحب يدوي)
         python3 channel_monitor.py --cron    (للكرون — يطبع ملخص فقط عند وجود جديد)
"""
import asyncio, os, sys, json
from datetime import datetime, timezone
from telethon import TelegramClient

API_ID = 39947157
API_HASH = "a23b3c6a1f17e86a946872d455680030"
SESSION = "/root/trading-bot/fazza_userbot.session"
STATE_FILE = "/root/trading-bot/knowledge/monitor_state.json"
OUT_DIR = "/root/trading-bot/knowledge/lessons/channels"

CHANNELS = {
    "mohammad-matr": "@ArabicWallStt0",
    "control-option": "@control_option_education",
    "sami-mukna": -1001773557219,
    "fawaz-alrja": "@fawazalrja",
    "gamma-fahad": "@FAHAD_GAMMA1",
}

def load_state():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE))
    return {}

def save_state(s):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(s, open(STATE_FILE, "w"), ensure_ascii=False, indent=2)

async def fetch(cron_mode=False):
    c = TelegramClient(SESSION, API_ID, API_HASH)
    await c.connect()
    state = load_state()
    os.makedirs(OUT_DIR, exist_ok=True)
    new_total = 0
    summary = []
    for key, ident in CHANNELS.items():
        try:
            ent = await c.get_entity(ident)
        except Exception as e:
            summary.append(f"{key}: خطأ وصول ({e})")
            continue
        last_id = state.get(key, 0)
        msgs_file = f"{OUT_DIR}/{key}.md"
        new_msgs = []
        try:
            async for m in c.iter_messages(ent, limit=50):
                if m.id <= last_id:
                    break
                # نص فقط — لا ميديا (ممنوع صور الإشارات)
                if m.text and len(m.text.strip()) > 30:
                    new_msgs.append((m.id, m.date, m.text))
        except Exception as e:
            summary.append(f"{key}: خطأ قراءة ({e})")
            continue
        if new_msgs:
            with open(msgs_file, "a", encoding="utf-8") as f:
                for mid, date, text in reversed(new_msgs):  # الأقدم أولاً
                    ds = date.strftime("%Y-%m-%d %H:%M")
                    clean = text.replace("\n", " ")[:1500]
                    f.write(f"\n### [{ds}] id:{mid}\n{clean}\n")
            state[key] = max(mid for mid, _, _ in new_msgs)
            new_total += len(new_msgs)
            summary.append(f"{key}: +{len(new_msgs)} رسالة جديدة")
        else:
            summary.append(f"{key}: لا جديد")
    save_state(state)
    await c.disconnect()
    if cron_mode:
        if new_total > 0:
            print(f"NEW CONTENT ({new_total} رسالة):\n" + "\n".join(summary))
        # صمت إذا لا جديد (watchdog pattern)
    else:
        print("\n".join(summary))
        print(f"\nالإجمالي الجديد: {new_total}")

if __name__ == "__main__":
    mode = "--cron" if "--cron" in sys.argv else "--fetch"
    asyncio.run(fetch(cron_mode=(mode == "--cron")))
