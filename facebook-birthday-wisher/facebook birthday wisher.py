# Facebook Birthday Wisher Python Script
# ================================
# CONFIGURATION SECTION
# ================================
import os
import subprocess
import time
import sys
import firebase_admin
from firebase_admin import credentials, db
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dateutil.parser import parse
from PIL import Image
import random
import traceback
from urllib3.exceptions import ReadTimeoutError

# ================================
# FLEXIBLE CONFIGURATION - AUTO-DETECTED
# ================================
# Auto-detect user home directory
USER_HOME = os.path.expanduser("~")
# Extract username from home directory path
BASE_USER = os.path.basename(USER_HOME)

# Base directory structure - Auto-detected
BASE_DIR = os.path.join(USER_HOME, "bots")
FACEBOOK_BIRTHDAY_DIR = os.path.join(BASE_DIR, "Facebook birthday wisher")

# All file and directory paths - CENTRALIZED
PATHS = {
    # Firebase
    "firebase_credentials": os.path.join(FACEBOOK_BIRTHDAY_DIR, "venv", "database access key.json"),
    
    # Google Sheets
    "google_sheets_credentials": os.path.join(FACEBOOK_BIRTHDAY_DIR, "venv", "spread sheet access key.json"),
    
    # Data files
    "report_number": os.path.join(FACEBOOK_BIRTHDAY_DIR, "venv", "report number"),
    "temp_report": os.path.join(FACEBOOK_BIRTHDAY_DIR, "Temp_report"),
    "wishes_file": os.path.join(FACEBOOK_BIRTHDAY_DIR, "Wishes"),
    
    # Screenshots
    "screenshot_dir": os.path.join(FACEBOOK_BIRTHDAY_DIR, "Temp_emoji"),
    
    # Browser
    "chrome_profile": os.path.join(USER_HOME, ".config", "chromium"),
    "chromedriver": "/usr/bin/chromedriver"  # System path
}

# ================================
# INITIALIZATION FUNCTIONS
# ================================

def create_required_directories():
    """Create all required directories if they don't exist"""
    directories = [
        os.path.dirname(PATHS["temp_report"]),
        PATHS["screenshot_dir"],
        os.path.dirname(PATHS["firebase_credentials"]),
        os.path.dirname(PATHS["google_sheets_credentials"])
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Ensured directory exists: {directory}")

def verify_required_files():
    """Check if required files exist"""
    required_files = [
        PATHS["firebase_credentials"],
        PATHS["google_sheets_credentials"], 
        PATHS["report_number"]
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"❌ Required file not found: {file_path}")
            return False
    
    print("✅ All required files verified")
    return True

# ================================
# ORIGINAL FUNCTIONS (UNMODIFIED LOGIC)
# ================================

# Firebase initialization
firebase_initialized = False
driver = None  # Global driver instance

def initialize_firebase():
    """Initialize Firebase connection"""
    global firebase_initialized
    try:
        cred_path = PATHS["firebase_credentials"]
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://thaniyanki-xpath-manager-default-rtdb.firebaseio.com/"
        })
        firebase_initialized = True
        return True
    except Exception as e:
        print(f"❌ Firebase initialization failed: {str(e)}")
        return False

def fetch_xpath_from_firebase(xpath_name, platform="Facebook"):
    """Fetch XPath from Firebase with retry logic"""
    while True:
        try:
            print(f"🔍 Fetching {platform.split('/')[0]} {xpath_name} from database...")
            ref = db.reference(f"{platform}/Xpath")
            xpaths = ref.get()
            
            if xpaths and xpath_name in xpaths:
                print(f"✅ {platform.split('/')[0]} {xpath_name} fetched from database")
                return xpaths[xpath_name]
            else:
                print(f"❌ {xpath_name} not found in database. Retrying in 1 second...")
                time.sleep(1)
        except Exception as e:
            print(f"❌ Error accessing database for {xpath_name}: {str(e)}. Retrying in 1 second...")
            time.sleep(1)

def fetch_color_from_firebase(color_name, platform="Facebook"):
    """Fetch Color from Firebase with retry logic"""
    while True:
        try:
            print(f"🔍 Fetching {platform.split('/')[0]} {color_name} from database...")
            ref = db.reference(f"{platform}/Color")
            colors = ref.get()
            
            if colors and color_name in colors:
                print(f"✅ {platform.split('/')[0]} {color_name} fetched from database")
                return colors[color_name]
            else:
                print(f"❌ {color_name} not found in database. Retrying in 1 second...")
                time.sleep(1)
        except Exception as e:
            print(f"❌ Error accessing database for {color_name}: {str(e)}. Retrying in 1 second...")
            time.sleep(1)

def search_and_click_element(xpath, success_message, refresh_threshold=120, restart_on_fail=False, xpath_name=None, main_flow_vars=None):
    """Search and click element with refresh logic"""
    start_time = time.time()
    refresh_count = 0
    
    while True:
        try:
            element = driver.find_element("xpath", xpath)
            element.click()
            print(success_message)
            return True
            
        except NoSuchElementException:
            current_time = time.time()
            elapsed = current_time - start_time
                
            if elapsed >= refresh_threshold:
                if restart_on_fail and xpath_name == "Xpath002":
                    print("🔄 Xpath002 not found - restarting entire process from Attempt #1")
                    close_chrome()
                    if main_flow_vars:
                        main_flow_vars['reset_attempt'] = True  # Signal to reset attempt count
                    return False
                refresh_count += 1
                print(f"🔄 Refreshing page (Attempt {refresh_count})...")
                driver.refresh()
                start_time = time.time()
                time.sleep(3)
            else:
                sys.stdout.write(f'\r🔍 Searching for element... ({int(elapsed)}s)')
                sys.stdout.flush()
                time.sleep(1)
                
        except Exception as e:
            print(f"❌ Error during search: {str(e)}")
            return False

def check_element_availability(xpath, success_message, timeout=120):
    """Check if element is available (without clicking)"""
    start_time = time.time()
    
    while True:
        try:
            WebDriverWait(driver, 1).until(EC.presence_of_element_located(("xpath", xpath)))
            print(success_message)
            return True
        except TimeoutException:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                print(f"Element not available within {timeout} seconds")
                return False
            sys.stdout.write(f'\r🔍 Checking for element... ({int(elapsed)}s)')
            sys.stdout.flush()
            time.sleep(1)
        except Exception as e:
            print(f"❌ Error during element check: {str(e)}")
            return False
            
def check_xpath006_availability(xpath006):
    """Check if Facebook Xpath006 is available"""
    start_time = time.time()
    while True:
        try:
            WebDriverWait(driver, 1).until(EC.presence_of_element_located(("xpath", xpath006)))
            print("Facebook Xpath006 is available")
            return "xpath006_available"
        except TimeoutException:
            elapsed = time.time() - start_time
            if elapsed >= 120:
                print("Facebook Xpath006 is not available within 120 seconds")
                return "xpath006_not_available"
            sys.stdout.write(f'\r🔍 Searching for XPath006... ({int(elapsed)}s)')
            sys.stdout.flush()
            time.sleep(1)
        except Exception as e:
            print(f"\n❌ Error checking XPath006: {str(e)}")
            close_chrome()
            return "error"            

def paste_birthdays_keyword():
    """Paste 'Birthdays' keyword into search box"""
    try:
        search_box = driver.switch_to.active_element
        search_box.send_keys("Birthdays")
        print("✅ Pasted 'Birthdays' keyword")
        return True
    except Exception as e:
        print(f"❌ Error pasting keyword: {str(e)}")
        return False

