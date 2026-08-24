# Gamma Pattern Monitor — Cron Setup

Script: `~/.hermes/scripts/gamma_monitor.py`
Monitors SPX, NVDA, TSLA, AAPL every 3 minutes during US market hours.

## Cron Job

```
schedule: */3 13-20 * * 0-4   (US market: 13:30-20:00 UTC)
repeat:   22 times             (≈ one week, expires Friday)
no_agent: true                 (script output IS the message)
```

## Tower Configuration

Towers must be adjustd to current price action. Current (May 2026):

| Symbol | Red    | Yellow | Blue   | White  |
|--------|--------|--------|--------|--------|
| SPX    | 7,400  | 7,460  | 7,520  | 7,580  |
| NVDA   | 195    | 203    | 212    | 220    |
| TSLA   | 415    | 428    | 440    | 455    |
| AAPL   | 298    | 305    | 312    | 320    |

## Execution

```bash
# Test single run
/root/trading-bot/.venv/bin/python3 /root/.hermes/scripts/gamma_monitor.py

# Returns ONLY when confidence >= 70% — silent otherwise (good for cron)
```

## yfinance MultiIndex Fix

yfinance v0.2+ returns MultiIndex columns. Access pattern:

```python
close_col = data['Close']
val = close_col.iloc[-1]
if hasattr(val, 'iloc'):
    val = val.iloc[0]   # unwrap Series
price = float(val)
```

Without this unwrap, `float()` throws `TypeError: only 0-dimensional arrays can be converted`.

## Adding New Symbols

Edit `TOWER_CONFIGS` and `TICKER_MAP` in `gamma_monitor.py`:

```python
TOWER_CONFIGS = {
    "SYM": [
        {"strength": "red",    "price": NNN},
        ...
    ],
}
TICKER_MAP = {"SYM": "TICKER", ...}
```
