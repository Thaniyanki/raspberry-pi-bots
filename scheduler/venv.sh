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
PHONE_NUMBER="9940585709"
REPORT_FILE="$VENV_PATH/report number"

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
sudo apt install -y python3 python3-venv python3-pip git curl

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
pip install --upgrade pip

# Install ONLY the required packages from your code
pip install gspread oauth2client google-auth google-auth-oauthlib
pip install firebase_admin google-cloud-storage google-cloud-firestore
pip install selenium psutil pyautogui python3-xlib requests
pip install Pillow python-dateutil

echo "[OK] Python dependencies installed"

# === Step 5: Create ONLY Report Number File ===
echo "[INFO] Creating report number file..."
echo "$PHONE_NUMBER" > "$REPORT_FILE"
echo "[OK] Report number file created: $REPORT_FILE"
echo "[OK] Phone number: $(cat "$REPORT_FILE")"

# === Step 6: Set Permissions ===
chmod -R 755 "$SCHEDULER_DIR"
chown -R $USER:$USER "$SCHEDULER_DIR"

# === Step 7: Final Summary ===
echo "------------------------------------------------------------"
echo "✅ SCHEDULER SETUP COMPLETE!"
echo "📁 Scheduler Path: $SCHEDULER_DIR"
echo "📂 Virtual Environment: $VENV_PATH"
echo "📞 Report Number File: $REPORT_FILE"
echo "📞 Phone Number: $(cat "$REPORT_FILE")"

echo
echo "📚 Installed Python Packages:"
pip list --format=columns

echo
echo "🎉 Setup completed successfully!"
echo "💡 Only created: 'report number' file with your phone number"
echo "📝 No other files created (no database keys, spreadsheet keys, scripts)"
echo "------------------------------------------------------------"
