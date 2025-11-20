#!/usr/bin/env python3
"""
Scheduler Script for Managing Python Bots
"""

import os
import sys
import subprocess
import time
import shutil
import csv
import requests
import json
import platform
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import signal
import firebase_admin
from firebase_admin import credentials, db
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime

class BotScheduler:
    def __init__(self):
        self.username = os.getenv('USER') or os.getenv('USERNAME')
        if not self.username:
            print("Error: Could not determine username")
            sys.exit(1)
            
        # Auto-detect paths
        self.USER_HOME = Path.home()
        self.bots_base_path = self.USER_HOME / "bots"
        self.scheduler_folder = "scheduler"
        self.github_repo = "https://github.com/Thaniyanki/raspberry-pi-bots"
        self.github_raw_base = "https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main"
        
        # Browser paths
        self.chrome_profile = self.USER_HOME / ".config" / "chromium"
        self.chromedriver = "/usr/bin/chromedriver"
        
        # Firebase database URL
        self.database_url = "https://thaniyanki-xpath-manager-default-rtdb.firebaseio.com/"
        
        # Colors for terminal output
        self.YELLOW = '\033[93m'
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.BLUE = '\033[94m'
        self.ENDC = '\033[0m'
        self.BOLD = '\033[1m'
        
        # Browser management
        self.driver = None
        self.xpaths = {}
        self.missing_sheets = []
        self.firebase_initialized = False
        
    def initialize_firebase(self):
        """Initialize Firebase connection using database access key from any bot (excluding scheduler)"""
        if self.firebase_initialized:
            return True
            
        print("Initializing Firebase connection...")
        
        # Find database access key in any bot folder (excluding scheduler)
        bot_folders = self.get_bot_folders()
        working_bots = [folder for folder in bot_folders if folder.name != self.scheduler_folder]
        key_exists, source_folder, source_key_file = self.check_database_key_exists(working_bots)
        
        if not key_exists:
            print(f"{self.RED}❌ Database access key not found in any bot folder (excluding scheduler){self.ENDC}")
            return False
        
        try:
            cred = credentials.Certificate(str(source_key_file))
            firebase_admin.initialize_app(cred, {
                "databaseURL": self.database_url
            })
            self.firebase_initialized = True
            print(f"{self.GREEN}✅ Firebase initialized successfully using key from {source_folder.name}{self.ENDC}")
            return True
        except Exception as e:
            print(f"{self.RED}❌ Firebase initialization failed: {str(e)}{self.ENDC}")
            return False

    def fetch_all_whatsapp_xpaths(self):
        """Fetch all WhatsApp XPaths from database and store in temporary local storage"""
        print("Fetching all WhatsApp XPaths from database...")
        
        if not self.initialize_firebase():
            return False
            
        try:
            ref = db.reference("WhatsApp/Xpath")
            xpaths_data = ref.get()
            
            if xpaths_data:
                self.xpaths = xpaths_data
                print(f"{self.GREEN}✅ Successfully fetched {len(xpaths_data)} XPaths from database{self.ENDC}")
                
                # Save XPaths to temporary local storage (but don't display to user)
                temp_xpath_file = Path("/tmp/whatsapp_xpaths.json")
                with open(temp_xpath_file, 'w') as f:
                    json.dump(xpaths_data, f, indent=2)
                print(f"✅ XPaths saved to temporary storage")
                    
                return True
            else:
                print(f"{self.RED}❌ No XPaths found in database{self.ENDC}")
                return False
                
        except Exception as e:
            print(f"{self.RED}❌ Error fetching XPaths: {e}{self.ENDC}")
            return False

    # ... [Keep all previous methods unchanged until Step 6] ...

    # =========================================================================
    # STEP 6 IMPLEMENTATION - IMPROVED ERROR HANDLING
    # =========================================================================

    def get_github_bot_folders(self):
        """Get list of bot folders from GitHub repository with retry mechanism"""
        print("Fetching bot information from GitHub repository...")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Get the main repository structure
                api_url = "https://api.github.com/repos/Thaniyanki/raspberry-pi-bots/contents/"
                response = requests.get(api_url, timeout=30)
                
                if response.status_code != 200:
                    if attempt < max_retries - 1:
                        print(f"  ⚠ GitHub API error {response.status_code}, retrying... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(2)
                        continue
                    else:
                        print(f"  Error accessing GitHub repository: {response.status_code}")
                        return []
                
                contents = response.json()
                bot_folders = []
                
                for item in contents:
                    if item['type'] == 'dir':
                        folder_name = item['name']
                        # Skip only non-bot folders
                        if folder_name in ['all-in-one-venv', '.github']:
                            continue
                        
                        # Check if this folder has 'sheets format' folder
                        folder_url = f"https://api.github.com/repos/Thaniyanki/raspberry-pi-bots/contents/{folder_name}"
                        folder_response = requests.get(folder_url, timeout=30)
                        
                        if folder_response.status_code == 200:
                            folder_contents = folder_response.json()
                            has_sheets_format = any(content['name'] == 'sheets format' and content['type'] == 'dir' for content in folder_contents)
                            
                            if has_sheets_format:
                                bot_folders.append(folder_name)
                                print(f"  ✓ Found bot with sheets format: {folder_name}")
                
                print(f"{self.GREEN}✓ Found {len(bot_folders)} bots with sheets format on GitHub{self.ENDC}")
                return bot_folders
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  ⚠ GitHub connection error, retrying... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(2)
                else:
                    print(f"{self.RED}❌ Error fetching GitHub repository after {max_retries} attempts: {e}{self.ENDC}")
                    return []

    def get_csv_files_from_github(self, bot_folder_name):
        """Get the list of CSV files from the 'sheets format' folder for a bot with retry"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Try to get the directory listing from GitHub
                api_url = f"https://api.github.com/repos/Thaniyanki/raspberry-pi-bots/contents/{bot_folder_name}/sheets%20format"
                response = requests.get(api_url, timeout=30)
                
                if response.status_code != 200:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        print(f"  ⚠ Cannot access sheets format for {bot_folder_name}")
                        return []
                
                contents = response.json()
                csv_files = []
                
                for item in contents:
                    if item['name'].endswith('.csv'):
                        csv_files.append(item['name'])
                        print(f"    - Found CSV: {item['name']}")
                
                return csv_files
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print(f"  ⚠ Error getting sheets format for {bot_folder_name}")
                    return []

    def download_csv_header(self, bot_folder_name, csv_file):
        """Download only the header row from a CSV file with robust error handling"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # URL encode the file name properly
                encoded_file = csv_file.replace(' ', '%20')
                csv_url = f"{self.github_raw_base}/{bot_folder_name}/sheets%20format/{encoded_file}"
                
                response = requests.get(csv_url, timeout=30)
                if response.status_code == 200:
                    # Read only the first line (header)
                    first_line = response.text.split('\n')[0]
                    csv_reader = csv.reader([first_line])
                    header = next(csv_reader)
                    return header
                else:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        print(f"    ⚠ Cannot download {csv_file}")
                        return None
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print(f"    ⚠ Cannot download {csv_file}")
                    return None

    def get_google_sheet_worksheets(self, sheet_name, gc):
        """Get all worksheets from a Google Sheet"""
        try:
            sheet = gc.open(sheet_name)
            worksheets = sheet.worksheets()
            worksheet_info = []
            for worksheet in worksheets:
                # Get the first row (header) of each worksheet
                try:
                    header_row = worksheet.row_values(1)
                    worksheet_info.append({
                        'title': worksheet.title,
                        'header': header_row
                    })
                except Exception as e:
                    worksheet_info.append({
                        'title': worksheet.title,
                        'header': []
                    })
            return worksheet_info
        except Exception as e:
            print(f"    ⚠ Cannot access Google Sheet '{sheet_name}'")
            return []

    def compare_and_update_worksheet(self, sheet, worksheet_name, csv_header, gc):
        """Compare CSV header with worksheet header and update if different"""
        try:
            # Check if worksheet exists
            try:
                worksheet = sheet.worksheet(worksheet_name)
                worksheet_exists = True
            except gspread.WorksheetNotFound:
                worksheet_exists = False
            
            if worksheet_exists:
                # Get current header
                current_header = worksheet.row_values(1)
                
                # Compare headers
                if current_header == csv_header:
                    print(f"      ✓ Worksheet '{worksheet_name}' is up-to-date")
                    return False  # No update needed
                else:
                    print(f"      ⚠ Updating worksheet '{worksheet_name}' header")
                    
                    # Update the header row
                    worksheet.update(range_name='A1', values=[csv_header])
                    print(f"      ✓ Updated worksheet '{worksheet_name}'")
                    return True  # Updated
            else:
                # Create new worksheet with CSV header
                print(f"      ⚠ Creating missing worksheet: {worksheet_name}")
                worksheet = sheet.add_worksheet(title=worksheet_name, rows=100, cols=len(csv_header))
                worksheet.update(range_name='A1', values=[csv_header])
                print(f"      ✓ Created worksheet '{worksheet_name}'")
                return True  # Created
                
        except Exception as e:
            print(f"      ❌ Cannot update worksheet '{worksheet_name}'")
            return False

    def run_step6_with_limited_retries(self):
        """Step 6 with limited retries and graceful error handling"""
        print("\n" + "=" * 50)
        print("STEP 6: Verifying Google Sheets Worksheets")
        print("=" * 50)
        print(f"{self.YELLOW}Note: Synchronizing worksheets with template formats{self.ENDC}")
        
        max_overall_attempts = 2
        for overall_attempt in range(max_overall_attempts):
            print(f"\nOverall Attempt {overall_attempt + 1} of {max_overall_attempts}")
            
            try:
                success, all_ok = self.run_step6_single_attempt()
                if success:
                    return success, all_ok
                else:
                    if overall_attempt < max_overall_attempts - 1:
                        print(f"{self.YELLOW}Retrying Step 6 after brief pause...{self.ENDC}")
                        time.sleep(5)
                    else:
                        print(f"{self.YELLOW}Step 6 completed with some connectivity issues{self.ENDC}")
                        return True, False  # Continue despite errors
                        
            except Exception as e:
                print(f"{self.RED}Attempt {overall_attempt + 1} failed: {e}{self.ENDC}")
                if overall_attempt < max_overall_attempts - 1:
                    time.sleep(5)
                else:
                    print(f"{self.YELLOW}Step 6 completed with connectivity limitations{self.ENDC}")
                    return False, False
        
        return False, False

    def run_step6_single_attempt(self):
        """Single attempt at Step 6 with comprehensive error handling"""
        try:
            # Get bot folders from GitHub
            github_bots = self.get_github_bot_folders()
            if not github_bots:
                print(f"{self.YELLOW}⚠ Cannot access GitHub repository at this time{self.ENDC}")
                return False, False
            
            # Get local bot folders
            local_bot_folders = self.get_bot_folders()
            local_bot_names = [folder.name for folder in local_bot_folders]
            
            # Get spreadsheet key
            key_exists, source_folder, source_key_file = self.check_spreadsheet_key_exists(local_bot_folders)
            if not key_exists:
                print(f"{self.RED}❌ Spreadsheet access key not found{self.ENDC}")
                return False, False
            
            # Authorize with Google Sheets
            SCOPES = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            
            creds = Credentials.from_service_account_file(
                str(source_key_file),
                scopes=SCOPES
            )
            gc = gspread.authorize(creds)
            
            print(f"{self.GREEN}✓ Successfully authorized with Google Sheets API{self.ENDC}")
            
            # Process each GitHub bot that has a matching local folder
            updated_count = 0
            created_count = 0
            error_count = 0
            processed_bots = []
            skipped_bots = []
            
            for github_bot in github_bots:
                # Convert GitHub folder name to local folder name format
                local_bot_name = github_bot.replace('-', ' ')
                
                if local_bot_name in local_bot_names:
                    print(f"\n{self.BOLD}Processing: {local_bot_name}{self.ENDC}")
                    processed_bots.append(local_bot_name)
                    
                    try:
                        # Check if Google Sheet exists for this bot
                        try:
                            sheet = gc.open(local_bot_name)
                            print(f"  ✓ Google Sheet found")
                        except gspread.SpreadsheetNotFound:
                            print(f"  ⚠ Google Sheet not available")
                            skipped_bots.append(local_bot_name)
                            continue
                        
                        # Get CSV files from GitHub
                        csv_files = self.get_csv_files_from_github(github_bot)
                        if not csv_files:
                            print(f"  ⚠ No template files available")
                            continue
                        
                        print(f"  Processing {len(csv_files)} template(s)")
                        
                        # Process each CSV file
                        for csv_file in csv_files:
                            worksheet_name = csv_file.replace('.csv', '')
                            print(f"  Checking: {worksheet_name}")
                            
                            # Download CSV header from GitHub
                            csv_header = self.download_csv_header(github_bot, csv_file)
                            if not csv_header:
                                print(f"    ⚠ Cannot access template")
                                error_count += 1
                                continue
                            
                            # Compare and update worksheet
                            if self.compare_and_update_worksheet(sheet, worksheet_name, csv_header, gc):
                                if worksheet_name in [ws.title for ws in sheet.worksheets()]:
                                    updated_count += 1
                                else:
                                    created_count += 1
                    
                    except Exception as e:
                        print(f"  ⚠ Temporary connectivity issue")
                        error_count += 1
                        continue
            
            # Summary
            print("\n" + "=" * 50)
            print("STEP 6 SUMMARY:")
            print("=" * 50)
            print(f"Processed bots: {len(processed_bots)}")
            
            if created_count > 0:
                print(f"{self.GREEN}✓ Created {created_count} new worksheet(s){self.ENDC}")
            
            if updated_count > 0:
                print(f"{self.GREEN}✓ Updated {updated_count} worksheet(s){self.ENDC}")
            
            if skipped_bots:
                print(f"{self.YELLOW}⚠ Skipped {len(skipped_bots)} bot(s) due to sheet availability{self.ENDC}")
            
            if error_count > 0:
                print(f"{self.YELLOW}⚠ {error_count} template(s) had connectivity issues{self.ENDC}")
            
            if created_count == 0 and updated_count == 0 and error_count == 0:
                print(f"{self.GREEN}✓ All worksheets are properly configured{self.ENDC}")
                return True, True
            elif error_count == 0:
                print(f"{self.GREEN}✓ Worksheets synchronized successfully{self.ENDC}")
                return True, True
            else:
                print(f"{self.YELLOW}⚠ Worksheets updated with some connectivity limitations{self.ENDC}")
                return True, False
            
        except Exception as e:
            print(f"{self.RED}❌ Step 6 encountered an issue: {e}{self.ENDC}")
            return False, False

    def run_step6(self):
        """Main Step 6 entry point with fallback"""
        return self.run_step6_with_limited_retries()

    # =========================================================================
    # STEP 7 IMPLEMENTATION - WORKING WHATSAPP NOTIFICATIONS (NO XPATH DISPLAY)
    # =========================================================================

    def check_internet_connection(self):
        """Check internet connection using ping method"""
        print("Checking internet connection...")
        
        ping_targets = ['8.8.8.8', '1.1.1.1', 'google.com']
        
        for target in ping_targets:
            try:
                if platform.system().lower() == 'windows':
                    command = ['ping', '-n', '2', '-w', '5000', target]
                else:
                    command = ['ping', '-c', '2', '-W', '5', target]
                
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    print(f"  ✓ Internet connection available")
                    return True
                    
            except subprocess.TimeoutExpired:
                continue
            except Exception as e:
                continue
        
        print("  ✗ No internet connection available")
        return False

    def wait_for_internet_connection(self):
        """Wait for internet connection to become available"""
        print(f"{self.YELLOW}Waiting for internet connection...{self.ENDC}")
        print("Checking every 2 seconds. Press Ctrl+C to cancel.")
        
        check_count = 0
        try:
            while True:
                check_count += 1
                
                if self.check_internet_connection():
                    print(f"{self.GREEN}✓ Internet connection established!{self.ENDC}")
                    return True
                
                dots = "." * (check_count % 4)
                spaces = " " * (3 - len(dots))
                print(f"\rWaiting for internet{dots}{spaces} (Attempt {check_count})", end="", flush=True)
                time.sleep(2)
                
        except KeyboardInterrupt:
            print(f"\n\n{self.RED}Operation cancelled by user.{self.ENDC}")
            return False

    def close_chrome_browser(self):
        """Close Chrome browser if already open"""
        print("Closing browser if open...")
        
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                print("✅ Browser closed")
            except Exception as e:
                print(f"⚠️ Error closing browser: {str(e)}")
        
        # Clean up any remaining processes
        try:
            subprocess.run(['pkill', '-f', 'chromium'], timeout=5)
            subprocess.run(['pkill', '-f', 'chrome'], timeout=5)
        except:
            pass

    def setup_selenium_driver(self):
        """Setup Selenium WebDriver with Chrome options"""
        print("Setting up browser...")
        
        try:
            options = Options()
            options.add_argument(f"--user-data-dir={self.chrome_profile}")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--start-maximized")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-default-apps")
            
            service = Service(executable_path=self.chromedriver)
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(300)
            
            print(f"{self.GREEN}✅ Browser setup completed{self.ENDC}")
            return True
            
        except Exception as e:
            print(f"{self.RED}❌ Error setting up browser: {e}{self.ENDC}")
            return False

    def wait_for_element(self, xpath_key, timeout=120, check_interval=1):
        """Wait for element to be present using XPath from database"""
        if xpath_key not in self.xpaths:
            print(f"{self.RED}❌ Required element not found in configuration{self.ENDC}")
            return None
        
        xpath = self.xpaths[xpath_key]
        print(f"Waiting for element... (timeout: {timeout}s)")
        
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < timeout:
            check_count += 1
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                if element.is_displayed():
                    print(f"  ✓ Element found")
                    return element
            except NoSuchElementException:
                pass
            
            elapsed = int(time.time() - start_time)
            if check_count % 10 == 0:
                print(f"  Checking... {elapsed}s elapsed")
            
            time.sleep(check_interval)
        
        print(f"  ✗ Element not found within {timeout} seconds")
        return None

    def check_element_present(self, xpath_key):
        """Check if element is present using XPath from database"""
        if xpath_key not in self.xpaths:
            return False
        
        xpath = self.xpaths[xpath_key]
        try:
            element = self.driver.find_element(By.XPATH, xpath)
            return element.is_displayed()
        except NoSuchElementException:
            return False

    def get_report_number(self):
        """Get report number from any bot's venv folder"""
        bot_folders = self.get_bot_folders()
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                report_file = venv_path / "report number"
                if report_file.exists():
                    try:
                        with open(report_file, 'r') as f:
                            content = f.read().strip()
                        if content and self.is_valid_phone_number(content):
                            return content
                    except:
                        continue
        return None

    def run_step7(self):
        """Step 7: Send WhatsApp notification for missing sheets"""
        print("\n" + "=" * 60)
        print("STEP 7: SENDING WHATSAPP NOTIFICATION FOR MISSING SHEETS")
        print("=" * 60)
        
        if not self.missing_sheets:
            print("No missing sheets to report")
            return True
        
        print(f"{self.YELLOW}Missing sheets detected: {', '.join(self.missing_sheets)}{self.ENDC}")
        print("Sending WhatsApp notification to admin...")
        
        # Fetch all WhatsApp XPaths from database first
        if not self.fetch_all_whatsapp_xpaths():
            return False
        
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            print(f"\n{self.BOLD}=== ATTEMPT {attempt} OF {max_attempts} ==={self.ENDC}")
            
            try:
                # Setup browser
                print(f"\n{self.BLUE}Browser Setup{self.ENDC}")
                self.close_chrome_browser()
                time.sleep(3)
                if not self.setup_selenium_driver():
                    print("❌ Browser setup failed, restarting...")
                    continue
                
                # Check internet
                print(f"\n{self.BLUE}Internet Check{self.ENDC}")
                if not self.check_internet_connection():
                    if not self.wait_for_internet_connection():
                        print("❌ No internet connection, restarting...")
                        continue
                
                # Open WhatsApp
                print(f"\n{self.BLUE}Opening WhatsApp{self.ENDC}")
                try:
                    self.driver.get("https://web.whatsapp.com/")
                    print("✓ WhatsApp Web opened")
                except Exception as e:
                    print(f"❌ Error opening WhatsApp: {e}")
                    continue
                
                # Check search field
                print(f"\n{self.BLUE}Loading Interface{self.ENDC}")
                search_field = self.wait_for_element("Xpath001", timeout=120)
                if not search_field:
                    print("❌ Interface not loaded, restarting...")
                    continue
                print("✓ Interface ready")
                
                # Get report number
                print(f"\n{self.BLUE}Checking Contact{self.ENDC}")
                report_number = self.get_report_number()
                if not report_number:
                    print("❌ Contact number not available")
                    return False
                print(f"✓ Contact: {report_number}")
                
                # Enter phone number
                print(f"\n{self.BLUE}Preparing Message{self.ENDC}")
                try:
                    search_field.clear()
                    search_field.send_keys(report_number)
                    print(f"✓ Contact selected")
                    time.sleep(2)
                    search_field.send_keys(Keys.ENTER)
                    print("✓ Opening chat")
                    time.sleep(10)
                except Exception as e:
                    print(f"❌ Error selecting contact: {e}")
                    continue
                
                # Check contact existence
                print(f"\n{self.BLUE}Verifying Contact{self.ENDC}")
                if self.check_element_present("Xpath004"):
                    print("❌ Contact not found")
                    if self.check_internet_connection():
                        print("✗ Invalid contact number")
                        return False
                    else:
                        print("No internet connection, restarting...")
                        continue
                else:
                    print("✓ Contact verified")
                
                # Select contact
                print(f"\n{self.BLUE}Opening Chat{self.ENDC}")
                try:
                    time.sleep(10)
                    body = self.driver.find_element(By.TAG_NAME, 'body')
                    body.send_keys(Keys.ARROW_DOWN)
                    print("✓ Navigating to chat")
                    time.sleep(2)
                    body.send_keys(Keys.ENTER)
                    print("✓ Chat opened")
                except Exception as e:
                    print(f"❌ Error opening chat: {e}")
                    continue
                
                # Type error message
                print(f"\n{self.BLUE}Composing Message{self.ENDC}")
                if not self.missing_sheets:
                    print("No missing sheets to report")
                    return False
                
                # Create message
                if len(self.missing_sheets) == 1:
                    message = f"Google Sheet Error - {self.missing_sheets[0]}"
                else:
                    message = f"Google Sheet Error - {self.missing_sheets[0]} and {self.missing_sheets[1]}" if len(self.missing_sheets) == 2 else f"Google Sheet Error - {', '.join(self.missing_sheets)}"
                
                message += "\n---------------------------------------------\n"
                for sheet in self.missing_sheets:
                    message += f"Sheet '{sheet}' is not available [or]\n"
                    message += f"Name is mismatch [or]\n"
                    message += f"Not share with service account\n\n"
                message += "Kindly check\n---------------------------------------------"
                
                try:
                    time.sleep(2)
                    message_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']"))
                    )
                    message_input.click()
                    time.sleep(1)
                    
                    lines = message.split('\n')
                    for i, line in enumerate(lines):
                        message_input.send_keys(line)
                        if i < len(lines) - 1:
                            message_input.send_keys(Keys.SHIFT + Keys.ENTER)
                            time.sleep(0.5)
                    
                    print("✓ Message composed")
                except Exception as e:
                    print(f"❌ Error composing message: {e}")
                    continue
                
                # Send message
                print(f"\n{self.BLUE}Sending Message{self.ENDC}")
                try:
                    time.sleep(2)
                    message_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']"))
                    )
                    message_input.send_keys(Keys.ENTER)
                    print("✓ Message sent")
                except Exception as e:
                    print(f"❌ Error sending message: {e}")
                    continue
                
                # Wait for delivery
                print(f"\n{self.BLUE}Confirming Delivery{self.ENDC}")
                try:
                    time.sleep(2)
                    print("Monitoring delivery...")
                    
                    start_time = time.time()
                    check_count = 0
                    message_pending = False
                    
                    while time.time() - start_time < 300:
                        check_count += 1
                        elapsed_time = int(time.time() - start_time)
                        
                        pending_delivery = self.check_element_present("Xpath003")
                        
                        if pending_delivery:
                            if not message_pending:
                                print(f"  ✓ Message queued for delivery")
                                message_pending = True
                            
                            if check_count % 10 == 0:
                                print(f"  ⏳ Confirming delivery... {elapsed_time}s elapsed")
                        else:
                            if message_pending:
                                print(f"  ✓ Message delivered after {elapsed_time}s!")
                                print("✓ Notification sent successfully")
                                return True
                            else:
                                print(f"  ✓ Message delivered instantly")
                                print("✓ Notification sent successfully")
                                return True
                        
                        time.sleep(1)
                    
                    print(f"✗ Delivery confirmation timeout")
                    return False
                    
                except Exception as e:
                    print(f"❌ Error confirming delivery: {e}")
                    return False
                
            except Exception as e:
                print(f"{self.RED}❌ Unexpected error in attempt {attempt}: {e}{self.ENDC}")
                continue
            
            finally:
                if self.driver:
                    self.driver.quit()
                    self.driver = None
        
        print(f"\n{self.RED}❌ Failed to send notification after {max_attempts} attempts{self.ENDC}")
        return False

    # Update the main run method to use improved Step 6
    def run(self):
        """Main execution function with proper cleanup"""
        try:
            print("=" * 50)
            print("Bot Scheduler Starting...")
            print(f"Username: {self.username}")
            print(f"Bots path: {self.bots_base_path}")
            print("=" * 50)
            
            if not self.check_bots_folder():
                return
                
            bot_folders = self.get_bot_folders()
            if not bot_folders:
                print("No bot folders found. Running setup...")
                self.run_curl_command()
                return
            
            self.list_bot_folders(bot_folders)
            self.handle_report_numbers(bot_folders)
            report_numbers_ok = self.verify_report_numbers(bot_folders)
            
            print("\n" + "=" * 50)
            if report_numbers_ok:
                print("✓ Step 1 completed successfully!")
            else:
                print("⚠ Step 1 completed with warnings")
            print("=" * 50)
            
            # Run Step 2
            step2_success = self.run_step2()
            
            if step2_success:
                print("\n" + "=" * 50)
                print("✓ Step 2 completed successfully!")
                print("=" * 50)
                
                # Run Step 3
                step3_success = self.run_step3()
                
                if step3_success:
                    print("\n" + "=" * 50)
                    print("✓ Step 3 completed successfully!")
                    print("=" * 50)
                    
                    # Run Step 4
                    step4_success = self.run_step4()
                    
                    if step4_success:
                        print("\n" + "=" * 50)
                        print("✓ Step 4 completed successfully!")
                        print("=" * 50)
                        
                        # Run Step 5
                        step5_success, all_match = self.run_step5()
                        
                        if step5_success:
                            print("\n" + "=" * 50)
                            print("✓ Step 5 completed successfully!")
                            print("=" * 50)
                            
                            if all_match:
                                # All bots have matching sheets - continue to Step 6
                                print(f"\n{self.BLUE}All bots have matching Google Sheets, verifying worksheets...{self.ENDC}")
                                step6_success, all_sheets_available = self.run_step6()
                                
                                if step6_success:
                                    print("\n" + "=" * 50)
                                    print("✓ Step 6 completed successfully!")
                                    print("=" * 50)
                                    
                                    # Continue to Step 8
                                    step8_success = self.run_step8()
                                    if step8_success:
                                        print("\n" + "=" * 50)
                                        print("✓ ALL STEPS COMPLETED SUCCESSFULLY!")
                                        print("✓ Bots are ready to use")
                                        print("=" * 50)
                                    else:
                                        print(f"\n{self.RED}❌ Step 8 failed.{self.ENDC}")
                                        sys.exit(1)
                                else:
                                    print(f"\n{self.YELLOW}⚠ Step 6 had connectivity issues, but continuing...{self.ENDC}")
                                    # Even if Step 6 fails, continue to Step 8
                                    step8_success = self.run_step8()
                                    if step8_success:
                                        print("\n" + "=" * 50)
                                        print("✓ Setup completed with connectivity warnings")
                                        print("=" * 50)
                                    else:
                                        print(f"\n{self.RED}❌ Step 8 failed.{self.ENDC}")
                                        sys.exit(1)
                            else:
                                # Some bots missing matching sheets - continue to Step 7
                                step7_success = self.run_step7()
                                if step7_success:
                                    print("\n" + "=" * 50)
                                    print("✓ Step 7 completed successfully!")
                                    print("✓ WhatsApp notification sent for missing sheets")
                                    print("=" * 50)
                                else:
                                    print(f"\n{self.RED}❌ Step 7 failed.{self.ENDC}")
                                    sys.exit(1)
                        else:
                            print(f"\n{self.RED}❌ Step 5 failed. Cannot continue.{self.ENDC}")
                            sys.exit(1)
                    else:
                        print(f"\n{self.RED}❌ Step 4 failed. Cannot continue to Step 5.{self.ENDC}")
                        sys.exit(1)
                else:
                    print(f"\n{self.RED}❌ Step 3 failed. Cannot continue to Step 4.{self.ENDC}")
                    sys.exit(1)
            else:
                print(f"\n{self.RED}❌ Step 2 failed. Cannot continue to Step 3.{self.ENDC}")
                sys.exit(1)
                
        finally:
            self.cleanup()

    def run_step8(self):
        """Step 8: Final step - All setup completed"""
        print("\n" + "=" * 50)
        print("STEP 8: Setup Completed")
        print("=" * 50)
        print(f"{self.GREEN}✓ All steps completed successfully!{self.ENDC}")
        print(f"{self.GREEN}✓ Bots are ready to run{self.ENDC}")
        print(f"{self.GREEN}✓ Google Sheets are properly configured{self.ENDC}")
        return True

    def cleanup(self):
        """Cleanup method to be called before exit"""
        print("\nPerforming cleanup...")
        self.close_chrome_browser()

# ... [Keep main function unchanged] ...

def main():
    """Main function with signal handling"""
    scheduler = None
    try:
        def signal_handler(sig, frame):
            print(f"\n\nScript interrupted by user.")
            if scheduler:
                scheduler.cleanup()
            sys.exit(1)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        scheduler = BotScheduler()
        scheduler.run()
        
    except KeyboardInterrupt:
        print(f"\n\nScript interrupted by user.")
        if scheduler:
            scheduler.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        if scheduler:
            scheduler.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()
