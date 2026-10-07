"""
MCP Server لبوت التداول — JSON-RPC 2.0 over stdio (متوافق مع بروتوكول MCP الرسمي)
النسخة القديمة كانت ببروتوكول مخصص (mcp.listTools) فما كان يتصل أبداً ويعيد المحاولة كل ~11 دقيقة.

مهم: يُشغَّل بـ /usr/bin/python3 (اللي عنده yfinance 1.4.0) — مو venv هيرميس.
"""
import json
import sys

sys.path.insert(0, "/root/trading-bot")

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "trading-bot-mcp", "version": "2.0.0"}

TOOLS = []


def tool(name, description, parameters):
    def decorator(func):
        TOOLS.append({
            "name": name,
            "description": description,
            "inputSchema": parameters,
            "handler": func,
        })
        return func
    return decorator


# ── الأدوات ──────────────────────────────────────────────

@tool(
    name="generate_signal",
    description="توليد إشارة تداول SPX (PUT/CALL)",
    parameters={
        "type": "object",
        "properties": {
            "strategy": {
                "type": "string",
                "enum": ["supply_demand", "gamma"],
                "description": "الاستراتيجية: supply_demand أو gamma",
            }
        },
        "required": ["strategy"],
    },
)
def handle_generate_signal(params):
    try:
        from bot.signal_builder import SignalBuilder
        sb = SignalBuilder()
        result = sb.build(strategy=params.get("strategy", "supply_demand"))
        return {"success": True, "signal": str(result)[:1000]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="get_spx_price",
    description="الحصول على آخر سعر SPX",
    parameters={"type": "object", "properties": {}},
)
def handle_get_spx_price(params):
    """يقرأ من كاش SQLite المحلي (زمن شبه صفري). الشبكة فقط عند انتهاء الصلاحية أو غياب القيمة."""
    try:
        import market_cache as mc
        r = mc.get_quote(params.get("symbol", "SPX") if params else "SPX")
        if not r.get("price"):
            return {"success": False, "error": r.get("error", "No data")}
        out = {
            "success": True,
            "price": r["price"],
            "high": r.get("high"),
            "low": r.get("low"),
            "volume": r.get("volume"),
            "prev_close": r.get("prev_close"),
            "cache_status": r.get("cache_status"),      # hit | refreshed | stale
            "age_minutes": r.get("age_minutes"),
            "as_of_utc": r.get("fetched_at"),
            "source": r.get("source"),
        }
        if r.get("stale"):
            out["stale_warning"] = "القيمة هي آخر ما توفر (تعذّر التحديث من المصدر) — مو لحظية"
        return out
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="check_price_alerts",
    description="فحص إنذارات السعر (مستويات الدعم والمقاومة)",
    parameters={"type": "object", "properties": {}},
)
def handle_check_price_alerts(params):
    """الإنذارات من كاش SQLite. لو انتهت صلاحيتها تُحسب من الشمعات المخزّنة (بلا شبكة)،
    والمصدر الخارجي ما يُستدعى إلا إذا ما فيه شمعات أصلاً."""
    try:
        import market_cache as mc
        r = mc.get_alerts(params.get("symbol", "SPX") if params else "SPX")
        if "current" not in r:
            return {"success": False, "error": r.get("error", "No data")}
        out = {
            "success": True,
            "current": r.get("current"),
            "support": r.get("support"),
            "resistance": r.get("resistance"),
            "alerts": r.get("alerts", []),
            "computed_at_utc": r.get("fetched_at"),
            "age_minutes": r.get("age_minutes"),
            "cache_status": r.get("cache_status"),
        }
        if r.get("stale"):
            out["stale_warning"] = "المستويات من آخر حساب متوفر — مو لحظية"
        return out
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── JSON-RPC / MCP ───────────────────────────────────────

def _ok(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle(req):
    method = req.get("method", "")
    req_id = req.get("id")

    if method == "initialize":
        return _ok(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        })

    if method == "notifications/initialized":
        return None

    if method == "ping":
        return _ok(req_id, {})

    if method == "tools/list":
        return _ok(req_id, {
            "tools": [
                {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
                for t in TOOLS
            ]
        })

    if method == "tools/call":
        p = req.get("params", {}) or {}
        name = p.get("name", "")
        args = p.get("arguments", {}) or {}
        for t in TOOLS:
            if t["name"] == name:
                try:
                    out = t["handler"](args)
                    is_error = bool(isinstance(out, dict) and out.get("success") is False)
                    return _ok(req_id, {
                        "content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}],
                        "isError": is_error,
                    })
                except Exception as e:
                    return _ok(req_id, {
                        "content": [{"type": "text", "text": json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)}],
                        "isError": True,
                    })
        return _err(req_id, -32602, f"Tool '{name}' not found")

    return _err(req_id, -32601, f"Method not found: {method}")


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            print(json.dumps({"jsonrpc": "2.0", "id": None,
                              "error": {"code": -32700, "message": "Parse error"}}), flush=True)
            continue
        resp = handle(req)
        if resp is not None:
            print(json.dumps(resp, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