def launch_chrome(url="https://www.facebook.com/", start_maximized=True):
    """Launch Chrome browser with specified profile"""
    global driver
    try:
        print("🚀 Launching Chrome browser...")
        options = Options()
        options.add_argument(f"--user-data-dir={PATHS['chrome_profile']}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        if start_maximized:
            options.add_argument("--start-maximized")
        
        # Increase timeout to 300 seconds (5 minutes)
        driver = webdriver.Chrome(
            service=Service(PATHS["chromedriver"]),
            options=options
        )
        driver.set_page_load_timeout(300)  # 5 minutes timeout
        
        print("✅ Chrome browser ready")
        
        print(f"🌐 Navigating to {url}...")
        driver.get(url)
        print(f"✅ {url.split('//')[1].split('/')[0]} loaded")
        return True
    except Exception as e:
        print(f"❌ Browser error: {str(e)}")
        return False

def check_internet():
    """Check internet connection"""
    retry_count = 1
    while True:
        try:
            subprocess.run(['ping', '-c', '1', '-W', '1', '8.8.8.8'], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE, 
                          timeout=5,
                          check=True)
            sys.stdout.write('\r' + ' ' * 50 + '\r')
            print("🌐 Internet connection established")
            return True
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            sys.stdout.write(f'\r🔄 Waiting for internet... ({retry_count})')
            sys.stdout.flush()
            retry_count += 1
            time.sleep(1)

def close_chrome():
    """Clean up browser processes"""
    global driver
    browsers = ['chromium', 'chrome']
    
    if driver:
        try:
            driver.quit()
            driver = None
        except:
            pass
    
    for browser in browsers:
        print(f"🔍 Checking for {browser} processes...")
        try:
            result = subprocess.run(['pgrep', '-f', browser], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  timeout=5)
            if result.stdout:
                print(f"🛑 Closing {browser}...")
                subprocess.run(['pkill', '-f', browser], 
                              check=True,
                              timeout=5)
                print(f"✅ {browser.capitalize()} closed")
        except Exception as e:
            print(f"⚠️ Error cleaning {browser}: {str(e)}")

def connect_to_google_sheets():
    """Connect to Google Sheets with unlimited retries"""
    json_path = PATHS["google_sheets_credentials"]
    
    while True:
        try:
            print("🔗 Attempting to connect to Google Sheets...")
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            
            creds = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
            client = gspread.authorize(creds)
            print("✅ Reached google sheets")
            return client
            
        except Exception as e:
            print(f"❌ Google Sheets connection error: {str(e)}")
            print("🔄 Retrying in 1 second...")
            time.sleep(1)

def update_google_sheet(client):
    """Delete all today's rows and insert fresh status row WITHOUT date"""
    while True:
        try:
            print("📊 Updating Google Sheet - clearing today's entries...")
            
            # Access worksheet
            spreadsheet = client.open("Facebook birthday wisher")
            worksheet = spreadsheet.worksheet("Report")
            
            current_date = datetime.now().strftime("%d-%m-%Y")
            current_time_full = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            
            # Get all data and find today's rows
            all_data = worksheet.get_all_values()
            today_rows = [
                i+1 for i, row in enumerate(all_data) 
                if row and row[0].split()[0] == current_date
            ]
            
            # Delete today's rows (bottom-up to maintain indices)
            for row_num in sorted(today_rows, reverse=True):
                worksheet.delete_rows(row_num)
                print(f"🗑️ Deleted row {row_num}")
            
            # Insert fresh new row at the first empty line WITHOUT date in the message
            next_row = len(all_data) - len(today_rows) + 1
            worksheet.insert_row(
                [current_time_full, '', '', '', '', '', 'No more birthday today'],  # Simple message without date
                index=next_row
            )
            
            print(f"✅ Added fresh row at position {next_row}")
            return True
            
        except Exception as e:
            print(f"❌ Sheet update failed: {str(e)}")
            time.sleep(1)

# ================================
# WHATSAPP FUNCTIONS WITH ENHANCED LOADING DETECTION
# ================================

def search_and_click_whatsapp_xpath001(whatsapp_xpath001):
    """Search and click WhatsApp Xpath001 with enhanced loading chats detection"""
    start_time = time.time()
    refresh_count = 0
    
    while True:
        try:
            element = driver.find_element("xpath", whatsapp_xpath001)
            element.click()
            print("✅ WhatsApp Xpath001 is clicked ready to search phone number")
            return True
            
        except NoSuchElementException:
            current_time = time.time()
            elapsed = current_time - start_time
            
            if elapsed >= 120:
                # Check for "Loading your chats" keyword at 121st second
                print("⏳ 120 seconds completed - checking for 'Loading your chats'...")
                
                try:
                    # Search for "Loading your chats" text in the page
                    loading_element = driver.find_element("xpath", "//*[contains(text(), 'Loading your chats')]")
                    print("🔍 'Loading your chats' keyword found - waiting for it to disappear...")
                    
                    # Wait for loading to complete (disappear) with internet checking
                    loading_wait_start = time.time()
                    last_internet_check = 0
                    internet_check_interval = 5  # Check internet every 5 seconds
                    
                    while True:
                        current_loading_time = time.time()
                        loading_elapsed = current_loading_time - loading_wait_start
                        
                        # Check internet every 5 seconds
                        if current_loading_time - last_internet_check >= internet_check_interval:
                            last_internet_check = current_loading_time
                            
                            if check_internet():
                                print("🌐 Internet available - continuing to wait for loading...")
                            else:
                                print("❌ Internet not available while loading - refreshing page")
                                refresh_count += 1
                                print(f"🔄 Refreshing page (Attempt {refresh_count})...")
                                driver.refresh()
                                start_time = time.time()
                                time.sleep(3)
                                break
                        
                        try:
                            # Check if loading text still exists
                            driver.find_element("xpath", "//*[contains(text(), 'Loading your chats')]")
                            
                            sys.stdout.write(f'\r⏳ Waiting for chats to load... ({int(loading_elapsed)}s)')
                            sys.stdout.flush()
                            time.sleep(1)
                            
                        except NoSuchElementException:
                            # Loading completed - continue with current flow
                            print("\n✅ Chats loading completed - continuing flow")
                            # Try clicking Xpath001 again now that loading is done
                            try:
                                element = driver.find_element("xpath", whatsapp_xpath001)
                                element.click()
                                print("✅ WhatsApp Xpath001 is clicked ready to search phone number")
                                return True
                            except NoSuchElementException:
                                # If still not found after loading, refresh
                                print("❌ Xpath001 still not found after loading - refreshing page")
                                refresh_count += 1
                                print(f"🔄 Refreshing page (Attempt {refresh_count})...")
                                driver.refresh()
                                start_time = time.time()
                                time.sleep(3)
                                break
                            
                except NoSuchElementException:
                    # "Loading your chats" not found at 121st second - refresh page
                    print("❌ 'Loading your chats' not found at 121st second - refreshing page")
                    refresh_count += 1
                    print(f"🔄 Refreshing page (Attempt {refresh_count})...")
                    driver.refresh()
                    start_time = time.time()
                    time.sleep(3)
                    
            else:
                sys.stdout.write(f'\r🔍 Searching for WhatsApp XPath001... ({int(elapsed)}s)')
                sys.stdout.flush()
                time.sleep(1)
                
        except Exception as e:
            print(f"❌ Error during WhatsApp XPath001 search: {str(e)}")
            return False

def open_whatsapp_and_fetch_xpath():
    """Open WhatsApp and fetch XPath"""
    close_chrome()

    if not launch_chrome(url="https://web.whatsapp.com/", start_maximized=True):
        print("❌ Failed to open WhatsApp Web")
        return None
    
    print("✅ Entered WhatsApp Web")
    
    whatsapp_xpath001 = fetch_xpath_from_firebase("Xpath001", "WhatsApp")
    return whatsapp_xpath001

def click_whatsapp_search_and_paste_number(whatsapp_xpath001):
    """Click search and paste number with enhanced loading detection"""
    while True:
        if search_and_click_whatsapp_xpath001(whatsapp_xpath001):
            break
        print("🔄 Restarting WhatsApp search click process...")
    
    while True:
        try:
            with open(PATHS["report_number"], "r") as file:
                phone_number = file.readline().strip()
                if not phone_number:
                    raise ValueError("Phone number not found in file")
                
                search_box = driver.switch_to.active_element
                search_box.send_keys(phone_number)
                print(f"📱 Mobile number transferred from text file to WhatsApp phone number search field: {phone_number}")
                return True
                
        except Exception as e:
            print(f"❌ Error processing phone number: {str(e)}")
            print("🔄 Retrying in 1 second...")
            time.sleep(1)

def press_down_arrow_and_enter_message_field():
    """Complete WhatsApp message field entry with enhanced loading awareness"""
    print("⏳ Waiting 10 seconds for stability...")
    time.sleep(10)
    
    try:
        active_element = driver.switch_to.active_element
        active_element.send_keys(Keys.ARROW_DOWN)
        print("⬇️ Down arrow pressed")
    except Exception as e:
        print(f"❌ Error pressing down arrow: {str(e)}")
        return False
    
    whatsapp_xpath002 = fetch_xpath_from_firebase("Xpath002", "WhatsApp")
    print("✅ WhatsApp Xpath002 fetched from database")
    
    start_time = time.time()
    while True:
        try:
            if search_and_click_element(whatsapp_xpath002, "✅ Entered into Type a message field"):
                return True
            
            elapsed = time.time() - start_time
            if elapsed >= 120:
                print("🔄 WhatsApp Xpath002 not found within 120 seconds - checking for loading chats...")
                
                # Check for "Loading your chats" before refreshing
                try:
                    loading_element = driver.find_element("xpath", "//*[contains(text(), 'Loading your chats')]")
                    print("🔍 'Loading your chats' found - waiting for completion with internet check...")
                    
                    loading_wait_start = time.time()
                    last_internet_check = 0
                    internet_check_interval = 5
                    
                    while True:
                        current_loading_time = time.time()
                        loading_elapsed = current_loading_time - loading_wait_start
                        
                        # Check internet every 5 seconds
                        if current_loading_time - last_internet_check >= internet_check_interval:
                            last_internet_check = current_loading_time
                            
                            if check_internet():
                                print("🌐 Internet available - continuing to wait for loading...")
                            else:
                                print("❌ Internet not available while loading - restarting process")
                                close_chrome()
                                return False
                        
                        try:
                            driver.find_element("xpath", "//*[contains(text(), 'Loading your chats')]")
                            sys.stdout.write(f'\r⏳ Waiting for chats to load... ({int(loading_elapsed)}s)')
                            sys.stdout.flush()
                            time.sleep(1)
                        except NoSuchElementException:
                            print("\n✅ Chats loading completed - retrying Xpath002 search")
                            # Reset timer and retry Xpath002 search
                            start_time = time.time()
                            break
                            
                except NoSuchElementException:
                    print("❌ 'Loading your chats' not found - restarting process")
                    close_chrome()
                    return False
                    
        except Exception as e:
            print(f"❌ Error during message field click: {str(e)}")
            time.sleep(1)

def paste_message_and_confirm():
    """Paste message and confirm delivery with date format for WhatsApp"""
    while True:
        try:
            # Get current date in DD-MM-YYYY format for WhatsApp
            current_date = datetime.now().strftime("%d-%m-%Y")
            
            # Format the message with date for WhatsApp
            message = f"Facebook birthday bot({current_date})\nNo more birthday today"
            
            active_element = driver.switch_to.active_element
            
            # Type the message with proper newline handling
            lines = message.split('\n')
            for i, line in enumerate(lines):
                active_element.send_keys(line)
                if i < len(lines) - 1:  # Add newline for all but last line
                    active_element.send_keys(Keys.SHIFT + Keys.ENTER)
            
            print("✅ Message is typed")
            break
        except Exception as e:
            print(f"❌ Error typing message: {str(e)}")
            print("🔄 Restarting from WhatsApp opening...")
            close_chrome()
            return False
    
    time.sleep(1)
    try:
        active_element = driver.switch_to.active_element
        active_element.send_keys(Keys.RETURN)
        print("✅ Enter key pressed")
    except Exception as e:
        print(f"❌ Error pressing Enter: {str(e)}")
        return False
    
    whatsapp_xpath003 = fetch_xpath_from_firebase("Xpath003", "WhatsApp")
    print("✅ WhatsApp Xpath003 fetched from database")
    return whatsapp_xpath003

def check_whatsapp_xpath003_availability(whatsapp_xpath003):
    """Check WhatsApp XPath003 availability with enhanced loading detection"""
    total_seconds = 0
    sys.stdout.write("⏳ WhatsApp Xpath003 is available in 0 sec")
    sys.stdout.flush()
    
    while True:
        time.sleep(1)
        total_seconds += 1
        
        try:
            driver.find_element("xpath", whatsapp_xpath003)
            sys.stdout.write(f'\r⏳ WhatsApp Xpath003 is available in {total_seconds} sec')
            sys.stdout.flush()
            
            if total_seconds >= 120:
                print("\n⏳ Reached 120 seconds - checking for loading chats...")
                
                # Check for "Loading your chats" before proceeding
                try:
                    loading_element = driver.find_element("xpath", "//*[contains(text(), 'Loading your chats')]")
                    print("🔍 'Loading your chats' found - waiting for completion with internet check...")
                    
                    loading_wait_start = time.time()
                    last_internet_check = 0
                    internet_check_interval = 5
                    
                    while True:
                        current_loading_time = time.time()
                        loading_elapsed = current_loading_time - loading_wait_start
                        
                        # Check internet every 5 seconds
                        if current_loading_time - last_internet_check >= internet_check_interval:
                            last_internet_check = current_loading_time
                            
                            if check_internet():
                                print("🌐 Internet available - continuing to wait for loading...")
                            else:
                                print("❌ Internet not available while loading - closing browser")
                                time.sleep(3)
                                close_chrome()
                                return False
                        
                        try:
                            driver.find_element("xpath", "//*[contains(text(), 'Loading your chats')]")
                            sys.stdout.write(f'\r⏳ Waiting for chats to load... ({int(loading_elapsed)}s)')
                            sys.stdout.flush()
                            time.sleep(1)
                        except NoSuchElementException:
                            print("\n✅ Chats loading completed - continuing to Step 13p")
                            close_chrome()
                            return True
                            
                except NoSuchElementException:
                    print("❌ 'Loading your chats' not found - waiting 3 seconds for stability...")
                    time.sleep(3)
                    print("🔒 Closing the browser")
                    close_chrome()
                    return False
                
        except NoSuchElementException:
            print("\n✅ WhatsApp Xpath003 is not available - message delivered")
            time.sleep(3)
            print("🔒 Closing the browser")
            close_chrome()
            return True
        except Exception as e:
            print(f"\n❌ Error checking WhatsApp Xpath003: {str(e)}")
            time.sleep(3)
            print("🔒 Closing the browser")
            close_chrome()
            return False

def whatsapp_retry_flow():
    """The retry flow when message is still pending after 120 seconds with enhanced loading detection"""
    while True:
        close_chrome()
        if not launch_chrome(url="https://web.whatsapp.com/", start_maximized=True):
            print("❌ Failed to open WhatsApp Web")
            time.sleep(1)
            continue
        print("✅ Entered WhatsApp Web")
        
        whatsapp_xpath001 = fetch_xpath_from_firebase("Xpath001", "WhatsApp")
        print("✅ WhatsApp Xpath001 fetched from database")
        
        while True:
            try:
                if search_and_click_whatsapp_xpath001(whatsapp_xpath001):
                    break
                print("🔄 Restarting WhatsApp search click process...")
            except Exception as e:
                print(f"❌ Error during WhatsApp search click: {str(e)}")
                time.sleep(1)
        
        while True:
            try:
                with open(PATHS["report_number"], "r") as file:
                    phone_number = file.readline().strip()
                    if not phone_number:
                        raise ValueError("Phone number not found in file")
                    
                    search_box = driver.switch_to.active_element
                    search_box.send_keys(phone_number)
                    print(f"📱 Mobile number transferred from text file to WhatsApp phone number search field: {phone_number}")
                    break
                    
            except Exception as e:
                print(f"❌ Error processing phone number: {str(e)}")
                print("🔄 Retrying in 1 second...")
                time.sleep(1)
        
        print("⏳ Waiting 10 seconds for stability...")
        time.sleep(10)
        
        try:
            active_element = driver.switch_to.active_element
            active_element.send_keys(Keys.ARROW_DOWN)
            print("⬇️ Down arrow pressed")
        except Exception as e:
            print(f"❌ Error pressing down arrow: {str(e)}")
            continue
        
        whatsapp_xpath003 = fetch_xpath_from_firebase("Xpath003", "WhatsApp")
        print("✅ WhatsApp Xpath003 fetched from database")
        
        total_seconds = 0
        sys.stdout.write("🔍 Checking WhatsApp Xpath003 for disappearance: 0 sec")
        sys.stdout.flush()
        
        while total_seconds < 120:
            time.sleep(1)
            total_seconds += 1
            
            try:
                driver.find_element("xpath", whatsapp_xpath003)
                sys.stdout.write(f'\r🔍 Checking WhatsApp Xpath003 for disappearance: {total_seconds} sec')
                sys.stdout.flush()
            except NoSuchElementException:
                print("\n✅ WhatsApp Xpath003 is not present - close the browser and script")
                close_chrome()
                return False
            except Exception as e:
                print(f"\n❌ Error checking WhatsApp Xpath003: {str(e)}")
                close_chrome()
                return False
        
        print("\n⏳ WhatsApp Xpath003 is still present after 120 seconds - checking for loading chats...")
        
        # Check for "Loading your chats" before restarting with enhanced internet checking
        try:
            loading_element = driver.find_element("xpath", "//*[contains(text(), 'Loading your chats')]")
            print("🔍 'Loading your chats' found - waiting for completion with internet check...")
            
            loading_wait_start = time.time()
            last_internet_check = 0
            internet_check_interval = 5
            
            while True:
                current_loading_time = time.time()
                loading_elapsed = current_loading_time - loading_wait_start
                
                # Check internet every 5 seconds
                if current_loading_time - last_internet_check >= internet_check_interval:
                    last_internet_check = current_loading_time
                    
                    if check_internet():
                        print("🌐 Internet available - continuing to wait for loading...")
                    else:
                        print("❌ Internet not available while loading - restarting flow")
                        break
                
                try:
                    driver.find_element("xpath", "//*[contains(text(), 'Loading your chats')]")
                    sys.stdout.write(f'\r⏳ Waiting for chats to load... ({int(loading_elapsed)}s)')
                    sys.stdout.flush()
                    time.sleep(1)
                except NoSuchElementException:
                    print("\n✅ Chats loading completed - restarting flow")
                    break
                    
        except NoSuchElementException:
            print("❌ 'Loading your chats' not found - restarting flow")
        
        print("🔄 WhatsApp Xpath003 is still present - restarting flow")

# ================================
# FACEBOOK BIRTHDAY FUNCTIONS (UNCHANGED)
# ================================

def modify_and_search_xpath004(original_xpath=None):
    """Modify XPath004 and search for it with refresh logic"""
    refresh_count = 0
    
    while True:
        if original_xpath is None:
            original_xpath = fetch_xpath_from_firebase("Xpath004")
        
        if "[]" in original_xpath:
            modified_xpath = original_xpath.replace("[]", "[1]")
        else:
            modified_xpath = original_xpath
        
        start_time = time.time()
        
        while True:
            try:
                element = driver.find_element("xpath", modified_xpath)
                print("Modified Facebook Xpath004 is found")
                return True
                
            except NoSuchElementException:
                current_time = time.time()
                elapsed = current_time - start_time
                
                if elapsed >= 120:
                    refresh_count += 1
                    print(f"🔄 Refreshing page (Attempt {refresh_count})...")
                    driver.refresh()
                    start_time = time.time()
                    time.sleep(3)
                    break
                else:
                    sys.stdout.write(f'\r🔍 Searching for modified XPath004... ({int(elapsed)}s)')
                    sys.stdout.flush()
                    time.sleep(1)
                    
            except Exception as e:
                print(f"❌ Error during search: {str(e)}")
                return False  

def count_birthday_people():
    """Count total birthday people by incrementally checking modified XPaths"""
    max_attempts = 50
    count = 0
    
    base_xpath = fetch_xpath_from_firebase("Xpath004")
    
    for i in range(1, max_attempts + 1):
        if "[]" in base_xpath:
            current_xpath = base_xpath.replace("[]", f"[{i}]")
        else:
            current_xpath = f"{base_xpath}[{i}]"
        
        try:
            driver.find_element("xpath", current_xpath)
            count = i
            print(f"✅ Birthday person {i} found")
            
        except NoSuchElementException:
            try:
                subprocess.run(['ping', '-c', '1', '-W', '1', '8.8.8.8'], 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE, 
                             timeout=5,
                             check=True)
                print(f"Today's birthday people: {count}")
                return count
            except:
                print("Internet not available while counting - restarting from Step14")
                return -1
                
        except Exception as e:
            print(f"❌ Error during counting: {str(e)}")
            return -1
    
    try:
        subprocess.run(['ping', '-c', '1', '-W', '1', '8.8.8.8'], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      timeout=5,
                      check=True)
        print(f"Reached maximum check limit ({max_attempts}), found {count} birthday people")
        return count
    except:
        print("Internet not available at max count - restarting from Step14")
        return -1

def create_google_sheets_temp_file():
    """Create or recreate the Temp_report file"""
    file_path = PATHS["temp_report"]
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print("Old temp file is deleted", end=" & ")
        
        open(file_path, 'w').close()
        print("New Temp_report is created")
        return True
        
    except Exception as e:
        print(f"❌ Error creating temp file: {str(e)}")
        return False

def fetch_birthday_people_details(count):
    """Fetch details of birthday people with age calculation and internet check"""
    if count <= 0:
        return False
    
    print(f"\n📝 Fetching details for {count} birthday people:")
    
    base_xpath = fetch_xpath_from_firebase("Xpath004")
    
    current_year = datetime.now().year
    people_details = []
    
    for i in range(1, count + 1):
        retry_count = 0
        max_retries = 2
        
        while retry_count < max_retries:
            try:
                if "[]" in base_xpath:
                    current_xpath = base_xpath.replace("[]", f"[{i}]")
                else:
                    current_xpath = f"{base_xpath}[{i}]"
                
                element = driver.find_element("xpath", current_xpath)
                
                name = element.text
                profile_link = element.get_attribute("href")
                aria_label = element.get_attribute("aria-label")
                
                dob = ""
                age = ""
                if aria_label and "," in aria_label:
                    try:
                        date_part = aria_label.split(",")[1].strip() + " " + aria_label.split(",")[2].strip()
                        parsed_date = parse(date_part)
                        dob = parsed_date.strftime("%d-%m-%Y")
                        birth_year = parsed_date.year
                        age = current_year - birth_year
                    except:
                        pass
                
                people_details.append({
                    "name": name,
                    "dob": dob,
                    "age": age,
                    "profile_link": profile_link
                })
                
                print(f"\n{i}. {name}")
                if dob:
                    print(f"  {dob} Age {age}")
                print(f"  {profile_link}")
                
                break
                
            except NoSuchElementException:
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"\n{i}. [Error: Could not fetch details for person {i}]")
                else:
                    print(f"\n🔄 Retrying to fetch details for person {i}...")
                    time.sleep(1)
                    
            except Exception as e:
                print(f"\n❌ Error fetching details for person {i}: {str(e)}")
                print("🔄 Refreshing page and restarting from Step14...")
                driver.refresh()
                time.sleep(3)
                return False
    
    try:
        subprocess.run(['ping', '-c', '1', '-W', '1', '8.8.8.8'], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      timeout=5,
                      check=True)
        print("\n✅ Internet connection verified after fetching all details")
        
        if create_google_sheets_temp_file():
            return people_details
        return False
        
    except:
        print("\n❌ Internet connection lost after fetching details")
        print("🔄 Refreshing page and restarting from Step14 due to internet issue...")
        driver.refresh()
        time.sleep(3)
        return False

