#!/usr/bin/env bash
set -e

echo "================================================================"
echo "🚀 TRUE AUTO-DETECT ALL BOTS VENV SETUP"
echo "================================================================"

# === Variables ===
HOME_DIR="$HOME"
BOTS_DIR="$HOME_DIR/bots"
GITHUB_REPO="https://github.com/Thaniyanki/raspberry-pi-bots"
GITHUB_RAW="https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main"
PHONE_NUMBER="9940585709"

OS=$(uname -s)
ARCH=$(uname -m)
echo "[INFO] Detected OS: $OS | Architecture: $ARCH"

# === Predefined bot list as fallback ===
PREDEFINED_BOTS=(
    "whatsapp-messenger"
    "whatsapp-birthday-wisher"
    "facebook-birthday-wisher" 
    "facebook-profile-liker"
)

# === Function to get folders using simple approach ===
get_all_folders_simple() {
    echo "[INFO] Using predefined bot list (GitHub scan failed)"
    for bot in "${PREDEFINED_BOTS[@]}"; do
        echo "$bot"
    done
}

# === Function to check if folder has venv.sh ===
check_folder_has_venv() {
    local folder="$1"
    local venv_url="$GITHUB_RAW/$folder/venv.sh"
    
    # Check if venv.sh exists by making a HEAD request
    if curl -s --head "$venv_url" | head -n1 | grep -q "200"; then
        echo "true"
    else
        echo "false"
    fi
}

# === Function to install system dependencies ===
install_system_deps() {
    echo "[INFO] Installing system dependencies..."
    sudo apt update -y
    
    sudo apt install -y python3 python3-venv python3-pip git curl wget unzip build-essential x11-utils \
        libnss3 libxkbcommon0 libdrm2 libgbm1 libxshmfence1 libjpeg-dev zlib1g-dev \
        libfreetype6-dev liblcms2-dev libopenjp2-7-dev libtiff-dev libwebp-dev tk-dev \
        libharfbuzz-dev libfribidi-dev libxcb1-dev || true

    # Try installing "t64" versions safely
    for pkg in libasound2t64 libatk-bridge2.0-0t64; do
        if apt-cache show "$pkg" >/dev/null 2>&1; then
            sudo apt install -y "$pkg" || true
        fi
    done
}

# === Function to install Chromium ===
install_chromium() {
    echo "[INFO] Installing Chromium and Chromedriver..."
    if [[ "$ARCH" == "armv7l" ]]; then
        echo "[INFO] 32-bit Raspberry Pi detected."
        sudo apt install -y chromium chromium-driver || sudo apt install -y chromium-browser chromium-chromedriver || true
    else
        echo "[INFO] 64-bit Raspberry Pi detected."
        sudo apt install -y chromium chromium-driver || true
    fi

    CHROME_BIN=$(command -v chromium-browser || command -v chromium || echo "")
    CHROMEDRIVER_BIN=$(command -v chromedriver || command -v chromium-chromedriver || echo "")

    if [ -z "$CHROME_BIN" ] || [ -z "$CHROMEDRIVER_BIN" ]; then
        echo "[WARNING] Chromium or Chromedriver not found after install!"
        echo "[INFO] Continuing without Chromium (some bots may not work)"
        return 1
    fi
    sudo chmod +x "$CHROMEDRIVER_BIN"

    echo "[OK] Chromium: $($CHROME_BIN --version || echo "Not available")"
    echo "[OK] Chromedriver: $($CHROMEDRIVER_BIN --version || echo "Not available")"
    return 0
}

# === Function to setup bot environment ===
setup_bot_environment() {
    local bot_folder="$1"
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
        if python3 -m venv "$venv_path"; then
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
            echo "[ERROR] Failed to create virtual environment for $bot_display_name"
            return 1
        fi
    else
        echo "[INFO] Virtual environment already exists, skipping..."
    fi

    echo "✅ ENVIRONMENT READY: $bot_display_name"
    return 0
}

# === Function to run bot setup script ===
run_bot_setup() {
    local bot_folder="$1"
    local bot_display_name="$2"
    
    echo ""
    echo "🚀 SETTING UP: $bot_display_name"
    echo "========================================"
    
    # Try to run the venv.sh script for this bot
    local setup_script_url="$GITHUB_RAW/$bot_folder/venv.sh"
    
    echo "[INFO] Running setup script: $setup_script_url"
    
    # Setup environment first
    if setup_bot_environment "$bot_folder" "$bot_display_name"; then
        # Run the setup script
        if bash <(curl -sL "$setup_script_url"); then
            echo "✅ SUCCESS: $bot_display_name"
            return 0
        else
            echo "❌ FAILED: $bot_display_name"
            return 1
        fi
    else
        echo "❌ FAILED: Could not setup environment for $bot_display_name"
        return 1
    fi
}

