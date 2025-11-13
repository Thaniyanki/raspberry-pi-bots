#!/usr/bin/env bash
set -e

echo "================================================================"
echo "🚀 AUTO-DETECT ALL BOTS VENV SETUP (Raspberry Pi Universal)"
echo "================================================================"

# === Variables ===
HOME_DIR="$HOME"
BOTS_DIR="$HOME_DIR/bots"
GITHUB_REPO="https://github.com/Thaniyanki/raspberry-pi-bots"
GITHUB_API="https://api.github.com/repos/Thaniyanki/raspberry-pi-bots/contents"
GITHUB_RAW="https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main"
PHONE_NUMBER="9940585709"

OS=$(uname -s)
ARCH=$(uname -m)
echo "[INFO] Detected OS: $OS | Architecture: $ARCH"

# === Function to get all folders from GitHub repo ===
get_all_folders() {
    echo "[INFO] Scanning GitHub repository for bot folders..."
    
    # Use GitHub API to get repository contents
    curl -s "$GITHUB_API" | \
    grep '"name":' | \
    grep -v '\.' | \
    cut -d'"' -f4 | \
    while read folder; do
        # Check if folder contains any .sh files
        if curl -s "$GITHUB_API/$folder" | grep -q '\.sh";'; then
            echo "$folder"
        fi
    done
}

# === Function to get .sh files from a folder ===
get_sh_files_from_folder() {
    local folder="$1"
    curl -s "$GITHUB_API/$folder" | \
    grep '"name".*\.sh"' | \
    cut -d'"' -f4
}

# === Function to install system dependencies ===
install_system_deps() {
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
}

# === Function to install Chromium ===
install_chromium() {
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
}

# === Function to run a shell script ===
run_bot_script() {
    local folder="$1"
    local script="$2"
    local script_url="$GITHUB_RAW/$folder/$script"
    
    echo ""
    echo "🔧 RUNNING: $folder/$script"
    echo "----------------------------------------"
    
    # Download and run the script
    if bash <(curl -sL "$script_url"); then
        echo "✅ SUCCESS: $folder/$script"
        return 0
    else
        echo "❌ FAILED: $folder/$script"
        return 1
    fi
}

# === Function to setup bot environment ===
setup_bot_environment() {
    local folder="$1"
    local bot_display_name="$2"
    local bot_path="$BOTS_DIR/$bot_display_name"
    local venv_path="$bot_path/venv"
    local report_file="$venv_path/report number"

    echo ""
    echo "🔧 SETTING UP ENVIRONMENT: $bot_display_name"
    echo "----------------------------------------"

    # Create bot folder
    mkdir -p "$bot_path"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$venv_path" ]; then
        python3 -m venv "$venv_path"
        source "$venv_path/bin/activate"
        
        # Install Python dependencies
        pip install --upgrade pip setuptools wheel
        pip install --no-cache-dir firebase_admin gspread selenium google-auth google-auth-oauthlib \
            google-cloud-storage google-cloud-firestore psutil pyautogui python3-xlib requests Pillow oauth2client python-dateutil
        
        # Create phone number file
        echo "$PHONE_NUMBER" > "$report_file"
        echo "[OK] Created phone number file: $report_file"
        
        deactivate
    else
        echo "[INFO] Virtual environment already exists, skipping..."
    fi

    echo "✅ ENVIRONMENT READY: $bot_display_name"
}

# === Main Installation Process ===
main() {
    # Create bots directory
    mkdir -p "$BOTS_DIR"
    echo "[OK] Created bots directory: $BOTS_DIR"

    # Install system dependencies (once for all bots)
    install_system_deps
    
    # Install Chromium (once for all bots)
    install_chromium

    # Get all folders with .sh files
    echo "[INFO] Discovering bots in repository..."
    folders_with_sh=$(get_all_folders)
    
    if [ -z "$folders_with_sh" ]; then
        echo "[WARNING] No bot folders found in repository!"
        exit 1
    fi

    echo "[INFO] Found folders with .sh files:"
    echo "$folders_with_sh" | while read folder; do
        echo "   📁 $folder"
    done

    # Process each folder
    echo "$folders_with_sh" | while read folder; do
        echo ""
        echo "📦 PROCESSING FOLDER: $folder"
        echo "========================================"
        
        # Get all .sh files in this folder
        sh_files=$(get_sh_files_from_folder "$folder")
        
        if [ -z "$sh_files" ]; then
            echo "[INFO] No .sh files found in $folder, skipping..."
            continue
        fi

        echo "[INFO] Found .sh files in $folder:"
        echo "$sh_files" | while read script; do
            echo "   📜 $script"
        done

        # Convert folder name to display name (remove hyphens)
        bot_display_name=$(echo "$folder" | sed 's/-/ /g')
        
        # Setup environment first
        setup_bot_environment "$folder" "$bot_display_name"
        
        # Run each .sh file
        echo "$sh_files" | while read script; do
            # Skip this all-in-one script to avoid infinite loop
            if [[ "$script" == "all in one venv.sh" ]]; then
                echo "[INFO] Skipping all-in-one script to avoid recursion"
                continue
            fi
            
            run_bot_script "$folder" "$script"
        done
        
        echo "✅ COMPLETED FOLDER: $folder"
    done

    # Final Summary
    echo ""
    echo "================================================================"
    echo "🎉 AUTO-DETECT SETUP COMPLETED!"
    echo "================================================================"
    echo "📁 Bots Directory: $BOTS_DIR"
    echo ""
    echo "🤖 PROCESSED FOLDERS:"
    echo "$folders_with_sh" | while read folder; do
        bot_display_name=$(echo "$folder" | sed 's/-/ /g')
        echo "   ✅ $bot_display_name"
    done
    echo ""
    echo "🌐 Chromium: $(command -v chromium-browser || command -v chromium | xargs --version)"
    echo "🔧 Chromedriver: $(command -v chromedriver || command -v chromium-chromedriver | xargs --version)"
    echo ""
    echo "💡 All detected bots are ready!"
    echo "================================================================"
}

# Run main function
main "$@"