def open_profile(profile_link, person_name, max_retries=3):
    """Open a person's profile with retry logic"""
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            print(f"🌐 Opening profile: {person_name} (Attempt {retry_count + 1}/{max_retries})")
            driver.get(profile_link)
            print(f"✅ Entered {person_name} profile...")
            return True
        except ReadTimeoutError:
            retry_count += 1
            print(f"❌ Timeout opening profile - Retrying {retry_count}/{max_retries}")
            close_chrome()
            if not launch_chrome(url="https://www.facebook.com/"):
                print("❌ Failed to relaunch Chrome")
                return False
            time.sleep(5)
        except Exception as e:
            print(f"❌ Error opening profile: {str(e)}")
            return False
    
    print(f"❌ Failed to open profile after {max_retries} attempts")
    return False

def fetch_and_check_xpath005():
    """Fetch and check XPath005"""
    xpath005 = fetch_xpath_from_firebase("Xpath005")
    print("✅ Facebook Xpath005 fetched from database")
    
    start_time = time.time()
    while True:
        try:
            WebDriverWait(driver, 1).until(EC.presence_of_element_located(("xpath", xpath005)))
            print("Facebook Xpath005 is available")
            return "xpath005_available"
        except TimeoutException:
            elapsed = time.time() - start_time
            if elapsed >= 120:
                print("Facebook Xpath005 is not available within 120 seconds")
                return "xpath005_not_available"
            sys.stdout.write(f'\r🔍 Searching for XPath005... ({int(elapsed)}s)')
            sys.stdout.flush()
            time.sleep(1)
        except Exception as e:
            print(f"\n❌ Error checking XPath005: {str(e)}")
            close_chrome()
            return "error"

def handle_popup_if_exists():
    """Handle popup if exists"""
    xpath007 = fetch_xpath_from_firebase("Xpath007")
    print("✅ Facebook Xpath007 fetched from database")
    
    try:
        # First click
        element = WebDriverWait(driver, 5).until(EC.presence_of_element_located(("xpath", xpath007)))
        element.click()
        print("Message tab 1 is closed")
        
        # Continue clicking until Xpath007 is not found
        click_count = 1
        while True:
            try:
                element = driver.find_element("xpath", xpath007)
                element.click()
                click_count += 1
                print(f"Message tab {click_count} is closed")
                time.sleep(0.5)  # Small delay between clicks
            except NoSuchElementException:
                print(f"Xpath007 not found after {click_count} clicks")
                break
            except Exception as e:
                print(f"Error clicking Xpath007: {str(e)}")
                break
        
        return True
    except TimeoutException:
        print("No popup found")
        return True
    except Exception as e:
        print(f"❌ Error checking popup: {str(e)}")
        return False

def click_message_button():
    """Click message button"""
    xpath005 = fetch_xpath_from_firebase("Xpath005")
    print("✅ Facebook Xpath005 fetched from database")
    
    if search_and_click_element(xpath005, "Message tab is open"):
        return True
    return False

