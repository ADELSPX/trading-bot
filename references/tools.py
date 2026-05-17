"""
مصادر وأدوات خارجية — تمت مراجعتها وإضافتها للمشروع
_______________________________________________________
المصدر: @bitcoin_way (X/Twitter)
تاريخ المراجعة: 17 مايو 2026

جميع الأدوات سليمة — مفتوحة المصدر، لا يوجد أدوات تهكير أو خبيثة.
"""

# ========================
# أدوات مباشرة تفيد بوت التداول
# ========================

REFERENCE_TOOLS = {
    "TradingAgents": {
        "url": "https://github.com/TradeMaster-NTU/TradeMaster",
        "why": "إطار تداول متعدد الوكلاء (Multi-Agent). يجمع: محلل أساسي + محلل مشاعر + فني + مدير مخاطر. نفس فلسفة بوتنا لكن بشكل متقدم. يدعم DeepSeek V4.",
        "integrate": True,  # ممكن نستلهم هيكل الـ agents
        "priority": "high",
    },
    "OpenBB": {
        "url": "https://github.com/OpenBB-finance/OpenBBTerminal",
        "why": "منصة بيانات مالية متكاملة — تدعم الأسهم، الخيارات (Options)، المشتقات. بديل Bloomberg Terminal مفتوح المصدر. عندها MCP تكامل مع AI agents.",
        "integrate": True,  # مصدر بيانات ممتاز للبوت
        "priority": "high",
    },
    "FinRL": {
        "url": "https://github.com/AI4Finance-Foundation/FinRL",
        "why": "مكتبة تعلم تعزيزي (RL) للتداول — ممكن نضيف باك تست ذكي باستخدام RL.",
        "integrate": False,  # معقد حالياً، للتوسع المستقبلي
        "priority": "medium",
    },
    "qlib": {
        "url": "https://github.com/microsoft/qlib",
        "why": "منصة Microsoft للاستثمار الكوانت — AI data → alpha → portfolio → execution.",
        "integrate": False,  # ثقيل، للتوسع المستقبلي
        "priority": "medium",
    },
    "FinceptTerminal": {
        "url": "https://github.com/Fincept/FinceptTerminal",
        "why": "بديل Bloomberg بـ C++20 + Qt6. 37 وكيل AI على نمط Buffett/Munger/Lynch.",
        "integrate": False,  # C++ مش Python، للاطلاع فقط
        "priority": "low",
    },
    "Vibe-Trading": {
        "url": "https://github.com/vibe-trading",
        "why": "وكيل تداول شخصي — لغة طبيعية → استراتيجية → باكتست → تصدير TradingView/MT5.",
        "integrate": True,  # الـ natural language → strategy فكرة ممتازة للبوت
        "priority": "medium",
    },
    "QuantDinger": {
        "url": "https://github.com/QuantDinger",
        "why": "نظام كوانت AI ذاتي الاستضافة — باكتست، تداول مباشر، Docker Compose.",
        "integrate": False,
        "priority": "low",
    },
    "Freqtrade": {
        "url": "https://github.com/freqtrade/freqtrade",
        "why": "بوت تداول عملات رقمية — لكن هندسته المعمارية ممتازة (strategy + backtest + live).",
        "integrate": False,  # للأطلاع على هندسة البوتات
        "priority": "low",
    },
}


def get_integration_candidates() -> list[str]:
    """أدوات جاهزة للتكامل المباشر"""
    return [
        name for name, info in REFERENCE_TOOLS.items()
        if info["integrate"]
    ]


def get_priority_tools(level: str = "high") -> list[str]:
    """تصفية حسب الأولوية"""
    return [
        name for name, info in REFERENCE_TOOLS.items()
        if info["priority"] == level
    ]
