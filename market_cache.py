"""market_cache.py — كاش SQLite محلي لبيانات السوق (نمط Local Cache + Background Worker).

المبدأ (المعيار المعتمد):
  1. أي أداة تطلب بيانات سوق تقرأ من هذه القاعدة أولاً → زمن شبه صفري وبلا شبكة.
  2. تحديث البيانات من المصدر الخارجي مسؤولية الكاتب الخلفي وحده
     (market_cache_writer.py عبر cron) — مو مسار استجابة المستخدم.
  3. لو انتهت الصلاحية (TTL) وما لحق الواركر يحدّث → الأداة تجرّب المصدر مرة واحدة كـ Fallback.
  4. لو فشل المصدر → ترجّع آخر قيمة معروفة موسومة stale=True مع عمرها.
     **ممنوع** عرض قيمة منتهية كأنها لحظية.

القاعدة: $MARKET_CACHE_DB أو /root/.hermes/state/market_cache.db  (خارج git عمداً)
"""
from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

DB_PATH = os.environ.get("MARKET_CACHE_DB", "/root/.hermes/state/market_cache.db")

# تجاوز TTL للاختبار فقط (ثواني للجميع)
TTL_OVERRIDE = os.environ.get("MARKET_CACHE_TTL_OVERRIDE")
# تعطيل الشبكة للاختبار فقط (محاكاة حجب/فشل المصدر)
FORCE_FETCH_FAIL = os.environ.get("MARKET_CACHE_FORCE_FAIL") == "1"

NY = ZoneInfo("America/New_York")

# رموز المؤشرات: الاسم المحلي ← رمز ياهو
INDEX_MAP = {"SPX": "^SPX", "GSPC": "^GSPC", "NDX": "^NDX", "DJI": "^DJI", "VIX": "^VIX", "RUT": "^RUT"}

# صلاحية كل نوع بيانات: (أثناء السوق، بعد الإغلاق) بالثواني
DEFAULT_TTL = {
    "quote": (30, 900),          # سعر لحظي
    "candles_1m": (60, 900),     # شمعات دقيقة
    "candles_5m": (300, 3600),   # شمعات 5 دقائق
    "alerts": (300, 1800),       # إنذارات محسوبة
    "option_chain": (1800, 7200),
    "doc": (86400, 604800),      # مخصص لمستندات/صفحات ثابتة
}


# ── الاتصال والتهيئة ────────────────────────────────────────────────