def check_emoji_button_color():
    """Check emoji button color with screenshot"""
    try:
        xpath009 = fetch_xpath_from_firebase("Xpath009")
        xpath008 = fetch_xpath_from_firebase("Xpath008")
        print("✅ Facebook Xpath009 and Xpath008 fetched from database")
        
        start_time = time.time()
        check_interval = 1
        
        while True:
            current_time = time.time()
            elapsed = current_time - start_time
            
            if elapsed >= 120:
                print("If both are not available upto 120 seconds then continue with Step 55.")
                
                # Step 55: Fetch XPath007 with infinite retry
                while True:
                    try:
                        xpath007 = fetch_xpath_from_firebase("Xpath007")
                        print("✅ Facebook Xpath007 fetched from database")
                        break
                    except Exception as e:
                        print(f"❌ Error fetching Xpath007: {str(e)}. Retrying in 1 second...")
                        time.sleep(1)
                
                # Step 56: Click XPath007
                try:
                    element = driver.find_element("xpath", xpath007)
                    element.click()
                    print("Message tab is closed")
                    return "continue_to_step20"
                except Exception as e:
                    print(f"❌ Error clicking Xpath007: {str(e)}")
                    return "continue_to_step20"
            
            # Try to find Xpath009 or Xpath008
            try:
                # First try Xpath009
                element = WebDriverWait(driver, 0.5).until(EC.presence_of_element_located(("xpath", xpath009)))
                print(f"Found Facebook Xpath009 - continuing with color check")
                break
            except TimeoutException:
                try:
                    # If Xpath009 not found, try Xpath008
                    element = WebDriverWait(driver, 0.5).until(EC.presence_of_element_located(("xpath", xpath008)))
                    print(f"Found Facebook Xpath008 - user can't access this chat")
                    return "xpath008_found"
                except TimeoutException:
                    pass
            
            sys.stdout.write(f'\r🔍 Searching for XPath009 or XPath008... ({int(elapsed)}s)')
            sys.stdout.flush()
            time.sleep(1)
        
        # If we get here, we found Xpath009
        emoji_button = element
        
        screenshot_dir = PATHS["screenshot_dir"]
        
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)
            print(f"📁 Created directory: {screenshot_dir}")
        
        for filename in os.listdir(screenshot_dir):
            file_path = os.path.join(screenshot_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    print(f"🧹 Deleted old file: {filename}")
            except Exception as e:
                print(f"❌ Error deleting {file_path}: {e}")
        
        emoji_color = fetch_color_from_firebase("Emoji Button")
        print("✅ Emoji button color fetched from database")

        start_time_color_check = time.time()
        last_color_check = 0
        color_check_interval = 5

        while True:
            current_time_color_check = time.time()
            elapsed_color_check = current_time_color_check - start_time_color_check
            
            if elapsed_color_check - last_color_check >= color_check_interval:
                last_color_check = elapsed_color_check
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = os.path.join(screenshot_dir, f"emoji_button_{timestamp}.png")
                    emoji_button.screenshot(screenshot_path)
                    print(f"📸 Saved emoji button screenshot to: {screenshot_path}")
                    
                    img = Image.open(screenshot_path)
                    width, height = img.size
                    print(f"📏 Captured element dimensions: {width}x{height} pixels")
                    
                    center_x = width // 2
                    center_y = height // 2
                    center_color = img.getpixel((center_x, center_y))
                    
                    if len(center_color) == 4:
                        r, g, b, a = center_color
                    else:
                        r, g, b = center_color
                    hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b).lower()
                    
                    print(f"🎨 Center color: {hex_color} (Expected: {emoji_color.lower()})")
                    
                    if hex_color == emoji_color.lower():
                        print("✅ Color is Matched available in Xpath009")
                        return "color_matched"
                    else:
                        print("❌ Color not matched with emoji")
                        return "color_not_matched_step68"
                    
                except Exception as e:
                    print(f"❌ Error checking color: {str(e)}")
                    return "error"
                
            if elapsed_color_check >= 120:
                print("⏳ Color is not Matched with Xpath009 after 120 seconds")
                return "color_not_matched"
            
            if elapsed_color_check - last_color_check < color_check_interval:
                time.sleep(1)
    
    except Exception as e:
        print(f"❌ Error in check_emoji_button_color: {str(e)}")
        return "error"

def delete_screenshot():
    """Delete captured screenshot"""
    screenshot_dir = PATHS["screenshot_dir"]
    for filename in os.listdir(screenshot_dir):
        if filename.startswith("emoji_button_") and filename.endswith(".png"):
            file_path = os.path.join(screenshot_dir, filename)
            try:
                os.remove(file_path)
                print(f"✅ Deleted captured screenshot: {filename}")
            except Exception as e:
                print(f"❌ Error deleting screenshot {filename}: {str(e)}")
    return True

def get_random_wish_from_file():
    """Get a random wish from the Wishes file"""
    wishes_path = PATHS["wishes_file"]
    
    while True:
        try:
            with open(wishes_path, 'r') as f:
                messages = [line.strip() for line in f.readlines() if line.strip()]
            
            if messages:
                wish_message = random.choice(messages)
                print("Wishes message is copied from file")
                print("Wishes message is copied and ready to paste")
                return wish_message
            else:
                print("❌ No wishes messages found in the file. Retrying in 1 second...")
                time.sleep(1)
        except Exception as e:
            print(f"❌ Error reading wishes file: {str(e)}. Retrying in 1 second...")
            time.sleep(1)

