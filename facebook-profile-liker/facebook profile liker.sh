#!/usr/bin/env bash
set -e

echo "------------------------------------------------------------"
echo "🤖 RASPBERRY PI UNIVERSAL BOT INSTALLER"
echo "------------------------------------------------------------"

# === 1️⃣ INPUT ARGUMENT ===
BOT_NAME="$1"
if [ -z "$BOT_NAME" ]; then
    echo "[ERROR] Usage: bash install-bot.sh <bot-folder-name>"
    exit 1
fi

# === 2️⃣ BASIC VARIABLES ===
HOME_DIR="$HOME"
BOTS_DIR="$HOME_DIR/bots"
BOT_PATH="$BOTS_DIR/$BOT_NAME"
VENV_PATH="$BOT_PATH/venv"
REPORT_FILE="$BOT_PATH/report_number.txt"
PHONE_NUMBER="9940585709"
GITHUB_REPO="https://github.com/Thaniyanki/raspberry-pi-bots.git"
BOT_SUBPATH="$BOT_NAME"

OS=$(uname -s)
ARCH=$(uname -m)
echo "[INFO] Detected OS: $OS | Architecture: $ARCH"

# === 3️⃣ CLEANUP & SETUP ===
mkdir -p "$BOTS_DIR"
if [ -d "$BOT_PATH" ]; then
    echo "[INFO] Removing existing bot folder..."
    rm -rf "$BOT_PATH"
fi
mkdir -p "$BOT_PATH"
echo "[OK] Created bot folder: $BOT_PATH"

# === 4️⃣ DEPENDENCIES ===
echo "[INFO] Installing dependencies..."
sudo apt update -y
sudo apt install -y python3 python3-venv python3-pip git curl unzip build-essential \
    chromium chromium-driver x11-utils libnss3 libxkbcommon0 libdrm2 libgbm1 \
    libxshmfence1 libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev \
    libopenjp2-7-dev libtiff-dev libwebp-dev tk-dev libharfbuzz-dev \
    libfribidi-dev libxcb1-dev || true

# Try installing optional t64 libs safely
for pkg in libasound2t64 libatk-bridge2.0-0t64; do
    if apt-cache show "$pkg" >/dev/null 2>&1; then
        sudo apt install -y "$pkg"
    fi
done

# === 5️⃣ CHROMIUM DETECTION ===
CHROME_BIN=$(command -v chromium-browser || command -v chromium)
CHROMEDRIVER_BIN=$(command -v chromedriver || command -v chromium-chromedriver)
if [ -z "$CHROME_BIN" ] || [ -z "$CHROMEDRIVER_BIN" ]; then
    echo "[ERROR] Chromium or Chromedriver not found!"
    exit 1
fi
sudo chmod +x "$CHROMEDRIVER_BIN"
echo "[OK] Chromium: $($CHROME_BIN --version)"
echo "[OK] Chromedriver: $($CHROMEDRIVER_BIN --version)"

# === 6️⃣ PYTHON ENVIRONMENT ===
echo "[INFO] Setting up Python virtual environment..."
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"
pip install --upgrade pip setuptools wheel
pip install --no-cache-dir firebase_admin gspread selenium google-auth google-auth-oauthlib \
    google-cloud-storage google-cloud-firestore psutil pyautogui python3-xlib requests Pillow \
    oauth2client python-dateutil

# === 7️⃣ CREATE PHONE NUMBER FILE ===
echo "$PHONE_NUMBER" > "$REPORT_FILE"
echo "[OK] Created phone number file: $REPORT_FILE"

# === 8️⃣ DOWNLOAD BOT FILES ===
echo "[INFO] Fetching bot source files from GitHub..."
cd "$BOT_PATH"
git clone --depth 1 "$GITHUB_REPO" temp_repo
cp -r temp_repo/$BOT_SUBPATH/* "$BOT_PATH" || true
rm -rf temp_repo

# === 9️⃣ UPDATE DRIVER PATH IN BOT SCRIPT ===
PY_FILE=$(find "$BOT_PATH" -maxdepth 1 -type f -iname "*.py" | head -n 1)
if [ -f "$PY_FILE" ]; then
    sed -i "s|CHROMEDRIVER_PATH *= *['\"].*['\"]|CHROMEDRIVER_PATH = \"$CHROMEDRIVER_BIN\"|" "$PY_FILE" || true
    sed -i "s|CHROME_PROFILE_PATH *= *os.path.join(USER_HOME, .*|CHROME_PROFILE_PATH = os.path.join(USER_HOME, \".config\", \"chromium\")|" "$PY_FILE" || true
    echo "[OK] Updated paths in: $PY_FILE"
fi

# === 🔟 SUMMARY ===
echo "------------------------------------------------------------"
echo "✅ INSTALLATION COMPLETE!"
echo "📦 Bot Name: $BOT_NAME"
echo "📁 Path: $BOT_PATH"
echo "📂 Virtual Env: $VENV_PATH"
echo "📄 Phone Number File: $REPORT_FILE"
echo
echo "🌐 Chromium: $($CHROME_BIN --version)"
echo "🔧 Chromedriver: $($CHROMEDRIVER_BIN --version)"
echo
echo "💡 To start manually:"
echo "  cd \"$BOT_PATH\""
echo "  source \"$VENV_PATH/bin/activate\""
echo "  python3 $(basename "$PY_FILE")"
echo "------------------------------------------------------------"
