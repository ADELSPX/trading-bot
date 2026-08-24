#!/usr/bin/env python3
"""توليد QR لتسجيل دخول Telethon — عرض في الترمينال + حفظ صورة"""
import asyncio
import io
from telethon import TelegramClient, functions
from telethon.password import compute_check
import qrcode

API_ID = 39947157
API_HASH = "a23b3c6a1f17e86a946872d455680030"
SESSION = "/root/trading-bot/fazza_userbot.session"

async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()

    exported = await client(functions.auth.ExportLoginTokenRequest(
        api_id=API_ID,
        api_hash=API_HASH,
        except_ids=[],
    ))

    # استخراج الرابط من token bytes
    import urllib.parse
    url = "tg://login?token=" + urllib.parse.quote(exported.token)
    print("URL:", url)

    # QR في الترمينال
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make()
    qr.print_ascii(invert=True)

    # صورة PNG للعرض
    img = qr.make_image(fill_color="black", back_color="white")
    img.save("/root/trading-bot/login_qr.png")
    print("QR saved: /root/trading-bot/login_qr.png")

    # انتظار المسح حتى دقيقتين
    for i in range(24):
        await asyncio.sleep(5)
        try:
            result = await client(functions.auth.ExportLoginTokenRequest(
                api_id=API_ID, api_hash=API_HASH, except_ids=[]))
            cls = result.__class__.__name__
            if cls == "auth_LoginTokenSuccess":
                print("✅ تم الربط بنجاح!")
                me = await client.get_me()
                try:
                    print(f"الحساب: {me.first_name} (@{me.username})")
                except Exception:
                    print("تم الدخول")
                break
            elif cls == "auth_LoginTokenMigrateTo":
                await client._switch_dc(result.dc_id)
                await client._on_login(await client.get_me())
                print("✅ تم (migrate)")
                break
            else:
                print(f"بانتظار المسح... ({i*5}ث) [{cls}]")
        except Exception as e:
            print("خطأ:", str(e)[:100])
    else:
        print("⏰ انتهت المدة — أعد المحاولة")

if __name__ == "__main__":
    asyncio.run(main())