def check_xpath010_and_xpath011_availability():
    """Check if Facebook Xpath010 or Xpath011 is available with proper loop"""
    while True:
        # Step 37: Fetch Xpath010 and Xpath011 with infinite retry
        while True:
            try:
                xpath010 = fetch_xpath_from_firebase("Xpath010")
                xpath011 = fetch_xpath_from_firebase("Xpath011")
                print("✅ Facebook Xpath010 and Xpath011 fetched from database")
                break
            except Exception as e:
                print(f"❌ Error fetching Xpaths: {str(e)}. Retrying in 1 second...")
                time.sleep(1)
        
        # Step 38: Search in alternating pattern for 120 seconds
        start_time = time.time()
        while time.time() - start_time < 120:
            elapsed = time.time() - start_time
            
            # Odd seconds check Xpath010
            if int(elapsed) % 2 == 1:
                try:
                    element = WebDriverWait(driver, 0.5).until(EC.presence_of_element_located(("xpath", xpath010)))
                    print("Facebook Xpath010 is available - continue with step 39")
                    return "xpath010_available"
                except TimeoutException:
                    pass
            # Even seconds check Xpath011
            else:
                try:
                    element = WebDriverWait(driver, 0.5).until(EC.presence_of_element_located(("xpath", xpath011)))
                    print("Facebook Xpath011 is available - continue with step 64")
                    
                    # Step 64a: Fetch Xpath007 with infinite retry
                    while True:
                        try:
                            xpath007 = fetch_xpath_from_firebase("Xpath007")
                            print("✅ Facebook Xpath007 fetched from database")
                            break
                        except Exception as e:
                            print(f"❌ Error fetching Xpath007: {str(e)}. Retrying in 1 second...")
                            time.sleep(1)
                    
                    # Step 64b: Click Xpath007 repeatedly until it disappears
                    click_count = 0
                    while True:
                        try:
                            element = driver.find_element("xpath", xpath007)
                            element.click()
                            click_count += 1
                            print(f"Message tab {click_count} is closed")
                            time.sleep(3)
                        except NoSuchElementException:
                            if click_count > 0:
                                print("Xpath007 no longer found - continuing with Step 64c")
                            else:
                                print("Xpath007 not found - continuing with Step 64c")
                            break
                        except Exception as e:
                            print(f"❌ Error clicking Xpath007: {str(e)}")
                            break
                    
                    # Step 64d: Fetch Xpath005 with infinite retry
                    while True:
                        try:
                            xpath005 = fetch_xpath_from_firebase("Xpath005")
                            print("✅ Facebook Xpath005 fetched from database")
                            break
                        except Exception as e:
                            print(f"❌ Error fetching Xpath005: {str(e)}. Retrying in 1 second...")
                            time.sleep(1)
                    
                    # Step 64e: Search for Xpath005 for 120 seconds
                    xpath005_found = False
                    start_time_xpath005 = time.time()
                    while time.time() - start_time_xpath005 < 120:
                        try:
                            element = driver.find_element("xpath", xpath005)
                            element.click()
                            print("Message tab is open")
                            xpath005_found = True
                            break
                        except NoSuchElementException:
                            sys.stdout.write(f'\r🔍 Searching for XPath005... ({int(time.time() - start_time_xpath005)}s)')
                            sys.stdout.flush()
                            time.sleep(1)
                        except Exception as e:
                            print(f"\n❌ Error clicking Xpath005: {str(e)}")
                            break
                    
                    if xpath005_found:
                        # Continue with Step 65a
                        while True:
                            try:
                                xpath009 = fetch_xpath_from_firebase("Xpath009")
                                print("✅ Facebook Xpath009 fetched from database")
                                break
                            except Exception as e:
                                print(f"❌ Error fetching Xpath009: {str(e)}. Retrying in 1 second...")
                                time.sleep(1)
                        
                        # Step 65b: Search for Xpath009 for 120 seconds
                        xpath009_found = False
                        start_time_xpath009 = time.time()
                        while time.time() - start_time_xpath009 < 120:
                            try:
                                element = driver.find_element("xpath", xpath009)
                                xpath009_found = True
                                break
                            except NoSuchElementException:
                                sys.stdout.write(f'\r🔍 Searching for XPath009... ({int(time.time() - start_time_xpath009)}s)')
                                sys.stdout.flush()
                                time.sleep(1)
                            except Exception as e:
                                print(f"\n❌ Error searching Xpath009: {str(e)}")
                                break
                        
                        if xpath009_found:
                            # Step 65c: Delete all files in Temp_emoji folder
                            screenshot_dir = PATHS["screenshot_dir"]
                            for filename in os.listdir(screenshot_dir):
                                file_path = os.path.join(screenshot_dir, filename)
                                try:
                                    if os.path.isfile(file_path):
                                        os.unlink(file_path)
                                        print(f"🧹 Deleted old file: {filename}")
                                except Exception as e:
                                    print(f"❌ Error deleting {file_path}: {e}")
                            
                            # Step 65d: Capture screenshot
                            try:
                                element = driver.find_element("xpath", xpath009)
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                screenshot_path = os.path.join(screenshot_dir, f"emoji_button_{timestamp}.png")
                                element.screenshot(screenshot_path)
                                print(f"📸 Saved emoji button screenshot to: {screenshot_path}")
                                
                                # Step 65e: Fetch emoji button color
                                while True:
                                    try:
                                        emoji_color = fetch_color_from_firebase("Emoji Button")
                                        print("✅ Emoji button color fetched from database")
                                        break
                                    except Exception as e:
                                        print(f"❌ Error fetching emoji color: {str(e)}. Retrying in 1 second...")
                                        time.sleep(1)
                                
                                # Step 65f: Check color match
                                img = Image.open(screenshot_path)
                                width, height = img.size
                                center_x = width // 2
                                center_y = height // 2
                                center_color = img.getpixel((center_x, center_y))
                                
                                if len(center_color) == 4:
                                    r, g, b, a = center_color
                                else:
                                    r, g, b = center_color
                                hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b).lower()
                                
                                print(f"🎨 Center color: {hex_color} (Expected: {emoji_color.lower()})")
                                
                                if hex_color == emoji_color.lower():
                                    # Step 65g: Delete screenshot
                                    try:
                                        os.remove(screenshot_path)
                                        print("✅ Deleted captured screenshot")
                                    except Exception as e:
                                        print(f"❌ Error deleting screenshot: {str(e)}")
                                    
                                    # Step 65h: Fetch Xpath006
                                    while True:
                                        try:
                                            xpath006 = fetch_xpath_from_firebase("Xpath006")
                                            print("✅ Facebook Xpath006 fetched from database")
                                            break
                                        except Exception as e:
                                            print(f"❌ Error fetching Xpath006: {str(e)}. Retrying in 1 second...")
                                            time.sleep(1)
                                    
                                    # Step 65i: Search for Xpath006 for 120 seconds
                                    xpath006_found = False
                                    start_time_xpath006 = time.time()
                                    while time.time() - start_time_xpath006 < 120:
                                        try:
                                            element = driver.find_element("xpath", xpath006)
                                            xpath006_found = True
                                            break
                                        except NoSuchElementException:
                                            sys.stdout.write(f'\r🔍 Searching for XPath006... ({int(time.time() - start_time_xpath006)}s)')
                                            sys.stdout.flush()
                                            time.sleep(1)
                                        except Exception as e:
                                            print(f"\n❌ Error searching Xpath006: {str(e)}")
                                            break
                                    
                                    if xpath006_found:
                                        # Step 65j: Click Xpath006
                                        try:
                                            element.click()
                                            print("Entered message input field")
                                            
                                            # Step 65k: Paste random wish and press Enter
                                            wish_message = get_random_wish_from_file()
                                            active_element = driver.switch_to.active_element
                                            active_element.send_keys(wish_message)
                                            print("Wishes message pasted.")
                                            time.sleep(5)
                                            active_element.send_keys(Keys.ENTER)
                                            print("Enter key pressed.")
                                            time.sleep(5)
                                            
                                            # Step 65l: Fetch Xpath010
                                            while True:
                                                try:
                                                    xpath010 = fetch_xpath_from_firebase("Xpath010")
                                                    print("✅ Facebook Xpath010 fetched from database")
                                                    break
                                                except Exception as e:
                                                    print(f"❌ Error fetching Xpath010: {str(e)}. Retrying in 1 second...")
                                                    time.sleep(1)
                                            
                                            # Step 65m: Search for Xpath010 for 120 seconds
                                            xpath010_found = False
                                            start_time_xpath010 = time.time()
                                            while time.time() - start_time_xpath010 < 120:
                                                try:
                                                    element = driver.find_element("xpath", xpath010)
                                                    xpath010_found = True
                                                    break
                                                except NoSuchElementException:
                                                    sys.stdout.write(f'\r🔍 Searching for XPath010... ({int(time.time() - start_time_xpath010)}s)')
                                                    sys.stdout.flush()
                                                    time.sleep(1)
                                                except Exception as e:
                                                    print(f"\n❌ Error searching Xpath010: {str(e)}")
                                                    break
                                            
                                            if xpath010_found:
                                                return "xpath010_available"  # Continue with Step 39
                                            else:
                                                print("Xpath010 not found within 120 seconds - continue with step 64")
                                                break
                                            
                                        except Exception as e:
                                            print(f"❌ Error clicking Xpath006: {str(e)}")
                                            break
                                    else:
                                        print("Xpath006 not found within 120 seconds - continue with Step 64")
                                        break
                                else:
                                    print("Color not matched - continue with Step 64")
                                    break
                            except Exception as e:
                                print(f"❌ Error capturing screenshot: {str(e)}")
                                break
                        else:
                            # Step 65n: Fetch Xpath008
                            while True:
                                try:
                                    xpath008 = fetch_xpath_from_firebase("Xpath008")
                                    print("✅ Facebook Xpath008 fetched from database")
                                    break
                                except Exception as e:
                                    print(f"❌ Error fetching Xpath008: {str(e)}. Retrying in 1 second...")
                                    time.sleep(1)
                            
                            # Step 65o: Search for Xpath008 for 120 seconds
                            xpath008_found = False
                            start_time_xpath008 = time.time()
                            while time.time() - start_time_xpath008 < 120:
                                try:
                                    element = driver.find_element("xpath", xpath008)
                                    xpath008_found = True
                                    break
                                except NoSuchElementException:
                                    sys.stdout.write(f'\r🔍 Searching for XPath008... ({int(time.time() - start_time_xpath008)}s)')
                                    sys.stdout.flush()
                                    time.sleep(1)
                                except Exception as e:
                                    print(f"\n❌ Error searching Xpath008: {str(e)}")
                                    break
                            
                            if xpath008_found:
                                return "xpath008_found"  # Continue with Step 57
                            else:
                                print("Xpath008 not found within 120 seconds - continue with step 64")
                                break
                    else:
                        # Xpath005 not found within 120 seconds - refresh and retry
                        print("\nXpath005 not found within 120 seconds - refreshing page")
                        driver.refresh()
                        time.sleep(3)
                        
                        # Step 64e1: Search again for Xpath005 for 120 seconds
                        xpath005_found = False
                        start_time_xpath005 = time.time()
                        while time.time() - start_time_xpath005 < 120:
                            try:
                                element = driver.find_element("xpath", xpath005)
                                element.click()
                                print("Message tab is open")
                                xpath005_found = True
                                break
                            except NoSuchElementException:
                                sys.stdout.write(f'\r🔍 Searching for XPath005... ({int(time.time() - start_time_xpath005)}s)')
                                sys.stdout.flush()
                                time.sleep(1)
                            except Exception as e:
                                print(f"\n❌ Error clicking Xpath005: {str(e)}")
                                break
                        
                        if xpath005_found:
                            continue  # Continue with Step 65a
                        else:
                            # Step 64e2: Check internet
                            if not check_internet():
                                print("Internet not available - waiting for connection")
                                while not check_internet():
                                    time.sleep(1)
                                print("Internet connected - refreshing page")
                                driver.refresh()
                                time.sleep(3)
                                continue  # Continue with Step 64e
                            else:
                                print("Internet available but Xpath005 not found - continue with Step 51")
                                return "continue_to_step51"
                
                except TimeoutException:
                    pass
            
            sys.stdout.write(f'\r🔍 Searching for XPath010 or XPath011... ({int(elapsed)}s)')
            sys.stdout.flush()
            time.sleep(1)
        
        # Step 66: Click Xpath007 repeatedly
        click_xpath007_repeatedly()
        
        # After Step 67, we should loop back to Step 37, not continue to next person
        print("🔄 Restarting XPath010/XPath011 search loop...")
        continue

def click_xpath007_repeatedly():
    """Click Xpath007 repeatedly until it's not found (Steps 66 and 67)"""
    # Step 66: Fetch Xpath007 with infinite retry
    while True:
        try:
            xpath007 = fetch_xpath_from_firebase("Xpath007")
            print("✅ Facebook Xpath007 fetched from database")
            break
        except Exception as e:
            print(f"❌ Error fetching Xpath007: {str(e)}. Retrying in 1 second...")
            time.sleep(1)
    
    # Step 67a: Click repeatedly until Xpath007 disappears
    click_count = 0
    while True:
        try:
            element = driver.find_element("xpath", xpath007)
            element.click()
            click_count += 1
            print(f"Message tab {click_count} is closed")
            time.sleep(3)
        except NoSuchElementException:
            if click_count == 0:
                print("Xpath007 not found - no clicks made")
            else:
                print(f"Xpath007 no longer found after {click_count} clicks")
            break
        except Exception as e:
            print(f"❌ Error clicking Xpath007: {str(e)}")
            break
    
    # Step 67b: Refresh the page
    print("Refreshing the page at once")
    driver.refresh()
    time.sleep(3)
    
    # Step 67c: Fetch Xpath005 with infinite retry
    while True:
        try:
            xpath005 = fetch_xpath_from_firebase("Xpath005")
            print("✅ Facebook Xpath005 fetched from database")
            break
        except Exception as e:
            print(f"❌ Error fetching Xpath005: {str(e)}. Retrying in 1 second...")
            time.sleep(1)
    
    # Step 67d: Search for Xpath005 for up to 120 seconds
    start_time = time.time()
    while time.time() - start_time < 120:
        try:
            element = driver.find_element("xpath", xpath005)
            element.click()
            print("Facebook Xpath005 found and clicked - continuing with Step 37")
            return True  # Return to restart the XPath010/XPath011 search loop
        except NoSuchElementException:
            sys.stdout.write(f'\r🔍 Searching for XPath005... ({int(time.time() - start_time)}s)')
            sys.stdout.flush()
            time.sleep(1)
        except Exception as e:
            print(f"\n❌ Error clicking Xpath005: {str(e)}")
            break
    
    print("\nFacebook Xpath005 not found within 120 seconds - continuing with Step 45")
    return False  # Signal to move to Step 45

def click_xpath006(xpath006):
    """Click Facebook Xpath006 - Modified as per Step 35 requirements"""
    # Step 35a: Fetch Xpath007 with infinite retry
    while True:
        try:
            xpath007 = fetch_xpath_from_firebase("Xpath007")
            print("✅ Facebook Xpath007 fetched from database")
            break
        except Exception as e:
            print(f"❌ Error fetching Xpath007: {str(e)}. Retrying in 1 second...")
            time.sleep(1)
    
    # Step 35b: Search immediately for Xpath007
    try:
        element = driver.find_element("xpath", xpath007)
        print("Xpath007 found - proceeding with Step 35c")
        
        # Step 35c: Click repeatedly until Xpath007 disappears
        click_count = 0
        while True:
            try:
                element = driver.find_element("xpath", xpath007)
                element.click()
                click_count += 1
                print(f"Message tab {click_count} is closed")
                time.sleep(0.5)  # Small delay between clicks
            except NoSuchElementException:
                print(f"Xpath007 not found after {click_count} clicks")
                break
            except Exception as e:
                print(f"Error clicking Xpath007: {str(e)}")
                break
        
        # Step 35d: Click Xpath005
        xpath005 = "//span[text()='Message']"
        try:
            element = driver.find_element("xpath", xpath005)
            element.click()
            print("Clicked Xpath005 - Message tab")
        except Exception as e:
            print(f"Error clicking Xpath005: {str(e)}")
    
    except NoSuchElementException:
        print("Xpath007 not found - proceeding with Step 35e")
    
    # Step 35e: Click Xpath006
    try:
        element = driver.find_element("xpath", xpath006)
        element.click()
        print("Ready to paste")
        return True
    except Exception as e:
        print(f"❌ Error clicking Xpath006: {str(e)}")
        return False

def paste_message_and_enter_from_file():
    """Transfer random wish from file and press Enter"""
    try:
        wish_message = get_random_wish_from_file()
        active_element = driver.switch_to.active_element
        active_element.send_keys(wish_message)
        print("Wishes message pasted.")
        time.sleep(5)
        active_element.send_keys(Keys.ENTER)
        print("Enter key pressed.")
        time.sleep(1)
        return wish_message  # Return the actual message sent
    except Exception as e:
        print(f"❌ Error during paste or enter: {str(e)}")
        return None

def print_message_sent():
    """Print 'Message sent'"""
    print("Message sent")
    return True

def save_report_to_temp_file(person_index, person_details, wish_message, remark):
    """Save data to temporary file with actual wish message"""
    file_path = PATHS["temp_report"]
    current_datetime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    with open(file_path, 'a') as f:
        f.write(f"{person_index}.{current_datetime}\n")
        f.write(f"  {person_details['name']}\n")
        f.write(f"  {person_details['profile_link']}\n")
        
        if person_details['dob']:
            f.write(f"  {person_details['dob']}\n")
            f.write(f"  {person_details['age']}\n")
        else:
            f.write(f"  Not available\n")
            f.write(f"  Not available\n")
        
        if wish_message:
            f.write(f"  {wish_message}\n")  # Store actual message instead of "Wish sent"
        else:
            f.write(f"  Not available\n")
        
        f.write(f"  {remark}\n\n")
    return True

