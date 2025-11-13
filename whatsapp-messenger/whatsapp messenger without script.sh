#!/usr/bin/env bash
set -e

echo "------------------------------------------------------------"
echo "🤖 WHATSAPP MESSENGER SETUP (Raspberry Pi Universal)"
echo "------------------------------------------------------------"

# === Variables ===
HOME_DIR="$HOME"
BOTS_DIR="$HOME_DIR/bots"  # ✅ lowercase 'bots'
BOT_NAME="whatsapp-messenger"  # ✅ changed to hyphenated name
BOT_PATH="$BOTS_DIR/$BOT_NAME"
VENV_PATH="$BOT_PATH/venv"
REPORT_FILE="$VENV_PATH/report number"
PHONE_NUMBER="9940585709"
GITHUB_REPO="https://github.com/Thaniyanki/raspberry-pi-bots.git"
BOT_SUBPATH="whatsapp-messenger"

OS=$(uname -s)
ARCH=$(uname -m)
echo "[INFO] Detected OS: $OS | Architecture: $ARCH"

# === Step 1: Folder Setup ===
mkdir -p "$BOTS_DIR"
if [ -d "$BOT_PATH" ]; then
    echo "[INFO] Removing existing bot folder..."
    rm -rf "$BOT_PATH"
fi
mkdir -p "$BOT_PATH"
echo "[OK] Created bot folder at: $BOT_PATH"

# === Step 2: Dependencies ===
echo "[INFO] Installing system dependencies..."
sudo apt update -y
sudo apt install -y python3 python3-venv python3-pip git curl unzip build-essential

# If desktop version (not Lite), install GUI and browser libs
if command -v startx >/dev/null 2>&1; then
    echo "[INFO] Desktop environment detected — installing X11 and multimedia libs..."
    sudo apt install -y x11-utils libnss3 libxkbcommon0 libdrm2 libgbm1 libxshmfence1 \
        libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7-dev \
        libtiff-dev libwebp-dev tk-dev libharfbuzz-dev libfribidi-dev libxcb1-dev
else
    echo "[INFO] Lite environment detected — skipping GUI-related packages."
fi

# Try installing "t64" variants safely
for pkg in libasound2t64 libatk-bridge2.0-0t64; do
    if apt-cache show "$pkg" >/dev/null 2>&1; then
        sudo apt install -y "$pkg"
    fi
done

# === Step 3: Chromium & Chromedriver ===
echo "[INFO] Installing Chromium and Chromedriver..."
if [[ "$ARCH" == "armv7l" ]]; then
    echo "[INFO] 32-bit Raspberry Pi detected."
    sudo apt install -y chromium chromium-driver || sudo apt install -y chromium-browser chromium-chromedriver
else
    echo "[INFO] 64-bit Raspberry Pi detected."
    sudo apt install -y chromium chromium-driver
fi

CHROME_BIN=$(command -v chromium-browser || command -v chromium)
CHROMEDRIVER_BIN=$(command -v chromedriver || command -v chromium-chromedriver)

if [ -z "$CHROME_BIN" ] || [ -z "$CHROMEDRIVER_BIN" ]; then
    echo "[ERROR] Chromium or Chromedriver not found after install!"
    exit 1
fi
sudo chmod +x "$CHROMEDRIVER_BIN"

echo "[OK] Chromium: $($CHROME_BIN --version)"
echo "[OK] Chromedriver: $($CHROMEDRIVER_BIN --version)"

# === Step 4: Python Virtual Environment ===
echo "[INFO] Creating Python virtual environment..."
if [ -d "$VENV_PATH" ]; then
    echo "[INFO] Removing old virtual environment..."
    rm -rf "$VENV_PATH"
fi
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

pip install --upgrade pip setuptools wheel
pip install --no-cache-dir firebase_admin gspread selenium google-auth google-auth-oauthlib \
    google-cloud-storage google-cloud-firestore psutil pyautogui python3-xlib requests Pillow oauth2client

# === Step 5: Create Phone Number File inside venv ===
echo "$PHONE_NUMBER" > "$REPORT_FILE"
echo "[OK] Created phone number file inside virtual environment: $REPORT_FILE"

# === Step 6: REMOVED - No Python script download ===
echo "[INFO] Skipping Python script download (will be handled by scheduler)"

# === Step 7: Create Folder Structure ===
echo "[INFO] Creating folder structure..."
CURRENT_DATE=$(date +"%d-%m-%Y")

# Create main folders
mkdir -p "$BOT_PATH/Image"
mkdir -p "$BOT_PATH/Document"
mkdir -p "$BOT_PATH/Audio"
mkdir -p "$BOT_PATH/Video"

# ✅ Create empty Caption.txt in main folders
touch "$BOT_PATH/Image/Caption.txt"
touch "$BOT_PATH/Document/Caption.txt"
touch "$BOT_PATH/Audio/Caption.txt"
touch "$BOT_PATH/Video/Caption.txt"

# Create date subfolders
mkdir -p "$BOT_PATH/Image/$CURRENT_DATE"
mkdir -p "$BOT_PATH/Document/$CURRENT_DATE"
mkdir -p "$BOT_PATH/Audio/$CURRENT_DATE"
mkdir -p "$BOT_PATH/Video/$CURRENT_DATE"

# ✅ Create empty Caption.txt in date subfolders
touch "$BOT_PATH/Image/$CURRENT_DATE/Caption.txt"
touch "$BOT_PATH/Document/$CURRENT_DATE/Caption.txt"
touch "$BOT_PATH/Audio/$CURRENT_DATE/Caption.txt"
touch "$BOT_PATH/Video/$CURRENT_DATE/Caption.txt"

echo "[OK] Created folder structure with date: $CURRENT_DATE"

# === Step 8: Summary ===
echo "------------------------------------------------------------"
echo "✅ SETUP COMPLETE!"
echo "📁 Bot Path: $BOT_PATH"
echo "📂 Virtual Environment: $VENV_PATH"
echo "📄 Phone number file: $REPORT_FILE"
echo
echo "📁 Folder Structure Created:"
echo "  ├── Image/Caption.txt"
echo "  ├── Document/Caption.txt"
echo "  ├── Audio/Caption.txt"
echo "  ├── Video/Caption.txt"
echo "  ├── Image/$CURRENT_DATE/Caption.txt"
echo "  ├── Document/$CURRENT_DATE/Caption.txt"
echo "  ├── Audio/$CURRENT_DATE/Caption.txt"
echo "  └── Video/$CURRENT_DATE/Caption.txt"
echo
echo "🌐 Chromium: $($CHROME_BIN --version)"
echo "🔧 Chromedriver: $($CHROMEDRIVER_BIN --version)"
echo
echo "💡 Ready for scheduler integration!"
echo "📝 Python script will be downloaded separately by scheduler"
echo "------------------------------------------------------------"
