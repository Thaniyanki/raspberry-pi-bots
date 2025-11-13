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

# === Check required commands ===
check_commands() {
    local commands=("curl" "git" "python3" "pip3")
    for cmd in "${commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            echo "[ERROR] Required command not found: $cmd"
            exit 1
        fi
    done
}

# === Function to get all folders from GitHub repo ===
get_all_folders() {
    echo "[INFO] Scanning GitHub repository for bot folders..."
    
    local response
    response=$(curl -s -f "$GITHUB_API" || {
        echo "[ERROR] Failed to fetch repository contents from GitHub API"
        exit 1
    })
    
    echo "$response" | \
    grep '"name":' | \
    grep -v '\.' | \
    cut -d'"' -f4 | \
    while read -r folder; do
        # Skip the all-in-one-venv folder to avoid recursion
        if [[ "$folder" == "all-in-one-venv" ]]; then
            continue
        fi
        
        # Check if folder contains any .sh files
        local folder_content
        folder_content=$(curl -s -f "$GITHUB_API/$folder" 2>/dev/null || echo "")
        if echo "$folder_content" | grep -q '\.sh";'; then
            echo "$folder"
        fi
    done
}

# === Function to get .sh files from a folder ===
get_sh_files_from_folder() {
    local folder="$1"
    local response
    response=$(curl -s -f "$GITHUB_API/$folder" 2>/dev/null || echo "")
    
    echo "$response" | \
    grep '"name".*\.sh"' | \
    cut -d'"' -f4
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

# === Function to run a shell script ===
run_bot_script() {
    local folder="$1"
    local script="$2"
    local script_url="$GITHUB_RAW/$folder/$script"
    
    echo ""
    echo "🔧 RUNNING: $folder/$script"
    echo "----------------------------------------"
    
    # Download and run the script with error handling
    if curl -sL "$script_url" | bash; then
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

# === Main Installation Process ===
main() {
    # Check required commands
    check_commands
    
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
        echo "[INFO] Please check your GitHub repository structure"
        exit 1
    fi

    echo "[INFO] Found folders with .sh files:"
    echo "$folders_with_sh" | while read -r folder; do
        echo "   📁 $folder"
    done

    # Process each folder
    local success_count=0
    local total_count=0
    
    while IFS= read -r folder; do
        ((total_count++))
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
        echo "$sh_files" | while read -r script; do
            echo "   📜 $script"
        done

        # Convert folder name to display name (remove hyphens)
        bot_display_name=$(echo "$folder" | sed 's/-/ /g')
        
        # Setup environment first
        if setup_bot_environment "$folder" "$bot_display_name"; then
            # Run each .sh file
            while IFS= read -r script; do
                # Skip scripts that might cause issues
                if [[ "$script" == *"all in one venv"* ]] || [[ "$script" == *"setup.sh"* ]]; then
                    echo "[INFO] Skipping script: $script"
                    continue
                fi
                
                if run_bot_script "$folder" "$script"; then
                    ((success_count++))
                fi
            done <<< "$sh_files"
        fi
        
        echo "✅ COMPLETED FOLDER: $folder"
    done <<< "$folders_with_sh"

    # Final Summary
    echo ""
    echo "================================================================"
    echo "🎉 AUTO-DETECT SETUP COMPLETED!"
    echo "================================================================"
    echo "📁 Bots Directory: $BOTS_DIR"
    echo ""
    echo "📊 SUMMARY:"
    echo "   Total folders processed: $total_count"
    echo "   Successful scripts: $success_count"
    echo ""
    echo "🤖 PROCESSED FOLDERS:"
    echo "$folders_with_sh" | while read -r folder; do
        bot_display_name=$(echo "$folder" | sed 's/-/ /g')
        echo "   ✅ $bot_display_name"
    done
    echo ""
    echo "💡 All detected bots are ready!"
    echo "================================================================"
}

# Run main function
main "$@"
