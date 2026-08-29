#!/usr/bin/env python3
"""watchlist.py — شاشة متابعة عدة أسهم دفعة واحدة (بيانات حقيقية yfinance)
الاستخدام: python3 watchlist.py  أو عدّل WATCHLIST بالأسهم اللي تبي
"""
import sys
sys.path.insert(0, '.')
from scripts.stock_snapshot import analyze

# أسهم مقترحة (عدّل كما تشاء)
WATCHLIST = [
    'SPY',        # مؤشر S&P 500
    'QQQ',        # ناسداك 100
    '2222.SR',    # أرامكو
    '7010.SR',    # stc
    '1180.SR',    # البنك الأهلي
    'TADAWUL:2222',  # أرامكو (رمز بديل)
]

if __name__ == '__main__':
    tickers = sys.argv[1:] or WATCHLIST
    for tk in tickers:
        try:
            analyze(tk)
            print()
        except Exception as e:
            print(f"❌ {tk}: {str(e)[:60]}\n")
