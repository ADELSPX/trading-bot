#!/usr/bin/env python3
"""spx_futures.py — محلل السوق الأمريكي: SPX + العقود + خيارات (بيانات حقيقية yfinance)
يركز على: المؤشر، العقود الآجلة، ومراكز السيولة (أعلى OI = مركز الصانع — مبادئ فهد)

الاستخدام: python3 spx_futures.py [--chain] [--strike 7700]
"""
import sys
import yfinance as yf
import pandas as pd

def fmt(x, d=2):
    try:
        return f"{x:.{d}f}"
    except:
        return str(x)

def analyze():
    print("📈 السوق الأمريكي — SPX والعقود")
    print("=" * 45)

    # 1) المؤشر والعقود
    data = {}
    for tk, name in [('^SPX', 'S&P 500 (SPX)'), ('ES=F', 'عقود E-mini S&P (ES)'), ('NQ=F', 'عقود ناسداك (NQ)')]:
        t = yf.Ticker(tk)
        h = t.history(period='5d')
        if not h.empty:
            last = float(h['Close'].iloc[-1])
            prev = float(h['Close'].iloc[-2]) if len(h) > 1 else last
            chg = (last - prev) / prev * 100 if prev else 0
            data[tk] = (last, chg)
            print(f"  {name}: {fmt(last)} ({chg:+.2f}%)")
    # 2) التذبذب (مجال 20 يوم)
    t = yf.Ticker('^SPX')
    h = t.history(period='1mo')
    if not h.empty:
        hi = float(h['High'].max())
        lo = float(h['Low'].min())
        last = float(h['Close'].iloc[-1])
        print(f"\n  نطاق الشهر: {fmt(lo)} — {fmt(hi)} | الحالي {fmt(last)} ({'أعلى' if last > (hi+lo)/2 else 'أدنى'} من المنتصف)")

    # 3) خيارات SPX — مراكز السيولة (أعلى Open Interest)
    try:
        spx_opt = yf.Ticker('^SPX')
        exps = spx_opt.options[:3]
        print(f"\n  🎯 خيارات SPX (أقرب 3 تواريخ): {', '.join(exps)}")
        all_calls, all_puts = [], []
        for exp in exps[:2]:
            chain = spx_opt.option_chain(exp)
            c = chain.calls.copy()
            p = chain.puts.copy()
            c['exp'] = exp; p['exp'] = exp
            all_calls.append(c); all_puts.append(p)
        calls = pd.concat(all_calls)
        puts = pd.concat(all_puts)

        # مركز السيولة = strike بأعلى OI (أقرب للـATM — فلترة أوت المال البعيد)
        atm = data['^SPX'][0]
        calls_near = calls[calls['strike'].between(atm*0.97, atm*1.03)]
        puts_near = puts[puts['strike'].between(atm*0.97, atm*1.03)]
        if calls_near.empty: calls_near = calls[calls['strike'].between(atm*0.9, atm*1.1)]
        if puts_near.empty: puts_near = puts[puts['strike'].between(atm*0.9, atm*1.1)]
        if calls_near.empty: calls_near = calls
        if puts_near.empty: puts_near = puts
        top_call = calls_near.loc[calls_near['openInterest'].idxmax()]
        top_put = puts_near.loc[puts_near['openInterest'].idxmax()]

        print(f"\n  🏦 مركز السيولة (مركز الصانع):")
        print(f"    كول: strike {fmt(top_call['strike'])} | OI {int(top_call['openInterest'])} | IV {float(top_call['impliedVolatility'])*100:.1f}%")
        print(f"    بوت: strike {fmt(top_put['strike'])} | OI {int(top_put['openInterest'])} | IV {float(top_put['impliedVolatility'])*100:.1f}%")

        # أعلى 3 مراكز OI إجمالية (كول+بوت) — صورة كاملة
        calls['type'] = 'كول'; puts['type'] = 'بوت'
        all_opt = pd.concat([calls, puts])
        top3 = all_opt.nlargest(3, 'openInterest')
        print(f"\n  🔥 أعلى 3 مراكز OI (من أقرب التواريخ):")
        for _, r in top3.iterrows():
            print(f"    {r['type']} {fmt(r['strike'])} | OI {int(r['openInterest'])} | IV {float(r['impliedVolatility'])*100:.1f}% | {r['exp']}")

        # قراءة القاما (مبدأ فهد): مركز سيولة = كول/بوت
        print(f"\n  📊 قراءة القاما (مبدأ فهد):")
        if top_call['strike'] > top_put['strike']:
            print(f"    الكول ({fmt(top_call['strike'])}) فوق البوت ({fmt(top_put['strike'])}) = ميل صاعد 🟢")
        else:
            print(f"    البوت ({fmt(top_put['strike'])}) فوق الكول ({fmt(top_call['strike'])}) = ميل هابط 🔴")
    except Exception as e:
        print(f"  خيارات ERR: {str(e)[:100]}")

    # 4) خلاصة سريعة
    print("\n  💡 الخلاصة:")
    if '^SPX' in data:
        spx = data['^SPX'][0]
        if 'ES=F' in data:
            diff = data['ES=F'][0] - spx
            if abs(diff) > 5:
                print(f"    الفارق SPX/ES: {fmt(diff)} — {'العقود متقدمة' if diff > 0 else 'العقود متأخرة'} (سيولة)")
            else:
                print(f"    SPX والعقود متقاربان ({fmt(diff)}) — السوق متوازن")

if __name__ == '__main__':
    analyze()