def print_person_data_stored(person_index, person_name):
    """Print data stored message"""
    print(f"{person_index}.{person_name} data stored in temporary file")
    return True

def click_xpath007():
    """Click Facebook Xpath007"""
    xpath007 = fetch_xpath_from_firebase("Xpath007")
    if search_and_click_element(xpath007, "Message tab is closed"):
        return True
    return False

def check_internet_and_refresh_or_continue(step_to_continue_if_internet_available):
    """Check internet and decide next step"""
    if check_internet():
        print("Internet is available")
        return step_to_continue_if_internet_available
    else:
        print("Internet is not available")
        return "step46"

def refresh_page_and_continue_to_step(step_number):
    """Refresh page and continue to a specific step"""
    print("Refreshing the web page at once")
    driver.refresh()
    time.sleep(3)
    return f"step{step_number}"

def click_xpath005_for_confirmation_recheck():
    """Click Facebook Xpath005 for confirmation recheck"""
    xpath005 = fetch_xpath_from_firebase("Xpath005")
    if search_and_click_element(xpath005, "Message tab is open for sent confirmation recheck"):
        return True
    return False

def step68_to_step70_flow():
    """Flow for Steps 68-70 when color doesn't match"""
    while True:
        try:
            xpath007 = fetch_xpath_from_firebase("Xpath007")
            print("✅ Facebook Xpath007 fetched from database")
            break
        except Exception as e:
            print(f"❌ Error fetching Xpath007: {str(e)}. Retrying in 1 second...")
            time.sleep(1)
    
    click_count = 0
    while True:
        try:
            element = driver.find_element("xpath", xpath007)
            element.click()
            click_count += 1
            if click_count == 1:
                print("Message tab 1 is closed")
                time.sleep(3)
            else:
                print(f"Message tab {click_count} is closed")
                time.sleep(3)
        except NoSuchElementException:
            print(f"Xpath007 not found after {click_count} attempts")
            break
        except Exception as e:
            print(f"❌ Error clicking Xpath007: {str(e)}")
            break
    
    return "continue_to_step20"

def transfer_data_to_google_sheets():
    """Transfer data from temp file to Google Sheets with unlimited retries"""
    while True:
        try:
            # Connect to Google Sheets
            client = connect_to_google_sheets()
            spreadsheet = client.open("Facebook birthday wisher")
            worksheet = spreadsheet.worksheet("Report")
            
            # Step 71: Delete all today's rows
            current_date = datetime.now().strftime("%d-%m-%Y")
            print("🔍 Searching for today's rows to delete...")
            
            # Get all data and find today's rows
            all_data = worksheet.get_all_values()
            today_rows = [
                i+1 for i, row in enumerate(all_data) 
                if row and row[0].startswith(current_date)
            ]
            
            # Delete today's rows (bottom-up)
            for row_num in sorted(today_rows, reverse=True):
                worksheet.delete_rows(row_num)
                print(f"🗑️ Deleted row {row_num}")
            
            # Step 72: Parse and upload data from temp file
            temp_file_path = PATHS["temp_report"]
            
            if not os.path.exists(temp_file_path):
                print("❌ Temp file not found")
                return False
            
            # Read and parse the temp file
            with open(temp_file_path, 'r') as f:
                content = f.read().strip()
            
            # Split into individual records
            records = []
            current_record = {}
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # New record starts with number (e.g., "1.28-07-2025 08:06:44")
                if line[0].isdigit() and '.' in line:
                    if current_record:  # Save previous record if exists
                        records.append(current_record)
                    parts = line.split('.', 1)
                    current_record = {
                        'datetime': parts[1].strip(),
                        'index': parts[0].strip()
                    }
                    field_order = ['name', 'profile_link', 'dob', 'age', 'message', 'remark']
                    current_field = 0
                else:
                    # Assign values based on expected order
                    if current_field < len(field_order):
                        field_name = field_order[current_field]
                        current_record[field_name] = line.strip()
                        current_field += 1
            
            # Add the last record if exists
            if current_record:
                records.append(current_record)
            
            # Transfer data to Google Sheets
            for record in records:
                row_data = [
                    record.get('datetime', ''),
                    record.get('name', ''),
                    record.get('profile_link', ''),
                    record.get('dob', ''),
                    record.get('age', ''),
                    record.get('message', ''),
                    record.get('remark', '')
                ]
                worksheet.append_row(row_data)
                print(f"📝 Added data for {record.get('name', 'Unknown')}")
            
            print(f"✅ Successfully transferred {len(records)} records to sheets")
            return True
            
        except Exception as e:
            print(f"❌ Error transferring data: {str(e)}")
            traceback.print_exc()
            time.sleep(1)

def process_whatsapp_report_flow():
    """Handle Steps 73-86 for WhatsApp reporting flow - sends complete report as one message"""
    # Step 73: Close and reopen browser to WhatsApp
    close_chrome()
    if not launch_chrome(url="https://web.whatsapp.com/", start_maximized=True):
        print("❌ Failed to open WhatsApp Web")
        return False
    print("✅ Entered WhatsApp Web")
    
    # Step 74: Fetch WhatsApp Xpath001 with unlimited retry
    while True:
        try:
            whatsapp_xpath001 = fetch_xpath_from_firebase("Xpath001", "WhatsApp")
            print("✅ WhatsApp Xpath001 fetched from database")
            break
        except Exception as e:
            print(f"❌ Error fetching WhatsApp Xpath001: {str(e)}. Retrying in 1 second...")
            time.sleep(1)
    
    # Step 75: Search and click WhatsApp Xpath001 with NEW loading detection logic
    if not search_and_click_whatsapp_xpath001(whatsapp_xpath001):
        print("❌ Failed to click WhatsApp Xpath001")
        return False
    
    # Step 76: Get and paste phone number with unlimited retry
    while True:
        try:
            with open(PATHS["report_number"], "r") as file:
                phone_number = file.readline().strip()
                if not phone_number:
                    raise ValueError("Phone number not found in file")
                
                search_box = driver.switch_to.active_element
                search_box.send_keys(phone_number)
                print(f"📱 Mobile number transferred from text file to WhatsApp phone number search field: {phone_number}")
                break
        except Exception as e:
            print(f"❌ Error processing phone number: {str(e)}. Retrying in 1 second...")
            time.sleep(1)
    
    # Step 77: Wait and press down arrow
    print("⏳ Waiting 10 seconds for stability...")
    time.sleep(10)
    try:
        active_element = driver.switch_to.active_element
        active_element.send_keys(Keys.ARROW_DOWN)
        print("⬇️ Down arrow pressed")
    except Exception as e:
        print(f"❌ Error pressing down arrow: {str(e)}")
        return False
    
    # Step 78: Fetch WhatsApp Xpath002 with unlimited retry
    while True:
        try:
            whatsapp_xpath002 = fetch_xpath_from_firebase("Xpath002", "WhatsApp")
            print("✅ WhatsApp Xpath002 fetched from database")
            break
        except Exception as e:
            print(f"❌ Error fetching WhatsApp Xpath002: {str(e)}. Retrying in 1 second...")
            time.sleep(1)
    
    # Step 79: Search WhatsApp Xpath002 for 120 seconds
    start_time = time.time()
    found = False
    
    while time.time() - start_time < 120:
        try:
            element = driver.find_element("xpath", whatsapp_xpath002)
            element.click()
            found = True
            break
        except NoSuchElementException:
            sys.stdout.write(f'\r🔍 Searching for WhatsApp XPath002... ({int(time.time() - start_time)}s)')
            sys.stdout.flush()
            time.sleep(1)
        except Exception as e:
            print(f"\n❌ Error clicking WhatsApp XPath002: {str(e)}")
            break
    
    if not found:
        print("\n❌ WhatsApp Xpath002 not found within 120 seconds - restarting flow")
        return False
    
    print("✅ Entered message input field")  # Step 80

    # Step 81: Process and paste report data as SINGLE MESSAGE with summary
    temp_file_path = PATHS["temp_report"]
    
    if os.path.exists(temp_file_path):
        try:
            # Read the file content
            with open(temp_file_path, 'r') as f:
                content = f.read()
            
            # Initialize counters
            total_birthdays = 0
            messages_sent = 0
            cant_access = 0
            button_unavailable = 0
            
            # Split into individual records
            records = []
            current_record = []
            
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # New record starts with number (e.g., "1.30-07-2025")
                if line[0].isdigit() and '.' in line:
                    if current_record:  # Save previous record
                        records.append(current_record)
                        total_birthdays += 1
                        
                        # Update counters based on last line of record
                        if len(current_record) >= 5:
                            status_line = current_record[-1].lower()
                            if "user can't access" in status_line:
                                cant_access += 1
                            elif "message button not available" in status_line:
                                button_unavailable += 1
                            elif "message sent" in status_line:
                                messages_sent += 1
                    
                    current_record = [line]
                else:
                    current_record.append(line)
            
            # Add the last record and update counters
            if current_record:
                records.append(current_record)
                total_birthdays += 1
                if len(current_record) >= 5:
                    status_line = current_record[-1].lower()
                    if "user can't access" in status_line:
                        cant_access += 1
                    elif "message button not available" in status_line:
                        button_unavailable += 1
                    elif "message sent" in status_line:
                        messages_sent += 1
            
            # Build the final message
            final_message = ""
            for record in records:
                # Each record has: [number, name, profile_link, dob, age, message, remark]
                # We want to skip profile_link (index 2) and message (index 5)
                if len(record) >= 7:  # Complete record
                    final_message += f"{record[0]}\n"  # Number and datetime
                    final_message += f"{record[1]}\n"  # Name
                    final_message += f"{record[3]}\n"  # DOB
                    final_message += f"{record[4]}\n"  # Age
                    final_message += f"{record[6]}\n\n"  # Remark
                elif len(record) >= 2:  # At least number and name
                    final_message += f"{record[0]}\n{record[1]}\n"
                    if len(record) > 3:  # Has DOB
                        final_message += f"{record[3]}\n"
                    if len(record) > 4:  # Has Age
                        final_message += f"{record[4]}\n"
                    if len(record) > 6:  # Has Remark
                        final_message += f"{record[6]}\n\n"
                    else:
                        final_message += "\n"
            
            # Add summary section
            final_message += "---------------------------------------------\n"
            final_message += f"Today's birthday people: {total_birthdays}\n"
            final_message += f"Message sent: {messages_sent}\n"
            final_message += f"Can't access chat: {cant_access}\n"
            final_message += f"Message button not available: {button_unavailable}\n"
            final_message += "---------------------------------------------"
            
            # Paste as single message
            active_element = driver.switch_to.active_element
            for line in final_message.split('\n'):
                active_element.send_keys(line)
                active_element.send_keys(Keys.SHIFT + Keys.ENTER)  # Newline without sending
            print(f"✅ Processed report with summary pasted ({total_birthdays} records)")
            
        except Exception as e:
            print(f"❌ Error processing report: {str(e)}")
            if not os.path.exists(temp_file_path):
                print("❌ Report file not found")
                active_element.send_keys("Report is not available in related directory")
            else:
                return False
    else:
        print("❌ Report file not found")
        active_element.send_keys("Report is not available in related directory")
    
    # Step 82: Wait and send the complete message
    # Step 82a: Wait 3 seconds for stability and press Enter
    print("⏳ Step 82a: Waiting 3 seconds for stability...")
    time.sleep(3)
    active_element.send_keys(Keys.ENTER)
    print("✅ Enter pressed - full report sent as single message")
    
    # Step 82b: Check internet connection
    print("⏳ Step 82b: Checking internet connection...")
    while True:
        if check_internet():
            print("🌐 Internet is present - waiting 5 seconds")
            time.sleep(5)
            break
        else:
            print("🔄 Internet not present - checking again in 1 second")
            time.sleep(1)
    
    # Step 83: Fetch WhatsApp Xpath003 with unlimited retry
    print("⏳ Step 83: Fetching WhatsApp Xpath003...")
    while True:
        try:
            whatsapp_xpath003 = fetch_xpath_from_firebase("Xpath003", "WhatsApp")
            print("✅ WhatsApp Xpath003 fetched from database")
            break
        except Exception as e:
            print(f"❌ Error fetching WhatsApp Xpath003: {str(e)}. Retrying in 1 second...")
            time.sleep(1)
    
    # Step 84: Monitor message status
    print("⏳ Step 84: Monitoring message status...")
    start_time = time.time()
    message_sent = False
    
    while True:
        # Step 84a: Check if Xpath003 is present
        try:
            driver.find_element("xpath", whatsapp_xpath003)
            elapsed = time.time() - start_time
            
            if elapsed >= 120:
                # Step 84b: Check internet after 120 seconds
                print("\n⏳ Step 84b: Checking internet connection after 120 seconds...")
                if check_internet():
                    print("🌐 Internet is present but still pending message is alive")
                else:
                    print("❌ Internet is not present so still pending message is alive")
                
                # Step 84c: Refresh the page
                print("🔄 Step 84c: Refreshing the page at once")
                driver.refresh()
                time.sleep(3)
                
                # Step 84d: Fetch WhatsApp Xpath001 with unlimited retry
                print("⏳ Step 84d: Fetching WhatsApp Xpath001...")
                while True:
                    try:
                        whatsapp_xpath001 = fetch_xpath_from_firebase("Xpath001", "WhatsApp")
                        print("✅ WhatsApp Xpath001 fetched from database")
                        break
                    except Exception as e:
                        print(f"❌ Error fetching WhatsApp Xpath001: {str(e)}. Retrying in 1 second...")
                        time.sleep(1)
                
                # Step 84e: Search and click WhatsApp Xpath001 with refresh logic
                print("⏳ Step 84e: Searching for WhatsApp Xpath001...")
                search_start_time = time.time()
                refresh_count = 0
                clicked = False
                
                while not clicked:
                    try:
                        element = driver.find_element("xpath", whatsapp_xpath001)
                        element.click()
                        print("✅ WhatsApp Xpath001 is clicked ready to search phone number")
                        clicked = True
                    except NoSuchElementException:
                        elapsed_search = time.time() - search_start_time
                        if elapsed_search >= 120:
                            refresh_count += 1
                            print(f"🔄 Refreshing page (Attempt {refresh_count})...")
                            driver.refresh()
                            search_start_time = time.time()
                            time.sleep(3)
                        else:
                            sys.stdout.write(f'\r🔍 Searching for WhatsApp XPath001... ({int(elapsed_search)}s)')
                            sys.stdout.flush()
                            time.sleep(1)
                    except Exception as e:
                        print(f"❌ Error during WhatsApp XPath001 search: {str(e)}")
                        break
                
                if not clicked:
                    print("❌ Failed to click WhatsApp Xpath001 - restarting flow")
                    return False
                
                # Step 84f: Get and paste phone number with unlimited retry
                print("⏳ Step 84f: Getting phone number from file...")
                while True:
                    try:
                        with open(PATHS["report_number"], "r") as file:
                            phone_number = file.readline().strip()
                            if not phone_number:
                                raise ValueError("Phone number not found in file")
                            
                            search_box = driver.switch_to.active_element
                            search_box.send_keys(phone_number)
                            print(f"📱 Mobile number transferred from text file to WhatsApp phone number search field: {phone_number}")
                            break
                    except Exception as e:
                        print(f"❌ Error processing phone number: {str(e)}. Retrying in 1 second...")
                        time.sleep(1)
                
                # Step 84g: Wait 10 seconds and press down arrow
                print("⏳ Step 84g: Waiting 10 seconds for stability...")
                time.sleep(10)
                try:
                    active_element = driver.switch_to.active_element
                    active_element.send_keys(Keys.ARROW_DOWN)
                    print("⬇️ Down arrow pressed")
                except Exception as e:
                    print(f"❌ Error pressing down arrow: {str(e)}")
                    return False
                
                # Step 84h: Continue with Step 82b
                print("🔄 Step 84h: Continuing with Step 82b")
                break
                
            else:
                sys.stdout.write(f'\r⏳ Monitoring message status... ({int(elapsed)}s)')
                sys.stdout.flush()
                time.sleep(1)
                
        except NoSuchElementException:
            print("\n✅ WhatsApp status report is sent")
            time.sleep(5)  # Wait 5 seconds for stability
            close_chrome()
            return True
            
        except Exception as e:
            print(f"\n❌ Error checking message status: {str(e)}")
            break
    
    print("\n❌ WhatsApp message still pending after retries")
    close_chrome()
    return False

