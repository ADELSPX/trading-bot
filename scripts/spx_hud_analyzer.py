#!/usr/bin/env python3
"""HUD Analyzer — تحليل فني مرئي لأي رمز (SPX افتراضياً)
الفكرة: نفس HUD Mode — يرسم على الشارت: دعم/مقاومة + فيبوناتشي + RSI + حجم
الاستخدام: python3 scripts/spx_hud_analyzer.py [SYMBOL] [PERIOD]
  مثال: python3 scripts/spx_hud_analyzer.py ^SPX 6mo
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

SYMBOL = sys.argv[1] if len(sys.argv) > 1 else '^SPX'
PERIOD = sys.argv[2] if len(sys.argv) > 2 else '6mo'
OUT = sys.argv[3] if len(sys.argv) > 3 else f'/tmp/{SYMBOL.replace("^","")}_hud.png'

df = yf.download(SYMBOL, period=PERIOD, interval='1d', progress=False, auto_adjust=True)
if df is None or df.empty:
    print('NO DATA'); sys.exit(1)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

close = df['Close'].dropna()
high = df['High'].dropna()
low = df['Low'].dropna()
vol = df['Volume'].fillna(0)

last_price = float(close.iloc[-1])
prev_close = float(close.iloc[-2])

# ===== RSI (14) =====
delta = close.diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = (-delta.clip(upper=0)).rolling(14).mean()
rs = gain / loss.replace(0, np.nan)
rsi = (100 - 100 / (1 + rs)).fillna(50)

# ===== فيبوناتشي =====
fib_high = float(high[-65:].max())
fib_low = float(low[-65:].min())
diff = fib_high - fib_low
fib_levels = {
    '0% (قمة)': fib_high,
    '23.6%': fib_high - 0.236 * diff,
    '38.2%': fib_high - 0.382 * diff,
    '50%': fib_high - 0.5 * diff,
    '61.8%': fib_high - 0.618 * diff,
    '100% (قاع)': fib_low,
}

ma20 = float(close[-20:].mean())
ma50 = float(close[-50:].mean()) if len(close) >= 50 else ma20
ma200 = float(close[-200:].mean()) if len(close) >= 200 else None
trend = 'صاعد' if ma20 > ma50 else 'هابط'
trend_color = '#22c55e' if ma20 > ma50 else '#ef4444'

resistance = float(high[-20:].max())
support = float(low[-20:].min())

# ===== رسم =====
fig = plt.figure(figsize=(13, 9), dpi=110)
fig.patch.set_facecolor('#0b192a')
gs = GridSpec(3, 1, height_ratios=[3, 1, 1], hspace=0.12)

ax = fig.add_subplot(gs[0])
ax.set_facecolor('#0e2238')
ax.plot(close.index, close.values, color='#65e6c6', linewidth=2.2, label=SYMBOL)
ax.plot(close.index, close.rolling(20).mean().values, color='#d4a948', linewidth=1.1, alpha=0.85, label='MA20')
ax.plot(close.index, close.rolling(50).mean().values, color='#7aa2f7', linewidth=1.1, alpha=0.8, label='MA50')
if ma200:
    ax.plot(close.index, close.rolling(200).mean().values, color='#f472b6', linewidth=1, alpha=0.6, label='MA200')

for level, price in fib_levels.items():
    ls = '-' if level in ('0% (قمة)', '100% (قاع)') else '--'
    alpha = 0.9 if level in ('0% (قمة)', '100% (قاع)') else 0.45
    color = '#ef4444' if level == '0% (قمة)' else ('#22c55e' if level == '100% (قاع)' else '#d4a948')
    ax.axhline(price, color=color, linestyle=ls, linewidth=1.2, alpha=alpha)
    if level not in ('0% (قمة)', '100% (قاع)'):
        ax.text(close.index[3], price * 1.0008, f'{level} {price:,.0f}', color=color, fontsize=8.5, alpha=0.85)

ax.axhspan(support * 0.995, support * 1.005, color='#22c55e', alpha=0.12)
ax.axhspan(resistance * 0.995, resistance * 1.005, color='#ef4444', alpha=0.12)
ax.text(close.index[2], support * 0.993, f'دعم {support:,.0f}', color='#22c55e', fontsize=11, fontweight='bold')
ax.text(close.index[2], resistance * 1.004, f'مقاومة {resistance:,.0f}', color='#ef4444', fontsize=11, fontweight='bold')

ax.scatter([close.index[-1]], [last_price], color='#ffffff', s=70, zorder=5, edgecolor='#0b192a', linewidth=1.5)
ax.annotate(f'{last_price:,.1f}', xy=(close.index[-1], last_price),
            xytext=(-90, 22), textcoords='offset points', color='#ffffff', fontsize=12, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#ffffff', lw=1.3))
ax.set_title(f'{SYMBOL} — تحليل فني متقدم (فيبوناتشي + RSI + متوسطات)', color='#ffffff', fontsize=15, fontweight='bold', pad=12)
ax.grid(alpha=0.12, color='#65e6c6')
ax.legend(loc='upper left', facecolor='#0b192a', edgecolor='#223a55', labelcolor='#ffffff', fontsize=9)
ax.tick_params(colors='#93a9c0')
for spine in ax.spines.values():
    spine.set_color('#223a55')

ax2 = fig.add_subplot(gs[1], sharex=ax)
ax2.set_facecolor('#0e2238')
ax2.plot(rsi.index, rsi.values, color='#d4a948', linewidth=1.8)
ax2.axhline(70, color='#ef4444', linestyle='--', linewidth=1, alpha=0.8)
ax2.axhline(30, color='#22c55e', linestyle='--', linewidth=1, alpha=0.8)
ax2.axhline(50, color='#71839a', linestyle=':', linewidth=0.8, alpha=0.6)
ax2.fill_between(rsi.index, 30, 70, color='#d4a948', alpha=0.06)
ax2.set_ylim(0, 100)
ax2.set_ylabel('RSI', color='#d4a948', fontsize=10, fontweight='bold')
ax2.text(0.02, 0.88, f'RSI: {float(rsi.iloc[-1]):.1f}', transform=ax2.transAxes, fontsize=11, fontweight='bold', color='#d4a948')
ax2.tick_params(colors='#93a9c0')
ax2.grid(alpha=0.1, color='#65e6c6')

ax3 = fig.add_subplot(gs[2], sharex=ax)
ax3.set_facecolor('#0e2238')
colors_vol = ['#22c55e' if c >= prev_close else '#ef4444' for c in close.values]
ax3.bar(close.index, vol.values, color=colors_vol, alpha=0.75, width=1.2)
ax3.set_ylabel('حجم', color='#93a9c0', fontsize=10)
ax3.tick_params(colors='#93a9c0')
ax3.grid(alpha=0.1, color='#65e6c6')

plt.tight_layout()
plt.savefig(OUT, facecolor=fig.get_facecolor())

# ===== ملخص نصي =====
rsi_val = float(rsi.iloc[-1])
fib618 = fib_levels['61.8%']
print(f'=== {SYMBOL} HUD ===')
print(f'LAST: {last_price:,.1f} | CHANGE: {((last_price/prev_close)-1)*100:+.2f}%')
print(f'TREND: {trend} (MA20 {ma20:,.0f} / MA50 {ma50:,.0f}' + (f' / MA200 {ma200:,.0f}' if ma200 else '') + ')')
print(f'SUPPORT: {support:,.1f} | RESISTANCE: {resistance:,.1f}')
print(f'RSI: {rsi_val:.1f}')
print(f'FIB 38.2%: {fib_levels["38.2%"]:,.0f} | FIB 50%: {fib_levels["50%"]:,.0f} | FIB 61.8%: {fib618:,.0f}')
print(f'CHART: {OUT}')
