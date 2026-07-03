"""
MCP Server لبوت التداول
يتيح لـ Hermes استدعاء أدوات التداول مباشرة عبر Model Context Protocol
"""

import json
import sys
import os
import importlib.util

sys.path.insert(0, "/root/trading-bot")

TOOLS = []

def tool(name, description, parameters):
    """Decorator لتسجيل أداة MCP"""
    def decorator(func):
        TOOLS.append({
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": func
        })
        return func
    return decorator


@tool(
    name="generate_signal",
    description="توليد إشارة تداول SPX (PUT/CALL)",
    parameters={
        "type": "object",
        "properties": {
            "strategy": {
                "type": "string",
                "enum": ["supply_demand", "gamma"],
                "description": "الاستراتيجية: supply_demand أو gamma"
            }
        },
        "required": ["strategy"]
    }
)
def handle_generate_signal(params):
    """توليد إشارة من bot.signal_builder"""
    try:
        from bot.signal_builder import SignalBuilder
        sb = SignalBuilder()
        result = sb.build(strategy=params.get("strategy", "supply_demand"))
        return {"success": True, "signal": result[:1000]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="get_spx_price",
    description="الحصول على آخر سعر SPX",
    parameters={"type": "object", "properties": {}}
)
def handle_get_spx_price(params):
    """جلب سعر SPX من yfinance"""
    try:
        import yfinance as yf
        spx = yf.Ticker("^SPX")
        data = spx.history(period="1d", interval="1m")
        if not data.empty:
            last = data.iloc[-1]
            return {
                "success": True,
                "price": round(float(last["Close"]), 2),
                "high": round(float(last["High"]), 2),
                "low": round(float(last["Low"]), 2),
                "volume": int(last["Volume"])
            }
        return {"success": False, "error": "No data"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="check_price_alerts",
    description="فحص إنذارات السعر (مستويات الدعم والمقاومة)",
    parameters={"type": "object", "properties": {}}
)
def handle_check_price_alerts(params):
    """فحص مستويات الدعم والمقاومة"""
    try:
        import yfinance as yf
        spx = yf.Ticker("^SPX")
        data = spx.history(period="5d", interval="5m")
        if data.empty:
            return {"success": False, "error": "No data"}
        
        closes = data["Close"].values
        current = closes[-1]
        support = round(float(min(closes[-20:])), 2)
        resistance = round(float(max(closes[-20:])), 2)
        
        alerts = []
        if current <= support * 1.005:
            alerts.append("⚠️ قرب الدعم — احتمال صعود (CALL)")
        if current >= resistance * 0.995:
            alerts.append("⚠️ قرب المقاومة — احتمال هبوط (PUT)")
        
        return {
            "success": True,
            "current": round(float(current), 2),
            "support": support,
            "resistance": resistance,
            "alerts": alerts
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── MCP Protocol Handler ────────────────────────────────

def handle_mcp_request(raw: str) -> str:
    """MCP handler: stdin/stdout protocol"""
    try:
        req = json.loads(raw)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"})

    method = req.get("method", "")
    
    if method == "mcp.listTools":
        return json.dumps({
            "result": {
                "tools": [
                    {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"]
                    }
                    for t in TOOLS
                ]
            }
        })
    
    elif method == "mcp.callTool":
        name = req.get("params", {}).get("name", "")
        params = req.get("params", {}).get("parameters", {})
        
        for t in TOOLS:
            if t["name"] == name:
                result = t["handler"](params)
                return json.dumps({"result": result})
        
        return json.dumps({"error": f"Tool '{name}' not found"})
    
    elif method == "mcp.describe":
        return json.dumps({
            "result": {
                "name": "trading-bot-mcp",
                "version": "1.0.0",
                "description": "MCP server لبوت تداول SPX"
            }
        })
    
    else:
        return json.dumps({"error": f"Unknown method: {method}"})


if __name__ == "__main__":
    # MCP mode: read JSON lines from stdin, write to stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        response = handle_mcp_request(line)
        print(response, flush=True)
