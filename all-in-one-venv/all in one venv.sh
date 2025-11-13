#!/usr/bin/env python3
import os
import sys
import subprocess
import requests
import time
from datetime import datetime

class AllInOneVenvSetup:
    def __init__(self):
        self.home_dir = os.path.expanduser("~")
        self.bots_dir = os.path.join(self.home_dir, "bots")
        self.github_repo = "https://github.com/Thaniyanki/raspberry-pi-bots"
        self.github_raw = "https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main"
        self.phone_number = "9940585709"
        
        # Colors for terminal output
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.BLUE = '\033[94m'
        self.ENDC = '\033[0m'
        self.BOLD = '\033[1m'

    def print_header(self, message):
        print(f"\n{self.BOLD}{self.BLUE}{'='*60}{self.ENDC}")
        print(f"{self.BOLD}{self.BLUE}{message}{self.ENDC}")
        print(f"{self.BOLD}{self.BLUE}{'='*60}{self.ENDC}")

    def print_success(self, message):
        print(f"{self.GREEN}✅ {message}{self.ENDC}")

    def print_error(self, message):
        print(f"{self.RED}❌ {message}{self.ENDC}")

    def print_warning(self, message):
        print(f"{self.YELLOW}⚠️  {message}{self.ENDC}")

    def print_info(self, message):
        print(f"{self.BLUE}ℹ️  {message}{self.ENDC}")

    def run_command(self, command, shell=False):
        """Run a shell command and return success status"""
        try:
            if shell:
                result = subprocess.run(command, shell=True, check=True, 
                                      capture_output=True, text=True)
            else:
                result = subprocess.run(command, check=True, 
                                      capture_output=True, text=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr

    def install_system_dependencies(self):
        """Install system dependencies"""
        self.print_info("Installing system dependencies...")
        
        dependencies = [
            "python3", "python3-venv", "python3-pip", "git", "curl", "wget", 
            "unzip", "build-essential", "x11-utils", "libnss3", "libxkbcommon0",
            "libdrm2", "libgbm1", "libxshmfence1", "libjpeg-dev", "zlib1g-dev",
            "libfreetype6-dev", "liblcms2-dev", "libopenjp2-7-dev", "libtiff-dev",
            "libwebp-dev", "tk-dev", "libharfbuzz-dev", "libfribidi-dev", "libxcb1-dev"
        ]
        
        # Update package list
        success, output = self.run_command("sudo apt update -y", shell=True)
        if not success:
            self.print_warning("Failed to update package list")
        
        # Install dependencies
        for dep in dependencies:
            success, output = self.run_command(f"sudo apt install -y {dep}", shell=True)
            if success:
                self.print_success(f"Installed {dep}")
            else:
                self.print_warning(f"Failed to install {dep}")

    def install_chromium(self):
        """Install Chromium and Chromedriver"""
        self.print_info("Installing Chromium and Chromedriver...")
        
        arch = os.uname().machine
        if "armv7" in arch:
            self.print_info("32-bit Raspberry Pi detected")
            success, output = self.run_command(
                "sudo apt install -y chromium chromium-driver || sudo apt install -y chromium-browser chromium-chromedriver", 
                shell=True
            )
        else:
            self.print_info("64-bit Raspberry Pi detected")
            success, output = self.run_command("sudo apt install -y chromium chromium-driver", shell=True)
        
        if success:
            self.print_success("Chromium installed successfully")
        else:
            self.print_warning("Chromium installation had issues")

    def get_all_folders_from_github(self):
        """Get all folders from GitHub repository using GitHub API"""
        self.print_info("Scanning GitHub repository for bot folders...")
        
        api_url = "https://api.github.com/repos/Thaniyanki/raspberry-pi-bots/contents"
        
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                contents = response.json()
                folders = []
                
                for item in contents:
                    if item['type'] == 'dir' and item['name'] != 'all-in-one-venv':
                        folders.append(item['name'])
                
                self.print_success(f"Found {len(folders)} folders in repository")
                return folders
            else:
                self.print_warning(f"GitHub API returned status {response.status_code}")
                return []
                
        except Exception as e:
            self.print_warning(f"Failed to fetch from GitHub API: {e}")
            return []

    def check_folder_has_venv_sh(self, folder_name):
        """Check if a folder has venv.sh file"""
        venv_url = f"{self.github_raw}/{folder_name}/venv.sh"
        
        try:
            response = requests.head(venv_url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def run_venv_script(self, folder_name, display_name):
        """Run the venv.sh script for a bot"""
        self.print_info(f"Setting up: {display_name}")
        
        venv_url = f"{self.github_raw}/{folder_name}/venv.sh"
        
        try:
            # Download and run the venv.sh script
            result = subprocess.run(
                f"bash <(curl -sL '{venv_url}')",
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.print_success(f"Completed: {display_name}")
                return True
            else:
                self.print_error(f"Failed: {display_name} - {result.stderr}")
                return False
                
        except Exception as e:
            self.print_error(f"Error running venv.sh for {display_name}: {e}")
            return False

    def setup_bot_environment(self, folder_name, display_name):
        """Setup basic environment for a bot"""
        bot_path = os.path.join(self.bots_dir, display_name)
        venv_path = os.path.join(bot_path, "venv")
        report_file = os.path.join(venv_path, "report number")
        
        self.print_info(f"Creating environment for: {display_name}")
        
        # Create bot directory
        os.makedirs(bot_path, exist_ok=True)
        
        # Create virtual environment
        if not os.path.exists(venv_path):
            success, output = self.run_command([
                "python3", "-m", "venv", venv_path
            ])
            
            if success:
                # Install Python dependencies
                pip_commands = [
                    f"source {os.path.join(venv_path, 'bin/activate')} && pip install --upgrade pip setuptools wheel",
                    f"source {os.path.join(venv_path, 'bin/activate')} && pip install firebase_admin gspread selenium google-auth google-auth-oauthlib google-cloud-storage google-cloud-firestore psutil pyautogui python3-xlib requests Pillow oauth2client python-dateutil"
                ]
                
                for cmd in pip_commands:
                    self.run_command(cmd, shell=True)
                
                # Create phone number file
                with open(report_file, 'w') as f:
                    f.write(self.phone_number)
                
                self.print_success(f"Environment created for {display_name}")
            else:
                self.print_error(f"Failed to create venv for {display_name}")
                return False
        
        return True

    def create_whatsapp_folders(self):
        """Create folder structure for WhatsApp Messenger"""
        bot_path = os.path.join(self.bots_dir, "whatsapp messenger")
        
        if os.path.exists(bot_path):
            self.print_info("Creating folder structure for WhatsApp Messenger...")
            
            current_date = datetime.now().strftime("%d-%m-%Y")
            folders = ["Image", "Document", "Audio", "Video"]
            
            for folder in folders:
                # Main folders
                main_folder = os.path.join(bot_path, folder)
                os.makedirs(main_folder, exist_ok=True)
                open(os.path.join(main_folder, "Caption.txt"), 'a').close()
                
                # Date subfolders
                date_folder = os.path.join(main_folder, current_date)
                os.makedirs(date_folder, exist_ok=True)
                open(os.path.join(date_folder, "Caption.txt"), 'a').close()
            
            self.print_success(f"Created folder structure with date: {current_date}")

    def main(self):
        """Main setup process"""
        self.print_header("🚀 ALL BOTS VENV SETUP (Python Version)")
        
        # Detect system info
        os_info = f"{os.uname().sysname} | {os.uname().machine}"
        self.print_info(f"Detected: {os_info}")
        
        # Create bots directory
        os.makedirs(self.bots_dir, exist_ok=True)
        self.print_success(f"Bots directory: {self.bots_dir}")
        
        # Install system dependencies
        self.install_system_dependencies()
        
        # Install Chromium
        self.install_chromium()
        
        # Get all folders from GitHub
        all_folders = self.get_all_folders_from_github()
        
        if not all_folders:
            self.print_warning("Using fallback bot list")
            all_folders = [
                "whatsapp-messenger",
                "whatsapp-birthday-wisher", 
                "facebook-birthday-wisher",
                "facebook-profile-liker"
            ]
        
        # Find folders with venv.sh
        bots_with_venv = []
        self.print_info("Checking for venv.sh files...")
        
        for folder in all_folders:
            if self.check_folder_has_venv_sh(folder):
                bots_with_venv.append(folder)
                self.print_success(f"  ✅ {folder} (has venv.sh)")
            else:
                self.print_warning(f"  ❌ {folder} (no venv.sh)")
        
        if not bots_with_venv:
            self.print_error("No bots with venv.sh found!")
            return
        
        # Setup each bot
        self.print_info(f"Starting setup for {len(bots_with_venv)} bots...")
        success_count = 0
        
        for i, bot_folder in enumerate(bots_with_venv, 1):
            # Convert folder name to display name
            display_name = bot_folder.replace('-', ' ')
            
            self.print_header(f"Bot {i}/{len(bots_with_venv)}: {display_name}")
            
            # Setup basic environment
            if self.setup_bot_environment(bot_folder, display_name):
                # Run the venv.sh script
                if self.run_venv_script(bot_folder, display_name):
                    success_count += 1
            
            # Add delay between bots
            if i < len(bots_with_venv):
                self.print_info("Waiting 3 seconds before next bot...")
                time.sleep(3)
        
        # Create WhatsApp folder structure
        self.create_whatsapp_folders()
        
        # Final summary
        self.print_header("🎉 SETUP COMPLETED!")
        self.print_success(f"Bots Directory: {self.bots_dir}")
        self.print_info(f"Successful setups: {success_count}/{len(bots_with_venv)}")
        
        self.print_info("Installed Bots:")
        for bot_folder in bots_with_venv:
            display_name = bot_folder.replace('-', ' ')
            self.print_success(f"  ✅ {display_name}")
        
        self.print_success("All bots are ready for scheduler integration!")

if __name__ == "__main__":
    setup = AllInOneVenvSetup()
    setup.main()