def close_browser_and_final_message():
    """Close browser and print final message"""
    close_chrome()
    print("All data stored in temporary file ready to upload sheets")
    
    # After closing browser, transfer data to Google Sheets
    transfer_data_to_google_sheets()
    
    # Start WhatsApp report flow
    while True:
        if process_whatsapp_report_flow():
            break
        print("🔄 Restarting WhatsApp report flow...")
    
    return True

def create_or_refresh_wishes_file(client):
    """Create or refresh the Wishes file and import from Google Sheets"""
    wishes_path = PATHS["wishes_file"]
    
    while True:
        try:
            if os.path.exists(wishes_path):
                os.remove(wishes_path)
                print("Old wishes file is deleted", end=" & ")
                open(wishes_path, 'w').close()
                print("new one is created")
            else:
                open(wishes_path, 'w').close()
                print("New wishes file is created")
            
            print("📊 Importing wishes from Google Sheets...")
            spreadsheet = client.open("Facebook birthday wisher")
            worksheet = spreadsheet.worksheet("Wishes")
            
            messages = worksheet.col_values(1)[1:]
            
            if messages:
                with open(wishes_path, 'w') as f:
                    for message in messages:
                        f.write(f"{message.strip()}\n")
                print("Wishes are imported from sheets")
                return True
            else:
                print("❌ No wishes messages found in the sheet. Retrying in 1 second...")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Error creating/refreshing Wishes file: {str(e)}. Retrying in 1 second...")
            time.sleep(1)

def handle_xpath005_absence(current_person_details, person_index):
    """Handle XPath005 absence according to Steps 45-54"""
    # Step 45: Check internet
    print("\nStep 45: Checking internet connection...")
    if check_internet():
        print("Internet available - continuing with Step 47")
        next_step = "step47"
    else:
        print("Internet not available - continuing with Step 46")
        next_step = "step46"

    # Step 46: Refresh and continue to Step 21
    if next_step == "step46":
        print("\nStep 46: Refreshing page and continuing to Step 21")
        driver.refresh()
        time.sleep(3)
        return "step21"

    # Step 47: Refresh and continue to Step 48
    if next_step == "step47":
        print("\nStep 47: Refreshing page and continuing to Step 48")
        driver.refresh()
        time.sleep(3)
        next_step = "step48"

    # Step 48: Fetch Xpath005 with infinite retry
    if next_step == "step48":
        print("\nStep 48: Fetching Facebook Xpath005 from Firebase...")
        while True:
            try:
                xpath005 = fetch_xpath_from_firebase("Xpath005")
                print("✅ Facebook Xpath005 fetched from database")
                next_step = "step49"
                break
            except Exception as e:
                print(f"Error fetching Xpath005: {str(e)} - Retrying in 1 second...")
                time.sleep(1)

    # Step 49: Search for Xpath005 for 120 seconds
    if next_step == "step49":
        print("\nStep 49: Searching for Xpath005 for up to 120 seconds...")
        start_time = time.time()
        found = False
        
        while time.time() - start_time < 120:
            try:
                driver.find_element("xpath", xpath005)
                print("Xpath005 found - continuing to Step 22")
                found = True
                return "step22"
            except NoSuchElementException:
                sys.stdout.write(f'\rSearching... ({int(time.time() - start_time)}s)')
                sys.stdout.flush()
                time.sleep(1)
            except Exception as e:
                print(f"\nError searching Xpath005: {str(e)}")
                break
        
        if not found:
            print("\nXpath005 not found within 120 seconds - continuing to Step 50")
            next_step = "step50"

    # Step 50: Check internet again
    if next_step == "step50":
        print("\nStep 50: Checking internet connection again...")
        if check_internet():
            print("Internet available - continuing with Step 51")
            next_step = "step51"
        else:
            print("Internet not available - continuing with Step 46")
            return "step46"

    # Steps 51-54: Handle unavailable message button
    if next_step == "step51":
        print("\nStep 51: Message button not available")
        
        # Step 52: Save to temp file
        current_datetime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        file_path = PATHS["temp_report"]
        
        with open(file_path, 'a') as f:
            f.write(f"{person_index}.{current_datetime}\n")
            f.write(f"  {current_person_details['name']}\n")
            f.write(f"  {current_person_details['profile_link']}\n")
            
            if current_person_details.get('dob'):
                f.write(f"  {current_person_details['dob']}\n")
                f.write(f"  {current_person_details['age']}\n")
            else:
                f.write(f"  Not available\n")
                f.write(f"  Not available\n")
            
            f.write(f"  Not available\n")  # For wish message
            f.write(f"  Message button not available\n\n")
        
        # Step 53
        print(f"\nStep 53: {person_index}.{current_person_details['name']} data stored in temporary file")
        
        # Step 54
        print("\nStep 54: Continuing to Step 19 with next person")
        return "step19"

