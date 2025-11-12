#!/usr/bin/env bash
set -e

echo "------------------------------------------------------------"
echo "🤖 FACEBOOK PROFILE LIKER INSTALLER (Raspberry Pi Universal)"
echo "------------------------------------------------------------"

# === Variables ===
HOME_DIR="$HOME"
BOTS_DIR="$HOME_DIR/Bots"
BOT_NAME="Facebook profile liker"
BOT_PATH="$BOTS_DIR/$BOT_NAME"
VENV_PATH="$BOT_PATH/venv"
REPORT_FILE="$VENV_PATH/Report number"
SPREADSHEET_KEY_FILE="$VENV_PATH/spread sheet access key.json"
DATABASE_KEY_FILE="$BOTS_DIR/database access key.json"
PHONE_NUMBER="9940585709"  # Replace with your actual phone number
GITHUB_REPO="https://github.com/Thaniyanki/raspberry-pi-bots.git"
BOT_SUBPATH="facebook-profile-liker"

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
mkdir -p "$VENV_PATH"
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
    google-cloud-storage google-cloud-firestore psutil pyautogui python3-xlib requests Pillow \
    oauth2client python-dateutil google-api-python-client

# === Step 5: Create Required Files ===
echo "$PHONE_NUMBER" > "$REPORT_FILE"
echo "[OK] Created phone number file: $REPORT_FILE"

# Create placeholder files for credentials (user needs to replace with actual files)
touch "$SPREADSHEET_KEY_FILE"
touch "$DATABASE_KEY_FILE"

echo "[INFO] Created placeholder credential files:"
echo "       - $SPREADSHEET_KEY_FILE"
echo "       - $DATABASE_KEY_FILE"
echo "[IMPORTANT] Please replace these with your actual credential files after installation"

# === Step 6: Download Python Script ===
echo "[INFO] Downloading bot script..."
cd "$BOT_PATH"

