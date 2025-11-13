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

    def get_sh_files_from_folder(self, folder_name):
        """Get all .sh files from a folder"""
        api_url = f"https://api.github.com/repos/Thaniyanki/raspberry-pi-bots/contents/{folder_name}"
        
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                contents = response.json()
                sh_files = []
                
                for item in contents:
                    if item['type'] == 'file' and item['name'].endswith('.sh'):
                        sh_files.append(item['name'])
                
                return sh_files
            return []
        except:
            return []

    def run_sh_script(self, folder_name, script_name):
        """Run a .sh script from GitHub"""
        script_url = f"{self.github_raw}/{folder_name}/{script_name}"
        
        self.print_info(f"Running: {folder_name}/{script_name}")
        
        # Create the bash command
        bash_command = f'bash <(curl -sL "{script_url}")'
        self.print_info(f"Command: {bash_command}")
        
        try:
            # Run the bash command
            result = subprocess.run(
                bash_command,
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.print_success(f"Completed: {folder_name}/{script_name}")
                return True
            else:
                self.print_error(f"Failed: {folder_name}/{script_name}")
                if result.stderr:
                    self.print_error(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            self.print_error(f"Error running {folder_name}/{script_name}: {e}")
            return False

    def main(self):
        """Main setup process"""
        self.print_header("🚀 AUTO-RUN ALL .SH SCRIPTS FROM GITHUB")
        
        # Get all folders from GitHub
        all_folders = self.get_all_folders_from_github()
        
        if not all_folders:
            self.print_error("No folders found in repository!")
            return
        
        # Find all .sh files in each folder
        all_sh_scripts = []
        
        self.print_info("Scanning for .sh files in all folders...")
        for folder in all_folders:
            sh_files = self.get_sh_files_from_folder(folder)
            for sh_file in sh_files:
                all_sh_scripts.append((folder, sh_file))
                self.print_success(f"  📁 {folder}/{sh_file}")
        
        if not all_sh_scripts:
            self.print_error("No .sh files found in any folder!")
            return
        
        self.print_info(f"Found {len(all_sh_scripts)} .sh scripts to run")
        
        # Run all .sh scripts
        success_count = 0
        
        for i, (folder, script) in enumerate(all_sh_scripts, 1):
            self.print_header(f"Script {i}/{len(all_sh_scripts)}: {folder}/{script}")
            
            if self.run_sh_script(folder, script):
                success_count += 1
            
            # Add delay between scripts
            if i < len(all_sh_scripts):
                self.print_info("Waiting 3 seconds before next script...")
                time.sleep(3)
        
        # Final summary
        self.print_header("🎉 ALL SCRIPTS EXECUTION COMPLETED!")
        self.print_info(f"Successful: {success_count}/{len(all_sh_scripts)}")
        self.print_info(f"Failed: {len(all_sh_scripts) - success_count}/{len(all_sh_scripts)}")
        
        if success_count == len(all_sh_scripts):
            self.print_success("🎊 All scripts executed successfully!")
        else:
            self.print_warning("Some scripts failed, check above for errors")

if __name__ == "__main__":
    setup = AllInOneVenvSetup()
    setup.main()
