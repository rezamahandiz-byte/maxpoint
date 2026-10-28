# راهنمای build APK — MAXPOINT

این راهنما مرحله به مرحله نشان می‌دهد چطور از سورس یک APK امضاشده بسازی که بدون مشکل روی گوشی اندرویدی نصب شود.

---

## پیش‌نیازها

### ۱. Java JDK 17 یا 21
```bash
java -version
# باید خروجی مثل "openjdk version 21" بدهد
```
اگر نیست:
- **ویندوز:** از [adoptium.net](https://adoptium.net) JDK 21 نصب کن
- **مک:** `brew install openjdk@21`
- **لینوکس:** `sudo apt install openjdk-21-jdk`

### ۲. Python 3.12+ و Flet
```bash
python --version          # باید 3.12+ باشد
pip install "flet>=1.0" "flet-charts>=1.0" "flet-secure-storage>=1.0" httpx
flet --version            # باید 1.0+ باشد
```

### ۳. Android SDK
**نکته مهم:** فلت به‌صورت خودکار Android SDK را هنگام اولین `flet build apk` دانلود می‌کند (~۲ گیگ). به Android Studio نیاز نداری.

اگر خواستی手动 نصب کنی:
- `ANDROID_HOME` را روی مسیر SDK تنظیم کن
- اما **توصیه:** همین به فلت بسپار

---

## مرحله ۱: ساخت keystore امضا (فقط یک‌بار — برای همیشه)

این فایل هویت برنامه‌ات است. اگر گم شود، دیگر نمی‌توانی نسخه‌های بعدی را به‌عنوان «آپدیت» همان برنامه منتشر کنی.

```bash
cd /home/z/my-project

keytool -genkey -v \
  -keystore upload-keystore.jks \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -alias maxpoint
```

سؤال‌هایی می‌پرسد:
- **رمز keystore:** یک رمز قوی انتخاب کن (مثلاً `MyStr0ng!Pass2026`)
- **رمز alias:** می‌تواند همان رمز بالا باشد
- **نام و نام خانوادگی:** نام خودت
- **سایر فیلدها:** می‌توانی Enter بزنی یا پر کنی
- در پایان `y` بزن تا تأیید شود

### ⚠️ هشدارهای حیاتی
- **هرگز `upload-keystore.jks` را در Git کامیت نکن** (در `.gitignore` هست)
- **یک کپی از آن روی فلش مموری یا فضای ابری امن بگیر** — اگر گم شود، آپدیت دادن برنامه غیرممکن می‌شود
- این فایل را با کسی به اشتراک نگذار

---

## مرحله ۲: تنظیم رمز keystore در متغیر محیطی

برای امنیت، رمز را در متغیر محیطی می‌گذاریم نه در خط فرمان:

### لینوکس / مک
```bash
export FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD='رمز-keystore-ای-که-انتخاب-کردی'
```

برای دائمی کردن:
```bash
echo 'export FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD="رمز"' >> ~/.bashrc
source ~/.bashrc
```

### ویندوز (PowerShell)
```powershell
$env:FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD = "رمز-keystore"
```

برای دائمی کردن:
```powershell
[System.Environment]::SetEnvironmentVariable("FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD", "رمز", "User")
```

---

## مرحله ۳: build APK

از پوشه ریشه پروژه:

```bash
cd /home/z/my-project

flet build apk \
  --android-signing-key-store upload-keystore.jks \
  --android-signing-key-alias maxpoint \
  --split-per-abi
```

### توضیح فلگ‌ها
- `--android-signing-key-store`: مسیر فایل keystore
- `--android-signing-key-alias`: نام alias که موقع ساخت keystore انتخاب کردی (`maxpoint`)
- `--split-per-abi`: به‌جای یک APK حجیم، سه APK سبک‌تر می‌سازد (یکی برای هر معماری پردازنده)

### اولین build چه اتفاقی می‌افتد؟
1. فلت Android SDK را دانلود می‌کند (~۲ گیگ، ۱۰-۲۰ دقیقه)
2. Gradle و ابزارهای build را دانلود می‌کند (~۵۰۰ مگ)
3. پروژه Flutter را تولید می‌کند
4. کد پایتون را در APK بسته‌بندی می‌کند
5. با keystore امضا می‌کند

**مدت زمان:** اولین build ۲۰-۴۰ دقیقه. buildهای بعدی ۵-۱۰ دقیقه.

### خروجی کجاست؟
```
build/android/
├── app-armeabi-v7a-release.apk   (برای پردازنده‌های قدیمی 32-بیت)
├── app-arm64-v8a-release.apk     (برای اکثر گوشی‌های امروزی ✅)
└── app-x86_64-release.apk        (برای شبیه‌ساز)
```

---

## مرحله ۴: کدام APK را نصب کنم؟

| گوشی | APK مناسب |
|------|-----------|
| گوشی‌های ۲۰۱۸ به بعد (اکثر) | `app-arm64-v8a-release.apk` ✅ |
| گوشی‌های قدیمی (قبل از ۲۰۱۸) | `app-armeabi-v7a-release.apk` |
| شبیه‌ساز اندروید روی کامپیوتر | `app-x86_64-release.apk` |

اگر مطمئن نیستی: `app-arm64-v8a-release.apk` را امتحان کن. اگر نصب نشد، `app-armeabi-v7a-release.apk` را امتحان کن.

---

## مرحله ۵: انتقال به گوشی و نصب

### روش ۱: کابل USB
1. گوشی را با کابل به کامپیوتر وصل کن
2. فایل APK را در پوشه `Download` گوشی کپی کن
3. روی گوشی: **فایل‌منجر → Download → روی APK ضربه بزن**
4. اگر پیام «نصب از منابع ناشناس مجاز نیست» آمد → تنظیمات → امنیت → اجازه نصب از منابع ناشناس

### روش ۲: Google Drive / تلگرام / ایمیل
1. APK را در Google Drive آپلود کن (یا به خودت در تلگرام بفرست)
2. روی گوشی دانلود کن
3. روی APK ضربه بزن و نصب کن

### روش ۳: ADB (اگر برنامه‌نویسی)
```bash
adb install build/android/app-arm64-v8a-release.apk
```

---

## مرحله ۶: رفع مشکلات رایج

### مشکل: «INSTALL_PARSE_FAILED_NO_CERTIFICATES»
**علت:** APK امضا نشده.
**راه‌حل:** مطمئن شو فلگ `--android-signing-key-store` و `--android-signing-key-alias` را گذاشتی و متغیر `FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD` تنظیم شده.

### مشکل: «INSTALL_FAILED_UPDATE_INCOMPATIBLE»
**علت:** نسخه قبلی با keystore دیگری امضا شده.
**راه‌حل:** اول نسخه قدیمی را از گوشی پاک کن، بعد نسخه جدید را نصب کن.

### مشکل: «APP_NOT_INSTALLED»
**علت‌های ممکن:**
1. **معماری اشتباه:** APK `x86_64` را روی گوشی `arm64` نصب می‌کنی → از `app-arm64-v8a-release.apk` استفاده کن
2. **اندروید قدیمی:** minSdkVersion بالاتر از نسخه اندروید گوشی است
3. **فضای ناکافی:** حداقل ۱۰۰ مگ آزاد کن

### مشکل: build با خطای «SDK license not accepted»
```bash
flet doctor
# یا دستی:
yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses
```

### مشکل: build با خطای «Java version incompatible»
فلت 1.0 به Java 17 یا 21 نیاز دارد. Java 8 یا 11 کار نمی‌کند.
```bash
java -version  # باید 17 یا 21 باشد
```

### مشکل: «Keystore file exists but is corrupted»
فایل `upload-keystore.jks` را با همان رمز قبلی باز کن. اگر رمز را فراموش کرده‌ای، باید keystore جدید بسازی — اما آنوقت آپدیت دادن برنامه‌های قبلی غیرممکن می‌شود.

### مشکل: برنامه نصب می‌شود اما کرش می‌کند
1. لاگcat را ببین:
```bash
adb logcat | grep -i "maxpoint\|flet\|python"
```
2. رایج‌ترین علت: **فیلد صدا** — اگر `focus_chime.wav` در `src/assets/sounds/` نباشد، برنامه موقع نوتیفیکیشن کرش می‌کند. مطمئن شو فایل هست.
3. علت دیگر: **عدم دسترسی اینترنت** — `time_sync` سعی می‌کند به google.com وصل شود. اگر مسدود باشد، باید بی‌صدا برگردد، ولی اگر httpx نصب نباشد کرش می‌کند.

---

## مرحله ۷: تست روی گوشی

بعد از نصب:
1. برنامه را باز کن — باید صفحه خانه با کارت «شروع مطالعه» بالا بیاید
2. به تب تنظیمات برو → گروه «یادآوری مطالعه» را باز کن → «تست یادآوری» را بزن → باید دیالگ «درس می‌خوانی؟» با صدا بیاید
3. «شروع مطالعه» را بزن → درس انتخاب کن → تایمر باید شروع به شمارش کند
4. «پایان و ثبت» را بزن → باید در صفحه خانه، عدد دقیقه مطالعه آپدیت شود
5. برنامه را ببند و دوباره باز کن → داده‌ها باید حفظ شده باشند

---

## خلاصه سریع (کپی-پیست)

```bash
# ۱. keystore (یک‌بار)
keytool -genkey -v -keystore upload-keystore.jks \
  -keyalg RSA -keysize 2048 -validity 10000 -alias maxpoint

# ۲. رمز را در متغیر محیطی بگذار
export FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD='رمز-keystore'

# ۳. build
cd /home/z/my-project
flet build apk \
  --android-signing-key-store upload-keystore.jks \
  --android-signing-key-alias maxpoint \
  --split-per-abi

# ۴. APK نهایی
ls -la build/android/app-arm64-v8a-release.apk
```

---

## نکات نهایی

- **شماره نسخه:** هر بار که build می‌گیری و می‌خواهی به‌عنوان آپدیت نصب کنی، در `pyproject.toml` مقدار `build_number` را یکی افزایش بده (مثلاً `1` → `2`)
- **حجم APK:** با `--split-per-abi` حدود ۲۰-۳۰ مگ برای هر APK. بدون این فلگ حدود ۸۰ مگ
- **پاک‌سازی cache build:** اگر build خراب شد: `flet clean` سپس دوباره build بگیر
- **build debug (بدون امضا، برای تست سریع):** `flet build apk --debug` — اما روی گوشی نصب نمی‌شود مگر با adb
