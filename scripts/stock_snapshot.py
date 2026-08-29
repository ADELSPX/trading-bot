#!/usr/bin/env python3
"""stock_snapshot.py — تحليل سريع لأي سهم/رمز (بيانات حقيقية yfinance)
الاستخدام: python3 stock_snapshot.py SPY  (أو 2222.SR للسوق السعودي)
"""
import sys
import yfinance as yf
import pandas as pd

def analyze(ticker):
    t = yf.Ticker(ticker)
    h = t.history(period='3mo')
    if h.empty:
        print(f"❌ {ticker}: لا توجد بيانات")
        return
    close = h['Close']
    last = close.iloc[-1]
    prev = close.iloc[-2]
    chg = (last - prev) / prev * 100

    # RSI (14)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi_series = 100 - 100 / (1 + rs)
    rsi = float(rsi_series.dropna().iloc[-1]) if not rsi_series.dropna().empty else 50.0

    # المتوسطات
    ma20 = float(close.rolling(20).mean().dropna().iloc[-1]) if len(close) >= 20 else float(close.mean())
    ma50 = float(close.rolling(50).mean().dropna().iloc[-1]) if len(close) >= 50 else float(close.mean())
    ma200 = float(close.rolling(200).mean().dropna().iloc[-1]) if len(close) >= 200 else None

    # دعم/مقاومة (قمة/قاع 20 يوم)
    recent = close.tail(20)
    support = recent.min()
    resistance = recent.max()

    # الاتجاه
    trend = "صاعد 📈" if last > ma20 > ma50 else ("هابط 📉" if last < ma20 < ma50 else "عرضي ↔️")
    rsi_state = "تشبع شراء ⚠️" if rsi > 70 else ("تشبع بيع 💎" if rsi < 30 else "محايد ✅")

    print(f"📊 {t.info.get('shortName', ticker)} ({ticker})")
    print(f"   السعر: {last:.2f} | التغير: {chg:+.2f}%")
    print(f"   RSI(14): {rsi:.1f} — {rsi_state}")
    print(f"   MA20: {ma20:.2f} | MA50: {ma50:.2f}" + (f" | MA200: {ma200:.2f}" if ma200 else ""))
    print(f"   الدعم (20ي): {support:.2f} | المقاومة (20ي): {resistance:.2f}")
    print(f"   الاتجاه: {trend}")

    # توصية
    print("\n   💡 الخلاصة:")
    if last < support * 1.02:
        print("   قريب من الدعم — منطقة اهتمام للمتابعة")
    elif last > resistance * 0.98:
        print("   قريب من المقاومة — حذر من التصحيح")
    if rsi > 70:
        print("   السهم مشبع شراء — انتظر تصحيح قبل الدخول")
    elif rsi < 30 and last > support:
        print("   فرصة انعكاس محتملة — راقب تأكيد الاتجاه")

if __name__ == '__main__':
    ticker = sys.argv[1] if len(sys.argv) > 1 else 'SPY'
    analyze(ticker)
