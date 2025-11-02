#!/usr/bin/env bash
set -e

echo "------------------------------------------------------------"
echo "🤖 WHATSAPP MESSENGER INSTALLER (Raspberry Pi Universal)"
echo "------------------------------------------------------------"

# === Variables ===
HOME_DIR="$HOME"
BOTS_DIR="$HOME_DIR/bots"
BOT_NAME="whatsapp messenger"
BOT_PATH="$BOTS_DIR/$BOT_NAME"
VENV_PATH="$BOT_PATH/venv"
REPORT_FILE="$VENV_PATH/report number"
PHONE_NUMBER="9940585709"
GITHUB_REPO="https://github.com/Thaniyanki/raspberry-pi-bots.git"
BOT_SUBPATH="whatsapp-birthday-wisher"

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

sudo apt install -y python3 python3-venv python3-pip git curl unzip build-essential x11-utils \
    libnss3 libxkbcommon0 libdrm2 libgbm1 libxshmfence1 libjpeg-dev zlib1g-dev \
    libfreetype6-dev liblcms2-dev libopenjp2-7-dev libtiff-dev libwebp-dev tk-dev \
    libharfbuzz-dev libfribidi-dev libxcb1-dev || true

# Try installing "t64" versions safely
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
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

pip install --upgrade pip setuptools wheel
pip install --no-cache-dir firebase_admin gspread selenium google-auth google-auth-oauthlib \
    google-cloud-storage google-cloud-firestore psutil pyautogui python3-xlib requests Pillow oauth2client

# === Step 5: Create Phone Number File ===
echo "$PHONE_NUMBER" > "$REPORT_FILE"
echo "[OK] Created phone number file: $REPORT_FILE"

# === Step 6: Download Python Script ===
echo "[INFO] Downloading bot script..."
cd "$BOT_PATH"
git clone "$GITHUB_REPO" temp_repo
cp -r temp_repo/$BOT_SUBPATH/*.py "$BOT_PATH" || true
rm -rf temp_repo
find "$BOT_PATH" -type f \( -name "*.sh" -o -name "README.md" \) -delete

# === Step 7: Update Python Paths ===
PY_FILE="$BOT_PATH/whatsapp messenger.py"
if [ -f "$PY_FILE" ]; then
    sed -i "s|CHROMEDRIVER_PATH *= *['\"].*['\"]|CHROMEDRIVER_PATH = \"$CHROMEDRIVER_BIN\"|" "$PY_FILE"
    sed -i "s|CHROME_PROFILE_PATH *= *os.path.join(USER_HOME, .*|CHROME_PROFILE_PATH = os.path.join(USER_HOME, \".config\", \"chromium\")|" "$PY_FILE"
    echo "[OK] Updated Chrome driver path in script."
fi

# === Step 8: Create Folder Structure ===
echo "[INFO] Creating folder structure..."
CURRENT_DATE=$(date +"%d-%m-%Y")

# Create main folders
mkdir -p "$BOT_PATH/Image"
mkdir -p "$BOT_PATH/Document"
mkdir -p "$BOT_PATH/Audio"
mkdir -p "$BOT_PATH/Video"

# Create date subfolders
mkdir -p "$BOT_PATH/Image/$CURRENT_DATE"
mkdir -p "$BOT_PATH/Document/$CURRENT_DATE"
mkdir -p "$BOT_PATH/Audio/$CURRENT_DATE"
mkdir -p "$BOT_PATH/Video/$CURRENT_DATE"

# Create Caption.txt files (except for Audio folder)
echo "Add your caption here" > "$BOT_PATH/Image/$CURRENT_DATE/Caption.txt"
echo "Add your caption here" > "$BOT_PATH/Document/$CURRENT_DATE/Caption.txt"
echo "Add your caption here" > "$BOT_PATH/Video/$CURRENT_DATE/Caption.txt"

echo "[OK] Created folder structure with date: $CURRENT_DATE"

# === Step 9: Summary ===
echo "------------------------------------------------------------"
echo "✅ INSTALLATION COMPLETE!"
echo "📁 Bot Path: $BOT_PATH"
echo "📂 Virtual Environment: $VENV_PATH"
echo "📄 Phone number file: $REPORT_FILE"
echo
echo "📁 Folder Structure Created:"
echo "  ├── Image/$CURRENT_DATE/Caption.txt"
echo "  ├── Document/$CURRENT_DATE/Caption.txt"
echo "  ├── Audio/$CURRENT_DATE/"
echo "  └── Video/$CURRENT_DATE/Caption.txt"
echo
echo "🌐 Chromium: $($CHROME_BIN --version)"
echo "🔧 Chromedriver: $($CHROMEDRIVER_BIN --version)"
echo
echo "💡 To start manually:"
echo "  cd \"$BOT_PATH\""
echo "  source \"$VENV_PATH/bin/activate\""
echo "  python3 'whatsapp messenger.py'"
echo "------------------------------------------------------------"
