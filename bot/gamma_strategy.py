"""
إستراتيجية أبو فهد قاما (GAMMA) 🚎
═══════════════════════════════════════
منهجية تداول كاملة مبنية على:
  ١. أبراج القاما — سيولة الصانع (أحمر > أصفر > أزرق > أبيض)
  ٢. مناطق العرض والطلب متعددة الأطر الزمنية
  ٣. الشموع البالعة والابتلاعية
  ٤. استعارة الباص — محطات النقل 🚎

المصدر: وثيقة شرح استراتيجية أبو فهد قاما — مايو 2026
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum
import math


# ═══════════════════════════════════════════════════════════
# Enums & Types
# ═══════════════════════════════════════════════════════════

class TowerStrength(str, Enum):
    RED = "red"       # 🔴 أقوى برج — سيولة الصانع الرئيسية
    YELLOW = "yellow" # 🟡 برج قوي
    BLUE = "blue"     # 🔵 متوسط
    WHITE = "white"   # ⚪ مضاربي لحظي (أضعف)


class ZoneType(str, Enum):
    DEMAND = "demand"   # 🟢 طلب
    SUPPLY = "supply"   # 🔴 عرض


class ZoneTimeframe(str, Enum):
    HOURLY = "hourly"       # 🟢🔴 منطقة ساعة
    DAILY = "daily"         # 🔵 يومية
    WEEKLY = "weekly"       # 🟡 أسبوعية
    MONTHLY = "monthly"     # 🟣 شهرية


class Direction(str, Enum):
    CALL = "call"
    PUT = "put"


class CandleBody(str, Enum):
    BULLISH = "bullish"     # 🟢 شمعة خضراء
    BEARISH = "bearish"     # 🔴 شمعة حمراء


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class GammaTower:
    """برج قاما — نقطة سيولة للصانع"""
    price: float
    strength: TowerStrength
    has_bus: bool = False  # 🚎 عليه علامة باص = محطة نقل ركاب
    description: str = ""


@dataclass
class SupplyDemandZone:
    """منطقة عرض أو طلب"""
    top: float        # الحد العلوي
    bottom: float     # الحد السفلي
    zone_type: ZoneType
    timeframe: ZoneTimeframe
    is_confirmed: bool = False  # تم كسرها/اختراقها → مؤكدة
    is_broken: bool = False     # ملغية = تم حذفها من الشارت


@dataclass
class CandleSignal:
    """إشارة شمعة"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    body: CandleBody
    is_engulfing: bool = False        # شمعة بالعة
    belly_sucked: bool = False        # شفط البطن (body at extreme)
    timeframe: str = "5m"             # 5m / 15m / 1h


@dataclass
class GammaEntry:
    """نقطة دخول وفق استراتيجية القاما"""
    direction: Direction
    entry_price: float
    tower: GammaTower          # البرج اللي دخلنا منه
    stop_loss: float           # الوقف = نفس البرج
    target_pct: float = 30.0   # الهدف 30%
    target_price: float = 0.0
    reason: str = ""           # سبب الدخول
    require_flip: bool = True  # نعكس الصفقة إذا ضرب الوقف؟
    max_candles_sideways: int = 2  # أقصى شمعتين عرضية قبل الخروج


@dataclass
class GammaAnalysis:
    """التحليل الكامل للاستراتيجية"""
    symbol: str
    current_price: float
    towers: list[GammaTower] = field(default_factory=list)
    zones: list[SupplyDemandZone] = field(default_factory=list)
    last_candle_5m: Optional[CandleSignal] = None
    last_candle_15m: Optional[CandleSignal] = None
    nearest_tower_above: Optional[GammaTower] = None
    nearest_tower_below: Optional[GammaTower] = None
    trend_daily: Optional[Direction] = None
    trend_hourly: Optional[Direction] = None
    entry: Optional[GammaEntry] = None
    notes: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# Constants — من الوثيقة
# ═══════════════════════════════════════════════════════════

# ألوان المناطق حسب الفريم
TIMEFRAME_COLORS = {
    ZoneTimeframe.HOURLY: ("🟢", "🔴"),   # طلب / عرض
    ZoneTimeframe.DAILY: ("🔵", "🔵"),
    ZoneTimeframe.WEEKLY: ("🟡", "🟡"),
    ZoneTimeframe.MONTHLY: ("🟣", "🟣"),
}

# أفضل شركات للمضاربة حسب أبو فهد
PREFERRED_SYMBOLS = ["QQQ", "LLY", "CRWD", "COST", "ASML", "MDB"]

