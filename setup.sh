#!/bin/bash
# ==============================================
# 🔄 استعادة كاملة لبوت التداول ومهارات Hermes
# ==============================================
# الاستخدام:
#   chmod +x setup.sh
#   ./setup.sh
#
# هذا السكريبت يستعيد كل شيء من GitHub:
# - بوت التداول (كود + استراتيجيات)
# - مهارات Hermes (للتداول)
# - ملفات التكوين الأساسية
# ==============================================
set -e

echo "🔧 بدء الاستعادة من GitHub..."
echo ""

REPO_URL="https://github.com/ADELSPX/trading-bot.git"
INSTALL_DIR="$HOME/trading-bot"
SKILLS_DIR="$HOME/.hermes/skills"

# 1. استنساخ المستودع
echo "📥 1/5 - تحميل المستودع..."
if [ -d "$INSTALL_DIR" ]; then
    echo "   المجلد موجود، تحديث..."
    cd "$INSTALL_DIR" && git pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 2. تثبيت المكتبات
echo "📦 2/5 - تثبيت المكتبات المطلوبة..."
pip install yfinance pandas numpy requests 2>/dev/null || echo "   ⚠️ بعض المكتبات ما تثبتت (موجودة مسبقاً؟)"

# 3. نسخ مهارات Hermes
echo "🧠 3/5 - نسخ مهارات Hermes..."
mkdir -p "$SKILLS_DIR"
cp -r skills/trading "$SKILLS_DIR/" 2>/dev/null && echo "   ✅ trading/trading-bot-from-videos"
cp -r skills/finance "$SKILLS_DIR/" 2>/dev/null && echo "   ✅ finance/options-trading"
cp -r skills/fazza-tools "$SKILLS_DIR/" 2>/dev/null && echo "   ✅ fazza-tools"
cp -r skills/arabic-video-transcription "$SKILLS_DIR/" 2>/dev/null && echo "   ✅ media/arabic-video-transcription"

# 4. إنشاء مجلدات البيانات
echo "📁 4/5 - إنشاء مجلدات البيانات..."
mkdir -p data logs reports

# 5. اختبار
echo "🧪 5/5 - اختبار التشغيل..."
python3 -c "from bot.signal_builder import SignalBuilder; print('   ✅ Signal Builder جاهز')" 2>&1 || echo "   ⚠️ فشل اختبار Signal Builder"
python3 -c "from bot.supply_demand_strategy import SupplyDemandStrategy; print('   ✅ استراتيجية العرض والطلب جاهزة')" 2>&1 || echo "   ⚠️ فشل اختبار الاستراتيجية"

echo ""
echo "══════════════════════════════════════════════"
echo "✅ تمت الاستعادة بنجاح!"
echo "══════════════════════════════════════════════"
echo ""
echo "📂 البوت: $INSTALL_DIR"
echo "🧠 المهارات: $SKILLS_DIR"
echo ""
echo "⚠️ تذكر تنقل ملف .env من السيرفر القديم (توكنات API)"
echo ""
echo "لتشغيل المراقب الحي:"
echo "  cd $INSTALL_DIR && python3 scripts/live_watcher.py"
echo ""
echo "لتوليد إشارة جديدة:"
echo "  cd $INSTALL_DIR && python3 scripts/gen_signal.py"
