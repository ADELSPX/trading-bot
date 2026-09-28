#!/usr/bin/env python3
"""
فزّاع — قاعدة الشموع الثلاث (آلة حالات) لمنهج فهد قاما لمراكز سيولة الصانع.

المنطق الحسابي نقي بلا شبكة. لا يُستورد yfinance إلا داخل دالة الجلب
(scripts.fetch_bars) كي تعمل الاختبارات بلا إنترنت.

الحدود:
  الدخول (IDLE):
    كول: open > center و close > open (شمعة خضراء) و low > center
    بوت: open < center و close < open (شمعة حمراء) و high < center
  بعد الدخول:
    - انتهاء الوقت أولاً: مضى >= max_bars*5 دقيقة => EXIT_TIMEOUT
    - شمعة في اتجاه الصفقة => HOLD
    - شمعة عكس الصفقة تلمس المركز => EXIT_TOUCH وإلا HOLD

الاستخدام:
  python3 scripts/three_candle.py --selftest
  python3 scripts/three_candle.py --center 6650 --symbol ^SPX
  python3 scripts/three_candle.py --center 6650 --symbol ^SPX --watch
  python3 scripts/three_candle.py --center 6650 --csv bars.csv
  python3 scripts/three_candle.py --center 6650 --symbol ^SPX --json out.json
  python3 scripts/three_candle.py --center 6650 --symbol ^SPX --quality weak
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime

STATE_IDLE = "IDLE"
STATE_IN_CALL = "IN_CALL"
STATE_IN_PUT = "IN_PUT"
STATE_EXITED = "EXITED"

ACTION_NO_TRADE = "NO_TRADE"
ACTION_ENTER_CALL = "ENTER_CALL"
ACTION_ENTER_PUT = "ENTER_PUT"
ACTION_HOLD = "HOLD"
ACTION_EXIT_TOUCH = "EXIT_TOUCH"
ACTION_EXIT_TIMEOUT = "EXIT_TIMEOUT"

BAR_MINUTES = 5
QUALITIES = ("strong", "weak", "lateral")


def parse_time(value):
    """يحاول تحويل نص الوقت إلى datetime. يرجع None عند الفشل."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    candidate = text
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