# أوقات التداول الرئيسية (EST)
GOLDEN_HOUR_START = 15  # 3 PM — الساعة الذهبية
MARKET_CLOSE = 16       # 4 PM
OPENING_HOUR = 9.5      # 9:30 AM
MID_SESSION = 13.5       # 1:30 PM

# الشمعة البالعة — لا تعاكسها إلا بعد تجاوزها
# (من فريم ربع ساعة وفوق)


# ═══════════════════════════════════════════════════════════
# GammaStrategy — المحرك الرئيسي
# ═══════════════════════════════════════════════════════════

class GammaStrategy:
    """
    استراتيجية أبو فهد قاما — المحرك الكامل 🚎

    ### القواعد الصارمة:
    1. صفقة واحدة باليوم — حقق التارقت وأغلق الشاشة
    2. تمش مع الصانع — لا تعاكس السوق
    3. دخول من باص (برج عليه علامة 🚎) فقط
    4. ربح 30% ثم بيع (أو ارفع الوقف)
    5. الوقف = نفس البرج اللي شريت منه
    6. إذا عاكس وكسر البرج → اعكس الصفقة (Flip)
    7. لا تدخل بدون سبب (كسر/اختراق برج أو منطقة)
    8. فريم 15 دقيقة للاتجاه، 5 دقائق للدخول
    """

    def __init__(
        self,
        symbol: str = "QQQ",
        target_profit_pct: float = 30.0,
        max_daily_trades: int = 1,
    ):
        self.symbol = symbol
        self.target_profit_pct = target_profit_pct
        self.max_daily_trades = max_daily_trades

    # ── الخطوة 1: تحليل الأبراج ──

    def detect_towers(
        self,
        price_data: dict,
        volume_profile: Optional[dict] = None,
    ) -> list[GammaTower]:
        """
        اكتشاف أبراج القاما من بيانات السعر

        الأبراج = نقاط سيولة عالية (Volume Nodes)
        الترتيب: أحمر (أقوى) > أصفر > أزرق > أبيض

        في التطبيق الحقيقي: تحتاج GAMMA indicator مخصص
        هنا نستخدم Volume Profile + Swing Points كبديل
        """
        towers = []
        if not price_data:
            return towers

        high = price_data.get("high", 0)
        low = price_data.get("low", 0)
        close = price_data.get("close", 0)

        if high == 0 or low == 0:
            return towers

        price_range = high - low

        # استخراج نقاط التأرجح (swing points)
        swings = price_data.get("swing_points", [])
        volume_nodes = volume_profile.get("nodes", []) if volume_profile else []

        # دمج النقاط مع ترتيب القوة
        all_levels = []

        # عقدة الحجم الأعلى = الأحمر (الأقوى)
        if volume_nodes:
            sorted_nodes = sorted(volume_nodes, key=lambda x: x.get("volume", 0), reverse=True)
            for i, node in enumerate(sorted_nodes[:4]):
                strength = (
                    TowerStrength.RED if i == 0
                    else TowerStrength.YELLOW if i == 1
                    else TowerStrength.BLUE if i == 2
                    else TowerStrength.WHITE
                )
                all_levels.append((node["price"], strength))

        # نقاط التأرجح
        for i, swing in enumerate(swings[:8]):
            all_levels.append((swing, TowerStrength.WHITE if i > 2 else TowerStrength.BLUE))

        # إزالة التكرار وتجميع
        seen = set()
        for price, strength in sorted(all_levels, key=lambda x: x[0]):
            rounded = round(price, 2)
            if rounded not in seen:
                seen.add(rounded)
                has_bus = strength in (TowerStrength.RED, TowerStrength.YELLOW)
                towers.append(GammaTower(
                    price=rounded,
                    strength=strength,
                    has_bus=has_bus,
                    description=f"برج {strength.value}"
                ))

        return sorted(towers, key=lambda t: t.price)

    # ── الخطوة 2: تحليل المناطق ──

    def detect_zones(
        self,
        price_data: dict,
        timeframe: ZoneTimeframe,
    ) -> list[SupplyDemandZone]:
        """
        اكتشاف مناطق العرض والطلب حسب الإطار الزمني
        """
        zones = []
        if not price_data:
            return zones

        # مناطق محددة مسبقاً (من التحليل اليدوي)
        predefined = price_data.get("zones", [])
        for z in predefined:
            zones.append(SupplyDemandZone(
                top=z.get("top", 0),
                bottom=z.get("bottom", 0),
                zone_type=ZoneType(z.get("type", "demand")),
                timeframe=timeframe,
                is_confirmed=z.get("confirmed", False),
                is_broken=z.get("broken", False),
            ))

        return zones

    # ── الخطوة 3: تحليل الشموع ──

    def analyze_candle(self, candle: dict, timeframe: str = "5m") -> CandleSignal:
        """
        تحليل شمعة واحدة — هل هي بالعة؟ شفط البطن؟
        """
        o = candle.get("open", 0)
        h = candle.get("high", 0)
        l = candle.get("low", 0)
        c = candle.get("close", 0)

        body = CandleBody.BULLISH if c >= o else CandleBody.BEARISH
        body_size = abs(c - o)
        total_range = h - l if h != l else 0.01

        # شمعة بالعة: جسمها > 60% من المدى الكلي
        is_engulfing = body_size / total_range > 0.6 if total_range > 0 else False

        # شفط البطن: الجسم عند أقصى الشمعة
        if body == CandleBody.BULLISH:
            belly_sucked = (c - l) / total_range > 0.85 if total_range > 0 else False
        else:
            belly_sucked = (h - c) / total_range > 0.85 if total_range > 0 else False

        return CandleSignal(
            timestamp=candle.get("timestamp", 0),
            open=o, high=h, low=l, close=c,
            body=body,
            is_engulfing=is_engulfing,
            belly_sucked=belly_sucked,
            timeframe=timeframe,
        )

    # ── الخطوة 4: تحديد أقرب الأبراج ──

    def find_nearest_towers(
        self,
        price: float,
        towers: list[GammaTower],
    ) -> tuple[Optional[GammaTower], Optional[GammaTower]]:
        """أقرب برج فوق وأقرب برج تحت"""
        above = None
        below = None

        sorted_towers = sorted(towers, key=lambda t: t.price)

        for t in sorted_towers:
            if t.price > price and (above is None or t.price < above.price):
                above = t
            if t.price < price and (below is None or t.price > below.price):
                below = t

        return above, below

    # ── الخطوة 5: شروط الدخول CALL ──

    def check_call_entry(
        self,
        analysis: GammaAnalysis,
        candle_5m: CandleSignal,
    ) -> Optional[GammaEntry]:
        """التحقق من شروط دخول CALL الأربعة"""

        price = analysis.current_price
        reasons = []

        # الشرط 1: فتحت شمعة خضراء فوق برج (غير ملامسة)
        if candle_5m.body == CandleBody.BULLISH:
            tower_below = analysis.nearest_tower_below
            if tower_below and candle_5m.low > tower_below.price:
                reasons.append(f"✅ شمعة خضراء فوق برج {tower_below.strength.value}")

        # الشرط 2: ارتداد من منطقة طلب + شمعة خضراء ثانية
        for zone in analysis.zones:
            if zone.zone_type == ZoneType.DEMAND and not zone.is_broken:
                if zone.bottom <= price <= zone.top:
                    reasons.append(f"✅ ارتداد من منطقة طلب {zone.timeframe.value}")

        # الشرط 3: تجاوز برج بشمعة خضراء كاملة
        if candle_5m.body == CandleBody.BULLISH and candle_5m.is_engulfing:
            tower_above = analysis.nearest_tower_above
            if tower_above and candle_5m.close > tower_above.price:
                reasons.append(f"✅ اختراق برج {tower_above.strength.value} بشمعة بالعة")

        # الشرط 4: اختراق ترند القاما
        if (analysis.trend_hourly == Direction.PUT and
            candle_5m.body == CandleBody.BULLISH and
            candle_5m.is_engulfing):
            reasons.append("✅ اختراق ترند القاما الهابط")

        if not reasons:
            return None

        # تحديد البرج للدخول والوقف
        entry_tower = analysis.nearest_tower_below or analysis.nearest_tower_above
        if not entry_tower:
            return None

        target_price = price * (1 + self.target_profit_pct / 100)

        return GammaEntry(
            direction=Direction.CALL,
            entry_price=price,
            tower=entry_tower,
            stop_loss=entry_tower.price,
            target_pct=self.target_profit_pct,
            target_price=target_price,
            reason=" | ".join(reasons),
        )

    # ── الخطوة 6: شروط الدخول PUT ──

    def check_put_entry(
        self,
        analysis: GammaAnalysis,
        candle_5m: CandleSignal,
    ) -> Optional[GammaEntry]:
        """التحقق من شروط دخول PUT الأربعة"""

        price = analysis.current_price
        reasons = []

        # الشرط 1: فتحت شمعة حمراء تحت برج (غير ملامسة)
        if candle_5m.body == CandleBody.BEARISH:
            tower_above = analysis.nearest_tower_above
            if tower_above and candle_5m.high < tower_above.price:
                reasons.append(f"✅ شمعة حمراء تحت برج {tower_above.strength.value}")

        # الشرط 2: ارتداد من منطقة عرض + شمعة حمراء ثانية
        for zone in analysis.zones:
            if zone.zone_type == ZoneType.SUPPLY and not zone.is_broken:
                if zone.bottom <= price <= zone.top:
                    reasons.append(f"✅ ارتداد من منطقة عرض {zone.timeframe.value}")

        # الشرط 3: كسر برج بشمعة حمراء كاملة
        if candle_5m.body == CandleBody.BEARISH and candle_5m.is_engulfing:
            tower_below = analysis.nearest_tower_below
            if tower_below and candle_5m.close < tower_below.price:
                reasons.append(f"✅ كسر برج {tower_below.strength.value} بشمعة بالعة")

        # الشرط 4: كسر ترند القاما
        if (analysis.trend_hourly == Direction.CALL and
            candle_5m.body == CandleBody.BEARISH and
            candle_5m.is_engulfing):
            reasons.append("✅ كسر ترند القاما الصاعد")

        if not reasons:
            return None

        entry_tower = analysis.nearest_tower_above or analysis.nearest_tower_below
        if not entry_tower:
            return None

        target_price = price * (1 - self.target_profit_pct / 100)

        return GammaEntry(
            direction=Direction.PUT,
            entry_price=price,
            tower=entry_tower,
            stop_loss=entry_tower.price,
            target_pct=self.target_profit_pct,
            target_price=target_price,
            reason=" | ".join(reasons),
        )

    # ── الخطوة 7: فحص Flip (عكس الصفقة) ──

    def should_flip(
        self,
        current_entry: GammaEntry,
        current_price: float,
        candle_5m: CandleSignal,
    ) -> Optional[GammaEntry]:
        """هل نعكس الصفقة؟ (Flip — إذا كسر الوقف)"""

        if current_entry.direction == Direction.CALL:
            # وقف الكول = تحت البرج → إذا فتحت شمعة حمراء تحت البرج → flip to PUT
            if (candle_5m.body == CandleBody.BEARISH and
                candle_5m.close < current_entry.stop_loss):
                return GammaEntry(
                    direction=Direction.PUT,
                    entry_price=current_price,
                    tower=current_entry.tower,
                    stop_loss=current_entry.tower.price,
                    target_pct=self.target_profit_pct,
                    target_price=current_price * (1 - self.target_profit_pct / 100),
                    reason="🔄 Flip: كسر وقف الكول → دخول PUT",
                )

        else:  # PUT
            # وقف البوت = فوق البرج → إذا فتحت شمعة خضراء فوق البرج → flip to CALL
            if (candle_5m.body == CandleBody.BULLISH and
                candle_5m.close > current_entry.stop_loss):
                return GammaEntry(
                    direction=Direction.CALL,
                    entry_price=current_price,
                    tower=current_entry.tower,
                    stop_loss=current_entry.tower.price,
                    target_pct=self.target_profit_pct,
                    target_price=current_price * (1 + self.target_profit_pct / 100),
                    reason="🔄 Flip: كسر وقف البوت → دخول CALL",
                )

        return None

    # ── الخطوة 8: التحليل الكامل ──

    def analyze(
        self,
        price_data: dict,
        candles_5m: list[dict],
        candles_15m: list[dict],
        volume_profile: Optional[dict] = None,
    ) -> GammaAnalysis:
        """
        التحليل الكامل — يحدد:
        - الأبراج والمناطق
        - الاتجاه اليومي والساعي
        - نقطة الدخول (إن وجدت)
        """

        current_price = price_data.get("close", price_data.get("price", 0))

        analysis = GammaAnalysis(
            symbol=self.symbol,
            current_price=current_price,
        )

        # 1. اكتشاف الأبراج
        analysis.towers = self.detect_towers(price_data, volume_profile)

        # 2. أقرب الأبراج
        analysis.nearest_tower_above, analysis.nearest_tower_below = \
            self.find_nearest_towers(current_price, analysis.towers)

        # 3. المناطق — كل فريم
        for tf in ZoneTimeframe:
            zones = self.detect_zones(price_data, tf)
            analysis.zones.extend(zones)

        # 4. تحليل الشموع
        if candles_5m:
            analysis.last_candle_5m = self.analyze_candle(candles_5m[-1], "5m")

        if candles_15m:
            analysis.last_candle_15m = self.analyze_candle(candles_15m[-1], "15m")

        # 5. تحديد الاتجاه من شمعة 15 دقيقة
        if analysis.last_candle_15m:
            if analysis.last_candle_15m.body == CandleBody.BULLISH and analysis.last_candle_15m.belly_sucked:
                analysis.trend_hourly = Direction.CALL
            elif analysis.last_candle_15m.body == CandleBody.BEARISH and analysis.last_candle_15m.belly_sucked:
                analysis.trend_hourly = Direction.PUT

        # 6. الاتجاه اليومي من السعر بالنسبة لـ MA200 (تقريبي)
        ma200 = price_data.get("ma200", 0)
        if ma200 > 0:
            analysis.trend_daily = Direction.CALL if current_price > ma200 else Direction.PUT

        # 7. البحث عن دخول
        if analysis.last_candle_5m:
            call_entry = self.check_call_entry(analysis, analysis.last_candle_5m)
            put_entry = self.check_put_entry(analysis, analysis.last_candle_5m)

            # الأولوية للاتجاه الأقوى
            if call_entry and put_entry:
                if analysis.trend_hourly == Direction.CALL:
                    analysis.entry = call_entry
                elif analysis.trend_hourly == Direction.PUT:
                    analysis.entry = put_entry
                else:
                    # الأقرب للبرج هو الأفضل
                    analysis.entry = call_entry  # تفضيل الكول (رضا الوالدين)
            elif call_entry:
                analysis.entry = call_entry
            elif put_entry:
                analysis.entry = put_entry

        # 8. ملاحظات
        if analysis.entry:
            analysis.notes.append(f"🚎 دخول {analysis.entry.direction.value.upper()} من برج {analysis.entry.tower.strength.value}")
            analysis.notes.append(f"🛑 الوقف: ${analysis.entry.stop_loss:.2f}")
            analysis.notes.append(f"🎯 الهدف: ${analysis.entry.target_price:.2f} (+{analysis.entry.target_pct}%)")
            analysis.notes.append(f"📋 السبب: {analysis.entry.reason}")

        return analysis

    # ── عقد رضا الوالدين (Parents' Blessing Contract) ──

    def parents_blessing_contract(
        self,
        towers: list[GammaTower],
        current_price: float,
        expiry_days: int = 2,
    ) -> dict:
        """
        عقد رضا الوالدين:
        - عقد CALL دائماً
        - عند أعمق برج قاع (تحت)
        - نصف سعر العقد (Limit Order)
        - مدة يومين على الأقل
        """
        # أعمق برج تحت السعر
        deep_tower = None
        for t in sorted(towers, key=lambda t: t.price):
            if t.price < current_price and t.strength in (TowerStrength.RED, TowerStrength.YELLOW):
                deep_tower = t

        if not deep_tower:
            # خذ أعمق برج متاح
            below = [t for t in towers if t.price < current_price]
            deep_tower = below[-1] if below else None

        if not deep_tower:
            return {"error": "لا توجد أبراج تحت السعر"}

        return {
            "type": "CALL",
            "strike": deep_tower.price,
            "limit_price_pct": 50,  # نصف السعر
            "expiry_days": max(expiry_days, 2),
            "tower": deep_tower,
            "note": "عقد رضا الوالدين — CALL من القاع 🕌",
        }

    # ── توليد ملخص ──

    def summary(self, analysis: GammaAnalysis) -> str:
        """توليد ملخص عربي للتحليل"""
        lines = [
            f"## 📊 تحليل قاما — {analysis.symbol}",
            f"السعر الحالي: **${analysis.current_price:.2f}**",
            "",
            "### 🗼 الأبراج القريبة:",
        ]

        if analysis.nearest_tower_above:
            t = analysis.nearest_tower_above
            bus = "🚎" if t.has_bus else ""
            lines.append(f"- فوق: ${t.price:.2f} ({t.strength.value}) {bus}")
        if analysis.nearest_tower_below:
            t = analysis.nearest_tower_below
            bus = "🚎" if t.has_bus else ""
            lines.append(f"- تحت: ${t.price:.2f} ({t.strength.value}) {bus}")

        if analysis.entry:
            lines.append("")
            lines.append(f"### {'🟢' if analysis.entry.direction == Direction.CALL else '🔴'} إشارة دخول:")
            lines.append(f"- **{analysis.entry.direction.value.upper()}** عند ${analysis.entry.entry_price:.2f}")
            lines.append(f"- 🛑 وقف: ${analysis.entry.stop_loss:.2f}")
            lines.append(f"- 🎯 هدف: ${analysis.entry.target_price:.2f} (+{analysis.entry.target_pct}%)")
        else:
            lines.append("")
            lines.append("⏳ لا توجد إشارة دخول حالياً")

        return "\n".join(lines)
