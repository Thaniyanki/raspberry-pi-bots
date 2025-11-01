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
echo "[OK] Created: $BOT_PATH"

# === Step 2: System Packages ===
echo "[INFO] Installing system dependencies..."
sudo apt update -y
sudo apt install -y python3 python3-venv python3-pip git curl unzip build-essential \
    libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7-dev \
    libtiff-dev libwebp-dev tk-dev libharfbuzz-dev libfribidi-dev libxcb1-dev

# === Step 3: Create Virtual Environment ===
echo "[INFO] Creating new Python virtual environment..."
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

# === Step 4: Upgrade pip & setuptools ===
pip install --upgrade pip setuptools wheel

# === Step 5: Install Python Libraries ===
echo "[INFO] Installing required Python packages..."
pip install --no-cache-dir firebase_admin gspread selenium google-auth google-auth-oauthlib \
    google-cloud-storage google-cloud-firestore psutil pyautogui python3-xlib requests Pillow oauth2client

# === Step 6: Create Phone Number File ===
echo "$PHONE_NUMBER" > "$REPORT_FILE"
echo "[OK] Created phone number file inside venv: $REPORT_FILE"

# === Step 7: Download Bot Script ===
echo "[INFO] Downloading latest WhatsApp Birthday Wisher bot..."
cd "$BOT_PATH"
git clone "$GITHUB_REPO" temp_repo
cp -r temp_repo/$BOT_SUBPATH/*.py "$BOT_PATH" || true
rm -rf temp_repo

# === Step 8: Cleanup README and shell scripts ===
echo "[INFO] Removing unnecessary files..."
rm -f "$BOT_PATH/README.md" "$BOT_PATH/"*.sh 2>/dev/null || true

# === Step 9: Done ===
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
