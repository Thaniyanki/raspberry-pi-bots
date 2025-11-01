#!/usr/bin/env bash
set -e

echo "------------------------------------------------------------"
echo "🤖 WHATSAPP BIRTHDAY WISHER INSTALLER (Universal for Raspberry Pi)"
echo "------------------------------------------------------------"

# === Basic Paths ===
HOME_DIR="$HOME"
BOT_DIR="$HOME_DIR/bot"
BOT_NAME="whatsapp birthday wisher"
BOT_PATH="$BOT_DIR/$BOT_NAME"
VENV_PATH="$BOT_PATH/venv"

echo "[INFO] Detected OS: $(uname -s) | Architecture: $(uname -m)"

# === Step 1: Create Folder Structure ===
if [ ! -d "$BOT_PATH" ]; then
    echo "[INFO] 'bot' folder not found, creating new structure..."
    mkdir -p "$BOT_PATH"
fi

if [ -d "$VENV_PATH" ]; then
    echo "[INFO] Old venv found, deleting..."
    rm -rf "$VENV_PATH"
fi

mkdir -p "$VENV_PATH"
echo "[OK] Folder ready: $VENV_PATH"

# === Step 2: Install System Dependencies ===
echo "[INFO] Installing system dependencies..."
sudo apt update -y
sudo apt install -y python3 python3-venv python3-pip git curl unzip build-essential \
    libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7-dev \
    libtiff-dev libwebp-dev tk-dev libharfbuzz-dev libfribidi-dev libxcb1-dev

# === Step 3: Create Python Virtual Environment ===
echo "[INFO] Creating Python virtual environment..."
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

# === Step 4: Upgrade pip & setuptools ===
pip install --upgrade pip setuptools wheel

# === Step 5: Install Python Packages ===
echo "[INFO] Installing Python packages..."
pip install --no-cache-dir firebase_admin gspread selenium google-auth google-auth-oauthlib \
    google-cloud-storage google-cloud-firestore psutil pyautogui python3-xlib requests Pillow oauth2client

# === Step 6: Download Bot Source Code ===
echo "[INFO] Downloading latest bot source from GitHub..."
cd "$BOT_PATH"
if [ -d ".git" ]; then
    git pull
else
    git clone https://github.com/Thaniyanki/raspberry-pi-bots.git temp_repo
    cp -r temp_repo/whatsapp-birthday-wisher/* "$BOT_PATH" || true
    rm -rf temp_repo
fi

# === Step 7: Completion ===
echo "------------------------------------------------------------"
echo "✅ Installation Complete!"
echo "📂 Bot Folder: $BOT_PATH"
echo "💡 To activate manually:"
echo "    source \"$VENV_PATH/bin/activate\""
echo "    python3 main.py"
echo "------------------------------------------------------------"
