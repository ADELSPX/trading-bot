"""
IB Integration — ربط البوت بـ IB Gateway عبر ib_insync
═══════════════════════════════════════════════════
يتصل بـ IB Gateway على A6 ويوفر:
  ١. بيانات السوق (أسعار، Options Chain)
  ٢. تنفيذ الأوامر (BUY/SELL)
  ٣. مراقبة الصفقات المفتوحة
"""

import time, json, os, logging
from datetime import datetime, timedelta
from typing import Optional, Literal
from dataclasses import dataclass, field

from ib_insync import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s [IB] %(message)s')
log = logging.getLogger('ib')

# ========== الإعدادات ==========
IB_HOST = "127.0.0.1"    # عبر SSH tunnel
IB_PORT = 4002            # IB Gateway API
CLIENT_ID = 1
ACCOUNT = "DUR156031"

POSITIONS_FILE = "/root/trading-bot/data/positions.json"


# ═══════════════════════════════════════════════
# إدارة الاتصال
# ═══════════════════════════════════════════════

class IBConnection:
    """اتصال دائم بـ IB Gateway مع إعادة اتصال تلقائي"""
    
    def __init__(self, host=IB_HOST, port=IB_PORT, client_id=CLIENT_ID):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()
        self.connected = False
    
    def connect(self, timeout=10) -> bool:
        """اتصال بـ IB Gateway"""
        try:
            cid = self.client_id
            self.ib.connect(self.host, self.port, clientId=cid, timeout=timeout)
            self.connected = True
            log.info(f"✅ متصل — Account: {self.ib.managedAccounts()}")
            return True
        except Exception as e:
            log.error(f"❌ فشل الاتصال: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """قطع الاتصال"""
        try:
            self.ib.disconnect()
        except:
            pass
        self.connected = False
    
    def reconnect(self) -> bool:
        """إعادة اتصال"""
        self.disconnect()
        time.sleep(1)
        return self.connect()
    
    def is_connected(self) -> bool:
        return self.connected and self.ib.isConnected()


# ═══════════════════════════════════════════════
# بيانات الحساب
# ═══════════════════════════════════════════════

def get_account_summary(ib: IB) -> dict:
    """جلب ملخص الحساب"""
    result = {}
    try:
        for v in ib.accountSummary():
            result[v.tag] = {"value": v.value, "currency": v.currency}
    except Exception as e:
        log.warning(f"accountSummary فشل: {e}")
    return result


def get_positions(ib: IB) -> list[dict]:
    """جلب المراكز المفتوحة"""
    positions = []
    try:
        for p in ib.positions():
            positions.append({
                "symbol": p.contract.symbol,
                "secType": p.contract.secType,
                "currency": p.contract.currency,
                "position": p.position,
                "avgCost": p.avgCost,
                "marketPrice": p.marketPrice,
                "marketValue": p.marketValue,
                "unrealizedPNL": p.unrealizedPNL,
                "realizedPNL": p.realizedPNL
            })
    except Exception as e:
        log.warning(f"positions فشل: {e}")
    return positions


# ═══════════════════════════════════════════════
# بيانات السوق
# ═══════════════════════════════════════════════

def get_spx_price(ib: IB) -> Optional[float]:
    """سعر SPX الحالي"""
    try:
        spx = Index('SPX', 'CBOE')
        ib.qualifyContracts(spx)
        ticker = ib.reqMktData(spx, '', False, False)
        time.sleep(1)
        ib.sleep(0.5)
        price = ticker.marketPrice()
        return price if price and price > 0 else None
    except Exception as e:
        log.warning(f"SPX price فشل: {e}")
        return None


def get_options_chain(ib: IB, symbol="SPX", weeks_ahead=2) -> dict:
    """سلسلة عقود الخيارات"""
    try:
        # تاريخ الانتهاء — أقرب جمعة بعد weeks_ahead
        today = datetime.now()
        days_ahead = (4 - today.weekday()) % 7 + weeks_ahead * 7
        expiry = today + timedelta(days=days_ahead)
        expiry_str = expiry.strftime("%Y%m%d")
        
        contract = Option(symbol, expiry_str, 0, "C", "SMART")
        ib.qualifyContracts(contract)
        
        chains = ib.reqSecDefOptParams(contract.symbol, '', contract.secType, contract.conId)
        
        result = {"expiry": expiry_str, "strikes": [], "calls": [], "puts": []}
        for chain in chains:
            if chain.expirations and expiry_str in chain.expirations:
                result["strikes"] = sorted(chain.strikes)
                result["exchange"] = chain.exchange
        
        return result
    except Exception as e:
        log.warning(f"Options chain فشل: {e}")
        return {"error": str(e)}


# ═══════════════════════════════════════════════
# تنفيذ الأوامر
# ═══════════════════════════════════════════════

def place_option_order(
    ib: IB,
    direction: Literal["CALL", "PUT"],
    strike: float,
    expiry_yyyymmdd: str,
    quantity: int = 1,
    order_type: str = "LMT",
    limit_price: float = 0.0,
    action: str = "BUY"
) -> Optional[dict]:
    """تنفيذ أمر خيار"""
    try:
        right = "C" if direction == "CALL" else "P"
        
        # بناء العقد — SPX على CBOE
        contract = Option("SPX", expiry_yyyymmdd, strike, right, "CBOE")
        qualified = ib.qualifyContracts(contract)
        
        # Fallback: reqContractDetails إذا qualify فشل
        if not qualified:
            log.warning(f"⚠️ qualifyContracts فشل، أجرب reqContractDetails...")
            details = ib.reqContractDetails(contract)
            if not details:
                log.error(f"❌ العقد غير صالح: SPX {expiry_yyyymmdd} {strike} {right}")
                return None
            contract = details[0].contract
        
        if not contract.conId:
            log.error(f"❌ العقد غير صالح: SPX {expiry_yyyymmdd} {strike} {right}")
            return None
        
        # بناء الأمر
        if order_type == "MKT":
            order = MarketOrder(action, quantity)
        elif order_type == "LMT":
            order = LimitOrder(action, quantity, limit_price)
        else:
            order = MarketOrder(action, quantity)
        
        # تنفيذ
        trade = ib.placeOrder(contract, order)
        log.info(f"📤 أمر: {action} {quantity} SPX {expiry_yyyymmdd} {strike} {direction} @ {order_type}")
        
        # انتظار التأكيد
        time.sleep(1)
        
        result = {
            "orderId": trade.order.orderId,
            "status": trade.orderStatus.status,
            "filled": trade.orderStatus.filled,
            "remaining": trade.orderStatus.remaining,
            "avgFillPrice": trade.orderStatus.avgFillPrice,
            "contract": str(contract),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # حفظ الصفقة
        _save_trade(result)
        
        return result
        
    except Exception as e:
        log.error(f"❌ فشل الأمر: {e}")
        return None


def _save_trade(trade: dict):
    """حفظ الصفقة في الملف"""
    os.makedirs(os.path.dirname(POSITIONS_FILE), exist_ok=True)
    positions = []
    try:
        with open(POSITIONS_FILE) as f:
            positions = json.load(f)
    except:
        pass
    positions.append(trade)
    with open(POSITIONS_FILE, "w") as f:
        json.dump(positions, f, indent=2)


# ═══════════════════════════════════════════════
# اختبار
# ═══════════════════════════════════════════════

def test_connection():
    """اختبار الاتصال وجلب ملخص الحساب"""
    conn = IBConnection()
    if not conn.connect():
        return {"error": "Connection failed"}
    
    ib = conn.ib
    result = {
        "accounts": list(ib.managedAccounts()),
        "account_summary": get_account_summary(ib),
        "positions": get_positions(ib),
        "server_time": str(ib.tradingDateTime().time()) if hasattr(ib, 'tradingDateTime') else str(datetime.now())
    }
    
    # SPX price
    spx_price = get_spx_price(ib)
    if spx_price:
        result["spx_price"] = spx_price
    
    conn.disconnect()
    return result


if __name__ == "__main__":
    print("🔌 IB Integration — اختبار")
    result = test_connection()
    print(json.dumps(result, indent=2, default=str))
