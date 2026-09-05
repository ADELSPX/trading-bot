#!/usr/bin/env python3
"""
TimesFM Forecast Tool v3 — أداة تنبؤ السلاسل الزمنية
=====================================================
أداة مستقلة تستخدم Google TimesFM 3.0 كطبقة تحليل إضافية بجانب إشارات Gamma.
ليست توصية بيع/شراء — معلومة تحليلية فقط.

التشغيل (على A6 — البيئة C:\timesfm_env):
    C:\timesfm_env\Scripts\python.exe timesfm_forecast.py --symbol "^SPX" --horizon 10

المخرجات JSON:
    {symbol, last_price, forecast[], move_pct, bias, data_points, generated_at}
"""
import warnings
warnings.filterwarnings('ignore')
import argparse
import json
import numpy as np

# ---------------------------------------------------------------------------
def fetch_closes(symbol: str, years: int = 3) -> np.ndarray:
    """جلب بيانات الإغلاق اليومية عبر yfinance."""
    import yfinance as yf
    df = yf.download(symbol, period=f'{years}y', interval='1d', progress=False)
    closes = np.asarray(df['Close'].values.flatten(), dtype=np.float64)
    if len(closes) == 0:
        raise ValueError(f'لا بيانات للسهم {symbol}')
    return closes


def build_forecaster():
    """تحميل TimesFM 3.0."""
    from timesfm3 import TimesFM3Evaluator, ModelConfig
    config = ModelConfig(
        checkpoint_path="google/timesfm-3.0-pytorch",
        per_core_batch_size=1,
        device="cpu",
    )
    return TimesFM3Evaluator(config)


def forecast(symbol: str, horizon: int = 10) -> dict:
    """تنفيذ التنبؤ الكامل وإرجاع النتيجة."""
    closes = fetch_closes(symbol)
    forecaster = build_forecaster()

    # TimesFM 3.0 يقبل سلاسل 1D بأطوال متغيرة — نعطيه آخر 700 نقطة
    series = closes[-700:]
    outputs = list(forecaster.predict_batch(
        [series],
        horizon=horizon,
        return_quantiles=True,
        use_symmetric_averaging=False,
    ))
    out = outputs[0]

    fc = np.asarray(out.forecast).flatten()
    last = float(closes[-1])
    move_pct = (float(fc[-1]) - last) / last * 100

    if move_pct > 0.3:
        bias = 'BULLISH'
    elif move_pct < -0.3:
        bias = 'BEARISH'
    else:
        bias = 'NEUTRAL'

    # نطاق الثقة 80% (من الكميّات)
    conf = None
    try:
        q = np.asarray(out.quantiles)  # (horizon, 9)
        conf = {'low': round(float(q[0, 0]), 2), 'high': round(float(q[0, -1]), 2)}
    except Exception:
        pass

    return {
        'symbol': symbol,
        'last_price': round(last, 2),
        'forecast': [round(float(x), 2) for x in fc],
        'move_pct': round(move_pct, 2),
        'bias': bias,
        'conf80': conf,
        'data_points': int(len(closes)),
        'generated_at': str(np.datetime64('now', 's')),
    }


# ---------------------------------------------------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TimesFM Forecast Tool v3')
    parser.add_argument('--symbol', default='^SPX', help='رمز السهم (افتراضي ^SPX)')
    parser.add_argument('--horizon', type=int, default=10, help='أفق التنبؤ بالأيام')
    args = parser.parse_args()

    result = forecast(args.symbol, args.horizon)
    print(json.dumps(result, ensure_ascii=False, indent=2))
