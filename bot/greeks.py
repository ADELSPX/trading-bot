"""
Greeks — Black-Scholes كامل + جميع اليونانيات
_______________________________________________
- Delta, Gamma, Theta, Vega, Rho
- Implied Volatility (Newton-Raphson)
- Option pricing (Call + Put)
"""

import math
from typing import Optional

# ثابتة: 1 سنة = 365 يوم
DAYS_IN_YEAR = 365


def _norm_cdf(x: float) -> float:
    """CDF للتوزيع الطبيعي"""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_pdf(x: float) -> float:
    """PDF للتوزيع الطبيعي"""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def _d1_d2(
    S: float, K: float, T: float, r: float, sigma: float
) -> tuple[float, float]:
    """حساب d1, d2 في Black-Scholes"""
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        raise ValueError("Invalid parameters")
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def option_price(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> float:
    """
    سعر العقد باستخدام Black-Scholes
    S: سعر السهم الحالي
    K: سعر التنفيذ (Strike)
    T: الوقت بالسنوات
    r: سعر الفائدة (مثل 0.05 = 5%)
    sigma: التقلب (مثل 0.20 = 20%)
    """
    if T <= 0:
        # عند الانتهاء — القيمة الجوهرية فقط
        intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
        return intrinsic

    d1, d2 = _d1_d2(S, K, T, r, sigma)

    if option_type == "call":
        price = S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    else:
        price = K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)

    return round(max(price, 0.01), 4)


def calculate_delta(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> float:
    """Delta: حساسية السعر لحركة السهم"""
    d1, _ = _d1_d2(S, K, T, r, sigma)
    if option_type == "call":
        return round(_norm_cdf(d1), 4)
    else:
        return round(-_norm_cdf(-d1), 4)


def calculate_gamma(
    S: float, K: float, T: float, r: float, sigma: float
) -> float:
    """
    Gamma: تغير الدلتا لكل $1 حركة في السهم
    عالية = الخيار حساس جداً (قرب expiry)
    """
    d1, _ = _d1_d2(S, K, T, r, sigma)
    gamma = _norm_pdf(d1) / (S * sigma * math.sqrt(T))
    return round(gamma, 6)


def calculate_theta(
    S: float, K: float, T: float, r: float, sigma: float,
    option_type: str = "call"
) -> float:
    """
    Theta: تآكل الوقت (كم نخسر كل يوم)
    سالبة = نخسر قيمة مع الوقت (كل يوم ضدك)
    """
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    pdf_d1 = _norm_pdf(d1)

    if option_type == "call":
        theta = (
            -(S * pdf_d1 * sigma) / (2 * math.sqrt(T))
            - r * K * math.exp(-r * T) * _norm_cdf(d2)
        )
    else:
        theta = (
            -(S * pdf_d1 * sigma) / (2 * math.sqrt(T))
            + r * K * math.exp(-r * T) * _norm_cdf(-d2)
        )

    # تحويل لقيمة يومية (تقسيم على 365)
    return round(theta / DAYS_IN_YEAR, 6)


def calculate_vega(
    S: float, K: float, T: float, r: float, sigma: float
) -> float:
    """
    Vega: حساسية السعر للتقلب (IV)
    كل 1% زيادة في IV = كذا دولار زيادة
    """
    d1, _ = _d1_d2(S, K, T, r, sigma)
    vega = S * _norm_pdf(d1) * math.sqrt(T)
    return round(vega / 100, 6)  # لكل 1%


def calculate_rho(
    S: float, K: float, T: float, r: float, sigma: float,
    option_type: str = "call"
) -> float:
    """Rho: حساسية السعر لتغير سعر الفائدة"""
    _, d2 = _d1_d2(S, K, T, r, sigma)
    if option_type == "call":
        rho = K * T * math.exp(-r * T) * _norm_cdf(d2)
    else:
        rho = -K * T * math.exp(-r * T) * _norm_cdf(-d2)
    return round(rho / 100, 6)  # لكل 1%


def calculate_iv(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = "call",
    initial_guess: float = 0.30,
    max_iter: int = 100,
    tolerance: float = 0.0001,
) -> Optional[float]:
    """
    حساب الـ Implied Volatility من سعر السوق
    Newton-Raphson method
    """
    sigma = initial_guess

    for _ in range(max_iter):
        try:
            price = option_price(S, K, T, r, sigma, option_type)
            vega_val = calculate_vega(S, K, T, r, sigma) * 100  # rescale

            diff = price - market_price

            if abs(diff) < tolerance:
                return round(sigma * 100, 2)  # كنسبة مئوية

            if abs(vega_val) < 1e-12:
                break

            sigma = sigma - diff / vega_val
            sigma = max(sigma, 0.01)  # ماينزل عن 1%

        except (ValueError, ZeroDivisionError, OverflowError):
            break

    return None


class GreeksCalculator:
    """حاسبة جميع اليونانيات لعقد واحد"""

    @staticmethod
    def calculate_all(
        S: float,
        K: float,
        days_to_expiry: int,
        r: float = 0.05,
        sigma: float = 0.20,
        option_type: str = "call",
    ) -> dict:
        """
        حساب جميع اليونانيات

        Returns:
        {
            'price': سعر العقد,
            'delta': Delta,
            'gamma': Gamma,
            'theta': Theta (يومي),
            'vega': Vega (لكل 1% IV),
            'rho': Rho,
            'iv': التقلب الضمني (إذا كان None = استخدمنا sigma),
            'type': call/put
        }
        """
        T = max(days_to_expiry, 1) / DAYS_IN_YEAR

        price = option_price(S, K, T, r, sigma, option_type)
        delta = calculate_delta(S, K, T, r, sigma, option_type)
        gamma = calculate_gamma(S, K, T, r, sigma)
        theta = calculate_theta(S, K, T, r, sigma, option_type)
        vega = calculate_vega(S, K, T, r, sigma)
        rho = calculate_rho(S, K, T, r, sigma, option_type)
        intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
        extrinsic = price - intrinsic

        return {
            "price": price,
            "delta": delta,
            "gamma": gamma,
            "theta": theta,
            "vega": vega,
            "rho": rho,
            "intrinsic": round(intrinsic, 2),
            "extrinsic": round(max(extrinsic, 0), 4),
            "iv_pct": round(sigma * 100, 1),
            "type": option_type,
            "S": S,
            "K": K,
            "days": days_to_expiry,
        }

    @staticmethod
    def calculate_spread(
        legs: list[dict],
    ) -> dict:
        """
        حساب اليونانيات لإستراتيجية متعددة الأرجل
        legs = [{'S': 100, 'K': 95, 'days': 30, 'sigma': 0.20, 'type': 'call', 'multiplier': 1}, ...]
        multiplier: 1 = شراء, -1 = بيع
        """
        total = {
            "price": 0,
            "delta": 0,
            "gamma": 0,
            "theta": 0,
            "vega": 0,
            "rho": 0,
        }

        for leg in legs:
            g = GreeksCalculator.calculate_all(
                S=leg["S"],
                K=leg["K"],
                days_to_expiry=leg.get("days", 30),
                r=leg.get("r", 0.05),
                sigma=leg.get("sigma", 0.20),
                option_type=leg["type"],
            )
            mult = leg.get("multiplier", 1)
            for key in total:
                total[key] += g.get(key, 0) * mult

        for key in total:
            total[key] = round(total[key], 4)

        return total
