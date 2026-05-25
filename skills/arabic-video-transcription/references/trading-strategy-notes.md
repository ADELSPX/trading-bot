# Trading Strategy Extraction — Video Analysis Log

Date: May 8, 2026
Source: User ابوجهاد — Options trading course (Arabic, ~35+ videos)
Instructor: محمد (20+ years experience)
Platforms: TradingView (analysis) + Derayah Global (execution)
Asset: SPX (S&P 500 Index Options — 0DTE daily expirations)

---

## Progress Tracker

| Video | Duration | Content | Status |
|-------|----------|---------|--------|
| 1 | 22 min | TradingView basics (chart, symbols, indicators) | ✅ Done |
| 2 | 17 min | Strike selection strategy, Fibonacci, support/resistance | ✅ Done |
| 3 | 18 min | Derayah execution, contract cost calculation | ✅ Done |
| 4 | 33 min | **Delta-based limit orders**, time decay, risk zones | ✅ Done |
| 5 | 5 min | Order types, trading hours, limit sell setup | ✅ Done |
| 6-35 | TBD | Remaining ~30 videos | ⏳ Pending |

---

## Consolidated Strategy Rules (from Videos 1-5)

### 1. Direction Analysis (Video 1-2)
- Use Fibonacci retracement to identify support/resistance zones
- Trade direction: put options (هبوط) — betting on downward movement
- Identify the expected target BEFORE choosing a strike
- MUST have chart (رسم بياني) — "بدون رسم بياني لا تعب نفسك"

### 2. Strike Selection — Core Rule (Video 2)
- **Strike ≠ current price** — it's the expected target price
- Choose strike CLOSEST to current price for higher probability
- The farther the strike, the lower the hit probability
- No fixed rule: "ما في قاعدة، ما في معيار محدد"
- Three risk tiers:
  - **Aggressive (مغامر):** farther strike = higher profit potential
  - **Conservative (متحفظ):** closer strike = higher probability
  - **Moderate:** between the two (instructor's preference)

### 3. Timeframe & Expiration (Video 4)
- Intraday preferred (0DTE — expires same day)
- **CRITICAL:** Don't enter with <1 hour remaining — take tomorrow's expiration instead
  - Last-hour trading is high risk due to time decay
  - "يحتمالي توصول للحركة ضعيف جداً"
- Frame selection: 1-hour typical
- Daily chart analysis before market open

### 4. Delta-Based Limit Orders (Video 4 — CRITICAL 🔥)
**The DELTA method for setting precise limit orders:**

```
Expected option price after move = Current option price - (Delta × Expected underlying move)
```

Real example from video:
```
Current option price = $0.25 (25 cents)
Delta = 0.17 (17 cents per $1 underlying move)
Expected SPX drop = $1.00 (from 4414 to 4413)
↓
Option price after drop = 0.25 - 0.17 = $0.08 (8 cents)
```

Also for take profit:
```
Current price = 25 cents
If SPX drops $1 and delta = 17 cents
→ New option price = 25 - 17 = 8 cents
→ If delta changes to higher value at that point, recalculate
→ Set limit sell at calculated price, not random
```

**Why this matters for the bot:**
- Set Limit orders at CALCULATED prices, not random
- Know exactly what the option will be worth when SPX hits target
- Can automate both entry limit and exit limit orders
- Delta is dynamic — changes as underlying moves

### 5. Execution on Derayah Global (Video 3, 5)
- **Order types:**
  - Market Order (سعر السوق) — immediate execution
  - Limit Order (أمر حد) — specific price entry/exit
  - Limit Sell above current price, Limit Buy below current price
- **Cost calculation:** Contracts × Premium × $100
  - Example: 1 contract × $4.40 × 100 = $440
- **Closing:** Market close or Limit sell at target
- **P&L tracking:** Both dollar and percentage views available
- Switch Derayah to Arabic (Settings → Language)

### 6. Trading Hours (Video 5)
- **Orders REJECTED outside market hours** — confirmed on Derayah
- US market hours: 9:30 AM - 4:00 PM EST (4:30 PM - 11:00 PM Saudi)
- Pre-market analysis only, execution during session
- Bot MUST check market hours before placing orders

### 7. Risk Management (Video 3-4)
- Moderate risk tolerance (لا مغامر ولا متحفظ)
- Has external position size calculator (name not revealed yet)
- Uses %-based P&L on Derayah
- Daily expiration only (ينتهي بنفس اليوم)
- Closing at support/resistance — "لما يوصل للدعم، أبيع"
- Don't wait too long — take profit when target is hit

---

## Bot Architecture (Inferred from Videos)

```
PRE-MARKET (before 9:30 AM EST):
  1. Analyze SPX daily chart (Fibonacci, support/resistance)
  2. Determine direction (Call/Put)
  3. Identify target price
  4. Calculate appropriate strike (closest to current with good probability)
  5. Check delta for limit order pricing

DURING MARKET:
  6. Place market order at open (or limit order at calculated price)
  7. Set stop loss (calculated via delta)
  8. Set take profit limit order (calculated via delta)
  9. Monitor P&L in real-time
  10. Close position at target or market close

KEY DECISIONS TO AUTOMATE:
  - Direction: Fibonacci levels → Call or Put
  - Strike: distance from current price + risk tier
  - Entry price: Market or Limit (based on delta)
  - Exit price: Calculated via delta formula
  - Position size: Uses external calculator (TBD)
```

---

## Remaining Questions (for later videos)
- Exact entry signals (what triggers buy?)
- Exit rules (trailing stop? fixed target?)
- Position sizing formula
- How many trades per day?
- Win rate / risk:reward ratio
- The external position size calculator details
- How to adjust for different market conditions (trending vs ranging)

---

## Technical Notes: Video Pipeline

**SSH Access to A6 (May 2026 — WORKING):**
```bash
sshpass -p '207676' ssh Adel.966@100.69.168.86 "command"
# Profile: C:\Users\adel9 (NOT adel.966!)
```

**Transcription Quality:** `base` model produces clean Arabic for strategy extraction. `tiny` is too garbled for detailed analysis.

**Performance:** ~2x realtime on CPU (33min video → ~5.5min transcription).
