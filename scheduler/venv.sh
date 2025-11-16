#!/usr/bin/env bash
set -e

echo "------------------------------------------------------------"
echo "🤖 SCHEDULER BOT SETUP (Raspberry Pi Universal)"
echo "------------------------------------------------------------"

# === Variables ===
HOME_DIR="$HOME"
BOTS_DIR="$HOME_DIR/bots"
BOT_NAME="scheduler"
BOT_PATH="$BOTS_DIR/$BOT_NAME"
VENV_PATH="$BOT_PATH/venv"
REPORT_FILE="$VENV_PATH/report number"
PHONE_NUMBER="9940585709"

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
sudo apt install -y python3 python3-venv python3-pip git curl

# === Step 3: Python Virtual Environment ===
echo "[INFO] Creating Python virtual environment..."
if [ -d "$VENV_PATH" ]; then
    echo "[INFO] Removing old virtual environment..."
    rm -rf "$VENV_PATH"
fi
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

pip install --upgrade pip setuptools wheel

# === Step 4: Install EXACT Python Dependencies from Your Code ===
echo "[INFO] Installing Python dependencies from scheduler code..."

# Core Python standard library (already available)
echo "[OK] Python standard libraries: os, time, json, subprocess, shutil, re, sys, pathlib"

# Google Sheets API (from your try/except block)
pip install gspread oauth2client

# Additional dependencies used in your code
pip install firebase_admin google-auth google-auth-oauthlib \
    google-cloud-storage google-cloud-firestore psutil \
    pyautogui python3-xlib requests Pillow python-dateutil

echo "[OK] All Python dependencies installed"

# === Step 5: Create Phone Number File ===
echo "$PHONE_NUMBER" > "$REPORT_FILE"
echo "[OK] Created phone number file: $REPORT_FILE"

# === Step 6: Summary ===
echo "------------------------------------------------------------"
echo "✅ SCHEDULER SETUP COMPLETE!"
echo "📁 Bot Path: $BOT_PATH"
echo "📂 Virtual Environment: $VENV_PATH"
echo "📄 Phone number file: $REPORT_FILE"
echo
echo "🐍 Python Dependencies Installed:"
echo "   ✅ gspread, oauth2client (Google Sheets API)"
echo "   ✅ firebase_admin, google-cloud-* (Firebase)"
echo "   ✅ selenium (Web automation)"
echo "   ✅ psutil, pyautogui, python3-xlib (System control)"
echo "   ✅ requests, Pillow (HTTP & Image processing)"
echo "   ✅ python-dateutil (Date utilities)"
echo
echo "💡 Ready for scheduler operation!"
echo "📝 The scheduler will handle all bot management automatically"
echo "------------------------------------------------------------"
