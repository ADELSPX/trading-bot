#!/usr/bin/env python3
"""تسجيل دخول Userbot — الكود يمرر كوسيط سطر أوامر"""
import asyncio
import sys
from telethon import TelegramClient

API_ID = 39947157
API_HASH = "a23b3c6a1f17e86a946872d455680030"
PHONE = "+966506317673"
SESSION = "/root/trading-bot/fazza_userbot.session"

async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"✅ مسجل مسبقاً: {me.first_name} (@{me.username})")
        return

    # طلب الكود
    sent = await client.send_code_request(PHONE)
    print("📩 كود التحقق أرسل لتليجرامك")
    code = input().strip()

    try:
        await client.sign_in(PHONE, code)
    except Exception as e:
        if "PASSWORD" in str(e).upper() or "2fa" in str(e).lower():
            pwd = input("كلمة التحقق الثنائية: ").strip()
            await client.sign_in(password=pwd)
        else:
            raise e

    me = await client.get_me()
    print(f"✅ تم الدخول: {me.first_name} (@{me.username})")
    print("Session محفوظ — لن نحتاج كود مرة أخرى")

if __name__ == "__main__":
    asyncio.run(main())
