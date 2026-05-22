#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# 🔥 فزاع — سكربت الاستعادة الكامل (Disaster Recovery)
# ═══════════════════════════════════════════════════════════════════
# يشغّل كل شيء من الصفر على سيرفر جديد بنقرة وحدة
#
# الاستخدام:
#   chmod +x recovery.sh
#   sudo ./recovery.sh
#
# المتطلبات المسبقة (يدوي):
#   1. سيرفر Ubuntu 22.04+
#   2. SSH مفتوح
#   3. دومين أو IP عام
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

HERMES_HOME="/usr/local/lib/hermes-agent"
TRADING_BOT_DIR="/root/trading-bot"
GITHUB_REPO="https://github.com/ADELSPX/trading-bot.git"

echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
echo -e "${YELLOW}🔥 فزاع — بدء الاستعادة الكاملة${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════${NC}"

# ─── المرحلة 1: تثبيت الحزم الأساسية ───────────────────────
echo -e "\n${GREEN}[1/7] تثبيت الحزم الأساسية...${NC}"
apt-get update -qq
apt-get install -y -qq curl git python3 python3-pip python3-venv nodejs npm sqlite3 nginx 2>&1 | tail -1

# ─── المرحلة 2: تثبيت Hermes Agent ───────────────────────
echo -e "\n${GREEN}[2/7] تثبيت Hermes Agent...${NC}"
if [ ! -d "$HERMES_HOME" ]; then
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
    echo "✅ Hermes Agent مثبت"
else
    echo "✅ Hermes Agent موجود مسبقاً"
fi

# ─── المرحلة 3: استنساخ مشروع التداول ───────────────────────
echo -e "\n${GREEN}[3/7] استنساخ مشروع التداول...${NC}"
if [ ! -d "$TRADING_BOT_DIR" ]; then
    git clone "$GITHUB_REPO" "$TRADING_BOT_DIR"
    echo "✅ المشروع مستنسخ"
else
    cd "$TRADING_BOT_DIR" && git pull
    echo "✅ المشروع محدّث"
fi

# تثبيت متطلبات Python
cd "$TRADING_BOT_DIR"
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -r requirements.txt -q 2>&1 | tail -1
echo "✅ متطلبات Python مثبتة"

# ─── المرحلة 4: تثبيت n8n ───────────────────────────────
echo -e "\n${GREEN}[4/7] تثبيت n8n...${NC}"
if ! command -v n8n &>/dev/null; then
    npm install -g n8n@latest 2>&1 | tail -1
fi

# نسخ خدمة systemd لـ n8n
cp "$TRADING_BOT_DIR/deploy/systemd/n8n.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable n8n
systemctl restart n8n
echo "✅ n8n مثبت وشغال"

# ─── المرحلة 5: تثبيت Telegram Bridge ───────────────────────
echo -e "\n${GREEN}[5/7] تثبيت Telegram Webhook Bridge...${NC}"
cp "$TRADING_BOT_DIR/scripts/telegram_bridge.py" /usr/local/bin/
cp "$TRADING_BOT_DIR/deploy/systemd/telegram-bridge.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable telegram-bridge
systemctl restart telegram-bridge
echo "✅ Telegram Bridge شغال على المنفذ 7890"

# ─── المرحلة 6: استعادة مهام Cron ───────────────────────
echo -e "\n${GREEN}[6/7] استعادة مهام Hermes Cron...${NC}"
echo "📋 المهام موجودة في: $TRADING_BOT_DIR/deploy/cron/hermes-cron-jobs.txt"
echo "   شغّل الأوامر يدوياً بعد ما تتأكد Hermes شغال:"
echo "   bash $TRADING_BOT_DIR/deploy/cron/hermes-cron-jobs.txt"

# ─── المرحلة 7: التحقق النهائي ──────────────────────────
echo -e "\n${GREEN}[7/7] التحقق النهائي...${NC}"
echo ""

# فحص الخدمات
check_service() {
    if systemctl is-active --quiet "$1"; then
        echo -e "  ${GREEN}✅${NC} $1 شغال"
    else
        echo -e "  ${RED}❌${NC} $1 متوقف — راجع السجلات: journalctl -u $1 -n 20"
    fi
}

echo "حالة الخدمات:"
check_service "n8n"
check_service "telegram-bridge"

# فحص Telegram Bridge
echo ""
if curl -s -X POST http://localhost:7890 -H "Content-Type: application/json" -d '{"test":"recovery"}' 2>/dev/null | grep -q "sent"; then
    echo -e "${GREEN}✅${NC} Telegram Bridge يستقبل الإشارات"
else
    echo -e "${RED}❌${NC} Telegram Bridge ما يستجيب"
fi

# فحص n8n
if curl -s http://localhost:5678/healthz 2>/dev/null | grep -q "ok"; then
    echo -e "${GREEN}✅${NC} n8n شغال وسليم"
else
    echo -e "${RED}❌${NC} n8n ما يستجيب"
fi

# فحص ملفات البوت
echo ""
echo "ملفات البوت:"
for f in bot/core.py bot/greeks.py bot/strategy.py scripts/signal_alert.py scripts/telegram_bridge.py scripts/live_signals.py; do
    if [ -f "$TRADING_BOT_DIR/$f" ]; then
        echo -e "  ${GREEN}✅${NC} $f"
    else
        echo -e "  ${RED}❌${NC} $f مفقود"
    fi
done

echo ""
echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}🔥 الاستعادة اكتملت!${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
echo ""
echo "📋 الخطوة الأخيرة (يدوية):"
echo "  1. سجّل دخول n8n: http://$(hostname -I | awk '{print $1}'):5678"
echo "  2. أعِد بناء Flow تقرير الصباح: $TRADING_BOT_DIR/deploy/n8n/morning-report-flow.md"
echo "  3. شغّل مهام cron: bash $TRADING_BOT_DIR/deploy/cron/hermes-cron-jobs.txt"
echo ""
echo "🔧 للفحص السريع:"
echo "  python $TRADING_BOT_DIR/scripts/signal_alert.py --type entry --symbol SPX --direction put --entry 7406 --target1 7392 --stop 7412"
echo ""
echo -e "${GREEN}جاهز يا أبو جهاد 🤝${NC}"
