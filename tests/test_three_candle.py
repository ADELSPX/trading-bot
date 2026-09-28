#!/usr/bin/env python3
"""اختبارات قاعدة الشموع الثلاث (بلا شبكة، بلا yfinance).

التشغيل من جذر المشروع:
    python3 tests/test_three_candle.py
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.three_candle import (  # noqa: E402
    ThreeCandle,
    ACTION_NO_TRADE,
    ACTION_ENTER_CALL,
    ACTION_ENTER_PUT,
    ACTION_HOLD,
    ACTION_EXIT_TOUCH,
    ACTION_EXIT_TIMEOUT,
    STATE_IDLE,
    STATE_IN_CALL,
    STATE_IN_PUT,
    STATE_EXITED,
)


def bar(time, o, h, low, c, premium=None):
    result = {"time": time, "open": o, "high": h, "low": low, "close": c}
    if premium is not None:
        result["premium"] = premium
    return result


class TestThreeCandle(unittest.TestCase):
    def test_01_entry_call(self):
        m = ThreeCandle(6650)
        r = m.on_bar(bar("t1", 6655, 6662, 6652, 6660))
        self.assertEqual(r["action"], ACTION_ENTER_CALL)
        self.assertEqual(r["state"], STATE_IN_CALL)

    def test_02_entry_put(self):
        m = ThreeCandle(6650)
        r = m.on_bar(bar("t1", 6645, 6648, 6638, 6640))
        self.assertEqual(r["action"], ACTION_ENTER_PUT)
        self.assertEqual(r["state"], STATE_IN_PUT)

    def test_03_open_at_center(self):
        m = ThreeCandle(6650)
        r = m.on_bar(bar("t1", 6650, 6660, 6645, 6658))
        self.assertEqual(r["action"], ACTION_NO_TRADE)
        self.assertEqual(r["state"], STATE_IDLE)

    def test_04_green_but_touch(self):
        m = ThreeCandle(6650)
        r = m.on_bar(bar("t1", 6655, 6662, 6649, 6660))
        self.assertEqual(r["action"], ACTION_NO_TRADE)
        self.assertEqual(r["reason"], "no_entry_touch")

    def test_05_doji(self):
        m = ThreeCandle(6650)
        r = m.on_bar(bar("t1", 6655, 6662, 6652, 6655))
        self.assertEqual(r["action"], ACTION_NO_TRADE)
        self.assertEqual(r["reason"], "no_entry_doji")

    def test_06_call_second_green_hold(self):
        m = ThreeCandle(6650)
        m.on_bar(bar("t1", 6655, 6662, 6652, 6660))
        r = m.on_bar(bar("t2", 6660, 6670, 6655, 6668))
        self.assertEqual(r["action"], ACTION_HOLD)
        self.assertEqual(r["state"], STATE_IN_CALL)

    def test_07_call_third_red_touch(self):
        m = ThreeCandle(6650)
        m.on_bar(bar("t1", 6655, 6662, 6652, 6660))
        m.on_bar(bar("t2", 6660, 6670, 6655, 6668))
        r = m.on_bar(bar("t3", 6665, 6666, 6645, 6648))
        self.assertEqual(r["action"], ACTION_EXIT_TOUCH)
        self.assertEqual(r["state"], STATE_EXITED)

    def test_08_call_third_red_no_touch(self):
        m = ThreeCandle(6650)
        m.on_bar(bar("t1", 6655, 6662, 6652, 6660))
        m.on_bar(bar("t2", 6660, 6670, 6655, 6668))
        r = m.on_bar(bar("t3", 6658, 6660, 6652, 6654))
        self.assertEqual(r["action"], ACTION_HOLD)
        self.assertEqual(r["state"], STATE_IN_CALL)

    def test_09_put_third_green_touch(self):
        m = ThreeCandle(6650)
        m.on_bar(bar("t1", 6645, 6648, 6638, 6640))
        m.on_bar(bar("t2", 6640, 6643, 6630, 6632))
        r = m.on_bar(bar("t3", 6635, 6655, 6632, 6650))
        self.assertEqual(r["action"], ACTION_EXIT_TOUCH)
        self.assertEqual(r["state"], STATE_EXITED)

    def test_10_timeout_after_60min(self):
        m = ThreeCandle(6650)
        bars = [bar("t0", 6655, 6662, 6652, 6660)]
        for i in range(1, 13):
            bars.append(bar("t%d" % i, 6660, 6670, 6655, 6668))
        results = [m.on_bar(b) for b in bars]
        self.assertEqual(results[-1]["action"], ACTION_EXIT_TIMEOUT)
        self.assertEqual(results[-1]["state"], STATE_EXITED)

    def test_11_weak_center(self):
        m = ThreeCandle(6650, center_quality="weak")
        r = m.on_bar(bar("t1", 6655, 6662, 6652, 6660))
        self.assertEqual(r["action"], ACTION_NO_TRADE)
        self.assertEqual(r["reason"], "weak_center")

    def test_12_exited_is_final(self):
        m = ThreeCandle(6650)
        m.on_bar(bar("t1", 6655, 6662, 6652, 6660))
        m.on_bar(bar("t2", 6660, 6670, 6655, 6668))
        m.on_bar(bar("t3", 6665, 6666, 6645, 6648))
        r = m.on_bar(bar("t4", 6650, 6660, 6640, 6655))
        self.assertEqual(r["action"], ACTION_NO_TRADE)
        self.assertEqual(r["state"], STATE_EXITED)

    def test_13_hit_30pct(self):
        m = ThreeCandle(6650)
        m.on_bar(bar("t1", 6655, 6662, 6652, 6660, premium=2.00))
        r = m.on_bar(bar("t2", 6660, 6670, 6655, 6668, premium=2.60))
        self.assertTrue(r["hit_30pct"])

    def test_14_import_clean_no_yfinance(self):
        import scripts.three_candle  # noqa: F401
        self.assertNotIn("yfinance", sys.modules)


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestThreeCandle)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print("RESULT pass=%d /%d" % (passed, total))
    if result.wasSuccessful():
        print("ALL TESTS PASSED")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
