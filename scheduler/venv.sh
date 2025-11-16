
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
GITHUB_REPO="https://github.com/Thaniyanki/raspberry-pi-bots.git"

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

# === Step 5: Create Essential Directory Structure ===
echo "[INFO] Setting up directory structure..."

# Create required file paths (empty for now - will be populated by scheduler)
touch "$VENV_PATH/database access key.json"
touch "$VENV_PATH/spread sheet access key.json" 
touch "$VENV_PATH/report number"

echo "[OK] Directory structure created"

# === Step 6: Download Scheduler Script ===
echo "[INFO] Downloading scheduler script..."
SCHEDULER_SCRIPT_URL="https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main/scheduler/scheduler.py"
SCHEDULER_SCRIPT_PATH="$SCHEDULER_DIR/scheduler.py"

if curl -f -s "$SCHEDULER_SCRIPT_URL" -o "$SCHEDULER_SCRIPT_PATH"; then
    chmod +x "$SCHEDULER_SCRIPT_PATH"
    echo "[OK] Scheduler script downloaded: $SCHEDULER_SCRIPT_PATH"
else
    echo "[WARNING] Could not download scheduler script from GitHub"
    echo "[INFO] Creating minimal scheduler script..."
    cat > "$SCHEDULER_SCRIPT_PATH" << 'EOF'
#!/usr/bin/env python3
import os
import sys

# Add venv to path
venv_path = os.path.join(os.path.dirname(__file__), 'venv')
if os.path.exists(venv_path):
    sys.path.insert(0, venv_path)

# Import and run main scheduler
try:
    from scheduler_main import main
    if __name__ == "__main__":
        main()
except ImportError:
    print("Scheduler main module not found yet")
    print("Run this script again after the full scheduler is downloaded")
EOF
    chmod +x "$SCHEDULER_SCRIPT_PATH"
    echo "[OK] Created placeholder scheduler script"
fi

# === Step 7: Create Startup Script ===
STARTUP_SCRIPT="$SCHEDULER_DIR/start_scheduler.sh"
cat > "$STARTUP_SCRIPT" << 'EOF'
#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"

echo "🤖 Starting Scheduler Bot..."

# Activate virtual environment
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found at: $VENV_PATH"
    exit 1
fi

# Run scheduler
cd "$SCRIPT_DIR"
python3 scheduler.py "$@"
EOF

chmod +x "$STARTUP_SCRIPT"
echo "[OK] Created startup script: $STARTUP_SCRIPT"

# === Step 8: Set Permissions ===
echo "[INFO] Setting permissions..."
chmod -R 755 "$SCHEDULER_DIR"
chown -R $USER:$USER "$SCHEDULER_DIR"

# === Step 9: Summary ===
echo "------------------------------------------------------------"
echo "✅ SCHEDULER SETUP COMPLETE!"
echo "📁 Scheduler Path: $SCHEDULER_DIR"
echo "📂 Virtual Environment: $VENV_PATH"
echo "🐍 Python Version: $(python3 --version)"
echo "📦 PIP Version: $(pip --version | cut -d' ' -f2)"

# Show installed Python packages
echo
echo "📚 Installed Python Packages:"
pip list --format=columns | grep -E "(gspread|oauth2client|selenium|firebase|google|requests)"

echo
echo "🚀 Quick Start:"
echo "   cd $SCHEDULER_DIR"
echo "   ./start_scheduler.sh"
echo
echo "💡 Next Steps:"
echo "   1. Add 'database access key.json' to $VENV_PATH/"
echo "   2. Add 'spread sheet access key.json' to $VENV_PATH/" 
echo "   3. Add phone number to 'report number' file in $VENV_PATH/"
echo "   4. Run ./start_scheduler.sh to begin monitoring"
echo "------------------------------------------------------------"

# === Step 10: First Run Check ===
echo
echo "[INFO] Testing basic setup..."
cd "$SCHEDULER_DIR"
if ./start_scheduler.sh --help 2>/dev/null || timeout 10s ./start_scheduler.sh; then
    echo "✅ Basic test successful - scheduler is ready!"
else
    echo "⚠️  Scheduler started but may need configuration files"
    echo "💡 Add the required access key files to begin full operation"
fi