# === Function to create folder structure for WhatsApp Messenger ===
create_whatsapp_folders() {
    local bot_path="$BOTS_DIR/whatsapp messenger"
    
    if [ -d "$bot_path" ]; then
        echo "[INFO] Creating folder structure for WhatsApp Messenger..."
        CURRENT_DATE=$(date +"%d-%m-%Y")
        
        # Create main folders
        mkdir -p "$bot_path/Image" "$bot_path/Document" "$bot_path/Audio" "$bot_path/Video"
        touch "$bot_path/Image/Caption.txt" "$bot_path/Document/Caption.txt" "$bot_path/Audio/Caption.txt" "$bot_path/Video/Caption.txt"
        
        # Create date subfolders
        mkdir -p "$bot_path/Image/$CURRENT_DATE" "$bot_path/Document/$CURRENT_DATE" "$bot_path/Audio/$CURRENT_DATE" "$bot_path/Video/$CURRENT_DATE"
        touch "$bot_path/Image/$CURRENT_DATE/Caption.txt" "$bot_path/Document/$CURRENT_DATE/Caption.txt" "$bot_path/Audio/$CURRENT_DATE/Caption.txt" "$bot_path/Video/$CURRENT_DATE/Caption.txt"
        
        echo "[OK] Created folder structure with date: $CURRENT_DATE"
    fi
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

    # Get folders (using simple approach)
    echo "[INFO] Getting bot folders..."
    ALL_FOLDERS=$(get_all_folders_simple)
    
    # Check which folders have venv.sh
    echo ""
    echo "[INFO] Checking which bots have venv.sh setup scripts..."
    BOTS_TO_SETUP=""
    
    while read -r folder; do
        if [ "$(check_folder_has_venv "$folder")" = "true" ]; then
            echo "   ✅ $folder (has venv.sh)"
            BOTS_TO_SETUP="${BOTS_TO_SETUP}$folder"$'\n'
        else
            echo "   ❌ $folder (no venv.sh)"
        fi
    done <<< "$ALL_FOLDERS"

    if [ -z "$BOTS_TO_SETUP" ]; then
        echo "[ERROR] No bots with venv.sh found!"
        exit 1
    fi

    echo ""
    echo "[INFO] Starting setup for bots with venv.sh..."
    
    local success_count=0
    local total_count=0
    
    # Process each bot that has venv.sh
    while read -r bot_folder; do
        [ -z "$bot_folder" ] && continue
        ((total_count++))
        
        # Convert folder name to display name (replace hyphens with spaces)
        bot_display_name=$(echo "$bot_folder" | sed 's/-/ /g')
        
        if run_bot_setup "$bot_folder" "$bot_display_name"; then
            ((success_count++))
        fi
        
        echo ""
        sleep 2  # Small delay between bots
    done <<< "$BOTS_TO_SETUP"

    # Create special folder structure for WhatsApp Messenger
    create_whatsapp_folders

    # Final Summary
    echo ""
    echo "================================================================"
    echo "🎉 AUTO-DETECT SETUP COMPLETED!"
    echo "================================================================"
    echo "📁 Bots Directory: $BOTS_DIR"
    echo ""
    echo "📊 SUMMARY:"
    echo "   Total bots found: $total_count"
    echo "   Successful setups: $success_count"
    echo ""
    echo "🤖 INSTALLED BOTS:"
    while read -r bot_folder; do
        [ -z "$bot_folder" ] && continue
        bot_display_name=$(echo "$bot_folder" | sed 's/-/ /g')
        echo "   ✅ $bot_display_name"
    done <<< "$BOTS_TO_SETUP"
    echo ""
    echo "🌐 Chromium: $(command -v chromium-browser || command -v chromium | xargs --version)"
    echo "🔧 Chromedriver: $(command -v chromedriver || command -v chromium-chromedriver | xargs --version)"
    echo ""
    echo "💡 All detected bots are ready!"
    echo "================================================================"
}

# Run main function
main "$@"
