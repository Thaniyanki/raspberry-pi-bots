#!/usr/bin/env python3
import os
import sys
import subprocess
import requests
import time
from datetime import datetime

class AllInOneVenvSetup:
    def __init__(self):
        self.github_repo = "https://github.com/Thaniyanki/raspberry-pi-bots"
        self.github_raw = "https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main"
        
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

    def get_all_folders_from_github(self):
        """Get all folders from GitHub repository using GitHub API"""
        self.print_info("Scanning GitHub repository for ALL folders...")
        
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

    def check_venv_sh_exists(self, folder_name):
        """Check if venv.sh exists in a folder"""
        venv_url = f"{self.github_raw}/{folder_name}/venv.sh"
        
        try:
            response = requests.head(venv_url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def run_venv_script(self, folder_name):
        """Run the venv.sh script from a folder"""
        # Use RAW GitHub URL, not blob URL
        script_url = f"{self.github_raw}/{folder_name}/venv.sh"
        
        # Convert folder name to display name
        display_name = folder_name.replace('-', ' ')
        
        self.print_info(f"Setting up: {display_name}")
        
        # Create the bash command with proper URL
        bash_command = f'bash <(curl -sL "{script_url}")'
        self.print_info(f"Command: {bash_command}")
        
        try:
            # First, let's check if the URL is accessible
            self.print_info("Checking if script URL is accessible...")
            response = requests.head(script_url, timeout=10)
            if response.status_code != 200:
                self.print_error(f"Script not found at: {script_url}")
                return False
            
            self.print_info("URL is accessible, running script...")
            
            # Run the bash command with timeout
            result = subprocess.run(
                bash_command,
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                self.print_success(f"Completed: {display_name}")
                return True
            else:
                self.print_error(f"Failed: {display_name}")
                if result.stderr:
                    self.print_error(f"Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.print_error(f"Timeout: {display_name} took too long to complete")
            return False
        except Exception as e:
            self.print_error(f"Error running {display_name}: {e}")
            return False

    def main(self):
        """Main setup process"""
        self.print_header("🚀 AUTO-RUN ALL VENV.SH SCRIPTS FROM GITHUB")
        
        # Get all folders from GitHub
        all_folders = self.get_all_folders_from_github()
        
        if not all_folders:
            self.print_error("No folders found in repository!")
            return
        
        # Find folders that have venv.sh
        folders_with_venv = []
        
        self.print_info("Checking for venv.sh files in all folders...")
        for folder in all_folders:
            if self.check_venv_sh_exists(folder):
                folders_with_venv.append(folder)
                display_name = folder.replace('-', ' ')
                self.print_success(f"  ✅ {display_name} (has venv.sh)")
            else:
                display_name = folder.replace('-', ' ')
                self.print_warning(f"  ❌ {display_name} (no venv.sh)")
        
        if not folders_with_venv:
            self.print_error("No venv.sh files found in any folder!")
            return
        
        self.print_info(f"Found {len(folders_with_venv)} bots with venv.sh")
        
        # Run all venv.sh scripts
        success_count = 0
        
        for i, folder in enumerate(folders_with_venv, 1):
            display_name = folder.replace('-', ' ')
            self.print_header(f"Bot {i}/{len(folders_with_venv)}: {display_name}")
            
            if self.run_venv_script(folder):
                success_count += 1
            
            # Add delay between scripts
            if i < len(folders_with_venv):
                self.print_info("Waiting 5 seconds before next bot...")
                time.sleep(5)
        
        # Final summary
        self.print_header("🎉 ALL VENV.SH SCRIPTS EXECUTION COMPLETED!")
        self.print_info(f"Total bots with venv.sh: {len(folders_with_venv)}")
        self.print_info(f"Successful setups: {success_count}")
        self.print_info(f"Failed setups: {len(folders_with_venv) - success_count}")
        
        self.print_info("Installed Bots:")
        for folder in folders_with_venv:
            display_name = folder.replace('-', ' ')
            self.print_success(f"  ✅ {display_name}")
        
        if success_count == len(folders_with_venv):
            self.print_success("🎊 All bots installed successfully!")
        else:
            self.print_warning("Some bots failed to install, check above for errors")

if __name__ == "__main__":
    setup = AllInOneVenvSetup()
    setup.main()