def main_flow():
    """Main execution with improved error handling and retry logic"""
    # Create required directories first
    create_required_directories()
    
    # Verify required files exist
    if not verify_required_files():
        print("❌ Required files missing. Please check configuration.")
        sys.exit(1)
    
    # Create a dictionary to hold variables we want to modify in nested functions
    flow_vars = {'attempt_count': 0, 'reset_attempt': False}
    
    # Initialize Firebase if not already done
    if not firebase_initialized and not initialize_firebase():
        print("❌ Failed to initialize Firebase. Exiting...")
        sys.exit(0)

    # Connect to Google Sheets once at start
    client = connect_to_google_sheets()

    while True:
        if flow_vars['reset_attempt']:
            flow_vars['attempt_count'] = 0
            flow_vars['reset_attempt'] = False
        
        flow_vars['attempt_count'] += 1
        is_even_attempt = flow_vars['attempt_count'] % 2 == 0
        print(f"\n{'='*50}\n🔄 Attempt #{flow_vars['attempt_count']} ({'EVEN - will check internet if no birthdays' if is_even_attempt else 'ODD - simple restart if no birthdays'})")
        
        # Clean up previous browser session
        close_chrome()
        
        # Check internet before each attempt
        if not check_internet():
            print("❌ No internet connection - waiting to retry...")
            time.sleep(5)
            continue
            
        # Launch browser and start main flow
        if launch_chrome():
            try:
                # Step 1: Search Facebook
                xpath001 = fetch_xpath_from_firebase("Xpath001")
                if not xpath001 or not search_and_click_element(xpath001, "✅ Entered Search Facebook Option"):
                    print("❌ Failed at Facebook search")
                    continue
                
                # Step 2: Paste birthdays keyword
                if not paste_birthdays_keyword():
                    print("❌ Failed to paste birthdays keyword")
                    continue
                
                # Step 3: Click birthday event page - MODIFIED SECTION
                xpath002 = fetch_xpath_from_firebase("Xpath002")
                if not xpath002 or not search_and_click_element(
                    xpath002, 
                    "✅ Entered birthday event page", 
                    restart_on_fail=True, 
                    xpath_name="Xpath002",
                    main_flow_vars=flow_vars  # Pass the flow variables dictionary
                ):
                    print("❌ Failed to enter birthday page - restarting from Attempt #1")
                    continue
                
                # Step 4: Check for birthdays
                xpath003 = fetch_xpath_from_firebase("Xpath003")
                if check_element_availability(xpath003, "Today's birthdays found"):
                    # Reset attempt counter if birthdays found
                    flow_vars['attempt_count'] = 0
                    
                    # Create/refresh Wishes file
                    if not create_or_refresh_wishes_file(client):
                        print("❌ Failed to create/refresh Wishes file")
                        continue
                    
                    # Step 14: Fetch Xpath004
                    xpath004 = fetch_xpath_from_firebase("Xpath004")
                    print("✅ Facebook Xpath004 fetched from database")
                    
                    # Step 15: Modify and search XPath004
                    if not modify_and_search_xpath004(xpath004):
                        print("❌ Failed to find modified XPath004")
                        continue
                    
                    # Step 16: Count birthday people
                    birthday_count = count_birthday_people()
                    if birthday_count > 0:
                        # Step 17: Fetch birthday people details
                        people_details = fetch_birthday_people_details(birthday_count)
                        if not people_details:
                            print("❌ Failed to fetch people details")
                            continue
                            
                        # Process each birthday person
                        for i, person in enumerate(people_details):
                            person_index = i + 1
                            current_person_details = person
                            retry_count = 0
                            max_retries = 3  # Maximum retries for same person
                            
                            while retry_count < max_retries:
                                try:
                                    # Step 19: Open profile
                                    if not open_profile(current_person_details['profile_link'], current_person_details['name']):
                                        print(f"❌ Failed to open profile for {current_person_details['name']}")
                                        break
                                    
                                    # Step 20-21: Check XPath005 availability
                                    xpath005_status = fetch_and_check_xpath005()
                                    if xpath005_status == "xpath005_available":
                                        # Step 22-24: Handle popup if exists
                                        if not handle_popup_if_exists():
                                            print(f"❌ Failed to handle popup for {current_person_details['name']}")
                                            break
                                        
                                        # Step 25-26: Click message button
                                        if not click_message_button():
                                            print(f"❌ Failed to click message button for {current_person_details['name']}")
                                            save_report_to_temp_file(person_index, current_person_details, "Not available", "Message button not available")
                                            print_person_data_stored(person_index, current_person_details['name'])
                                            break
                                        
                                        # Step 27-30: Check emoji button color
                                        emoji_check_status = check_emoji_button_color()
                                        
                                        if emoji_check_status == "color_matched":
                                            # Step 31: Delete screenshot
                                            delete_screenshot()
                                            
                                            # Step 33: Fetch XPath006
                                            xpath006 = fetch_xpath_from_firebase("Xpath006")
                                            print("✅ Facebook Xpath006 fetched from database")
                                            
                                            # Step 34: Check XPath006 availability
                                            xpath006_status = check_xpath006_availability(xpath006)
                                            if xpath006_status == "xpath006_available":
                                                # Step 35: Click XPath006
                                                if click_xpath006(xpath006):
                                                    # Step 36: Paste message from file and press Enter
                                                    wish_message = paste_message_and_enter_from_file()
                                                    if wish_message:
                                                        # Step 37-38: Check XPath010 and XPath011 availability
                                                        xpath_status = check_xpath010_and_xpath011_availability()
                                                        
                                                        if xpath_status == "xpath010_available":
                                                            print_message_sent() # Step 39
                                                            save_report_to_temp_file(person_index, current_person_details, wish_message, "Message sent") # Step 40
                                                            print_person_data_stored(person_index, current_person_details['name']) # Step 41
                                                            click_xpath007() # Step 43
                                                            time.sleep(5) # Step 44
                                                            break  # Successfully sent - move to next person
                                                        elif xpath_status == "restart_with_same_person":
                                                            print("🔄 Restarting process with same person due to failed message delivery")
                                                            retry_count += 1
                                                            continue  # This will restart the loop with the same person
                                                        
                                                else:
                                                    print("Failed to click XPath006")
                                                    retry_count += 1
                                                    continue
                                            elif xpath006_status == "xpath006_not_available":
                                                click_xpath007() # Step 63
                                                print("Message tab is closed")
                                                save_report_to_temp_file(person_index, current_person_details, "Not available", "Message field not available (retry needed)")
                                                print_person_data_stored(person_index, current_person_details['name'])
                                                retry_count += 1
                                                continue
                                        
                                        elif emoji_check_status == "xpath008_found":
                                            print("User can't access this chat") # Step 57
                                            save_report_to_temp_file(person_index, current_person_details, "Not available", "User can't access this chat") # Step 58
                                            print_person_data_stored(person_index, current_person_details['name']) # Step 59a
                                            click_xpath007() # Step 59c
                                            print("Message tab is closed")
                                            break
                                        
                                        elif emoji_check_status == "color_not_matched_step68":
                                            step68_result = step68_to_step70_flow()
                                            if step68_result == "continue_to_step20":
                                                retry_count += 1
                                                continue  # Continue with same person
                                        
                                        elif emoji_check_status == "error":
                                            print("❌ Error in emoji check - retrying with same person")
                                            retry_count += 1
                                            continue
                                    
                                    elif xpath005_status == "xpath005_not_available":
                                        next_step = handle_xpath005_absence(current_person_details, person_index)
                                        if next_step == "step19":
                                            break  # Move to next person
                                        elif next_step == "step21":
                                            retry_count += 1
                                            continue  # Restart check after refresh
                                        elif next_step == "step22":
                                            continue  # Proceed with message flow
                                    
                                    elif xpath005_status == "error":
                                        print("❌ Error checking XPath005 - retrying with same person")
                                        retry_count += 1
                                        continue
                                
                                except Exception as e:
                                    print(f"❌ Unexpected error processing {current_person_details['name']}: {str(e)}")
                                    traceback.print_exc()
                                    retry_count += 1
                                    if retry_count < max_retries:
                                        print(f"🔄 Retrying with same person (attempt {retry_count + 1} of {max_retries})")
                                        continue
                                    else:
                                        print(f"❌ Max retries reached for {current_person_details['name']} - moving to next person")
                                        save_report_to_temp_file(person_index, current_person_details, "Not available", f"Error after {max_retries} retries")
                                        print_person_data_stored(person_index, current_person_details['name'])
                                        break
                            
                            # After processing person (success or max retries)
                            print(f"ℹ️ Finished processing {current_person_details['name']}")
                        
                        # After processing all birthdays
                        close_browser_and_final_message()
                        sys.exit(0)
                        
                    elif birthday_count == 0:
                        print("No birthdays found today")
                        close_chrome()
                        
                        if is_even_attempt:
                            print("⚡ EVEN ATTEMPT: Checking internet for WhatsApp flow...")
                            if check_internet():
                                print("🌐 Internet available - proceeding to WhatsApp notification")
                                
                                # WhatsApp Notification Flow
                                try:
                                    # Update Google Sheets
                                    if not update_google_sheet(client):
                                        print("❌ Failed to update Google Sheets")
                                        raise Exception("Google Sheets update failed")
                                    
                                    # Open WhatsApp
                                    whatsapp_xpath001 = open_whatsapp_and_fetch_xpath()
                                    if not whatsapp_xpath001:
                                        print("❌ Failed to open WhatsApp")
                                        raise Exception("WhatsApp open failed")
                                    
                                    # Paste number
                                    if not click_whatsapp_search_and_paste_number(whatsapp_xpath001):
                                        print("❌ Failed to paste WhatsApp number")
                                        raise Exception("WhatsApp number paste failed")
                                    
                                    # Enter message field
                                    if not press_down_arrow_and_enter_message_field():
                                        print("❌ Failed to enter WhatsApp message field")
                                        raise Exception("WhatsApp message field failed")
                                    
                                    # Send message
                                    whatsapp_xpath003 = paste_message_and_confirm()
                                    if not whatsapp_xpath003:
                                        print("❌ Failed to confirm WhatsApp message")
                                        raise Exception("WhatsApp message confirm failed")
                                    
                                    # Verify delivery
                                    if not check_whatsapp_xpath003_availability(whatsapp_xpath003):
                                        print("⚠️ WhatsApp message pending - starting retry flow")
                                        whatsapp_retry_flow()
                                    
                                    print("✅ WhatsApp notification successfully completed!")
                                    sys.exit(0)
                                    
                                except Exception as e:
                                    print(f"❌ WhatsApp flow failed: {str(e)}")
                                    sys.exit(1)
                            else:
                                print("🌐 No internet available - restarting cycle")
                                continue
                        else:
                            print("⚡ ODD ATTEMPT: Simple restart")
                            continue
                    
                    else: # birthday_count is -1 (error)
                        print("❌ Error counting birthdays")
                        continue
                        
                else:
                    print("❌ Today's birthdays not available")
                    
                    if is_even_attempt:
                        print("⚡ EVEN ATTEMPT: Checking internet for WhatsApp flow...")
                        if check_internet():
                            print("🌐 Internet available - proceeding to WhatsApp notification")
                            
                            # Close Facebook browser
                            close_chrome()
                            
                            # WhatsApp Notification Flow
                            try:
                                # Update Google Sheets
                                if not update_google_sheet(client):
                                    print("❌ Failed to update Google Sheets")
                                    raise Exception("Google Sheets update failed")
                                
                                # Open WhatsApp
                                whatsapp_xpath001 = open_whatsapp_and_fetch_xpath()
                                if not whatsapp_xpath001:
                                    print("❌ Failed to open WhatsApp")
                                    raise Exception("WhatsApp open failed")
                                
                                # Paste number
                                if not click_whatsapp_search_and_paste_number(whatsapp_xpath001):
                                    print("❌ Failed to paste WhatsApp number")
                                    raise Exception("WhatsApp number paste failed")
                                
                                # Enter message field
                                if not press_down_arrow_and_enter_message_field():
                                    print("❌ Failed to enter WhatsApp message field")
                                    raise Exception("WhatsApp message field failed")
                                
                                # Send message
                                whatsapp_xpath003 = paste_message_and_confirm()
                                if not whatsapp_xpath003:
                                    print("❌ Failed to confirm WhatsApp message")
                                    raise Exception("WhatsApp message confirm failed")
                                
                                # Verify delivery
                                if not check_whatsapp_xpath003_availability(whatsapp_xpath003):
                                    print("⚠️ WhatsApp message pending - starting retry flow")
                                    whatsapp_retry_flow()
                                
                                print("✅ WhatsApp notification successfully completed!")
                                sys.exit(0)
                                
                            except Exception as e:
                                print(f"❌ WhatsApp flow failed: {str(e)}")
                                sys.exit(1)
                                
                        else:
                            print("🌐 No internet available - restarting cycle")
                            continue
                            
                    else:
                        print("⚡ ODD ATTEMPT: Simple restart")
                        continue
                        
            except Exception as e:
                print(f"❌ Unexpected error in main flow: {str(e)}")
                traceback.print_exc()
                continue

if __name__ == "__main__":
    try:
        main_flow()
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user")
    finally:
        pass
