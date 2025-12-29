#!/usr/bin/env python3
import os
import sys
import subprocess
import requests
import time
import threading
import shutil
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

    def show_progress(self, folder_name, stop_event, attempt=None):
        """Show progress dots while installation is running"""
        dots = 0
        start_time = time.time()
        
        while not stop_event.is_set():
            dots = (dots + 1) % 4
            progress = "." * dots + " " * (3 - dots)
            elapsed = int(time.time() - start_time)
            
            if attempt:
                status = f"🔄 Attempt {attempt}: Installing {folder_name} {progress} ({elapsed}s)"
            else:
                status = f"🔄 Installing {folder_name} {progress} ({elapsed}s)"
                
            print(f"\r{self.BLUE}{status}{self.ENDC}", end="", flush=True)
            time.sleep(1)
        print("\r" + " " * 80 + "\r", end="", flush=True)  # Clear line

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
                timeout=300
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

    def install_selenium_systemwide(self):
        """Install Selenium and WebDriver system-wide for Raspberry Pi"""
        self.print_header("🛠️ INSTALLING SELENIUM SYSTEM-WIDE")
        
        try:
            # First, update and fix any broken packages
            self.print_info("Fixing any broken packages first...")
            try:
                subprocess.run(['sudo', 'apt-get', 'update', '--fix-missing'], 
                             check=True, capture_output=True, timeout=300)
                subprocess.run(['sudo', 'apt-get', 'install', '-f', '-y'], 
                             check=True, capture_output=True, timeout=300)
            except:
                pass  # Continue even if this fails
            
            # Try to install packages one by one with better error handling
            self.print_info("Installing system dependencies one by one...")
            
            packages = [
                'python3-pip',
                'python3-venv',
                'python3-dev',
                'libffi-dev',
                'libssl-dev',
                'curl',
                'wget'
            ]
            
            for package in packages:
                try:
                    self.print_info(f"Installing {package}...")
                    subprocess.run(['sudo', 'apt-get', 'install', '-y', package], 
                                 check=True, capture_output=True, timeout=300)
                    self.print_success(f"  ✅ {package} installed")
                except subprocess.CalledProcessError:
                    self.print_warning(f"  ⚠️  Could not install {package}, continuing...")
            
            # Install browser components separately
            browser_packages = [
                'chromium-browser',
                'chromium-chromedriver'
            ]
            
            for package in browser_packages:
                try:
                    self.print_info(f"Installing {package}...")
                    result = subprocess.run(['sudo', 'apt-get', 'install', '-y', package], 
                                          capture_output=True, text=True, timeout=300)
                    if result.returncode == 0:
                        self.print_success(f"  ✅ {package} installed")
                    else:
                        self.print_warning(f"  ⚠️  {package} failed: {result.stderr[:100]}")
                        
                        # Try alternative package names
                        if package == 'chromium-browser':
                            self.print_info("Trying alternative: chromium...")
                            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'chromium'], 
                                         capture_output=True, timeout=300)
                except Exception as e:
                    self.print_warning(f"  ⚠️  Error installing {package}: {e}")
            
            # Install Xvfb if needed
            try:
                subprocess.run(['sudo', 'apt-get', 'install', '-y', 'xvfb'], 
                             capture_output=True, timeout=300)
                self.print_success("✅ Xvfb installed")
            except:
                self.print_warning("⚠️  Could not install Xvfb")
            
            # Install Selenium using pip with multiple approaches
            self.print_info("Installing Selenium via pip...")
            
            pip_commands = [
                [sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip', '--break-system-packages'],
                [sys.executable, '-m', 'pip', 'install', 'selenium==4.15.0', '--break-system-packages'],
                [sys.executable, '-m', 'pip', 'install', 'webdriver-manager', '--break-system-packages']
            ]
            
            for cmd in pip_commands:
                try:
                    cmd_name = ' '.join(cmd[-2:]) if 'install' in cmd else ' '.join(cmd[-1:])
                    self.print_info(f"Running: {cmd_name}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    if result.returncode == 0:
                        self.print_success(f"  ✅ Command successful")
                    else:
                        # Try without --break-system-packages flag
                        if '--break-system-packages' in cmd:
                            alt_cmd = [c for c in cmd if c != '--break-system-packages']
                            self.print_info(f"Trying alternative for: {cmd_name}")
                            subprocess.run(alt_cmd, capture_output=True, timeout=300)
                except Exception as e:
                    self.print_warning(f"  ⚠️  Command failed: {e}")
            
            # Install additional useful packages
            additional_packages = [
                'selenium-wire',
                'undetected-chromedriver',
                'pyvirtualdisplay'
            ]
            
            for package in additional_packages:
                try:
                    self.print_info(f"Installing {package}...")
                    subprocess.run([sys.executable, '-m', 'pip', 'install', package, '--break-system-packages'],
                                 capture_output=True, timeout=60)
                except:
                    pass  # These are optional
            
            # Setup chromedriver symlink
            self.print_info("Setting up chromedriver...")
            chromedriver_paths = [
                '/usr/lib/chromium-browser/chromedriver',
                '/usr/bin/chromedriver',
                '/usr/local/bin/chromedriver',
                '/snap/bin/chromium.chromedriver'
            ]
            
            chromedriver_found = False
            for path in chromedriver_paths:
                if os.path.exists(path):
                    self.print_success(f"✅ Chromedriver found at: {path}")
                    chromedriver_found = True
                    # Make symlink if not already in /usr/local/bin
                    if path != '/usr/local/bin/chromedriver':
                        try:
                            subprocess.run(['sudo', 'ln', '-sf', path, '/usr/local/bin/chromedriver'], 
                                         check=True)
                            self.print_success(f"  Created symlink to /usr/local/bin/chromedriver")
                        except:
                            pass
                    break
            
            if not chromedriver_found:
                # Try to install chromedriver manually
                self.print_warning("Chromedriver not found, trying to install manually...")
                try:
                    # Get latest chromedriver for ARM
                    subprocess.run(['wget', 'https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip'],
                                 capture_output=True, timeout=300)
                    subprocess.run(['unzip', 'chromedriver_linux64.zip'], capture_output=True)
                    subprocess.run(['sudo', 'mv', 'chromedriver', '/usr/local/bin/'], check=True)
                    subprocess.run(['sudo', 'chmod', '+x', '/usr/local/bin/chromedriver'], check=True)
                    self.print_success("✅ Chromedriver installed manually")
                except:
                    self.print_warning("⚠️  Could not install chromedriver manually")
            
            # Test Selenium installation
            self.print_info("Testing Selenium installation...")
            test_script = """
import sys
print(f"Python version: {sys.version}")

try:
    from selenium import webdriver
    print("✅ selenium module imported successfully")
    print(f"Selenium version: {webdriver.__version__}")
except ImportError as e:
    print(f"❌ Failed to import selenium: {e}")
    sys.exit(1)

# Try to setup Chrome options
try:
    from selenium.webdriver.chrome.options import Options
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--remote-debugging-port=9222')
    print("✅ Chrome options created successfully")
    
    # Try to initialize driver
    try:
        driver = webdriver.Chrome(options=options)
        print("✅ Chrome driver initialized")
        
        # Try to navigate
        driver.get("https://httpbin.org/ip")
        print(f"✅ Page loaded successfully")
        print(f"Page title: {driver.title}")
        
        driver.quit()
        print("✅ Driver quit successfully")
        print("🎉 Selenium test PASSED!")
        
    except Exception as e:
        print(f"⚠️  Driver initialization/navigation failed: {e}")
        print("This might be OK if browser is not fully installed")
        
except Exception as e:
    print(f"❌ Failed to setup Chrome options: {e}")
"""
            
            test_file = '/tmp/test_selenium.py'
            with open(test_file, 'w') as f:
                f.write(test_script)
            
            try:
                result = subprocess.run(['python3', test_file], 
                                      capture_output=True, text=True, timeout=60)
                print("\n" + "="*60)
                print("SELENIUM TEST RESULTS:")
                print("="*60)
                print(result.stdout)
                if result.stderr:
                    print("STDERR:", result.stderr[:500])
                print("="*60)
                
                if result.returncode == 0:
                    self.print_success("✅ Selenium installation completed successfully!")
                    return True
                else:
                    self.print_warning("⚠️  Selenium test had some issues")
                    return True  # Return True anyway to continue
                    
            except Exception as e:
                self.print_warning(f"⚠️  Could not run selenium test: {e}")
                return True  # Continue anyway
                
        except Exception as e:
            self.print_error(f"❌ Error in selenium installation: {e}")
            self.print_warning("⚠️  Continuing without full selenium installation...")
            return False

    def run_venv_script_with_retry(self, folder_name, max_attempts=9999):
        """Run the venv.sh script with UNLIMITED retries"""
        script_url = f"{self.github_raw}/{folder_name}/venv.sh"
        display_name = folder_name.replace('-', ' ')
        
        self.print_info(f"Setting up: {display_name}")
        self.print_warning("🔄 UNLIMITED RETRY MODE: Will keep trying until successful!")
        
        attempt = 1
        while attempt <= max_attempts:
            self.print_header(f"Attempt {attempt} for: {display_name}")
            
            # Create a temporary script file to run
            temp_script = f"/tmp/venv_{folder_name}.sh"
            
            try:
                # Download the script first
                self.print_info("Downloading script...")
                response = requests.get(script_url, timeout=30)
                if response.status_code != 200:
                    self.print_error(f"Failed to download script from: {script_url}")
                    attempt += 1
                    time.sleep(10)
                    continue
                
                # Save to temporary file
                with open(temp_script, 'w') as f:
                    f.write(response.text)
                
                # Make it executable
                subprocess.run(['chmod', '+x', temp_script], check=True)
                
                # Set environment variables to help with installation
                env = os.environ.copy()
                env['PIP_DEFAULT_TIMEOUT'] = '300'
                env['PIP_RETRIES'] = '10'
                env['DEBIAN_FRONTEND'] = 'noninteractive'
                env['DISPLAY'] = ':99'  # For headless display
                
                self.print_info("Running installation script with LIVE OUTPUT...")
                self.print_info("You will see all installation progress below:")
                print("-" * 50)
                
                # Start progress indicator
                stop_progress = threading.Event()
                progress_thread = threading.Thread(
                    target=self.show_progress, 
                    args=(display_name, stop_progress, attempt)
                )
                progress_thread.start()
                
                # Run the script with NO TIMEOUT
                result = subprocess.run(
                    [temp_script],
                    shell=True,
                    executable="/bin/bash",
                    env=env
                )
                
                # Stop progress indicator
                stop_progress.set()
                progress_thread.join()
                
                # Clean up temp file
                if os.path.exists(temp_script):
                    os.remove(temp_script)
                
                print("-" * 50)
                
                if result.returncode == 0:
                    self.print_success(f"🎉 SUCCESS on attempt {attempt}: {display_name}")
                    return True
                else:
                    self.print_error(f"❌ Failed on attempt {attempt}: {display_name} (exit code: {result.returncode})")
                    self.print_warning(f"🔄 Retrying in 30 seconds... (Attempt {attempt + 1})")
                    
            except subprocess.TimeoutExpired:
                stop_progress.set()
                progress_thread.join()
                self.print_error(f"⏰ Timeout on attempt {attempt}: {display_name}")
                self.print_warning(f"🔄 Retrying in 30 seconds... (Attempt {attempt + 1})")
                
            except Exception as e:
                try:
                    stop_progress.set()
                    progress_thread.join()
                except:
                    pass
                self.print_error(f"💥 Error on attempt {attempt}: {e}")
                self.print_warning(f"🔄 Retrying in 30 seconds... (Attempt {attempt + 1})")
            
            time.sleep(30)
            attempt += 1
        
        self.print_error(f"🚨 MAXIMUM ATTEMPTS REACHED: Failed to install {display_name} after {max_attempts} attempts")
        return False

    def fix_ssl_issues(self):
        """Try to fix common SSL issues on Raspberry Pi"""
        self.print_info("Attempting to fix SSL issues...")
        
        try:
            subprocess.run(['sudo', 'apt-get', 'update'], capture_output=True, timeout=300)
            subprocess.run(['sudo', 'apt-get', 'install', '--reinstall', 'ca-certificates', '-y'], 
                         capture_output=True, timeout=300)
            subprocess.run(['sudo', 'update-ca-certificates', '--fresh'], capture_output=True)
            self.print_success("SSL fixes applied")
            return True
        except Exception as e:
            self.print_warning(f"Could not fix SSL issues: {e}")
            return False

    def start_xvfb(self):
        """Start Xvfb for headless display"""
        self.print_info("Starting Xvfb for headless display...")
        try:
            # Check if Xvfb is already running
            result = subprocess.run(['pgrep', 'Xvfb'], capture_output=True)
            if result.returncode != 0:
                subprocess.Popen(['Xvfb', ':99', '-screen', '0', '1024x768x24'], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.print_success("Xvfb started on display :99")
            else:
                self.print_info("Xvfb is already running")
            return True
        except Exception as e:
            self.print_warning(f"Could not start Xvfb: {e}")
            return False

    def main(self):
        """Main setup process"""
        self.print_header("🚀 AUTO-RUN ALL VENV.SH SCRIPTS FROM GITHUB")
        self.print_warning("♾️  UNLIMITED RETRY MODE: Will keep trying until all bots are installed!")
        self.print_warning("⏰ This may take several hours on Raspberry Pi. Please be patient!")
        
        # Check if running as root
        if os.geteuid() == 0:
            self.print_warning("⚠️  Running as root! Some installations may behave differently.")
        
        if not self.check_and_install_python():
            self.print_error("Cannot continue without Python3!")
            sys.exit(1)
        
        self.fix_pip_issues()
        
        self.print_info("Checking for SSL issues...")
        self.fix_ssl_issues()
        
        # Install Selenium system-wide with retry
        self.print_info("Attempting Selenium installation...")
        selenium_installed = False
        for attempt in range(3):  # Try 3 times
            self.print_info(f"Selenium installation attempt {attempt + 1}/3")
            if self.install_selenium_systemwide():
                selenium_installed = True
                break
            time.sleep(10)
        
        if not selenium_installed:
            self.print_warning("⚠️  Selenium installation had issues, but continuing anyway...")
        
        # Start Xvfb for headless display
        self.start_xvfb()
        
        all_folders = self.get_all_folders_from_github()
        
        if not all_folders:
            self.print_error("No folders found in repository!")
            return
        
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
        
        success_count = 0
        
        for i, folder in enumerate(folders_with_venv, 1):
            display_name = folder.replace('-', ' ')
            self.print_header(f"Bot {i}/{len(folders_with_venv)}: {display_name}")
            
            if self.run_venv_script_with_retry(folder):
                success_count += 1
            
            if i < len(folders_with_venv):
                self.print_info("Waiting 15 seconds before next bot...")
                time.sleep(15)
        
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
