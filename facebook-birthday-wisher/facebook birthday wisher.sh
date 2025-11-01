#!/usr/bin/env bash
#!/usr/bin/env bash
set -e

echo "------------------------------------------------------------"
echo "📘 FACEBOOK BIRTHDAY WISHER INSTALLER (Universal for Raspberry Pi)"
echo "------------------------------------------------------------"

HOME_DIR="$HOME"
BOT_DIR="$HOME_DIR/bot"
BOT_NAME="facebook birthday wisher"
BOT_PATH="$BOT_DIR/$BOT_NAME"
VENV_PATH="$BOT_PATH/venv"

# ✅ Corrected: use RAW GitHub URL instead of blob
FACEBOOK_BOT_URL="https://raw.githubusercontent.com/Thaniyanki/Raspberry-Pi-Bots/main/facebook-birthday-wisher/facebook%20birthday%20wisher.py"
PHONE_NUMBER="9940585709"

# Detect OS and architecture
OS=$(uname -s)
ARCH=$(uname -m)
echo "[INFO] Detected OS: $OS | Architecture: $ARCH"

# --- STEP 1 : Check if bot folder exists ---
if [ -d "$BOT_DIR" ]; then
    echo "[INFO] Found existing 'bot' folder ✅"
    # --- STEP 2 : Handle facebook birthday wisher folder ---
    if [ -d "$BOT_PATH" ]; then
        echo "[INFO] Removing old '$BOT_NAME' folder..."
        rm -rf "$BOT_PATH"
    fi
    echo "[INFO] Creating fresh '$BOT_NAME' folder inside bot directory..."
    mkdir -p "$BOT_PATH"
else
    # --- STEP 3 : Create bot folder and structure ---
    echo "[INFO] 'bot' folder not found, creating new structure..."
    mkdir -p "$BOT_PATH/venv"
    echo "[OK] Created: $BOT_PATH/venv"
fi

# --- STEP 5 : Create or recreate venv and install dependencies ---
echo "[INFO] Preparing virtual environment..."
cd "$BOT_PATH"

if [ -d "venv" ]; then
    echo "[INFO] Old venv found, deleting..."
    rm -rf venv
fi

mkdir -p venv
VENV_DIR="$PWD/venv"
echo "[OK] Folder ready: $VENV_DIR"

# Install system dependencies
echo "[INFO] Installing system dependencies..."
sudo apt-get update -y || true
sudo apt-get install -y python3 python3-venv python3-pip git curl unzip || true

# Create and activate venv
echo "[INFO] Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip setuptools wheel

echo "[INFO] Installing Python packages..."
pip install firebase_admin gspread selenium google-auth google-auth-oauthlib \
    google-cloud-storage google-cloud-firestore psutil pyautogui python3-xlib requests Pillow oauth2client

# Create phone number file
REPORT_FILE="$VENV_DIR/report number"
echo "$PHONE_NUMBER" > "$REPORT_FILE"
echo "[OK] Created phone number file: '$REPORT_FILE'"

# --- STEP 4 : Download facebook birthday wisher script ---
cd "$BOT_PATH"
echo "[INFO] Downloading main bot script..."
curl -L -o "facebook birthday wisher.py" "$FACEBOOK_BOT_URL"

if [ -f "facebook birthday wisher.py" ]; then
    echo "[OK] Bot script downloaded successfully."
else
    echo "[ERROR] Bot script download failed!"
fi

echo
echo "------------------------------------------------------------"
echo "✅ INSTALLATION COMPLETE!"
echo "📁 Bot Folder: $BOT_PATH"
echo "📦 Virtual Environment: $VENV_DIR"
echo "🐍 To activate venv, run:"
echo "   source \"$VENV_DIR/bin/activate\""
echo "🚀 To run your bot:"
echo "   python3 \"facebook birthday wisher.py\""
echo "------------------------------------------------------------"
echo "[INFO] Detected OS: $OS | Arch: $ARCH"
