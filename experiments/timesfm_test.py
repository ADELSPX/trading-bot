import warnings
warnings.filterwarnings('ignore')
import numpy as np

print('=== جلب بيانات SPX ===')
try:
    import yfinance as yf
    df = yf.download('^SPX', period='6mo', interval='1d', progress=False)
    closes = np.asarray(df['Close'].values.flatten(), dtype=np.float64)[-200:]
    print('نقاط:', len(closes), '| آخر سعر:', closes[-1])
except Exception as e:
    print('yfinance فشل:', e)
    rng = np.random.default_rng(42)
    closes = 5000 + np.cumsum(rng.normal(0, 20, 200))
    print('بيانات تجريبية بديلة')

print('=== تحميل TimesFM 2.5 (200M) ===')
from timesfm.timesfm_2p5.timesfm_2p5_torch import TimesFM_2p5_200M_torch

model = TimesFM_2p5_200M_torch.from_pretrained(
    'google/timesfm-2.5-200m-pytorch',
    torch_compile=False,
)
print('النموذج جاهز')

print('=== التنبؤ (10 أيام قادمة) ===')
inputs = closes[-200:].reshape(1, -1)
forecast = model.forecast(inputs, horizon_len=10)
fc = np.asarray(forecast[0]).flatten()
print('توقع:', [round(float(x), 1) for x in fc])
print('آخر سعر:', round(float(closes[-1]), 2))

last = float(closes[-1])
move_pct = (float(fc[-1]) - last) / last * 100
print(f'=== حركة متوقعة 10 أيام: {move_pct:+.2f}% ===')
if move_pct > 0.3:
    print('نظرة: CALL (صعود متوقع)')
elif move_pct < -0.3:
    print('نظرة: PUT (هبوط متوقع)')
else:
    print('نظرة: حياد (تماسك)')
