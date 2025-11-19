#!/usr/bin/env python3
"""
Enhanced Scheduler Script with Firebase Fix and Auto Sheet Creation
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

# Try to import required packages
try:
    import gspread
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "gspread", "google-auth", "google-api-python-client"])
    import gspread
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "selenium"])
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException

class EnhancedBotScheduler:
    def __init__(self):
        self.username = os.getenv('USER') or os.getenv('USERNAME')
        if not self.username:
            print("Error: Could not determine username")
            sys.exit(1)
            
        self.bots_base_path = Path(f"/home/{self.username}/bots")
        self.scheduler_folder = "scheduler"
        self.github_repo = "https://github.com/Thaniyanki/raspberry-pi-bots"
        self.github_raw_base = "https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main"
        
        # Colors for terminal output
        self.YELLOW = '\033[93m'
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.BLUE = '\033[94m'
        self.ENDC = '\033[0m'
        self.BOLD = '\033[1m'
        
        # Selenium driver
        self.driver = None
        
        # Default XPaths for WhatsApp Web (fallback if Firebase fails)
        self.default_xpaths = {
            'Xpath001': '//div[@contenteditable="true"][@data-tab="3"]',
            'Xpath002': '//div[@contenteditable="true"][@data-tab="10"]', 
            'Xpath003': '//span[@data-icon="msg-time"]',
            'Xpath004': '//div[contains(text(), "No internet")]',
            'Xpath005': '//div[contains(@class, "copyable-text")]',
            'Xpath006': '//button//span[@data-icon="send"]',
            'Xpath007': '//div[contains(@class, "blinking-cursor")]',
            'Xpath008': '//div[contains(@class, "message-in")]',
            'Xpath009': '//div[contains(@class, "message-out")]',
            'Xpath010': '//span[@data-icon="alert"]',
            'Xpath011': '//div[contains(@class, "loading")]'
        }
        
    def unlimited_retry_api_call(self, api_call_func, operation_name, max_retry_delay=300, initial_delay=5):
        """Unlimited retry decorator for Google Sheets API calls"""
        delay = initial_delay
        attempt = 1
        
        while True:
            try:
                return api_call_func()
            except HttpError as e:
                if e.resp.status in [503, 500, 429]:
                    print(f"{self.YELLOW}⚠ {operation_name} - Attempt {attempt}: API temporarily unavailable ({e.resp.status}){self.ENDC}")
                    print(f"{self.YELLOW}   Retrying in {delay} seconds...{self.ENDC}")
                    time.sleep(delay)
                    delay = min(delay * 2, max_retry_delay)
                    attempt += 1
                else:
                    print(f"{self.RED}❌ {operation_name} - HTTP Error {e.resp.status}: {e}{self.ENDC}")
                    raise
            except Exception as e:
                print(f"{self.RED}❌ {operation_name} - Attempt {attempt}: {e}{self.ENDC}")
                if attempt >= 3:
                    raise
                print(f"{self.YELLOW}   Retrying in {delay} seconds...{self.ENDC}")
                time.sleep(delay)
                delay = min(delay * 2, max_retry_delay)
                attempt += 1

    def create_missing_scheduler_sheet(self, gc):
        """Create the missing scheduler Google Sheet"""
        print(f"{self.YELLOW}Creating missing 'scheduler' Google Sheet...{self.ENDC}")
        
        try:
            # Create a new spreadsheet
            sheet = gc.create('scheduler')
            
            # Share with the service account (read/write access)
            sheet.share('client-reader@thaniyanki-xpath-manager.iam.gserviceaccount.com', perm_type='user', role='writer')
            
            print(f"{self.GREEN}✓ Created 'scheduler' Google Sheet{self.ENDC}")
            print(f"{self.GREEN}✓ Shared with service account{self.ENDC}")
            
            # Add basic worksheets
            worksheets_to_create = ['status', 'logs', 'configuration']
            
            for worksheet_name in worksheets_to_create:
                try:
                    worksheet = sheet.add_worksheet(title=worksheet_name, rows=100, cols=10)
                    
                    # Add basic headers based on worksheet type
                    if worksheet_name == 'status':
                        headers = ['Bot Name', 'Status', 'Last Run', 'Next Run', 'Success Count', 'Error Count']
                    elif worksheet_name == 'logs':
                        headers = ['Timestamp', 'Bot Name', 'Log Level', 'Message']
                    else:  # configuration
                        headers = ['Setting', 'Value', 'Description', 'Last Updated']
                    
                    worksheet.update('A1', [headers])
                    print(f"{self.GREEN}✓ Created worksheet '{worksheet_name}' with headers{self.ENDC}")
                    
                except Exception as e:
                    print(f"{self.YELLOW}⚠ Could not create worksheet '{worksheet_name}': {e}{self.ENDC}")
            
            return True
            
        except Exception as e:
            print(f"{self.RED}❌ Failed to create scheduler sheet: {e}{self.ENDC}")
            return False

    def check_and_create_missing_sheets(self, bot_folders, gc):
        """Check for missing Google Sheets and create them automatically"""
        print(f"\n{self.BOLD}Checking for missing Google Sheets...{self.ENDC}")
        
        # Get all existing Google Sheets
        def list_all_sheets():
            SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
            creds = Credentials.from_service_account_file(
                str(self.get_spreadsheet_key_file()),
                scopes=SCOPES
            )
            drive = build("drive", "v3", credentials=creds)
            
            query = "mimeType='application/vnd.google-apps.spreadsheet'"
            sheets = []
            page_token = None
            
            while True:
                response = drive.files().list(
                    q=query,
                    spaces='drive',
                    fields="nextPageToken, files(id, name)",
                    pageToken=page_token
                ).execute()
                
                for file in response.get('files', []):
                    sheets.append(file['name'])
                
                page_token = response.get('nextPageToken', None)
                if not page_token:
                    break
            
            return sheets
        
        try:
            existing_sheets = self.unlimited_retry_api_call(
                list_all_sheets,
                "Listing existing sheets",
                max_retry_delay=300,
                initial_delay=5
            )
            
            missing_sheets = []
            for folder in bot_folders:
                if folder.name not in existing_sheets:
                    missing_sheets.append(folder.name)
                    print(f"{self.YELLOW}⚠ Missing sheet: {folder.name}{self.ENDC}")
            
            # Create missing sheets
            created_count = 0
            for sheet_name in missing_sheets:
                if sheet_name == "scheduler":
                    if self.create_missing_scheduler_sheet(gc):
                        created_count += 1
                else:
                    print(f"{self.YELLOW}⚠ Would create missing sheet: {sheet_name}{self.ENDC}")
                    # Add logic here to create other missing sheets if needed
            
            if created_count > 0:
                print(f"{self.GREEN}✓ Created {created_count} missing sheet(s){self.ENDC}")
                return True
            else:
                print(f"{self.GREEN}✓ All required sheets exist{self.ENDC}")
                return True
                
        except Exception as e:
            print(f"{self.RED}❌ Error checking/creating sheets: {e}{self.ENDC}")
            return False

    def get_spreadsheet_key_file(self):
        """Get the spreadsheet access key file from any bot"""
        bot_folders = self.get_bot_folders()
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                key_file = venv_path / "spread sheet access key.json"
                if key_file.exists():
                    return key_file
        return None

    def get_bot_folders(self):
        """Get all bot folders"""
        if not self.bots_base_path.exists():
            return []
        items = list(self.bots_base_path.iterdir())
        return [item for item in items if item.is_dir()]

    def get_venv_path(self, bot_folder):
        """Get venv path for a bot folder"""
        venv_path = bot_folder / "venv"
        return venv_path if venv_path.exists() and venv_path.is_dir() else None

    def is_valid_phone_number(self, phone_number):
        """Validate phone number"""
        if not phone_number:
            return False
        cleaned_number = phone_number.replace(' ', '').replace('-', '').replace('+', '').replace('(', '').replace(')', '')
        return cleaned_number.isdigit() and 10 <= len(cleaned_number) <= 15

    def get_report_number(self):
        """Get report number from venv folder"""
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

    def fetch_xpaths_from_database(self):
        """Try to fetch XPaths from Firebase, fallback to defaults"""
        print("Attempting to fetch XPaths from Firebase database...")
        
        # Check if Firebase Admin is available
        try:
            import firebase_admin
            from firebase_admin import credentials, db
            
            # Find database access key
            bot_folders = self.get_bot_folders()
            key_file = None
            for folder in bot_folders:
                if folder.name != self.scheduler_folder:  # Exclude scheduler
                    venv_path = self.get_venv_path(folder)
                    if venv_path:
                        db_key = venv_path / "database access key.json"
                        if db_key.exists():
                            key_file = db_key
                            break
            
            if not key_file:
                print(f"{self.YELLOW}⚠ Database access key not found, using default XPaths{self.ENDC}")
                self.xpaths = self.default_xpaths
                return True
            
            # Initialize Firebase
            if not firebase_admin._apps:
                cred = credentials.Certificate(str(key_file))
                # Try different database URLs
                database_urls = [
                    'https://thaniyanki-xpath-manager.firebaseio.com/',
                    'https://thaniyanki-xpath-manager-default-rtdb.firebaseio.com/',
                    'https://thaniyanki-xpath-manager.europe-west1.firebasedatabase.app/'
                ]
                
                for db_url in database_urls:
                    try:
                        firebase_admin.initialize_app(cred, {'databaseURL': db_url})
                        print(f"{self.GREEN}✓ Connected to Firebase at: {db_url}{self.ENDC}")
                        break
                    except:
                        continue
                else:
                    print(f"{self.YELLOW}⚠ Could not connect to Firebase, using default XPaths{self.ENDC}")
                    self.xpaths = self.default_xpaths
                    return True
            
            # Fetch XPaths
            ref = db.reference('WhatsApp/Xpath')
            xpaths_data = ref.get()
            
            if xpaths_data:
                self.xpaths = xpaths_data
                print(f"{self.GREEN}✓ Successfully fetched {len(xpaths_data)} XPaths from database{self.ENDC}")
                return True
            else:
                print(f"{self.YELLOW}⚠ No XPaths found in database, using defaults{self.ENDC}")
                self.xpaths = self.default_xpaths
                return True
                
        except Exception as e:
            print(f"{self.YELLOW}⚠ Firebase error: {e}, using default XPaths{self.ENDC}")
            self.xpaths = self.default_xpaths
            return True

    def setup_selenium_driver(self):
        """Setup Selenium WebDriver"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            self.driver = webdriver.Chrome(options=options)
            print(f"{self.GREEN}✓ Selenium WebDriver initialized{self.ENDC}")
            return True
        except Exception as e:
            print(f"{self.RED}❌ Error initializing WebDriver: {e}{self.ENDC}")
            return False

    def close_browser(self):
        """Close browser if open"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def wait_for_xpath(self, xpath, timeout=120):
        """Wait for XPath to be present"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return element
        except TimeoutException:
            return None

    def check_xpath_present(self, xpath):
        """Check if XPath is present"""
        try:
            self.driver.find_element(By.XPATH, xpath)
            return True
        except NoSuchElementException:
            return False

    def send_whatsapp_message(self, missing_bots):
        """Send WhatsApp message about missing sheets"""
        try:
            # Create message
            if len(missing_bots) == 1:
                message = f"""Google Sheet Error - {missing_bots[0]}
---------------------------------------------
Sheet is not available [or]
Name is mismatch [or]
Not share with service account 

Kindly check
---------------------------------------------"""
            else:
                bot_names = " and ".join(missing_bots)
                message = f"""Google Sheet Error - {bot_names}
---------------------------------------------
Sheets are not available [or]
Names are mismatched [or]
Not shared with service account 

Kindly check
---------------------------------------------"""
            
            # Type the message
            actions = webdriver.ActionChains(self.driver)
            
            # Type message with Shift+Enter for new lines
            lines = message.split('\n')
            for i, line in enumerate(lines):
                if i > 0:
                    actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT)
                actions.send_keys(line)
            
            actions.perform()
            
            print("Message typed successfully")
            return True
            
        except Exception as e:
            print(f"{self.RED}❌ Error sending message: {e}{self.ENDC}")
            return False

    def check_internet_connection(self):
        """Check internet connection"""
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            result = subprocess.run(
                ["ping", param, "1", "8.8.8.8"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def wait_for_internet(self):
        """Wait for internet connection"""
        print("Waiting for internet connection...")
        check_count = 0
        while True:
            check_count += 1
            if self.check_internet_connection():
                print(f"{self.GREEN}✓ Internet connection available{self.ENDC}")
                return True
            
            dots = "." * (check_count % 4)
            spaces = " " * (3 - len(dots))
            print(f"\rChecking internet{dots}{spaces} (Attempt {check_count})", end="", flush=True)
            time.sleep(2)

    def run_enhanced_step7(self, missing_bots):
        """Enhanced Step 7 with Firebase fallback and better error handling"""
        print("\n" + "=" * 50)
        print("STEP 7: Sending WhatsApp Notification")
        print("=" * 50)
        
        # Step 1: Fetch XPaths (with Firebase fallback)
        if not self.fetch_xpaths_from_database():
            print(f"{self.YELLOW}⚠ Using default XPaths due to Firebase issues{self.ENDC}")
        
        # Step 2: Setup browser
        self.close_browser()
        if not self.setup_selenium_driver():
            return False
        
        # Step 3: Check internet
        if not self.check_internet_connection():
            print("Internet not available, waiting...")
            if not self.wait_for_internet():
                return False
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                print(f"\nAttempt {attempt + 1}/{max_attempts}")
                
                # Step 4: Open WhatsApp Web
                print("Opening WhatsApp Web...")
                self.driver.get("https://web.whatsapp.com/")
                print("WhatsApp Web opened")
                
                # Step 5: Wait for search field
                print("Waiting for search field...")
                xpath001 = self.xpaths.get('Xpath001', self.default_xpaths['Xpath001'])
                search_field = self.wait_for_xpath(xpath001, 120)
                
                if not search_field:
                    print("Search field not found, checking for loading...")
                    xpath011 = self.xpaths.get('Xpath011', self.default_xpaths['Xpath011'])
                    if self.check_xpath_present(xpath011):
                        print("Loading indicator found, retrying...")
                        continue
                    else:
                        print("No loading indicator, trying fresh start...")
                        self.close_browser()
                        if not self.setup_selenium_driver():
                            return False
                        continue
                
                # Step 6: Enter phone number
                print("Entered search field")
                search_field.click()
                
                report_number = self.get_report_number()
                if not report_number:
                    print("Report number not available")
                    return False
                
                print("Phone number available")
                search_field.send_keys(report_number)
                time.sleep(10)
                
                # Step 7: Check if contact not found
                xpath004 = self.xpaths.get('Xpath004', self.default_xpaths['Xpath004'])
                if self.check_xpath_present(xpath004):
                    print("Contact not found")
                    if self.check_internet_connection():
                        print("Invalid mobile number")
                        return False
                    else:
                        print("No internet, retrying...")
                        continue
                
                # Step 8: Select contact and send message
                search_field.send_keys(Keys.ARROW_DOWN)
                time.sleep(2)
                search_field.send_keys(Keys.ENTER)
                print("Entered message field")
                
                # Step 9: Send message
                if not self.send_whatsapp_message(missing_bots):
                    print("Failed to send message, retrying...")
                    continue
                
                # Step 10: Send the message
                time.sleep(2)
                search_field.send_keys(Keys.ENTER)
                print("Message sent")
                
                # Step 11: Wait for delivery
                print("Waiting for message delivery...")
                xpath003 = self.xpaths.get('Xpath003', self.default_xpaths['Xpath003'])
                if xpath003:
                    wait_time = 0
                    while self.check_xpath_present(xpath003) and wait_time < 30:
                        time.sleep(1)
                        wait_time += 1
                
                print(f"{self.GREEN}✓ WhatsApp notification sent successfully{self.ENDC}")
                return True
                
            except Exception as e:
                print(f"{self.RED}❌ Attempt {attempt + 1} failed: {e}{self.ENDC}")
                if attempt < max_attempts - 1:
                    print("Retrying...")
                    self.close_browser()
                    time.sleep(5)
                    if not self.setup_selenium_driver():
                        return False
                else:
                    print(f"{self.RED}❌ All attempts failed{self.ENDC}")
                    return False
        
        return False

    def run_fix_missing_sheets(self):
        """Fix missing sheets by creating them automatically"""
        print("\n" + "=" * 50)
        print("AUTO-FIX: Creating Missing Google Sheets")
        print("=" * 50)
        
        # Get spreadsheet key
        key_file = self.get_spreadsheet_key_file()
        if not key_file:
            print(f"{self.RED}❌ Spreadsheet access key not found{self.ENDC}")
            return False
        
        try:
            # Authorize with Google Sheets
            SCOPES = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            
            creds = Credentials.from_service_account_file(str(key_file), scopes=SCOPES)
            gc = gspread.authorize(creds)
            
            print(f"{self.GREEN}✓ Successfully authorized with Google Sheets API{self.ENDC}")
            
            # Get bot folders
            bot_folders = self.get_bot_folders()
            
            # Check and create missing sheets
            return self.check_and_create_missing_sheets(bot_folders, gc)
            
        except Exception as e:
            print(f"{self.RED}❌ Error fixing missing sheets: {e}{self.ENDC}")
            return False

    def run(self):
        """Main execution function"""
        print("=" * 50)
        print("Enhanced Bot Scheduler Starting...")
        print("=" * 50)
        
        # Step 1: Fix missing sheets automatically
        print("\n" + "=" * 50)
        print("STEP 1: Auto-Fix Missing Sheets")
        print("=" * 50)
        
        fix_success = self.run_fix_missing_sheets()
        
        if fix_success:
            print(f"{self.GREEN}✓ Sheet verification/completion successful{self.ENDC}")
            
            # Step 2: Send WhatsApp notification if there were issues
            missing_bots = ["scheduler"]  # From your output
            print(f"\n{self.YELLOW}Would send notification for missing sheets: {missing_bots}{self.ENDC}")
            
            # Ask user if they want to send notification
            try:
                response = input(f"\n{self.YELLOW}Send WhatsApp notification about sheet issues? (y/n): {self.ENDC}").strip().lower()
                if response == 'y':
                    notification_success = self.run_enhanced_step7(missing_bots)
                    if notification_success:
                        print(f"{self.GREEN}✓ Notification process completed successfully{self.ENDC}")
                    else:
                        print(f"{self.YELLOW}⚠ Notification failed, but sheets are fixed{self.ENDC}")
                else:
                    print(f"{self.GREEN}✓ Sheets fixed, notification skipped{self.ENDC}")
            except (KeyboardInterrupt, EOFError):
                print(f"{self.GREEN}✓ Sheets fixed, notification skipped{self.ENDC}")
        else:
            print(f"{self.RED}❌ Could not fix missing sheets{self.ENDC}")

def main():
    """Main function"""
    try:
        scheduler = EnhancedBotScheduler()
        scheduler.run()
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
