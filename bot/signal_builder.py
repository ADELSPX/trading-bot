"""
مولد الإشارات الذكي — Signal Builder
═══════════════════════════════════════
يحوّل تحليل البوت إلى إشارة جاهزة للتنفيذ

الميزات:
  ١. توليد رمز العقد كامل (SPXW + تاريخ + Strike)
  ٢. منطقة دخول (Range) + هدفين
  ٣. متابعة الصفقة (Entry → Target1 → Target2)
"""

from __future__ import annotations
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Literal
import json, math


@dataclass
class ContractSpec:
    """مواصفات العقد"""
    symbol: str          # SPX
    strike: float        # 7590
    direction: str       # CALL / PUT
    expiry: str          # 260526 (YYMMDD)
    full_symbol: str     # SPXW 260526 C 7590
    weekly: bool = True
    reason: str = ""


@dataclass
class TradeSignal:
    """إشارة تداول كاملة"""
    # العقد
    contract: ContractSpec

    # منطقة الدخول
    entry_zone_low: float
    entry_zone_high: float

    # الوقف
    stop_loss: float

    # هدفين
    target1: float        # هدف أول (جزئي)
    target2: float        # هدف ثاني (كامل)

    # نوع الدخول
    entry_type: str       # breakout / retest

    # الثقة
    confidence: float     # 0.0-1.0
    confidence_label: str # عالية / متوسطة / منخفضة

    # التصنيف
    trade_type: str       # مضاربة سريعة / سوينق / يومي

    # متابعة
    current_stage: str = "pending"  # pending / active / target1_hit / target2_hit / stopped / closed

    # ميتاداتا
    generated_at: str = ""
    reason: str = ""
    note: str = "للتحليل فقط — ليست توصية مالية"


@dataclass
class Position:
    """صفقة نشطة للمتابعة"""
    signal: TradeSignal
    entry_price: float = 0.0       # سعر العقد عند الدخول
    current_price: float = 0.0     # سعر العقد الحالي
    pnl: float = 0.0
    pnl_pct: float = 0.0
    entered_at: str = ""
    contract_price: float = 0.0     # سعر العقد الفعلي


