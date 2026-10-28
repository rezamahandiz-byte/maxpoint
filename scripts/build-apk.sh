#!/usr/bin/env bash
#
# build-apk.sh — ساخت APK امضاشده MAXPOINT
#
# استفاده:
#   ./scripts/build-apk.sh
#
# این اسکریپت:
#   1. وجود keystore را چک می‌کند (اگر نیست، می‌سازد)
#   2. وجود متغیر FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD را چک می‌کند
#   3. APK را با --split-per-abi می‌سازد
#   4. مسیر APK نهایی را چاپ می‌کند
#
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"
KEYSTORE="upload-keystore.jks"
ALIAS="maxpoint"

echo "═══════════════════════════════════════════════════════════"
echo "  MAXPOINT — APK Builder"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ─── مرحله ۱: چک keystore ───────────────────────────────────
if [ ! -f "$KEYSTORE" ]; then
    echo "⚠️  Keystore پیدا نشد: $KEYSTORE"
    echo "   اولین بار است؟ یک keystore جدید می‌سازیم."
    echo ""
    read -s -p "رمز جدید برای keystore (حداقل ۶ کاراکتر): " KEYSTORE_PASS
    echo ""
    read -s -p "تکرار رمز: " KEYSTORE_PASS_CONFIRM
    echo ""

    if [ "$KEYSTORE_PASS" != "$KEYSTORE_PASS_CONFIRM" ]; then
        echo "❌ رمزها مطابقت ندارند. دوباره امتحان کن."
        exit 1
    fi

    if [ ${#KEYSTORE_PASS} -lt 6 ]; then
        echo "❌ رمز خیلی کوتاه است. حداقل ۶ کاراکتر."
        exit 1
    fi

    echo "🔑 ساخت keystore..."
    keytool -genkey -v \
        -keystore "$KEYSTORE" \
        -keyalg RSA \
        -keysize 2048 \
        -validity 10000 \
        -alias "$ALIAS" \
        -storepass "$KEYSTORE_PASS" \
        -keypass "$KEYSTORE_PASS" \
        -dname "CN=MAXPOINT, OU=Personal, O=Personal, L=Tehran, ST=Tehran, C=IR"

    echo ""
    echo "⚠️  هشدار حیاتی:"
    echo "   فایل $KEYSTORE را در جای امنی کپی کن (فلش، فضای ابری)"
    echo "   اگر گم شود، آپدیت دادن برنامه غیرممکن می‌شود!"
    echo ""
    echo "   این فایل در .gitignore هست — هرگز در Git کامیت نکن."
    echo ""

    export FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD="$KEYSTORE_PASS"
    echo "✅ متغیر FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD برای این session تنظیم شد."
    echo "   برای sessionهای بعدی، این را در ~/.bashrc بگذار:"
    echo "   export FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD='رمز'"
else
    echo "✅ Keystore موجود: $KEYSTORE"
    if [ -z "${FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD:-}" ]; then
        echo "❌ متغیر FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD تنظیم نشده."
        echo "   تنظیمش کن:"
        echo "   export FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD='رمز-keystore'"
        exit 1
    fi
    echo "✅ رمز keystore از متغیر محیطی خوانده شد."
fi

echo ""

# ─── مرحله ۲: چک پیش‌نیازها ─────────────────────────────────
echo "🔍 چک پیش‌نیازها..."

if ! command -v flet &>/dev/null; then
    echo "❌ flet نصب نیست. اجرا کن:"
    echo "   pip install \"flet>=1.0\""
    exit 1
fi
echo "   ✓ flet $(flet --version 2>&1 | head -1)"

if ! command -v java &>/dev/null; then
    echo "❌ java نصب نیست. JDK 17 یا 21 نصب کن."
    exit 1
fi
JAVA_VER=$(java -version 2>&1 | head -1 | grep -oE '[0-9]+' | head -1)
echo "   ✓ Java $JAVA_VER"

if ! command -v keytool &>/dev/null; then
    echo "❌ keytool نصب نیست (بخشی از JDK)."
    exit 1
fi
echo "   ✓ keytool"

echo ""

# ─── مرحله ۳: build ─────────────────────────────────────────
echo "🔨 شروع build APK..."
echo "   (اولین build ممکن است ۲۰-۴۰ دقیقه طول بکشد — SDK دانلود می‌شود)"
echo ""

flet build apk \
    --android-signing-key-store "$KEYSTORE" \
    --android-signing-key-alias "$ALIAS" \
    --split-per-abi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ Build کامل شد!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📁 APKهای ساخته‌شده:"
ls -lh build/android/*.apk 2>/dev/null || echo "   (پوشه build/android/ را چک کن)"
echo ""
echo "📱 کدام را نصب کنم؟"
echo "   • app-arm64-v8a-release.apk   ← اکثر گوشی‌های امروزی (۲۰۱۸+)"
echo "   • app-armeabi-v7a-release.apk ← گوشی‌های قدیمی"
echo "   • app-x86_64-release.apk       ← شبیه‌ساز"
echo ""
echo "📦 انتقال به گوشی:"
echo "   کابل USB / Google Drive / تلگرام → روی APK ضربه بزن"
echo ""
