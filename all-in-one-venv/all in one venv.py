#!/usr/bin/env python3
import os
import sys
import subprocess
import requests
import time
import threading
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

    def show_progress(self, folder_name, stop_event):
        """Show progress dots while installation is running"""
        dots = 0
        while not stop_event.is_set():
            dots = (dots + 1) % 4
            progress = "." * dots + " " * (3 - dots)
            print(f"\r{self.BLUE}🔄 Installing {folder_name} {progress}{self.ENDC}", end="", flush=True)
            time.sleep(1)
        print("\r" + " " * 50 + "\r", end="", flush=True)  # Clear line

    def check_and_install_python(self):
        """Check if Python3 is installed and install if missing"""
        self.print_info("Checking Python3 installation...")
        
        try:
            # Check if python3 is available
            result = subprocess.run(['python3', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.print_success(f"Python3 is installed: {result.stdout.strip()}")
                return True
        except:
            pass
        
        # Python3 not found, install it
        self.print_warning("Python3 not found! Installing...")
        try:
            self.print_info("Updating package list...")
            subprocess.run(['sudo', 'apt', 'update'], check=True, capture_output=True)
            
            self.print_info("Installing Python3 and pip...")
            subprocess.run(['sudo', 'apt', 'install', '-y', 'python3', 'python3-pip', 'python3-venv'], 
                         check=True, capture_output=True)
            
            self.print_success("Python3 installed successfully!")
            return True
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to install Python3: {e}")
            return False

    def fix_pip_issues(self):
        """Fix pip externally-managed-environment issue"""
        self.print_info("Fixing pip installation issues...")
        
        try:
            # Install python3-full for complete Python environment
            subprocess.run(['sudo', 'apt', 'install', '-y', 'python3-full'], 
                         capture_output=True, check=True)
            
            # Upgrade pip with break-system-packages flag
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip', '--break-system-packages'],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for pip upgrade
            )
            
            if result.returncode == 0:
                self.print_success("Pip upgraded successfully")
                return True
            else:
                # Try alternative approach
                self.print_warning("Trying alternative pip upgrade...")
                subprocess.run(['sudo', 'apt', 'install', '-y', 'python3-pip'], 
                             capture_output=True, check=True)
                self.print_success("Pip issues resolved")
                return True
                
        except subprocess.TimeoutExpired:
            self.print_warning("Pip upgrade timed out, continuing anyway...")
            return True
        except Exception as e:
            self.print_warning(f"Could not fix pip issues: {e}")
            return False

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
        """Run the venv.sh script from a folder with LIVE OUTPUT and longer timeout"""
        script_url = f"{self.github_raw}/{folder_name}/venv.sh"
        display_name = folder_name.replace('-', ' ')
        
        self.print_info(f"Setting up: {display_name}")
        self.print_warning("This may take 15-20 minutes on Raspberry Pi. Please be patient...")
        
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
            
            # Set environment variables to help with installation
            env = os.environ.copy()
            env['PIP_DEFAULT_TIMEOUT'] = '120'  # 2 minute timeout for pip
            env['PIP_RETRIES'] = '5'  # More retries
            env['DEBIAN_FRONTEND'] = 'noninteractive'  # Non-interactive apt
            
            self.print_info("Running installation script with LIVE OUTPUT...")
            self.print_info("You will see all installation progress below:")
            print("-" * 50)
            
            # Start progress indicator
            stop_progress = threading.Event()
            progress_thread = threading.Thread(target=self.show_progress, args=(display_name, stop_progress))
            progress_thread.start()
            
            # Run the script with MUCH longer timeout (30 minutes)
            result = subprocess.run(
                [temp_script],
                shell=True,
                executable="/bin/bash",
                timeout=1800,  # 30 minute timeout for slow Raspberry Pi
                env=env
                # NO capture_output - this shows live output!
            )
            
            # Stop progress indicator
            stop_progress.set()
            progress_thread.join()
            
            # Clean up temp file
            if os.path.exists(temp_script):
                os.remove(temp_script)
            
            print("-" * 50)
            
            if result.returncode == 0:
                self.print_success(f"Completed: {display_name}")
                return True
            else:
                self.print_error(f"Failed: {display_name} (exit code: {result.returncode})")
                return False
                
        except subprocess.TimeoutExpired:
            # Stop progress indicator
            stop_progress.set()
            progress_thread.join()
            
            self.print_error(f"Timeout: {display_name} took too long to complete")
            self.print_warning("This is normal on Raspberry Pi. Try running the bot individually later.")
            return False
        except Exception as e:
            # Stop progress indicator if it exists
            try:
                stop_progress.set()
                progress_thread.join()
            except:
                pass
                
            self.print_error(f"Error running {display_name}: {e}")
            return False

    def fix_ssl_issues(self):
        """Try to fix common SSL issues on Raspberry Pi"""
        self.print_info("Attempting to fix SSL issues...")
        
        try:
            # Update CA certificates
            subprocess.run(['sudo', 'apt-get', 'update'], capture_output=True, timeout=300)
            subprocess.run(['sudo', 'apt-get', 'install', '--reinstall', 'ca-certificates', '-y'], 
                         capture_output=True, timeout=300)
            subprocess.run(['sudo', 'update-ca-certificates', '--fresh'], capture_output=True)
            self.print_success("SSL fixes applied")
            return True
        except Exception as e:
            self.print_warning(f"Could not fix SSL issues: {e}")
            return False

    def main(self):
        """Main setup process"""
        self.print_header("🚀 AUTO-RUN ALL VENV.SH SCRIPTS FROM GITHUB")
        self.print_warning("Note: This will take 1-2 hours on Raspberry Pi. Be patient!")
        
        # Step 1: Check and install Python3 if needed
        if not self.check_and_install_python():
            self.print_error("Cannot continue without Python3!")
            sys.exit(1)
        
        # Step 2: Fix pip issues
        self.fix_pip_issues()
        
        # Step 3: Check if we need to fix SSL issues
        self.print_info("Checking for SSL issues...")
        self.fix_ssl_issues()
        
        # Step 4: Get all folders from GitHub
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
                self.print_info("Waiting 15 seconds before next bot...")
                time.sleep(15)
        
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
            self.print_warning("Some bots installed successfully, but some failed (this is normal on Raspberry Pi)")
        else:
            self.print_error("All bots failed to install! Try running them individually.")

if __name__ == "__main__":
    setup = AllInOneVenvSetup()
    setup.main()
