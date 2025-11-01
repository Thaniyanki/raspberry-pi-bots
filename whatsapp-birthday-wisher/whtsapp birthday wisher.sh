#!/usr/bin/env bash
set -e

echo "------------------------------------------------------------"
echo "🤖 WHATSAPP BIRTHDAY WISHER INSTALLER (Raspberry Pi Universal)"
echo "------------------------------------------------------------"

# === Paths ===
HOME_DIR="$HOME"
BOTS_DIR="$HOME_DIR/bots"
BOT_NAME="whatsapp birthday wisher"
BOT_PATH="$BOTS_DIR/$BOT_NAME"
VENV_PATH="$BOT_PATH/venv"
REPORT_FILE="$VENV_PATH/report number"
PHONE_NUMBER="9940585709"
GITHUB_REPO="https://github.com/Thaniyanki/raspberry-pi-bots.git"
BOT_SUBPATH="whatsapp-birthday-wisher"

echo "[INFO] Detected OS: $(uname -s) | Architecture: $(uname -m)"

# === Step 1: Folder Setup ===
mkdir -p "$BOTS_DIR"
if [ -d "$BOT_PATH" ]; then
    echo "[INFO] Removing existing bot folder..."
    rm -rf "$BOT_PATH"
fi
mkdir -p "$BOT_PATH"
echo "[OK] Created bot folder at: $BOT_PATH"

# === Step 2: System Dependencies ===
echo "[INFO] Installing system dependencies..."
sudo apt update -y
sudo apt install -y python3 python3-venv python3-pip git curl unzip build-essential \
    libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7-dev \
    libtiff-dev libwebp-dev tk-dev libharfbuzz-dev libfribidi-dev libxcb1-dev \
    chromium-browser chromium-chromedriver

# === Step 3: Detect Chromium + Chromedriver Paths ===
echo "[INFO] Detecting Chromium and Chromedriver paths..."
CHROME_BIN=$(command -v chromium-browser || command -v chromium)
CHROMEDRIVER_BIN=$(command -v chromedriver || echo "/usr/lib/chromium-browser/chromedriver")

if [ ! -f "$CHROMEDRIVER_BIN" ]; then
    echo "[ERROR] Chromedriver not found after install."
    exit 1
fi

echo "[OK] Chromium path: $CHROME_BIN"
echo "[OK] Chromedriver path: $CHROMEDRIVER_BIN"

# === Step 4: Create Virtual Environment ===
echo "[INFO] Creating new Python virtual environment..."
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

# === Step 5: Upgrade pip & setuptools ===
pip install --upgrade pip setuptools wheel

# === Step 6: Install Python Libraries ===
echo "[INFO] Installing required Python packages..."
pip install --no-cache-dir firebase_admin gspread selenium google-auth google-auth-oauthlib \
    google-cloud-storage google-cloud-firestore psutil pyautogui python3-xlib requests Pillow oauth2client

# === Step 7: Create Phone Number File Inside venv ===
echo "$PHONE_NUMBER" > "$REPORT_FILE"
echo "[OK] Created phone number file inside venv: $REPORT_FILE"

# === Step 8: Download WhatsApp Birthday Wisher Script ===
echo "[INFO] Downloading bot Python script..."
cd "$BOT_PATH"
git clone "$GITHUB_REPO" temp_repo
cp -r temp_repo/$BOT_SUBPATH/*.py "$BOT_PATH" || true
rm -rf temp_repo

# === Step 9: Cleanup (Remove README.md & .sh) ===
find "$BOT_PATH" -type f \( -name "*.sh" -o -name "README.md" \) -delete

# === Step 10: Auto-update ChromeDriver path inside Python script ===
echo "[INFO] Updating ChromeDriver path inside Python script..."
PY_FILE="$BOT_PATH/whatsapp birthday wisher.py"

if [ -f "$PY_FILE" ]; then
    sed -i "s|CHROMEDRIVER_PATH *= *['\"].*['\"]|CHROMEDRIVER_PATH = \"$CHROMEDRIVER_BIN\"|" "$PY_FILE"
    sed -i "s|CHROME_PROFILE_PATH *= *os.path.join(USER_HOME, .*|CHROME_PROFILE_PATH = os.path.join(USER_HOME, \".config\", \"chromium\")|" "$PY_FILE"
    echo "[OK] Updated driver path in Python script."
else
    echo "[WARN] Python file not found at $PY_FILE"
fi

# === Step 11: Show Chromium & Chromedriver versions ===
echo "------------------------------------------------------------"
echo "🧩 Chromium version: $($CHROME_BIN --version 2>/dev/null || echo 'N/A')"
echo "🧩 Chromedriver version: $($CHROMEDRIVER_BIN --version 2>/dev/null || echo 'N/A')"

# === Step 12: Done ===
echo "------------------------------------------------------------"
echo "✅ INSTALLATION COMPLETE!"
echo "📁 Bot Path: $BOT_PATH"
echo "📂 Virtual Environment: $VENV_PATH"
echo "📄 Phone number stored in: $REPORT_FILE"
echo
echo "🐍 Python version: $(python --version)"
echo "💡 To start manually:"
echo "  cd \"$BOT_PATH\""
echo "  source \"$VENV_PATH/bin/activate\""
echo "  python3 'whatsapp birthday wisher.py'"
echo "------------------------------------------------------------"
