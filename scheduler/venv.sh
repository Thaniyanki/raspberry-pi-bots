#!/usr/bin/env bash
set -e

echo "------------------------------------------------------------"
echo "🤖 SCHEDULER BOT SETUP (Raspberry Pi Universal)"
echo "------------------------------------------------------------"

# === Variables ===
HOME_DIR="$HOME"
BOTS_DIR="$HOME_DIR/bots"
SCHEDULER_DIR="$BOTS_DIR/scheduler"
VENV_PATH="$SCHEDULER_DIR/venv"
PHONE_NUMBER="9940585709"  # Change this to your desired phone number
PHONE_FILE="$VENV_PATH/phone_number.txt"

OS=$(uname -s)
ARCH=$(uname -m)
echo "[INFO] Detected OS: $OS | Architecture: $ARCH"

# === Step 1: Folder Setup ===
mkdir -p "$BOTS_DIR"
mkdir -p "$SCHEDULER_DIR"
mkdir -p "$VENV_PATH"
echo "[OK] Created scheduler folder at: $SCHEDULER_DIR"

# === Step 2: System Dependencies ===
echo "[INFO] Installing system dependencies..."
sudo apt update -y

# Core system utilities
sudo apt install -y python3 python3-venv python3-pip git curl unzip build-essential \
    x11-utils wget procps

# Graphics and display libraries
sudo apt install -y libnss3 libxkbcommon0 libdrm2 libgbm1 libxshmfence1 \
    libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7-dev \
    libtiff-dev libwebp-dev tk-dev libharfbuzz-dev libfribidi-dev libxcb1-dev

# Audio libraries
sudo apt install -y libasound2 libpulse0

# Additional Python development libraries
sudo apt install -y libssl-dev libffi-dev libsqlite3-dev libreadline-dev \
    libbz2-dev libncurses5-dev libgdbm-dev

# Try installing "t64" versions safely if available
for pkg in libasound2t64 libatk-bridge2.0-0t64 libpulse0t64; do
    if apt-cache show "$pkg" >/dev/null 2>&1; then
        sudo apt install -y "$pkg"
    fi
done

echo "[OK] System dependencies installed"

# === Step 3: Python Virtual Environment ===
echo "[INFO] Creating Python virtual environment..."
if [ -d "$VENV_PATH" ]; then
    echo "[INFO] Removing old virtual environment..."
    rm -rf "$VENV_PATH"
fi
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

# === Step 4: Python Dependencies ===
echo "[INFO] Installing Python dependencies..."

# Upgrade pip first
pip install --upgrade pip setuptools wheel

# Core Google APIs
pip install --no-cache-dir gspread oauth2client google-auth google-auth-oauthlib

# Firebase dependencies
pip install --no-cache-dir firebase_admin google-cloud-storage google-cloud-firestore

# Web automation and browser control
pip install --no-cache-dir selenium psutil pyautogui python3-xlib requests

# Image processing
pip install --no-cache-dir Pillow

# Date and time utilities
pip install --no-cache-dir python-dateutil

# Additional utilities
pip install --no-cache-dir beautifulsoup4 lxml html5lib

echo "[OK] Python dependencies installed"

# === Step 5: Create Phone Number File ===
echo "[INFO] Creating phone number file..."
echo "$PHONE_NUMBER" > "$PHONE_FILE"
echo "[OK] Phone number file created: $PHONE_FILE"
echo "[OK] Phone number: $(cat "$PHONE_FILE")"

# === Step 6: Set Permissions ===
echo "[INFO] Setting permissions..."
chmod -R 755 "$SCHEDULER_DIR"
chown -R $USER:$USER "$SCHEDULER_DIR"

# === Step 7: Summary ===
echo "------------------------------------------------------------"
echo "✅ SCHEDULER SETUP COMPLETE!"
echo "📁 Scheduler Path: $SCHEDULER_DIR"
echo "📂 Virtual Environment: $VENV_PATH"
echo "📞 Phone Number: $(cat "$PHONE_FILE")"
echo "📞 Phone File: $PHONE_FILE"
echo "🐍 Python Version: $(python3 --version)"
echo "📦 PIP Version: $(pip --version | cut -d' ' -f2)"

# Show installed Python packages
echo
echo "📚 Installed Python Packages:"
pip list --format=columns | grep -E "(gspread|oauth2client|selenium|firebase|google|requests)"

echo
echo "💡 Setup Summary:"
echo "   ✅ Created directory structure"
echo "   ✅ Installed system dependencies" 
echo "   ✅ Created Python virtual environment"
echo "   ✅ Installed all required Python packages"
echo "   ✅ Created phone number file: $PHONE_FILE"
echo "   ✅ Set proper permissions"
echo
echo "🚀 Ready for scheduler integration!"
echo "📝 The scheduler will handle the rest automatically"
echo "------------------------------------------------------------"

# === Step 8: Verification ===
echo
echo "[INFO] Verifying setup..."
if [ -f "$PHONE_FILE" ] && [ -s "$PHONE_FILE" ]; then
    echo "✅ Phone number file verified: $(cat "$PHONE_FILE")"
else
    echo "❌ Phone number file missing or empty"
    exit 1
fi

if [ -d "$VENV_PATH" ] && [ -f "$VENV_PATH/bin/activate" ]; then
    echo "✅ Virtual environment verified"
else
    echo "❌ Virtual environment setup failed"
    exit 1
fi

echo "✅ All verifications passed!"
echo
echo "🎉 Scheduler setup completed successfully!"
