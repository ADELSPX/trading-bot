#!/usr/bin/env python3
"""فحص رد ياسر — صامت إلا عند وجود رد جديد"""
import asyncio, json, os, sys
from telethon import TelegramClient
API_ID=39947157; API_HASH="a23b3c6a1f17e86a946872d455680030"
STATE="/root/trading-bot/knowledge/yasir_state.json"
async def main():
    c=TelegramClient("/root/trading-bot/fazza_userbot.session",API_ID,API_HASH)
    await c.connect()
    msgs = await c.get_messages("@YsPalm", limit=5)
    last = msgs[0]
    state = {}
    if os.path.exists(STATE):
        state = json.load(open(STATE))
    sent_id = state.get("last_out_id")
    # هل فيه رسالة واردة جديدة (من ياسر) بعد آخر فحص؟
    incoming = [m for m in msgs if m.out is False]
    last_seen_in = state.get("last_in_id", 0)
    new_replies = [m for m in incoming if m.id > last_seen_in]
    state["last_out_id"] = max((m.id for m in msgs if m.out), default=sent_id or 0)
    state["last_check"] = str(asyncio.get_event_loop().time())
    if new_replies:
        state["last_in_id"] = max(m.id for m in new_replies)
        json.dump(state, open(STATE,"w"))
        for m in new_replies:
            print(f"رد جديد من ياسر: {(m.text or '[ميديا]')[:300]}")
    else:
        json.dump(state, open(STATE,"w"))
        print("لا رد جديد")  # سيُخفى في وضع cron الصامت إذا أردنا
    await c.disconnect()
asyncio.run(main())