class ThreeCandle:
    """آلة حالات تطبق قاعدة الشموع الثلاث حول مركز سيولة الصانع."""

    def __init__(self, center, max_bars=12, third_bar_only=False,
                 center_quality="strong"):
        self.center = float(center)
        self.max_bars = int(max_bars)
        self.third_bar_only = bool(third_bar_only)
        if center_quality not in QUALITIES:
            raise ValueError("center_quality must be one of %s" % (QUALITIES,))
        self.center_quality = center_quality

        self.state = STATE_IDLE
        self.history = []
        self.bar_index = -1
        self.entry_bar_index = None
        self.entry_time = None
        self.entry_premium = None
        self._count = 0

    # ------------------------------------------------------------------ #
    def on_bar(self, bar):
        """يمرّر شمعة واحدة ويرجع dict بالحالة والفعل."""
        self._count += 1
        idx = self._count - 1
        self.bar_index = idx

        o = float(bar["open"])
        h = float(bar["high"])
        low = float(bar["low"])
        c = float(bar["close"])
        t_raw = bar.get("time")
        premium = bar.get("premium")
        if premium is not None:
            premium = float(premium)

        if self.state == STATE_EXITED:
            return self._record(idx, STATE_EXITED, ACTION_NO_TRADE, "exited",
                                idx - (self.entry_bar_index or idx),
                                self._elapsed_min(t_raw, self._bars_in_trade(idx)),
                                self._hit_30pct(premium))

        if self.state == STATE_IDLE:
            return self._handle_idle(idx, o, h, low, c, t_raw, premium)

        return self._handle_in_trade(idx, o, h, low, c, t_raw, premium)

    # ------------------------------------------------------------------ #
    def _handle_idle(self, idx, o, h, low, c, t_raw, premium):
        if self.center_quality in ("weak", "lateral"):
            return self._record(idx, STATE_IDLE, ACTION_NO_TRADE, "weak_center",
                                0, 0, False)

        if o > self.center and c > o and low > self.center:
            self.state = STATE_IN_CALL
            self.entry_bar_index = idx
            self.entry_time = parse_time(t_raw)
            self.entry_premium = premium
            return self._record(idx, STATE_IN_CALL, ACTION_ENTER_CALL, "entry_call",
                                0, 0, self._hit_30pct(premium))

        if o < self.center and c < o and h < self.center:
            self.state = STATE_IN_PUT
            self.entry_bar_index = idx
            self.entry_time = parse_time(t_raw)
            self.entry_premium = premium
            return self._record(idx, STATE_IN_PUT, ACTION_ENTER_PUT, "entry_put",
                                0, 0, self._hit_30pct(premium))

        return self._record(idx, STATE_IDLE, ACTION_NO_TRADE,
                            self._idle_reason(o, h, low, c), 0, 0, False)

    def _idle_reason(self, o, h, low, c):
        if o == self.center:
            return "no_entry_at_center"
        if c == o:
            return "no_entry_doji"
        if o > self.center:
            if c > o:
                if low <= self.center:
                    return "no_entry_touch"
                return "no_entry"
            return "no_entry_direction"
        if c < o:
            if h >= self.center:
                return "no_entry_touch"
            return "no_entry"
        return "no_entry_direction"

    def _handle_in_trade(self, idx, o, h, low, c, t_raw, premium):
        bars = self._bars_in_trade(idx)
        elapsed = self._elapsed_min(t_raw, bars)

        if elapsed >= self.max_bars * BAR_MINUTES:
            self.state = STATE_EXITED
            return self._record(idx, STATE_EXITED, ACTION_EXIT_TIMEOUT,
                                "timeout_60min", bars, elapsed,
                                self._hit_30pct(premium))

        if self.state == STATE_IN_CALL:
            direction = c > o
            touched = low <= self.center
        else:
            direction = c < o
            touched = h >= self.center

        if direction:
            return self._record(idx, self.state, ACTION_HOLD, "hold", bars,
                                elapsed, self._hit_30pct(premium))

        if touched:
            if self.third_bar_only and bars != 2:
                return self._record(idx, self.state, ACTION_HOLD, "hold", bars,
                                    elapsed, self._hit_30pct(premium))
            self.state = STATE_EXITED
            return self._record(idx, STATE_EXITED, ACTION_EXIT_TOUCH,
                                "touch_center", bars, elapsed,
                                self._hit_30pct(premium))

        return self._record(idx, self.state, ACTION_HOLD, "hold", bars, elapsed,
                            self._hit_30pct(premium))

    # ------------------------------------------------------------------ #
    def _bars_in_trade(self, idx):
        if self.entry_bar_index is None:
            return 0
        return idx - self.entry_bar_index

    def _elapsed_min(self, t_raw, bars):
        now = parse_time(t_raw)
        if now is not None and self.entry_time is not None:
            delta = (now - self.entry_time).total_seconds() / 60.0
            if delta < 0:
                return 0
            return int(delta)
        return bars * BAR_MINUTES

    def _hit_30pct(self, premium):
        if premium is None or self.entry_premium in (None, 0):
            return False
        return (premium - self.entry_premium) / self.entry_premium >= 0.30

    def _record(self, bar_index, state, action, reason, bars_in_trade,
                elapsed_min, hit_30pct):
        result = {
            "state": state,
            "action": action,
            "reason": reason,
            "bar_index": bar_index,
            "bars_in_trade": bars_in_trade,
            "elapsed_min": elapsed_min,
            "hit_30pct": bool(hit_30pct),
        }
        self.history.append(dict(result))
        return result


# ---------------------------------------------------------------------- #
def fetch_bars(symbol, period="5d", interval="5m", all_bars=False):
    """يجلب الشموع من yfinance. الاستيراد داخل الدالة فقط (بلا شبكة عند الاستيراد)."""
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    frame = ticker.history(period=period, interval=interval)
    bars = []
    for index, row in frame.iterrows():
        bar = {
            "time": str(index),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
        }
        if "premium" in row:
            try:
                bar["premium"] = float(row["premium"])
            except (TypeError, ValueError):
                pass
        bars.append(bar)
    if not bars:
        return bars
    if not all_bars:
        last_day = bars[-1]["time"][:10]
        bars = [b for b in bars if b["time"][:10] == last_day]
    return bars


def read_csv_bars(path):
    bars = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            bar = {
                "time": row.get("time") or row.get("Time") or "",
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }
            premium = row.get("premium")
            if premium not in (None, ""):
                bar["premium"] = float(premium)
            bars.append(bar)
    return bars


def run_bars(machine, bars):
    results = []
    for bar in bars:
        results.append(machine.on_bar(bar))
    return results


def print_transitions(results):
    last_action = None
    for result in results:
        if result["action"] != last_action:
            print(json.dumps(result, ensure_ascii=False))
            last_action = result["action"]