def connect(path: Optional[str] = None) -> sqlite3.Connection:
    p = path or DB_PATH
    os.makedirs(os.path.dirname(p), exist_ok=True)
    con = sqlite3.connect(p, timeout=10.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=8000")
    con.execute("PRAGMA synchronous=NORMAL")
    _ensure_schema(con)
    return con


def _ensure_schema(con: sqlite3.Connection) -> None:
    """يضمن وجود الجداول (رخيص: استعلام واحد) — عشان أي عملية على قاعدة جديدة تشتغل بلا تهيئة يدوية."""
    row = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ttl_policy'").fetchone()
    if row is None:
        init_db(con)


SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
  symbol      TEXT PRIMARY KEY,
  price REAL, high REAL, low REAL, volume INTEGER, prev_close REAL,
  source      TEXT, fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS candles (
  symbol TEXT NOT NULL, interval TEXT NOT NULL, ts TEXT NOT NULL,
  open REAL, high REAL, low REAL, close REAL, volume INTEGER,
  source TEXT, fetched_at TEXT NOT NULL,
  PRIMARY KEY (symbol, interval, ts)
);
CREATE INDEX IF NOT EXISTS idx_candles_lookup ON candles(symbol, interval, ts DESC);
CREATE TABLE IF NOT EXISTS option_chains (
  symbol TEXT NOT NULL, expiry TEXT NOT NULL, strike REAL NOT NULL, side TEXT NOT NULL DEFAULT '',
  oi INTEGER, volume INTEGER, gamma REAL, source TEXT, fetched_at TEXT NOT NULL,
  PRIMARY KEY (symbol, expiry, strike, side)
);
CREATE TABLE IF NOT EXISTS alerts (
  symbol TEXT PRIMARY KEY,
  computed_at TEXT NOT NULL, current REAL, support REAL, resistance REAL,
  alerts_json TEXT, window_desc TEXT, source TEXT
);
CREATE TABLE IF NOT EXISTS fetch_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL, scope TEXT NOT NULL, key TEXT NOT NULL,
  ok INTEGER NOT NULL, latency_ms INTEGER, rows INTEGER, error TEXT, note TEXT
);
CREATE INDEX IF NOT EXISTS idx_fetchlog_at ON fetch_log(at DESC);
CREATE TABLE IF NOT EXISTS ttl_policy (
  kind TEXT PRIMARY KEY, open_sec INTEGER NOT NULL, closed_sec INTEGER NOT NULL, note TEXT
);
"""


def init_db(con: Optional[sqlite3.Connection] = None) -> None:
    own = con is None
    con = con or connect()
    con.executescript(SCHEMA)
    con.executemany(
        "INSERT OR REPLACE INTO ttl_policy(kind, open_sec, closed_sec, note) VALUES (?,?,?,?)",
        [(k, v[0], v[1], "أثناء السوق / بعد الإغلاق") for k, v in DEFAULT_TTL.items()],
    )
    con.commit()
    if own:
        con.close()


# ── أدوات وقت ───────────────────────────────────────────────────────

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def market_open(ts: Optional[datetime] = None) -> bool:
    """سوق الأسهم الأمريكي بتوقيت نيويورك (يتعامل مع التوقيت الصيفي تلقائياً)."""
    t = ts.astimezone(NY) if ts else datetime.now(NY)
    if t.weekday() > 4:
        return False
    minutes = t.hour * 60 + t.minute
    return 9 * 60 + 30 <= minutes < 16 * 60


def age_seconds(fetched_at: str) -> float:
    try:
        dt = datetime.fromisoformat(fetched_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds()
    except Exception:
        return float("inf")


def ttl_for(kind: str, con: Optional[sqlite3.Connection] = None) -> int:
    if TTL_OVERRIDE:
        return int(TTL_OVERRIDE)
    open_now = market_open()
    try:
        own = con is None
        con = con or connect()
        row = con.execute("SELECT open_sec, closed_sec FROM ttl_policy WHERE kind=?", (kind,)).fetchone()
        if own:
            con.close()
        if row:
            return int(row["open_sec"] if open_now else row["closed_sec"])
    except Exception:
        pass
    return DEFAULT_TTL.get(kind, (300, 1800))[0 if open_now else 1]


def yahoo_symbol(sym: str) -> str:
    s = (sym or "").strip().upper()
    if not s:
        return s
    if s.startswith("^"):
        return s
    return INDEX_MAP.get(s, s)


def log_fetch(scope: str, key: str, ok: bool, latency_ms: int = 0, rows: int = 0,
              error: Optional[str] = None, note: Optional[str] = None,
              con: Optional[sqlite3.Connection] = None) -> None:
    try:
        own = con is None
        con = con or connect()
        con.execute(
            "INSERT INTO fetch_log(at, scope, key, ok, latency_ms, rows, error, note) VALUES (?,?,?,?,?,?,?,?)",
            (now_utc(), scope, key, 1 if ok else 0, latency_ms, rows, error, note),
        )
        con.commit()
        if own:
            con.close()
    except Exception:
        pass


# ── قلب النمط: قراءة من الكاش ثم Fallback ──────────────────────────

def _result(row: Any, kind: str, key: str, status: str, age: float = 0.0, extra: Optional[dict] = None,
            ts_col: str = "fetched_at") -> dict:
    out = {
        "cache": status,               # hit | refreshed | stale | miss
        "cache_status": status,
        "age_seconds": int(age) if age != float("inf") else None,
        "age_minutes": round(age / 60.0, 1) if age not in (float("inf"),) else None,
        "stale": status == "stale",
        "kind": kind,
        "key": key,
        "fetched_at": (dict(row).get(ts_col) if row is not None else None),
    }
    if row is not None:
        out.update({k: dict(row)[k] for k in dict(row) if k not in ("fetched_at",)})
    if extra:
        out.update(extra)
    return out


def cached_or_fetch(
    kind: str,
    key: str,
    read_row: Callable[[sqlite3.Connection], Any],
    fetch_fn: Callable[[], Any],
    write_fn: Callable[[sqlite3.Connection, Any], int],
    ttl_sec: Optional[int] = None,
    force: bool = False,
    ts_col: str = "fetched_at",
) -> dict:
    """النمط كامل: كاش → TTL → تحديث → Fallback → وسم stale."""
    con = connect()
    try:
        row = read_row(con)
        ttl = ttl_sec if ttl_sec is not None else ttl_for(kind, con)
        if row is not None and not force:
            age = age_seconds(dict(row)[ts_col])
            if age <= ttl:
                return _result(row, kind, key, "hit", age, ts_col=ts_col)
        age = age_seconds(dict(row)[ts_col]) if row is not None else float("inf")

        # انتهت الصلاحية (أو ما فيه قيمة) → نداء واحد للمصدر
        t0 = time.time()
        try:
            if FORCE_FETCH_FAIL:
                raise RuntimeError("forced fetch failure (test mode)")
            data = fetch_fn()
            if not data:
                raise RuntimeError("empty response from source")
            n = write_fn(con, data)
            con.commit()
            log_fetch(kind, key, True, int((time.time() - t0) * 1000), n, con=con)
            new_row = read_row(con)
            return _result(new_row, kind, key, "refreshed", 0.0,
                           {"rows_written": n, "fetch_ms": int((time.time() - t0) * 1000)}, ts_col=ts_col)
        except Exception as e:  # noqa: BLE001
            log_fetch(kind, key, False, int((time.time() - t0) * 1000), 0, error=f"{type(e).__name__}: {e}", con=con)
            if row is not None:
                return _result(row, kind, key, "stale", age,
                               {"note": f"تعذّر التحديث ({type(e).__name__}) — القيمة المعروضة آخر ما توفر",
                                "error": str(e)}, ts_col=ts_col)
            return {"cache": "miss", "cache_status": "miss", "stale": True, "kind": kind, "key": key,
                    "success": False, "error": f"لا قيمة في الكاش وتعذّر الجلب: {e}"}
    finally:
        con.close()


# ── الأسعار (quotes) ────────────────────────────────────────────────

def _read_quote(con, symbol):
    return con.execute("SELECT * FROM quotes WHERE symbol=?", (symbol.upper(),)).fetchone()


def _write_quote(con, d: dict) -> int:
    con.execute(
        """INSERT INTO quotes(symbol, price, high, low, volume, prev_close, source, fetched_at)
           VALUES (:symbol,:price,:high,:low,:volume,:prev_close,:source,:fetched_at)
           ON CONFLICT(symbol) DO UPDATE SET price=excluded.price, high=excluded.high, low=excluded.low,
             volume=excluded.volume, prev_close=excluded.prev_close, source=excluded.source,
             fetched_at=excluded.fetched_at""",
        d,
    )
    return 1


def fetch_quote_from_source(symbol: str) -> Optional[dict]:
    """الجالب الخارجي الوحيد للأسعار (يُستدعى من الواركر، أو كـ Fallback)."""
    import yfinance as yf

    ysym = yahoo_symbol(symbol)
    df = yf.Ticker(ysym).history(period="1d", interval="1m")
    if df is None or df.empty:
        raise RuntimeError(f"لا توجد بيانات من المصدر لـ {symbol} ({ysym})")
    last = df.iloc[-1]
    prev = None
    try:
        fi = yf.Ticker(ysym).fast_info
        prev = float(fi.previous_close) if fi and fi.previous_close else None
    except Exception:
        prev = None
    return {
        "symbol": symbol.upper(),
        "price": round(float(last["Close"]), 2),
        "high": round(float(last["High"]), 2),
        "low": round(float(last["Low"]), 2),
        "volume": int(last["Volume"]) if last["Volume"] == last["Volume"] else 0,
        "prev_close": prev,
        "source": "yfinance",
        "fetched_at": now_utc(),
    }


def get_quote(symbol: str = "SPX", force: bool = False) -> dict:
    return cached_or_fetch(
        "quote", symbol.upper(),
        lambda con: _read_quote(con, symbol),
        lambda: fetch_quote_from_source(symbol),
        _write_quote,
        force=force,
    )


# ── الشمعات (candles) ───────────────────────────────────────────────

def fetch_candles_from_source(symbol: str, period: str, interval: str) -> list[dict]:
    import yfinance as yf

    df = yf.Ticker(yahoo_symbol(symbol)).history(period=period, interval=interval)
    if df is None or df.empty:
        raise RuntimeError(f"لا شمعات من المصدر لـ {symbol} ({period}/{interval})")
    ts_now = now_utc()
    rows = []
    for idx, r in df.iterrows():
        try:
            ts = idx.tz_convert("UTC").isoformat()
        except Exception:
            ts = str(idx)
        rows.append({
            "symbol": symbol.upper(), "interval": interval, "ts": ts,
            "open": float(r["Open"]), "high": float(r["High"]), "low": float(r["Low"]),
            "close": float(r["Close"]),
            "volume": int(r["Volume"]) if r["Volume"] == r["Volume"] else 0,
            "source": "yfinance", "fetched_at": ts_now,
        })
    return rows


def write_candles(con, rows: list[dict]) -> int:
    if not rows:
        return 0
    con.executemany(
        """INSERT INTO candles(symbol, interval, ts, open, high, low, close, volume, source, fetched_at)
           VALUES (:symbol,:interval,:ts,:open,:high,:low,:close,:volume,:source,:fetched_at)
           ON CONFLICT(symbol, interval, ts) DO UPDATE SET open=excluded.open, high=excluded.high,
             low=excluded.low, close=excluded.close, volume=excluded.volume,
             source=excluded.source, fetched_at=excluded.fetched_at""",
        rows,
    )
    return len(rows)


def refresh_candles(symbol: str, period: str, interval: str) -> tuple[int, int]:
    """يحدّث الشمعات ويرجّع (عدد الصفوف، المللي ثانية). يُستخدم من الواركر."""
    con = connect()
    t0 = time.time()
    try:
        rows = fetch_candles_from_source(symbol, period, interval)
        n = write_candles(con, rows)
        con.commit()
        ms = int((time.time() - t0) * 1000)
        log_fetch(f"candles_{interval}", f"{symbol.upper()}:{period}", True, ms, n, con=con)
        return n, ms
    except Exception as e:  # noqa: BLE001
        log_fetch(f"candles_{interval}", f"{symbol.upper()}:{period}", False,
                  int((time.time() - t0) * 1000), 0, error=f"{type(e).__name__}: {e}", con=con)
        raise
    finally:
        con.close()


def read_candles(symbol: str, interval: str, limit: int = 400, con=None) -> list[sqlite3.Row]:
    own = con is None
    con = con or connect()
    rows = con.execute(
        "SELECT * FROM candles WHERE symbol=? AND interval=? ORDER BY ts DESC LIMIT ?",
        (symbol.upper(), interval, limit),
    ).fetchall()
    if own:
        con.close()
    return list(reversed(rows))


def candles_age(symbol: str, interval: str, con=None) -> float:
    own = con is None
    con = con or connect()
    row = con.execute(
        "SELECT MAX(fetched_at) AS f FROM candles WHERE symbol=? AND interval=?",
        (symbol.upper(), interval)).fetchone()
    if own:
        con.close()
    return age_seconds(row["f"]) if row and row["f"] else float("inf")


# ── الإنذارات المحسوبة (alerts) ─────────────────────────────────────

def compute_alerts(current: float, closes: list[float]) -> dict:
    window = closes[-20:]
    support = round(min(window), 2)
    resistance = round(max(window), 2)
    alerts = []
    if current <= support * 1.005:
        alerts.append("قرب الدعم — احتمال صعود (CALL)")
    if current >= resistance * 0.995:
        alerts.append("قرب المقاومة — احتمال هبوط (PUT)")
    return {"support": support, "resistance": resistance, "alerts": alerts}


def _read_alerts(con, symbol):
    return con.execute("SELECT * FROM alerts WHERE symbol=?", (symbol.upper(),)).fetchone()


def _write_alerts(con, d: dict) -> int:
    con.execute(
        """INSERT INTO alerts(symbol, computed_at, current, support, resistance, alerts_json, window_desc, source)
           VALUES (:symbol,:computed_at,:current,:support,:resistance,:alerts_json,:window_desc,:source)
           ON CONFLICT(symbol) DO UPDATE SET computed_at=excluded.computed_at, current=excluded.current,
             support=excluded.support, resistance=excluded.resistance, alerts_json=excluded.alerts_json,
             window_desc=excluded.window_desc, source=excluded.source""",
        d,
    )
    return 1


def compute_alerts_from_cache(symbol: str = "SPX") -> Optional[dict]:
    """يحسب الإنذارات من الشمعات المخزّنة (بلا شبكة) — الطريق المفضل عند التحديث."""
    import json as _json

    con = connect()
    try:
        rows = read_candles(symbol, "5m", 400, con=con)
        if len(rows) < 5:
            return None
        closes = [float(r["close"]) for r in rows]
        current = closes[-1]
        calc = compute_alerts(current, closes)
        return {
            "symbol": symbol.upper(), "computed_at": now_utc(), "current": round(current, 2),
            "support": calc["support"], "resistance": calc["resistance"],
            "alerts_json": _json.dumps(calc["alerts"], ensure_ascii=False),
            "window_desc": "آخر 20 شمعة (5 دقائق)", "source": "cache",
        }
    finally:
        con.close()


def fetch_alerts_from_source(symbol: str = "SPX") -> dict:
    """Fallback: يجيب الشمعات من المصدر ثم يحسب."""
    import json as _json

    rows = fetch_candles_from_source(symbol, "5d", "5m")
    closes = [r["close"] for r in rows]
    calc = compute_alerts(closes[-1], closes)
    return {
        "symbol": symbol.upper(), "computed_at": now_utc(), "current": round(closes[-1], 2),
        "support": calc["support"], "resistance": calc["resistance"],
        "alerts_json": _json.dumps(calc["alerts"], ensure_ascii=False),
        "window_desc": "آخر 20 شمعة (5 دقائق)", "source": "yfinance",
    }


def get_alerts(symbol: str = "SPX", force: bool = False) -> dict:
    """الإنذارات: كاش → (إعادة حساب من الشمعات المخزّنة بلا شبكة) → المصدر كـ Fallback."""
    import json as _json

    def _smart_fetch():
        d = compute_alerts_from_cache(symbol)
        if d:
            return d
        return fetch_alerts_from_source(symbol)

    out = cached_or_fetch(
        "alerts", symbol.upper(),
        lambda con: _read_alerts(con, symbol),
        _smart_fetch,
        _write_alerts,
        force=force,
        ts_col="computed_at",
    )
    if "alerts_json" in out:
        try:
            out["alerts"] = _json.loads(out.pop("alerts_json") or "[]")
        except Exception:
            out["alerts"] = []
    return out


# ── الصيانة والإحصاء ───────────────────────────────────────────────

def prune(days: int = 30) -> int:
    con = connect()
    try:
        n = con.execute(
            "DELETE FROM candles WHERE fetched_at < datetime('now', ?)", (f"-{int(days)} days",)).rowcount
        con.execute("DELETE FROM fetch_log WHERE at < datetime('now', '-14 days')")
        con.commit()
        return n
    finally:
        con.close()


def stats(con=None) -> dict:
    own = con is None
    con = con or connect()
    try:
        out = {}
        for t in ("quotes", "candles", "option_chains", "alerts", "fetch_log"):
            out[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        out["ttl"] = {r["kind"]: (r["open_sec"], r["closed_sec"]) for r in con.execute("SELECT * FROM ttl_policy")}
        return out
    finally:
        if own:
            con.close()


if __name__ == "__main__":
    init_db()
    print("DB:", DB_PATH)
    print("market_open:", market_open())
    print(stats())
