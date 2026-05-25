# Real-Time Trading Signal Infrastructure

## Architecture Overview

```
Bot Python Script ──POST──→ Telegram Bridge (localhost:7890) ──→ Telegram API ──→ User
                                  ↑
                      Hermes Cron (daily reports + monitoring)
```

## Why Hermes Cron Instead of n8n

**Pitfall discovered May 25, 2026:** n8n workflow scheduler was unreliable. All trading workflows (Morning Report, Signal Alert) executed once on May 22 and failed silently — errors in under 1 second with no useful logs. The scheduler never retried. The Sunday May 24 report never ran.

**Decision:** All scheduled trading tasks use **Hermes Cron** instead. Hermes Cron has been running backup, news, and monitoring jobs reliably since setup — zero failures. n8n is kept only for the Telegram Bridge (real-time signals) and as a fallback.

| Component | Speed | Purpose |
|-----------|-------|---------|
| Telegram Bridge (Python) | **~0.5s** | Real-time signal → Telegram (entry/update/close) |
| Hermes Cron | scheduled | Daily reports, position monitoring, contract suggestions |

## Components

### 1. Telegram Webhook Bridge

**Location:** `~/trading-bot/scripts/telegram_bridge.py`
**Service:** `telegram-bridge.service` (systemd, auto-restart)
**Port:** 7890

```python
# Send a signal from any Python script
import json, urllib.request

def send_signal(data: dict):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        "http://localhost:7890",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=3)
```

**Signal types:**

| Type    | When                 | Fields                                                     |
|---------|----------------------|------------------------------------------------------------|
| `entry` | New trade signal     | symbol, direction, entry, target1, target2, stop, delta, ror, note |
| `update`| Position monitoring  | symbol, pnl, suggestion                                    |
| `close` | Trade closed         | symbol, direction, entry, exit, pnl, duration, reason      |

### 2. CLI Alert Script

**Location:** `~/trading-bot/scripts/signal_alert.py`

```bash
python scripts/signal_alert.py \
  --type entry \
  --symbol SPX \
  --direction put \
  --entry 7406 \
  --target1 7392 \
  --stop 7412
```

### 3. Hermes Cron Jobs (replaced n8n workflows)

All managed via `hermes cron`:

| Job ID        | Name                  | Schedule           | Purpose                         |
|---------------|-----------------------|--------------------|----------------------------------|
| `22318e17b136`| 📊 تقرير التداول اليومي | `30 13 * * 0-4`    | Daily analysis Sun-Thu 4:30 PM Mecca |
| `1e5ad803a095`| ⚡ مراقبة الصفقات      | `*/10 * * * 0-4`   | Position monitoring every 10 min |

**n8n workflows are left active but NOT relied upon.** If n8n runs, it's bonus; Hermes Cron is the primary scheduler.

## Python Bot Circular Import Fix

Problem: `bot/core.py` imports `RiskManager` from `bot/risk.py`, and `bot/risk.py` imports `TradeConfig` from `bot/core.py` → circular.

**Fix:** Extract `TradeConfig` into `config/models.py`:

```python
# config/models.py
from dataclasses import dataclass
from datetime import time

@dataclass
class TradeConfig:
    symbol: str = "SPX"
    max_position_size: float = 1000.0
    target_profit_pct: float = 50.0
    stop_loss_pct: float = 100.0
    market_open: time = time(9, 30)
    market_close: time = time(16, 0)
```

Then import from `config.models` everywhere:
- `bot/core.py`: `from config.models import TradeConfig`
- `bot/risk.py`: `from config.models import TradeConfig`
- `config/settings.py`: `from config.models import TradeConfig`

## Static Method Bug in indicators.py

`@staticmethod` methods cannot use `self`. `calculate_delta()` called `self._norm_cdf(d1)` but both were `@staticmethod`.

**Fix:** Use class name to call static methods: `TechnicalIndicators._norm_cdf(d1)` instead of `self._norm_cdf(d1)`.

## n8n Webhook Alternative

The Telegram Bridge is preferred over n8n's webhook trigger because:
- n8n Code node has limited sandbox (no `require('https')` reliably)
- n8n's HTTP Request node body format is finicky with Telegram API
- Direct Python HTTP server is simpler, faster, and more reliable

If n8n webhook is desired later, create a simple 2-node flow:
1. Webhook (receives POST)
2. Code (formats + sends via `https.request` — available in n8n v2 Code node)

## Notes for This User

- Bot token is stored in `~/.hermes/config.yaml` (telegram section)
- Chat ID: `15036469`
- The user expects real-time alerts (seconds), not batch reports
- Systemd services should use `Restart=on-failure` with `RestartSec=5`
- n8n database is at `/root/.n8n/database.sqlite` — queryable via Python sqlite3 when `sqlite3` CLI not installed
- **Commitment tracking:** When you promise follow-up on a future date ("Sunday report"), set a reminder or rely on the cron job itself to deliver. The user expects autonomous operation — not hand-holding, but also not silent failure.
