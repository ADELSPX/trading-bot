#!/usr/bin/env python3
"""
TimesFM Forecast Tool — أداة تنبؤ السلاسل الزمنية
=================================================
أداة مستقلة تستخدم نموذج Google TimesFM 2.5 (200M) كطبقة تحليل إضافية
بجانب إشارات Gamma. ليست توصية بيع/شراء — معلومة تحليلية فقط.

التشغيل (على A6 — البيئة C:\timesfm_env):
    C:\timesfm_env\Scripts\python.exe timesfm_forecast.py --symbol ^SPX --horizon 10

المخرجات JSON:
    {symbol, last_price, forecast[], move_pct, bias, generated_at}
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


def build_model():
    """تحميل نموذج TimesFM 2.5 200M وتجهيزه."""
    import timesfm
    from timesfm.timesfm_2p5.timesfm_2p5_torch import TimesFM_2p5_200M_torch

    model = TimesFM_2p5_200M_torch.from_pretrained(
        'google/timesfm-2.5-200m-pytorch',
        torch_compile=False,
    )
    cfg = timesfm.ForecastConfig(
        max_context=1024,
        max_horizon=256,
        normalize_inputs=True,
        use_continuous_quantile_head=True,
        force_flip_invariance=True,
        infer_is_positive=True,
        fix_quantile_crossing=True,
    )
    model.compile(forecast_config=cfg)
    return model


def forecast(symbol: str, horizon: int = 10) -> dict:
    """تنفيذ التنبؤ الكامل وإرجاع النتيجة."""
    closes = fetch_closes(symbol)
    model = build_model()

    # النموذج يقبل مصفوفة 1D — نعطيه آخر 700 نقطة (ضمن سياق 1024)
    series = closes[-700:]
    point_forecast, _ = model.forecast(horizon=horizon, inputs=[series])

    fc = np.asarray(point_forecast[0]).flatten()
    last = float(closes[-1])
    move_pct = (float(fc[-1]) - last) / last * 100

    if move_pct > 0.3:
        bias = 'BULLISH'
    elif move_pct < -0.3:
        bias = 'BEARISH'
    else:
        bias = 'NEUTRAL'

    return {
        'symbol': symbol,
        'last_price': round(last, 2),
        'forecast': [round(float(x), 2) for x in fc],
        'move_pct': round(move_pct, 2),
        'bias': bias,
        'data_points': int(len(closes)),
        'generated_at': str(np.datetime64('now', 's')),
    }


# ---------------------------------------------------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TimesFM Forecast Tool')
    parser.add_argument('--symbol', default='^SPX', help='رمز السهم (افتراضي ^SPX)')
    parser.add_argument('--horizon', type=int, default=10, help='أفق التنبؤ بالأيام')
    args = parser.parse_args()

    result = forecast(args.symbol, args.horizon)
    print(json.dumps(result, ensure_ascii=False, indent=2))
