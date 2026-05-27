"""
أنماط الرسم البياني — Chart Patterns
═══════════════════════════════════════
منهجية سامي ضيف الله WH SPX — مايو 2026

الأنماط المدعومة:
  القسم 1 — أنماط الانعكاس:
    - القاع المزدوج (Double Bottom / W)
    - القمة المزدوجة (Double Top / M)
    - الرأس والكتفين (Head & Shoulders)
    - الرأس والكتفين المقلوب (Inverse H&S)

  القسم 2 — أنماط الاستمرار:
    - الأعلام (Flags)
    - الرايات (Pennants)
    - المثلثات (Triangles): صاعد / هابط / متماثل

القاعدة الذهبية:
"النمط صالح فقط عند الكسر المؤكد مع الحجم. احذر من الكسر الزائف."
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class PatternCategory(Enum):
    REVERSAL = "reversal"       # انعكاسي
    CONTINUATION = "continuation"  # استمراري


class PatternType(Enum):
    """نوع النمط"""
    # انعكاسية
    DOUBLE_BOTTOM = "double_bottom"
    DOUBLE_TOP = "double_top"
    HEAD_SHOULDERS = "head_shoulders"
    INVERSE_HEAD_SHOULDERS = "inverse_head_shoulders"

    # استمرارية
    BULL_FLAG = "bull_flag"
    BEAR_FLAG = "bear_flag"
    BULL_PENNANT = "bull_pennant"
    BEAR_PENNANT = "bear_pennant"
    ASCENDING_TRIANGLE = "ascending_triangle"
    DESCENDING_TRIANGLE = "descending_triangle"
    SYMMETRICAL_TRIANGLE = "symmetrical_triangle"


@dataclass
class PatternSignal:
    """إشارة نمط الرسم البياني"""
    pattern_type: PatternType
    category: PatternCategory
    direction: str               # "call" | "put"
    entry_price: float           # سعر الدخول عند الكسر
    stop_loss: float             # وقف الخسارة
    target_price: float          # هدف
    confidence: float            # ثقة (0-1)
    neckline: float = 0          # خط العنق (للرأس والكتفين)
    breakout_price: float = 0    # سعر الكسر
    description: str = ""


class ChartPatternDetector:
    """
    كاشف أنماط الرسم البياني

    الاستخدام:
        detector = ChartPatternDetector()
        patterns = detector.detect_all(candles)
    """

    MIN_CANDLES = 20  # أقل عدد شموع للتحليل

    def detect_all(self, candles: list[dict]) -> list[PatternSignal]:
        """كشف جميع الأنماط المدعومة"""
        if len(candles) < self.MIN_CANDLES:
            return []

        patterns: list[PatternSignal] = []

        # أنماط الانعكاس
        patterns.extend(self._detect_double_top(candles))
        patterns.extend(self._detect_double_bottom(candles))
        patterns.extend(self._detect_head_shoulders(candles))
        patterns.extend(self._detect_inverse_head_shoulders(candles))

        # أنماط الاستمرار
        patterns.extend(self._detect_flags(candles))
        patterns.extend(self._detect_pennants(candles))
        patterns.extend(self._detect_triangles(candles))

        # ترتيب حسب الثقة
        patterns.sort(key=lambda p: p.confidence, reverse=True)

        return patterns

    def detect_reversal(self, candles: list[dict]) -> list[PatternSignal]:
        """كشف الأنماط الانعكاسية فقط"""
        if len(candles) < self.MIN_CANDLES:
            return []

        patterns: list[PatternSignal] = []
        patterns.extend(self._detect_double_top(candles))
        patterns.extend(self._detect_double_bottom(candles))
        patterns.extend(self._detect_head_shoulders(candles))
        patterns.extend(self._detect_inverse_head_shoulders(candles))
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        return patterns

    def detect_continuation(self, candles: list[dict]) -> list[PatternSignal]:
        """كشف الأنماط الاستمرارية فقط"""
        if len(candles) < self.MIN_CANDLES:
            return []

        patterns: list[PatternSignal] = []
        patterns.extend(self._detect_flags(candles))
        patterns.extend(self._detect_pennants(candles))
        patterns.extend(self._detect_triangles(candles))
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        return patterns

    # ═══════════════════════════════════════════════════
    # القمة المزدوجة (Double Top / M)
    # ═══════════════════════════════════════════════════

    def _detect_double_top(self, candles: list[dict]) -> list[PatternSignal]:
        """
        القمة المزدوجة = قمتين متساويتين تقريباً يفصلهما قاع
        
        التأكيد: كسر خط العنق (القاع بين القمتين) للأسفل
        الإشارة: PUT
        """
        signals = []
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]

        # البحث عن قمتين في آخر 60 شمعة
        lookback = min(60, len(candles))
        window = candles[-lookback:]

        peaks = self._find_peaks(window, strength=3)

        for i in range(len(peaks) - 1):
            p1 = peaks[i]
            p2 = peaks[i + 1]

            # شرط المسافة بين القمتين
            if p2["index"] - p1["index"] < 5:
                continue

            # شرط التساوي (±1%)
            avg = (p1["level"] + p2["level"]) / 2
            if avg == 0:
                continue
            if abs(p1["level"] - p2["level"]) / avg > 0.015:
                continue

            # البحث عن القاع بين القمتين (خط العنق)
            between_lows = [
                c["low"] for c in window[p1["index"]:p2["index"]]
            ]
            if not between_lows:
                continue

            neckline = min(between_lows)
            current_price = closes[-1]

            # تأكيد الكسر: السعر الحالي تحت خط العنق
            if current_price < neckline:
                pattern_height = (p1["level"] + p2["level"]) / 2 - neckline
                target = neckline - pattern_height

                signals.append(PatternSignal(
                    pattern_type=PatternType.DOUBLE_TOP,
                    category=PatternCategory.REVERSAL,
                    direction="put",
                    entry_price=current_price,
                    stop_loss=neckline * 1.005,
                    target_price=target,
                    confidence=0.7,
                    neckline=neckline,
                    breakout_price=neckline,
                    description=f"قمة مزدوجة M — كسر خط العنق {neckline:.1f}",
                ))

        return signals

    # ═══════════════════════════════════════════════════
    # القاع المزدوج (Double Bottom / W)
    # ═══════════════════════════════════════════════════

    def _detect_double_bottom(self, candles: list[dict]) -> list[PatternSignal]:
        """
        القاع المزدوج = قاعين متساويين تقريباً تفصل بينهما قمة
        
        التأكيد: كسر خط العنق (القمة بين القاعين) للأعلى
        الإشارة: CALL
        """
        signals = []
        closes = [c["close"] for c in candles]

        lookback = min(60, len(candles))
        window = candles[-lookback:]

        troughs = self._find_troughs(window, strength=3)

        for i in range(len(troughs) - 1):
            t1 = troughs[i]
            t2 = troughs[i + 1]

            if t2["index"] - t1["index"] < 5:
                continue

            avg = (t1["level"] + t2["level"]) / 2
            if avg == 0:
                continue
            if abs(t1["level"] - t2["level"]) / avg > 0.015:
                continue

            between_highs = [
                c["high"] for c in window[t1["index"]:t2["index"]]
            ]
            if not between_highs:
                continue

            neckline = max(between_highs)
            current_price = closes[-1]

            if current_price > neckline:
                pattern_height = neckline - (t1["level"] + t2["level"]) / 2
                target = neckline + pattern_height

                signals.append(PatternSignal(
                    pattern_type=PatternType.DOUBLE_BOTTOM,
                    category=PatternCategory.REVERSAL,
                    direction="call",
                    entry_price=current_price,
                    stop_loss=neckline * 0.995,
                    target_price=target,
                    confidence=0.7,
                    neckline=neckline,
                    breakout_price=neckline,
                    description=f"قاع مزدوج W — كسر خط العنق {neckline:.1f}",
                ))

        return signals

    # ═══════════════════════════════════════════════════
    # الرأس والكتفين (Head & Shoulders)
    # ═══════════════════════════════════════════════════

    def _detect_head_shoulders(self, candles: list[dict]) -> list[PatternSignal]:
        """
        الرأس والكتفين = 3 قمم — الوسطى أعلى (الرأس) والطرفان أقل (الكتفين)
        
        التأكيد: كسر خط العنق (الخط الواصل بين القاعين تحت الكتفين) للأسفل
        الإشارة: PUT
        """
        signals = []
        closes = [c["close"] for c in candles]

        lookback = min(60, len(candles))
        window = candles[-lookback:]

        peaks = self._find_peaks(window, strength=3)

        for i in range(len(peaks) - 2):
            left = peaks[i]     # الكتف الأيسر
            head = peaks[i + 1] # الرأس
            right = peaks[i + 2] # الكتف الأيمن

            # الرأس أعلى من الكتفين
            if not (head["level"] > left["level"] and head["level"] > right["level"]):
                continue

            # الكتفين متساويين تقريباً (±1.5%)
            avg_shoulder = (left["level"] + right["level"]) / 2
            if avg_shoulder == 0:
                continue
            if abs(left["level"] - right["level"]) / avg_shoulder > 0.02:
                continue

            # المسافة بين القمم مناسبة
            if head["index"] - left["index"] < 3 or right["index"] - head["index"] < 3:
                continue

            # خط العنق: القاعين بين القمم
            trough_between_lh = [
                c["low"] for c in window[left["index"]:head["index"] + 1]
            ]
            trough_between_hr = [
                c["low"] for c in window[head["index"]:right["index"] + 1]
            ]

            if not trough_between_lh or not trough_between_hr:
                continue

            neckline_left = min(trough_between_lh)
            neckline_right = min(trough_between_hr)
            neckline = (neckline_left + neckline_right) / 2

            current_price = closes[-1]

            if current_price < neckline:
                pattern_height = head["level"] - neckline
                target = neckline - pattern_height

                signals.append(PatternSignal(
                    pattern_type=PatternType.HEAD_SHOULDERS,
                    category=PatternCategory.REVERSAL,
                    direction="put",
                    entry_price=current_price,
                    stop_loss=neckline * 1.005,
                    target_price=target,
                    confidence=0.75,
                    neckline=neckline,
                    breakout_price=neckline,
                    description=f"رأس وكتفين — كسر خط العنق {neckline:.1f}",
                ))

        return signals

    # ═══════════════════════════════════════════════════
    # الرأس والكتفين المقلوب (Inverse H&S)
    # ═══════════════════════════════════════════════════

    def _detect_inverse_head_shoulders(self, candles: list[dict]) -> list[PatternSignal]:
        """
        الرأس والكتفين المقلوب = 3 قيعان — الأوسط الأدنى (الرأس) والطرفان أعلى
        
        التأكيد: كسر خط العنق للأعلى
        الإشارة: CALL
        """
        signals = []
        closes = [c["close"] for c in candles]

        lookback = min(60, len(candles))
        window = candles[-lookback:]

        troughs = self._find_troughs(window, strength=3)

        for i in range(len(troughs) - 2):
            left = troughs[i]
            head = troughs[i + 1]
            right = troughs[i + 2]

            # الرأس أدنى من الكتفين
            if not (head["level"] < left["level"] and head["level"] < right["level"]):
                continue

            avg_shoulder = (left["level"] + right["level"]) / 2
            if avg_shoulder == 0:
                continue
            if abs(left["level"] - right["level"]) / avg_shoulder > 0.02:
                continue

            if head["index"] - left["index"] < 3 or right["index"] - head["index"] < 3:
                continue

            peak_between_lh = [
                c["high"] for c in window[left["index"]:head["index"] + 1]
            ]
            peak_between_hr = [
                c["high"] for c in window[head["index"]:right["index"] + 1]
            ]

            if not peak_between_lh or not peak_between_hr:
                continue

            neckline_left = max(peak_between_lh)
            neckline_right = max(peak_between_hr)
            neckline = (neckline_left + neckline_right) / 2

            current_price = closes[-1]

            if current_price > neckline:
                pattern_height = neckline - head["level"]
                target = neckline + pattern_height

                signals.append(PatternSignal(
                    pattern_type=PatternType.INVERSE_HEAD_SHOULDERS,
                    category=PatternCategory.REVERSAL,
                    direction="call",
                    entry_price=current_price,
                    stop_loss=neckline * 0.995,
                    target_price=target,
                    confidence=0.75,
                    neckline=neckline,
                    breakout_price=neckline,
                    description=f"رأس وكتفين مقلوب — كسر خط العنق {neckline:.1f}",
                ))

        return signals

    # ═══════════════════════════════════════════════════
    # الأعلام (Flags)
    # ═══════════════════════════════════════════════════

    def _detect_flags(self, candles: list[dict]) -> list[PatternSignal]:
        """
        الأعلام = حركة حادة (سارية) + تصحيح في قناة ضيقة متوازية
        
        - علم صاعد (Bull Flag): سارية صاعدة + قناة هابطة ضيقة
        - علم هابط (Bear Flag): سارية هابطة + قناة صاعدة ضيقة
        
        التأكيد: كسر حدود القناة مع اتجاه السارية
        """
        signals = []
        closes = [c["close"] for c in candles]
        lookback = min(40, len(candles))
        window = candles[-lookback:]

        # نقسم النافذة إلى نصفين: النصف الأول = السارية، النصف الثاني = العلم
        mid = len(window) // 2
        pole = window[:mid]
        flag = window[mid:]

        if len(pole) < 5 or len(flag) < 4:
            return signals

        pole_start = pole[0]["close"]
        pole_end = pole[-1]["close"]
        pole_move = abs(pole_end - pole_start) / abs(pole_start) if pole_start else 0

        # السارية يجب أن تكون قوية (>1.5% حركة)
        if pole_move < 0.015:
            return signals

        flag_highs = [c["high"] for c in flag]
        flag_lows = [c["low"] for c in flag]
        flag_range = max(flag_highs) - min(flag_lows)

        # العلم يجب أن يكون ضيق (<50% من السارية)
        pole_range = max(p["high"] for p in pole) - min(p["low"] for p in pole)
        if pole_range == 0:
            return signals
        if flag_range / pole_range > 0.5:
            return signals

        current_price = closes[-1]

        # علم صاعد (Bull Flag)
        if pole_end > pole_start:  # سارية صاعدة
            flag_trend = self._linear_regression_slope(
                [f["close"] for f in flag]
            )
            if flag_trend < -0.001:  # العلم هابط (تصحيح)
                # الكسر للأعلى
                flag_resistance = max(flag_highs)
                if current_price > flag_resistance:
                    target = flag_resistance + (pole_end - pole_start)
                    signals.append(PatternSignal(
                        pattern_type=PatternType.BULL_FLAG,
                        category=PatternCategory.CONTINUATION,
                        direction="call",
                        entry_price=current_price,
                        stop_loss=min(flag_lows) * 0.998,
                        target_price=target,
                        confidence=0.65,
                        description=f"علم صاعد — استمرار الصعود بعد التصحيح",
                    ))

        # علم هابط (Bear Flag)
        elif pole_end < pole_start:  # سارية هابطة
            flag_trend = self._linear_regression_slope(
                [f["close"] for f in flag]
            )
            if flag_trend > 0.001:  # العلم صاعد (تصحيح)
                flag_support = min(flag_lows)
                if current_price < flag_support:
                    target = flag_support - abs(pole_end - pole_start)
                    signals.append(PatternSignal(
                        pattern_type=PatternType.BEAR_FLAG,
                        category=PatternCategory.CONTINUATION,
                        direction="put",
                        entry_price=current_price,
                        stop_loss=max(flag_highs) * 1.002,
                        target_price=target,
                        confidence=0.65,
                        description=f"علم هابط — استمرار الهبوط بعد التصحيح",
                    ))

        return signals

    # ═══════════════════════════════════════════════════
    # الرايات (Pennants)
    # ═══════════════════════════════════════════════════

    def _detect_pennants(self, candles: list[dict]) -> list[PatternSignal]:
        """
        الرايات = حركة حادة + مثلث صغير متقارب (تجميع)
        
        الفرق عن العلم: الراية تتقارب (تضيق) بشكل مثلث، العلم قناة متوازية
        """
        signals = []
        closes = [c["close"] for c in candles]
        lookback = min(40, len(candles))
        window = candles[-lookback:]

        mid = len(window) // 2
        pole = window[:mid]
        pennant = window[mid:]

        if len(pole) < 5 or len(pennant) < 4:
            return signals

        pole_start = pole[0]["close"]
        pole_end = pole[-1]["close"]
        pole_move = abs(pole_end - pole_start) / abs(pole_start) if pole_start else 0

        if pole_move < 0.015:
            return signals

        # الراية: النطاق يضيق مع الوقت
        first_half_range = max(
            p["high"] for p in pennant[:len(pennant)//2]
        ) - min(p["low"] for p in pennant[:len(pennant)//2])
        second_half_range = max(
            p["high"] for p in pennant[len(pennant)//2:]
        ) - min(p["low"] for p in pennant[len(pennant)//2:])

        # التأكد من أن النطاق يضيق
        if first_half_range == 0:
            return signals
        if second_half_range / first_half_range > 0.8:  # ما ضاق بشكل كافي
            return signals

        current_price = closes[-1]
        pennant_high = max(p["high"] for p in pennant)
        pennant_low = min(p["low"] for p in pennant)

        # راية صاعدة
        if pole_end > pole_start:
            if current_price > pennant_high:
                target = pennant_high + (pole_end - pole_start)
                signals.append(PatternSignal(
                    pattern_type=PatternType.BULL_PENNANT,
                    category=PatternCategory.CONTINUATION,
                    direction="call",
                    entry_price=current_price,
                    stop_loss=pennant_low * 0.998,
                    target_price=target,
                    confidence=0.65,
                    description="راية صاعدة — استمرار الصعود",
                ))

        # راية هابطة
        elif pole_end < pole_start:
            if current_price < pennant_low:
                target = pennant_low - abs(pole_end - pole_start)
                signals.append(PatternSignal(
                    pattern_type=PatternType.BEAR_PENNANT,
                    category=PatternCategory.CONTINUATION,
                    direction="put",
                    entry_price=current_price,
                    stop_loss=pennant_high * 1.002,
                    target_price=target,
                    confidence=0.65,
                    description="راية هابطة — استمرار الهبوط",
                ))

        return signals

    # ═══════════════════════════════════════════════════
    # المثلثات (Triangles)
    # ═══════════════════════════════════════════════════

    def _detect_triangles(self, candles: list[dict]) -> list[PatternSignal]:
        """
        المثلثات:
        - صاعد (Ascending): قمم متساوية + قيعان صاعدة
        - هابط (Descending): قيعان متساوية + قمم هابطة
        - متماثل (Symmetrical): قمم هابطة + قيعان صاعدة
        """
        signals = []
        closes = [c["close"] for c in candles]
        lookback = min(50, len(candles))
        window = candles[-lookback:]

        highs = [c["high"] for c in window]
        lows = [c["low"] for c in window]

        peaks = self._find_peaks(window, strength=3)
        troughs = self._find_troughs(window, strength=3)

        if len(peaks) < 2 or len(troughs) < 2:
            return signals

        peak_levels = [p["level"] for p in peaks[-4:]]
        trough_levels = [t["level"] for t in troughs[-4:]]

        peak_slope = self._linear_regression_slope(peak_levels) if len(peak_levels) >= 2 else 0
        trough_slope = self._linear_regression_slope(trough_levels) if len(trough_levels) >= 2 else 0

        # حساب نطاق المثلث
        tri_range = max(highs[-10:]) - min(lows[-10:])

        current_price = closes[-1]

        # ── مثلث صاعد: قمم مسطحة + قيعان صاعدة ──
        if abs(peak_slope) < 0.002 and trough_slope > 0.002:
            resistance = max(peak_levels)
            if current_price > resistance:
                target = resistance + tri_range
                signals.append(PatternSignal(
                    pattern_type=PatternType.ASCENDING_TRIANGLE,
                    category=PatternCategory.CONTINUATION,
                    direction="call",
                    entry_price=current_price,
                    stop_loss=min(trough_levels) * 0.998,
                    target_price=target,
                    confidence=0.7,
                    breakout_price=resistance,
                    description=f"مثلث صاعد — كسر المقاومة {resistance:.1f}",
                ))

        # ── مثلث هابط: قيعان مسطحة + قمم هابطة ──
        if abs(trough_slope) < 0.002 and peak_slope < -0.002:
            support = min(trough_levels)
            if current_price < support:
                target = support - tri_range
                signals.append(PatternSignal(
                    pattern_type=PatternType.DESCENDING_TRIANGLE,
                    category=PatternCategory.CONTINUATION,
                    direction="put",
                    entry_price=current_price,
                    stop_loss=max(peak_levels) * 1.002,
                    target_price=target,
                    confidence=0.7,
                    breakout_price=support,
                    description=f"مثلث هابط — كسر الدعم {support:.1f}",
                ))

        # ── مثلث متماثل: قمم هابطة + قيعان صاعدة ──
        if peak_slope < -0.002 and trough_slope > 0.002:
            # الكسر يحدد الاتجاه
            peak_line = max(peak_levels) + peak_slope * len(window)
            trough_line = min(trough_levels) + trough_slope * len(window)

            if current_price > peak_line:  # كسر للأعلى
                target = peak_line + tri_range
                signals.append(PatternSignal(
                    pattern_type=PatternType.SYMMETRICAL_TRIANGLE,
                    category=PatternCategory.CONTINUATION,
                    direction="call",
                    entry_price=current_price,
                    stop_loss=trough_line * 0.998,
                    target_price=target,
                    confidence=0.6,
                    breakout_price=peak_line,
                    description=f"مثلث متماثل — كسر للأعلى",
                ))
            elif current_price < trough_line:  # كسر للأسفل
                target = trough_line - tri_range
                signals.append(PatternSignal(
                    pattern_type=PatternType.SYMMETRICAL_TRIANGLE,
                    category=PatternCategory.CONTINUATION,
                    direction="put",
                    entry_price=current_price,
                    stop_loss=peak_line * 1.002,
                    target_price=target,
                    confidence=0.6,
                    breakout_price=trough_line,
                    description=f"مثلث متماثل — كسر للأسفل",
                ))

        return signals

    # ═══════════════════════════════════════════════════
    # أدوات مساعدة
    # ═══════════════════════════════════════════════════

    def _find_peaks(self, candles: list[dict], strength: int = 3) -> list[dict]:
        """البحث عن القمم في سلسلة شموع"""
        peaks = []
        for i in range(strength, len(candles) - strength):
            c = candles[i]
            is_peak = all(
                c["high"] >= candles[i - j]["high"]
                and c["high"] >= candles[i + j]["high"]
                for j in range(1, strength + 1)
            )
            if is_peak:
                peaks.append({"index": i, "level": c["high"]})
        return peaks

    def _find_troughs(self, candles: list[dict], strength: int = 3) -> list[dict]:
        """البحث عن القيعان في سلسلة شموع"""
        troughs = []
        for i in range(strength, len(candles) - strength):
            c = candles[i]
            is_trough = all(
                c["low"] <= candles[i - j]["low"]
                and c["low"] <= candles[i + j]["low"]
                for j in range(1, strength + 1)
            )
            if is_trough:
                troughs.append({"index": i, "level": c["low"]})
        return troughs

    @staticmethod
    def _linear_regression_slope(y_values: list[float]) -> float:
        """حساب ميل الانحدار الخطي"""
        n = len(y_values)
        if n < 2:
            return 0.0

        x_values = list(range(n))
        mean_x = sum(x_values) / n
        mean_y = sum(y_values) / n

        numerator = sum(
            (x_values[i] - mean_x) * (y_values[i] - mean_y)
            for i in range(n)
        )
        denominator = sum((x - mean_x) ** 2 for x in x_values)

        if denominator == 0:
            return 0.0

        return numerator / denominator
