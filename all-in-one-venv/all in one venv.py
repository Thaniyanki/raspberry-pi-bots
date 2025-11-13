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
        """Run the venv.sh script from a folder with better error handling"""
        script_url = f"{self.github_raw}/{folder_name}/venv.sh"
        display_name = folder_name.replace('-', ' ')
        
        self.print_info(f"Setting up: {display_name}")
        
        # Create a temporary script file to run
        temp_script = f"/tmp/venv_{folder_name}.sh"
        
        try:
            # Download the script first
            self.print_info("Downloading script...")
            response = requests.get(script_url, timeout=30)
            if response.status_code != 200:
                self.print_error(f"Failed to download script from: {script_url}")
                return False
            
            # Save to temporary file
            with open(temp_script, 'w') as f:
                f.write(response.text)
            
            # Make it executable
            subprocess.run(['chmod', '+x', temp_script], check=True)
            
            # Set environment variables to help with SSL issues
            env = os.environ.copy()
            env['PIP_DEFAULT_TIMEOUT'] = '60'
            env['PIP_RETRIES'] = '3'
            
            self.print_info("Running installation script (this may take several minutes)...")
            
            # Run the script with improved environment
            result = subprocess.run(
                [temp_script],
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                env=env
            )
            
            # Clean up temp file
            if os.path.exists(temp_script):
                os.remove(temp_script)
            
            if result.returncode == 0:
                self.print_success(f"Completed: {display_name}")
                return True
            else:
                self.print_error(f"Failed: {display_name} (exit code: {result.returncode})")
                if result.stdout:
                    self.print_info(f"Output: {result.stdout[-500:]}")  # Last 500 chars
                if result.stderr:
                    # Filter out common warnings
                    error_lines = []
                    for line in result.stderr.split('\n'):
                        if any(warning in line for warning in ['WARNING:', 'Retrying', 'apt does not have']):
                            continue
                        if line.strip():
                            error_lines.append(line)
                    
                    if error_lines:
                        self.print_error(f"Errors: {' '.join(error_lines[-3:])}")  # Last 3 errors
                return False
                
        except subprocess.TimeoutExpired:
            self.print_error(f"Timeout: {display_name} took too long to complete")
            return False
        except Exception as e:
            self.print_error(f"Error running {display_name}: {e}")
            return False

    def fix_ssl_issues(self):
        """Try to fix common SSL issues on Raspberry Pi"""
        self.print_info("Attempting to fix SSL issues...")
        
        try:
            # Update CA certificates
            subprocess.run(['sudo', 'apt-get', 'update'], capture_output=True)
            subprocess.run(['sudo', 'apt-get', 'install', '--reinstall', 'ca-certificates', '-y'], 
                         capture_output=True)
            subprocess.run(['sudo', 'update-ca-certificates', '--fresh'], capture_output=True)
            
            # Update pip and set trusted hosts
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                         capture_output=True)
            
            self.print_success("SSL fixes applied")
            return True
        except Exception as e:
            self.print_warning(f"Could not fix SSL issues: {e}")
            return False

    def main(self):
        """Main setup process"""
        self.print_header("🚀 AUTO-RUN ALL VENV.SH SCRIPTS FROM GITHUB")
        
        # Check if we need to fix SSL issues
        self.print_info("Checking for SSL issues...")
        self.fix_ssl_issues()
        
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
                self.print_info("Waiting 10 seconds before next bot...")
                time.sleep(10)
        
        # Final summary
        self.print_header("🎉 ALL VENV.SH SCRIPTS EXECUTION COMPLETED!")
        self.print_info(f"Total bots with venv.sh: {len(folders_with_venv)}")
        self.print_info(f"Successful setups: {success_count}")
        self.print_info(f"Failed setups: {len(folders_with_venv) - success_count}")
        
        if success_count > 0:
            self.print_info("Successfully installed Bots:")
            for folder in folders_with_venv:
                display_name = folder.replace('-', ' ')
                self.print_success(f"  ✅ {display_name}")
        
        if success_count == len(folders_with_venv):
            self.print_success("🎊 All bots installed successfully!")
        elif success_count > 0:
            self.print_warning("Some bots installed successfully, but some failed")
        else:
            self.print_error("All bots failed to install!")

if __name__ == "__main__":
    setup = AllInOneVenvSetup()
    setup.main()