# Method 1: Try to clone from GitHub
if command -v git >/dev/null 2>&1; then
    echo "[INFO] Attempting to download from GitHub..."
    git clone "$GITHUB_REPO" temp_repo 2>/dev/null || true
    if [ -d "temp_repo" ]; then
        if [ -d "temp_repo/$BOT_SUBPATH" ]; then
            cp -r temp_repo/$BOT_SUBPATH/* "$BOT_PATH" 2>/dev/null || true
        else
            # If specific subpath doesn't exist, copy all Python files
            find temp_repo -name "*.py" -exec cp {} "$BOT_PATH" \; 2>/dev/null || true
        fi
        rm -rf temp_repo
    fi
fi

# Method 2: If no Python files found, create a basic script structure
if [ -z "$(find "$BOT_PATH" -name "*.py" -type f)" ]; then
    echo "[INFO] Creating basic script structure..."
    cat > "$BOT_PATH/facebook_profile_liker.py" << 'EOF'
# Facebook Profile Liker - Basic Structure
print("Facebook Profile Liker - Please download the full script from GitHub")
print("Repository: https://github.com/Thaniyanki/raspberry-pi-bots")
EOF
fi

# Clean up any unnecessary files
find "$BOT_PATH" -type f \( -name "*.sh" -o -name "README.md" -o -name "*.txt" \) -delete 2>/dev/null || true

# === Step 7: Create Essential Directories ===
mkdir -p "$HOME_DIR/.config/chromium"
echo "[OK] Created Chromium profile directory"

# === Step 8: Create Desktop Shortcut ===
DESKTOP_FILE="$HOME_DIR/Desktop/Facebook Profile Liker.desktop"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Facebook Profile Liker
Comment=Automated Facebook Profile Liker Bot
Exec=gnome-terminal --working-directory="$BOT_PATH" -- bash -c 'source "$VENV_PATH/bin/activate" && python3 "Facebook profile liker.py"; bash'
Icon=facebook
Terminal=true
StartupNotify=false
Categories=Utility;
EOF

chmod +x "$DESKTOP_FILE"
echo "[OK] Created desktop shortcut: $DESKTOP_FILE"

# === Step 9: Create Startup Script ===
STARTUP_SCRIPT="$BOT_PATH/start_bot.sh"
cat > "$STARTUP_SCRIPT" << EOF
#!/usr/bin/env bash
cd "$BOT_PATH"
source "$VENV_PATH/bin/activate"
python3 "Facebook profile liker.py"
EOF

chmod +x "$STARTUP_SCRIPT"
echo "[OK] Created startup script: $STARTUP_SCRIPT"

# === Step 10: Create Configuration Check Script ===
CONFIG_CHECK="$BOT_PATH/check_config.sh"
cat > "$CONFIG_CHECK" << 'EOF'
#!/usr/bin/env bash
echo "🔧 Facebook Profile Liker - Configuration Check"
echo "=============================================="

# Check required files
echo "📁 Checking required files:"
REQUIRED_FILES=(
    "venv/spread sheet access key.json"
    "../database access key.json" 
    "venv/Report number"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file - FOUND"
    else
        echo "❌ $file - MISSING"
    fi
done

# Check Python environment
echo
echo "🐍 Checking Python environment:"
if source venv/bin/activate && python3 -c "import selenium, gspread, firebase_admin"; then
    echo "✅ Python dependencies - OK"
else
    echo "❌ Python dependencies - MISSING"
fi

# Check Chromium
echo
echo "🌐 Checking Chromium:"
if command -v chromium >/dev/null || command -v chromium-browser >/dev/null; then
    echo "✅ Chromium - INSTALLED"
else
    echo "❌ Chromium - NOT FOUND"
fi

# Check Chromedriver
echo
echo "🔧 Checking Chromedriver:"
if command -v chromedriver >/dev/null; then
    echo "✅ Chromedriver - INSTALLED"
else
    echo "❌ Chromedriver - NOT FOUND"
fi

echo
echo "=============================================="
echo "📝 NEXT STEPS:"
echo "1. Add your Google Sheets credentials to: venv/spread sheet access key.json"
echo "2. Add your Firebase credentials to: ../database access key.json" 
echo "3. Update phone number in: venv/Report number"
echo "4. Run: ./start_bot.sh"
echo "=============================================="
EOF

chmod +x "$CONFIG_CHECK"
echo "[OK] Created configuration check script: $CONFIG_CHECK"

# === Step 11: Set Proper Permissions ===
chmod -R 755 "$BOT_PATH"
echo "[OK] Set proper permissions"

# === Step 12: Summary ===
echo "------------------------------------------------------------"
echo "✅ FACEBOOK PROFILE LIKER INSTALLATION COMPLETE!"
echo "------------------------------------------------------------"
echo "📁 Bot Path: $BOT_PATH"
echo "📂 Virtual Environment: $VENV_PATH"
echo "🔑 Credential Files:"
echo "   - Spreadsheet Key: $SPREADSHEET_KEY_FILE"
echo "   - Database Key: $DATABASE_KEY_FILE"
echo "   - Report Number: $REPORT_FILE"
echo
echo "🌐 Browser Setup:"
echo "   - Chromium: $($CHROME_BIN --version)"
echo "   - Chromedriver: $($CHROMEDRIVER_BIN --version)"
echo
echo "🚀 Quick Start Options:"
echo "   1. Desktop: Double-click 'Facebook Profile Liker' on desktop"
echo "   2. Terminal: cd '$BOT_PATH' && ./start_bot.sh"
echo "   3. Check config: cd '$BOT_PATH' && ./check_config.sh"
echo
echo "📋 IMPORTANT NEXT STEPS:"
echo "   1. Replace placeholder credential files with your actual files:"
echo "      - Google Sheets service account JSON"
echo "      - Firebase service account JSON"
echo "   2. Update the phone number in 'venv/Report number' if needed"
echo "   3. Run the configuration check: ./check_config.sh"
echo "------------------------------------------------------------"

# Run configuration check
echo
echo "🔧 Running initial configuration check..."
cd "$BOT_PATH"
bash "$CONFIG_CHECK"
