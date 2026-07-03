"""
IBKR Executor — ينفذ إشارات Signal Engine v2 عبر IBKR API
يرتبط مع TWS (Trader WorkStation) على A6
"""

import json, time, os
from datetime import datetime

# ========== إعدادات IBKR ==========
IBKR_CONFIG = {
    "host": "127.0.0.1",
    "port": 7497,  # 7497 = Paper, 7496 = Live
    "client_id": 1,
    "account": "Dur156031"
}

# ========== مسارات الملفات ==========
SIGNAL_FILE = "/root/trading-bot/data/active_signal.json"
POSITIONS_FILE = "/root/trading-bot/data/positions.json"

def load_active_signal():
    """قراءة الإشارة النشطة"""
    try:
        with open(SIGNAL_FILE) as f:
            return json.load(f)
    except:
        return None

def save_position(position):
    """حفظ الصفقة"""
    os.makedirs(os.path.dirname(POSITIONS_FILE), exist_ok=True)
    positions = []
    try:
        with open(POSITIONS_FILE) as f:
            positions = json.load(f)
    except:
        pass
    positions.append(position)
    with open(POSITIONS_FILE, "w") as f:
        json.dump(positions, f, indent=2)

def build_contract(symbol, strike, expiry, right):
    """بناء عقد Option"""
    return {
        "symbol": symbol,
        "right": right.upper(),  # CALL / PUT
        "strike": strike,
        "lastTradeDateOrContractMonth": expiry,
        "exchange": "SMART",
        "currency": "USD",
        "secType": "OPT"
    }

def place_order(contract, quantity, order_type="LMT", price=0.0):
    """بناء أمر"""
    return {
        "contract": contract,
        "order": {
            "action": "BUY",
            "totalQuantity": quantity,
            "orderType": order_type,
            "lmtPrice": price if order_type == "LMT" else 0.0,
            "tif": "GTC"
        }
    }

def execute_signal(signal):
    """تنفيذ إشارة — يحولها إلى أمر IBKR"""
    direction = signal.get("direction", "").upper()
    entry = signal.get("entry", 0)
    symbol = signal.get("symbol", "SPX")
    strike = signal.get("strike", entry)
    expiry = signal.get("expiry", "")
    
    # العقد
    right = "CALL" if direction == "CALL" else "PUT"
    contract = build_contract(symbol, strike, expiry, right)
    
    # الأمر — نضع أمر بـ entry price
    order = place_order(contract, 1, "LMT", entry)
    
    position = {
        "timestamp": datetime.utcnow().isoformat(),
        "account": IBKR_CONFIG["account"],
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "target1": signal.get("target1"),
        "target2": signal.get("target2"),
        "stop": signal.get("stop"),
        "contract": contract,
        "order": order,
        "status": "pending"
    }
    
    save_position(position)
    return position

def main():
    print(f"🤖 IBKR Executor — Account: {IBKR_CONFIG['account']}")
    print(f"📡 Paper Port: {IBKR_CONFIG['port']}")
    print()
    
    signal = load_active_signal()
    if signal:
        print(f"📊 إشارة نشطة: {signal.get('symbol')} {signal.get('direction')} @ {signal.get('entry')}")
        pos = execute_signal(signal)
        print(f"✅ أمر جاهز للتنفيذ: {pos['direction']} {pos['symbol']} {strike} @ {entry}")
        print(f"   T1: {signal.get('target1')} | T2: {signal.get('target2')} | Stop: {signal.get('stop')}")
    else:
        print("⏸️ لا توجد إشارة نشطة")

if __name__ == "__main__":
    main()