def run_watch(machine, symbol, period, interval, all_bars, json_path, state):
    seen = set(state.get("seen", []))
    while True:
        try:
            bars = fetch_bars(symbol, period=period, interval=interval,
                              all_bars=all_bars)
        except Exception as exc:  # noqa: BLE001
            print("خطأ في الجلب: %s" % exc, file=sys.stderr)
            bars = []
        for bar in bars:
            if bar["time"] in seen:
                continue
            seen.add(bar["time"])
            result = machine.on_bar(bar)
            if result["action"] != ACTION_NO_TRADE or result["state"] != STATE_IDLE:
                print(json.dumps(result, ensure_ascii=False))
        state["seen"] = list(seen)
        if json_path:
            save_json(machine, json_path, bars)
        try:
            import time as _time
            _time.sleep(60)
        except KeyboardInterrupt:
            print("توقف المراقب (Ctrl+C)", file=sys.stderr)
            break


def save_json(machine, path, bars):
    payload = {
        "state": machine.state,
        "history": machine.history,
        "last_actions": machine.history[-20:],
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print("حُفظت النتيجة في %s" % path, file=sys.stderr)


# ---------------------------------------------------------------------- #
def _bar(time, o, h, low, c, premium=None):
    bar = {"time": time, "open": o, "high": h, "low": low, "close": c}
    if premium is not None:
        bar["premium"] = premium
    return bar


def _embedded_tests():
    """اختبارات مدمجة سريعة — تطابق منطق tests/test_three_candle.py."""
    passed = 0
    total = 0
    cases = []

    def case(name, fn):
        cases.append((name, fn))

    def t_entry_call():
        m = ThreeCandle(6650)
        r = m.on_bar(_bar("t1", 6655, 6662, 6652, 6660))
        assert r["action"] == ACTION_ENTER_CALL, r
        assert r["state"] == STATE_IN_CALL, r

    def t_entry_put():
        m = ThreeCandle(6650)
        r = m.on_bar(_bar("t1", 6645, 6648, 6638, 6640))
        assert r["action"] == ACTION_ENTER_PUT, r

    def t_at_center():
        m = ThreeCandle(6650)
        r = m.on_bar(_bar("t1", 6650, 6660, 6645, 6658))
        assert r["action"] == ACTION_NO_TRADE, r

    def t_touch():
        m = ThreeCandle(6650)
        r = m.on_bar(_bar("t1", 6655, 6662, 6649, 6660))
        assert r["action"] == ACTION_NO_TRADE, r
        assert r["reason"] == "no_entry_touch", r

    def t_doji():
        m = ThreeCandle(6650)
        r = m.on_bar(_bar("t1", 6655, 6662, 6652, 6655))
        assert r["action"] == ACTION_NO_TRADE, r
        assert r["reason"] == "no_entry_doji", r

    def t_hold_green():
        m = ThreeCandle(6650)
        m.on_bar(_bar("t1", 6655, 6662, 6652, 6660))
        r = m.on_bar(_bar("t2", 6660, 6670, 6655, 6668))
        assert r["action"] == ACTION_HOLD, r

    def t_exit_touch_call():
        m = ThreeCandle(6650)
        m.on_bar(_bar("t1", 6655, 6662, 6652, 6660))
        m.on_bar(_bar("t2", 6660, 6670, 6655, 6668))
        r = m.on_bar(_bar("t3", 6665, 6666, 6645, 6648))
        assert r["action"] == ACTION_EXIT_TOUCH, r
        assert r["state"] == STATE_EXITED, r

    def t_no_touch_call():
        m = ThreeCandle(6650)
        m.on_bar(_bar("t1", 6655, 6662, 6652, 6660))
        m.on_bar(_bar("t2", 6660, 6670, 6655, 6668))
        r = m.on_bar(_bar("t3", 6658, 6660, 6652, 6654))
        assert r["action"] == ACTION_HOLD, r

    def t_exit_touch_put():
        m = ThreeCandle(6650)
        m.on_bar(_bar("t1", 6645, 6648, 6638, 6640))
        m.on_bar(_bar("t2", 6640, 6643, 6630, 6632))
        r = m.on_bar(_bar("t3", 6635, 6655, 6632, 6650))
        assert r["action"] == ACTION_EXIT_TOUCH, r

    def t_timeout():
        m = ThreeCandle(6650)
        bars = [_bar("t0", 6655, 6662, 6652, 6660)]
        for i in range(1, 13):
            bars.append(_bar("t%d" % i, 6660, 6670, 6655, 6668))
        results = [m.on_bar(b) for b in bars]
        assert results[-1]["action"] == ACTION_EXIT_TIMEOUT, results[-1]

    def t_weak():
        m = ThreeCandle(6650, center_quality="weak")
        r = m.on_bar(_bar("t1", 6655, 6662, 6652, 6660))
        assert r["action"] == ACTION_NO_TRADE, r
        assert r["reason"] == "weak_center", r

    def t_exited_final():
        m = ThreeCandle(6650)
        m.on_bar(_bar("t1", 6655, 6662, 6652, 6660))
        m.on_bar(_bar("t2", 6660, 6670, 6655, 6668))
        m.on_bar(_bar("t3", 6665, 6666, 6645, 6648))
        r = m.on_bar(_bar("t4", 6650, 6660, 6640, 6655))
        assert r["action"] == ACTION_NO_TRADE, r
        assert r["state"] == STATE_EXITED, r

    def t_hit_30pct():
        m = ThreeCandle(6650)
        m.on_bar(_bar("t1", 6655, 6662, 6652, 6660, premium=2.00))
        r = m.on_bar(_bar("t2", 6660, 6670, 6655, 6668, premium=2.60))
        assert r["hit_30pct"] is True, r

    for name, fn in (
        ("entry_call", t_entry_call),
        ("entry_put", t_entry_put),
        ("at_center", t_at_center),
        ("touch", t_touch),
        ("doji", t_doji),
        ("hold_green", t_hold_green),
        ("exit_touch_call", t_exit_touch_call),
        ("no_touch_call", t_no_touch_call),
        ("exit_touch_put", t_exit_touch_put),
        ("timeout", t_timeout),
        ("weak", t_weak),
        ("exited_final", t_exited_final),
        ("hit_30pct", t_hit_30pct),
    ):
        total += 1
        try:
            fn()
            passed += 1
        except AssertionError as exc:
            print("فشل: %s -> %s" % (name, exc), file=sys.stderr)
        except Exception as exc:  # noqa: BLE001
            print("خطأ: %s -> %s" % (name, exc), file=sys.stderr)
    return passed, total


# ---------------------------------------------------------------------- #
def main(argv=None):
    parser = argparse.ArgumentParser(description="قاعدة الشموع الثلاث — فهد قاما")
    parser.add_argument("--center", type=float, help="استرايك مركز سيولة الصانع")
    parser.add_argument("--symbol", default="^SPX", help="الرمز (افتراضي ^SPX)")
    parser.add_argument("--csv", help="ملف شموع محفوظ (time,open,high,low,close)")
    parser.add_argument("--watch", action="store_true", help="حلقة كل 60 ثانية")
    parser.add_argument("--json", dest="json_path", help="حفظ النتيجة JSON")
    parser.add_argument("--quality", default="strong", choices=list(QUALITIES),
                        help="جودة المركز: strong|weak|lateral")
    parser.add_argument("--all-bars", action="store_true",
                        help="استخدم كل الشموع لا آخر جلسة فقط")
    parser.add_argument("--max-bars", type=int, default=12,
                        help="أقصى عدد شموع داخل الصفقة (افتراضي 12 = 60 دقيقة)")
    parser.add_argument("--third-bar-only", action="store_true",
                        help="لا يُحكم بالخروج إلا على الشمعة الثالثة")
    parser.add_argument("--selftest", action="store_true",
                        help="يشغّل الاختبارات المدمجة")
    args = parser.parse_args(argv)

    if args.selftest:
        passed, total = _embedded_tests()
        print("RESULT pass=%d/%d" % (passed, total))
        if passed == total:
            print("ALL TESTS PASSED")
            return 0
        return 1

    if args.center is None:
        parser.error("--center مطلوب (أو استخدم --selftest)")

    machine = ThreeCandle(args.center, max_bars=args.max_bars,
                          third_bar_only=args.third_bar_only,
                          center_quality=args.quality)

    if args.watch:
        print("بدء المراقبة على %s حول المركز %s (Ctrl+C للإيقاف)"
              % (args.symbol, args.center), file=sys.stderr)
        run_watch(machine, args.symbol, "5d", "5m", args.all_bars,
                  args.json_path, {})
        print("آخر حالة: %s" % machine.state)
        return 0

    if args.csv:
        bars = read_csv_bars(args.csv)
    else:
        bars = fetch_bars(args.symbol, all_bars=args.all_bars)

    if not bars:
        print("لا توجد شموع للتحليل", file=sys.stderr)
        return 1

    results = run_bars(machine, bars)
    if args.json_path:
        save_json(machine, args.json_path, bars)

    print("عدد الشموع: %d" % len(bars))
    print("آخر حالة: %s" % machine.state)
    print("آخر فعل: %s (%s)" % (results[-1]["action"], results[-1]["reason"]))
    print("سجل الانتقالات:")
    print_transitions(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