class SignalBuilder:
    """مولد الإشارات الذكي"""

    # أيام الأسبوع للعقود الأسبوعية SPXW
    WEEKLY_EXPIRY_DAYS = [1, 3, 5]  # اثنين / أربعاء / جمعة

    def __init__(self):
        pass

    # ═══════════════════════════════════════
    # ١. توليد العقد
    # ═══════════════════════════════════════

    def generate_contract(
        self,
        symbol: str = "SPX",
        current_price: float = 0.0,
        direction: str = "CALL",
        strike_offset_pct: float = 1.0,
        weekly: bool = True,
    ) -> ContractSpec:
        """
        توليد رمز العقد كامل

        Args:
            direction: CALL / PUT
            strike_offset_pct: كم % فوق/تحت السعر الحالي
            weekly: True = SPXW أسبوعي | False = SPX شهري
        """
        direction = direction.upper()
        strike = self._round_strike(current_price, direction, strike_offset_pct)
        expiry = self._next_weekly_expiry() if weekly else self._next_monthly_expiry()

        prefix = "SPXW" if weekly else "SPX"
        option_code = "C" if direction == "CALL" else "P"
        full = f"{prefix} {expiry} {option_code} {strike}"

        return ContractSpec(
            symbol=symbol,
            strike=strike,
            direction=direction,
            expiry=expiry,
            full_symbol=full,
            weekly=weekly,
            reason=f"Strike عند {strike} ({'+' if direction=='CALL' else '-'}{strike_offset_pct}% من السعر)"
        )

    def _round_strike(self, price: float, direction: str, offset_pct: float) -> int:
        """تدوير الـ Strike لأقرب 5 نقاط"""
        if direction == "CALL":
            raw = price * (1 + offset_pct / 100)
        else:
            raw = price * (1 - offset_pct / 100)
        return round(raw / 5) * 5

    def _next_weekly_expiry(self, from_date: datetime = None) -> str:
        """أقرب تاريخ انتهاء أسبوعي (اثنين/أربعاء/جمعة)"""
        if from_date is None:
            from_date = datetime.now()

        d = from_date
        for _ in range(7):
            if d.weekday() in self.WEEKLY_EXPIRY_DAYS and d > from_date:
                return d.strftime("%y%m%d")
            d += timedelta(days=1)

        return (from_date + timedelta(days=7)).strftime("%y%m%d")

    def _next_monthly_expiry(self, from_date: datetime = None) -> str:
        """أقرب تاريخ انتهاء شهري (ثالث جمعة)"""
        if from_date is None:
            from_date = datetime.now()
        # تقريبي — ثالث جمعة من الشهر الجاي
        next_month = from_date.month % 12 + 1
        year = from_date.year + (1 if next_month == 1 else 0)
        # جمعة ثالثة تقريباً = اليوم 15-21
        for day in range(15, 22):
            d = datetime(year, next_month, day)
            if d.weekday() == 4:  # جمعة
                return d.strftime("%y%m%d")
        return datetime(year, next_month, 21).strftime("%y%m%d")

    # ═══════════════════════════════════════
    # ٢. بناء الإشارة الكاملة
    # ═══════════════════════════════════════

    def build_signal(
        self,
        entry_decision,         # EntrySignal من supply_demand_strategy
        current_price: float,
        symbol: str = "SPX",
        weekly: bool = True,
    ) -> TradeSignal:
        """
        بناء إشارة تداول كاملة من قرار الدخول

        يأخذ EntrySignal من استراتيجية العرض والطلب
        ويحوله إلى إشارة جاهزة للتنفيذ
        """
        from bot.supply_demand_strategy import EntryDecision

        dec = entry_decision.decision

        if dec == EntryDecision.WAIT:
            return None

        # تحديد الاتجاه
        direction = "CALL" if dec in (EntryDecision.BUY, EntryDecision.FLIP_BUY) else "PUT"

        # توليد العقد
        strike_offset = 0.5  # 0.5% فوق/تحت السعر
        contract = self.generate_contract(
            symbol=symbol,
            current_price=current_price,
            direction=direction,
            strike_offset_pct=strike_offset,
            weekly=weekly,
        )

        # منطقة الدخول = حول الـ Proximal Line
        if entry_decision.entry_price > 0:
            zone_width = abs(entry_decision.entry_price * 0.001)  # 0.1%
            entry_low = entry_decision.entry_price - zone_width
            entry_high = entry_decision.entry_price + zone_width
        else:
            # إذا ما فيه سعر دخول، استخدم السعر الحالي
            entry_low = current_price * 0.998
            entry_high = current_price * 1.002

        # الوقف
        stop = entry_decision.stop_loss if entry_decision.stop_loss > 0 else entry_low * 0.99

        # هدفين
        if entry_decision.take_profit > 0:
            target2 = entry_decision.take_profit
            target1 = entry_decision.entry_price + (target2 - entry_decision.entry_price) * 0.5
        else:
            # هدف افتراضي
            if direction == "CALL":
                target2 = current_price * 1.01
                target1 = current_price * 1.005
            else:
                target2 = current_price * 0.99
                target1 = current_price * 0.995

        # نوع الدخول
        entry_type = "retest" if dec in (EntryDecision.BUY, EntryDecision.SELL) else "breakout"

        # الثقة
        conf = entry_decision.confidence
        if conf >= 0.8:
            conf_label = "عالية 🔥"
        elif conf >= 0.5:
            conf_label = "متوسطة 🟡"
        else:
            conf_label = "منخفضة ⚠️"

        # تصنيف
        if dec in (EntryDecision.FLIP_BUY, EntryDecision.FLIP_SELL):
            trade_type = "مضاربة سريعة"
        else:
            trade_type = "سوينق"

        return TradeSignal(
            contract=contract,
            entry_zone_low=round(entry_low, 1),
            entry_zone_high=round(entry_high, 1),
            stop_loss=round(stop, 1),
            target1=round(target1, 1),
            target2=round(target2, 1),
            entry_type=entry_type,
            confidence=conf,
            confidence_label=conf_label,
            trade_type=trade_type,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            reason=entry_decision.reason,
        )

    # ═══════════════════════════════════════
    # ٣. تنسيق الإشارة
    # ═══════════════════════════════════════

    def format_signal(self, signal: TradeSignal) -> str:
        """تنسيق الإشارة كنص تلغرام"""
        c = signal.contract
        entry_type_ar = "اختراق 🚀" if signal.entry_type == "breakout" else "إعادة اختبار 🔄"
        direction_emoji = "🟢" if c.direction == "CALL" else "🔴"

        msg = f"""
🤖 إشارة تداول {c.symbol}

⛔️ ينطوي تداول الخيارات على مخاطر عالية ⛔️

{direction_emoji} الاتجاه: {c.direction}
{direction_emoji} العقد: {c.full_symbol}

🟡 نوع الفرصة: {signal.trade_type}
🟡 درجة الثقة: {signal.confidence_label} ({signal.confidence:.0%})

⚙️ خطة التنفيذ:

🔹 نوع الدخول: {entry_type_ar}
🔹 منطقة الدخول: {signal.entry_zone_low:.0f} – {signal.entry_zone_high:.0f}
🔹 مستوى الوقف: {signal.stop_loss:.0f}
🔹 الهدف الأول: {signal.target1:.0f}
🔹 الهدف الثاني: {signal.target2:.0f}

📋 العقد المقترح:
{c.direction} | {c.full_symbol}
Strike: {c.strike} | انتهاء: {c.expiry}

🎯 السبب: {signal.reason}
━━━━━━━━━━━━━━━━━━━━━
⚠️ {signal.note}
💡 التزم بإدارة رأس المال
"""
        return msg

    # ═══════════════════════════════════════
    # ٤. متابعة الصفقة
    # ═══════════════════════════════════════

    def save_position(self, position: Position, path: str = "/root/trading-bot/data/positions.json"):
        """حفظ الصفقة للمتابعة"""
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)

        pos_dict = {
            "entry_zone": [position.signal.entry_zone_low, position.signal.entry_zone_high],
            "stop_loss": position.signal.stop_loss,
            "target1": position.signal.target1,
            "target2": position.signal.target2,
            "direction": position.signal.contract.direction,
            "contract": position.signal.contract.full_symbol,
            "strike": position.signal.contract.strike,
            "entry_price": position.entry_price,
            "current_price": position.current_price,
            "pnl": position.pnl,
            "pnl_pct": position.pnl_pct,
            "entered_at": position.entered_at,
            "stage": position.signal.current_stage,
            "confidence": position.signal.confidence,
        }

        positions = []
        if os.path.exists(path):
            try:
                with open(path) as f:
                    positions = json.load(f)
            except:
                pass

        positions = [p for p in positions if p.get("stage") not in ("target2_hit", "stopped", "closed")]
        positions.append(pos_dict)

        with open(path, 'w') as f:
            json.dump(positions, f, indent=2, ensure_ascii=False)


    def check_position(self, current_price: float, position: dict) -> Optional[str]:
        """
        فحص الصفقة — هل وصلت لهدف/وقف؟

        Returns: "target1" | "target2" | "stopped" | None
        """
        if position["direction"] == "CALL":
            if current_price >= position["target2"] and position.get("stage") != "target2_hit":
                return "target2"
            if current_price >= position["target1"] and position.get("stage") != "target1_hit":
                return "target1"
            if current_price <= position["stop_loss"]:
                return "stopped"
        else:  # PUT
            if current_price <= position["target2"] and position.get("stage") != "target2_hit":
                return "target2"
            if current_price <= position["target1"] and position.get("stage") != "target1_hit":
                return "target1"
            if current_price >= position["stop_loss"]:
                return "stopped"

        return None
