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
# FLEXIBLE CONFIGURATION
# ================================
# Auto-detect user home directory
USER_HOME = os.path.expanduser("~")
# Extract username from home directory path
BASE_USER = os.path.basename(USER_HOME)

# Base directory structure - Auto-detected
BASE_DIR = os.path.join(USER_HOME, "bots")
FACEBOOK_BIRTHDAY_DIR = os.path.join(BASE_DIR, "facebook birthday wisher")

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
# ENHANCED FUNCTIONS WITH CLICK INTERCEPTION HANDLING
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
    """Search and click element with refresh logic and click interception handling"""
    start_time = time.time()
    refresh_count = 0
    
    while True:
        try:
            # Wait for element to be clickable with explicit wait
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(("xpath", xpath))
            )
            element.click()
            print(success_message)
            return True
            
        except Exception as e:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Handle click interception with multiple strategies
            if "element click intercepted" in str(e).lower() or "not clickable" in str(e).lower():
                print("🔄 Element click intercepted - trying alternative click methods...")
                
                # Strategy 1: JavaScript click
                try:
                    element = driver.find_element("xpath", xpath)
                    driver.execute_script("arguments[0].click();", element)
                    print(f"✅ {success_message} (via JavaScript)")
                    return True
                except Exception as js_e:
                    print(f"❌ JavaScript click failed: {str(js_e)}")
                
                # Strategy 2: Enter key
                try:
                    element = driver.find_element("xpath", xpath)
                    element.send_keys(Keys.ENTER)
                    print(f"✅ {success_message} (via Enter key)")
                    return True
                except Exception as enter_e:
                    print(f"❌ Enter key method failed: {str(enter_e)}")
                
                # Strategy 3: Action chains
                try:
                    from selenium.webdriver.common.action_chains import ActionChains
                    element = driver.find_element("xpath", xpath)
                    actions = ActionChains(driver)
                    actions.move_to_element(element).click().perform()
                    print(f"✅ {success_message} (via ActionChains)")
                    return True
                except Exception as action_e:
                    print(f"❌ ActionChains method failed: {str(action_e)}")
            
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

def click_birthday_event_with_retry(xpath002, max_retries=5):
    """Special handling for birthday event click with multiple strategies"""
    for attempt in range(max_retries):
        try:
            # Wait for element to be clickable
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(("xpath", xpath002))
            )
            element.click()
            print("✅ Entered birthday event page")
            return True
            
        except Exception as e:
            print(f"❌ Click attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                # Try JavaScript click
                try:
                    element = driver.find_element("xpath", xpath002)
                    driver.execute_script("arguments[0].click();", element)
                    print("✅ Entered birthday event page (via JavaScript)")
                    return True
                except Exception:
                    pass
                
                # Try Enter key
                try:
                    element = driver.find_element("xpath", xpath002)
                    element.send_keys(Keys.ENTER)
                    print("✅ Entered birthday event page (via Enter key)")
                    return True
                except Exception:
                    pass
                
                print(f"🔄 Retrying in 2 seconds... ({attempt + 1}/{max_retries})")
                time.sleep(2)
    
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
            spreadsheet = client.open("facebook birthday wisher")
            worksheet = spreadsheet.worksheet("report")
            
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
# NEW WHATSAPP MESSAGE FLOW (Steps 19a-19m)
# ================================

def new_whatsapp_message_flow(has_birthdays=False):
    """New WhatsApp message flow as per requirements"""
    
    # Step 19a: Close browser and reopen
    print("🔄 Step 19a: Closing browser...")
    close_chrome()
    
    # Step 19b: Check internet connection
    print("🌐 Step 19b: Checking internet connection...")
    while True:
        if check_internet():
            print("✅ Internet is present - continuing with step 19c")
            break
        else:
            print("🔄 Internet not present - checking again in 2 seconds")
            time.sleep(2)
    
    # Step 19c: Open WhatsApp Web
    print("🌐 Step 19c: Opening WhatsApp Web...")
    if not launch_chrome(url="https://web.whatsapp.com/", start_maximized=True):
        print("❌ Failed to open WhatsApp Web")
        return False
    print("✅ Entered WhatsApp Web")
    
    # Step 19d: Check Xpath001 for 120 seconds
    print("🔍 Step 19d: Checking for WhatsApp Xpath001...")
    whatsapp_xpath001 = fetch_xpath_from_firebase("Xpath001", "WhatsApp")
    print("✅ WhatsApp Xpath001 fetched from database")
    
    start_time = time.time()
    xpath001_found = False
    
    while time.time() - start_time < 120:
        try:
            element = driver.find_element("xpath", whatsapp_xpath001)
            xpath001_found = True
            print("✅ WhatsApp Xpath001 found")
            break
        except NoSuchElementException:
            sys.stdout.write(f'\r🔍 Searching for WhatsApp XPath001... ({int(time.time() - start_time)}s)')
            sys.stdout.flush()
            time.sleep(1)
        except Exception as e:
            print(f"\n❌ Error searching Xpath001: {str(e)}")
            break
    
    if not xpath001_found:
        print("\n❌ WhatsApp Xpath001 not found within 120 seconds - checking for loading chats")
        # Step 19f: Check Xpath011 (Loading your chats)
        whatsapp_xpath011 = fetch_xpath_from_firebase("Xpath011", "WhatsApp")
        print("✅ WhatsApp Xpath011 fetched from database")
        
        try:
            driver.find_element("xpath", whatsapp_xpath011)
            print("✅ WhatsApp Xpath011 found - loading chats detected")
            print("🔄 Continuing with step 19d")
            return new_whatsapp_message_flow(has_birthdays)  # Restart the flow
        except NoSuchElementException:
            print("❌ WhatsApp Xpath011 not found - restarting from step 19a")
            return new_whatsapp_message_flow(has_birthdays)  # Restart the flow
    
    # Step 19e: Click Xpath001 and check report number file
    print("🖱️ Step 19e: Clicking WhatsApp Xpath001...")
    try:
        element = driver.find_element("xpath", whatsapp_xpath001)
        element.click()
        print("✅ Entered Mobile number search field")
    except Exception as e:
        print(f"❌ Error clicking Xpath001: {str(e)}")
        return False
    
    # Check report number file
    if os.path.exists(PATHS["report_number"]):
        print("✅ Report number file available")
    else:
        print("❌ Report number file not available")
        return False
    
    # Step 19g: Check phone number in file
    print("📱 Step 19g: Checking phone number in file...")
    try:
        with open(PATHS["report_number"], "r") as file:
            phone_number = file.readline().strip()
            if phone_number:
                print("✅ Phone number is available")
            else:
                print("❌ Phone number is not available")
                return False
    except Exception as e:
        print(f"❌ Error reading phone number: {str(e)}")
        return False
    
    # Step 19h: Paste number and press Enter
    print("📝 Step 19h: Pasting phone number...")
    try:
        search_box = driver.switch_to.active_element
        search_box.send_keys(phone_number)
        print(f"✅ Phone number pasted: {phone_number}")
        time.sleep(1)
        search_box.send_keys(Keys.ENTER)
        print("✅ Enter key pressed")
        time.sleep(10)  # Wait for stability
    except Exception as e:
        print(f"❌ Error pasting phone number: {str(e)}")
        return False
    
    # Step 19i: Check Xpath004 (No chats found)
    print("🔍 Step 19i: Checking for invalid number...")
    whatsapp_xpath004 = fetch_xpath_from_firebase("Xpath004", "WhatsApp")
    print("✅ WhatsApp Xpath004 fetched from database")
    
    try:
        driver.find_element("xpath", whatsapp_xpath004)
        print("❌ Xpath004 found - checking internet...")
        if check_internet():
            print("❌ Invalid Mobile Number")
            return False
        else:
            print("🔄 Internet not present - restarting from step 19a")
            return new_whatsapp_message_flow(has_birthdays)
    except NoSuchElementException:
        print("✅ Valid mobile number - continuing with step 19j")
    
    # Step 19j: Press down arrow and enter message field
    print("⬇️ Step 19j: Pressing down arrow...")
    try:
        active_element = driver.switch_to.active_element
        active_element.send_keys(Keys.ARROW_DOWN)
        print("✅ Down arrow pressed")
        time.sleep(2)  # Wait for stability
        active_element.send_keys(Keys.ENTER)
        print("✅ Entered Message Field")
    except Exception as e:
        print(f"❌ Error in step 19j: {str(e)}")
        return False
    
    # Step 19k: Type message with EXACT FORMAT (NO LINKS, NO WISH MESSAGES)
    print("💬 Step 19k: Typing message...")
    try:
        current_date = datetime.now().strftime("%d-%m-%Y")
        
        if not has_birthdays:
            # No birthdays today message
            message = f"Facebook birthday bot({current_date})\nNo more birthday today"
        else:
            # Process birthday report with CLEAN FORMAT
            temp_file_path = PATHS["temp_report"]
            if os.path.exists(temp_file_path):
                # Read and clean the temp file content
                with open(temp_file_path, 'r') as f:
                    lines = f.readlines()
                
                # Filter out profile links and wish messages
                clean_lines = []
                skip_next = False
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Skip profile links (lines containing http)
                    if 'http' in line:
                        continue
                    
                    # Skip wish message lines
                    if 'Celebrating' in line or 'Happy birthday' in line or 'Wishes' in line:
                        continue
                    
                    # Skip "Not available" lines that are redundant
                    if 'Not available' in line and len(clean_lines) > 0:
                        last_line = clean_lines[-1].strip()
                        if 'Age' in last_line or any(char.isdigit() for char in last_line if len(last_line) <= 3):
                            continue
                    
                    clean_lines.append(line)
                
                # Build the CLEAN message
                message = f"Facebook birthday bot({current_date})\n"
                message += "\n".join(clean_lines) + "\n"
                
                # Add summary statistics
                total_birthdays = len([line for line in clean_lines if 'Message sent' in line or "User can't access" in line or "Message button not available" in line])
                messages_sent = len([line for line in clean_lines if 'Message sent' in line])
                cant_access = len([line for line in clean_lines if "User can't access" in line])
                button_unavailable = len([line for line in clean_lines if "Message button not available" in line])
                
                message += "---------------------------------------------\n"
                message += f"Today's birthday people: {total_birthdays}\n"
                message += f"Message sent: {messages_sent}\n"
                message += f"Can't access chat: {cant_access}\n"
                message += f"Message button not available: {button_unavailable}\n"
                message += "---------------------------------------------"
            else:
                message = f"Facebook birthday bot({current_date})\nReport file not available"
        
        # Type the message with proper formatting
        active_element = driver.switch_to.active_element
        lines = message.split('\n')
        for i, line in enumerate(lines):
            active_element.send_keys(line)
            if i < len(lines) - 1:  # Add newline for all but last line
                active_element.send_keys(Keys.SHIFT + Keys.ENTER)
        
        print("✅ Message typed successfully")
        
    except Exception as e:
        print(f"❌ Error typing message: {str(e)}")
        traceback.print_exc()
        return False
    
    # Step 19l: Wait and press Enter
    print("⏳ Step 19l: Waiting 2 seconds for stability...")
    time.sleep(2)
    try:
        active_element = driver.switch_to.active_element
        active_element.send_keys(Keys.ENTER)
        print("✅ Enter key pressed - message sent")
    except Exception as e:
        print(f"❌ Error sending message: {str(e)}")
        return False
    
    # Step 19m: Check for message delivery
    print("📨 Step 19m: Checking message delivery...")
    time.sleep(2)  # Wait for stability
    
    whatsapp_xpath003 = fetch_xpath_from_firebase("Xpath003", "WhatsApp")
    print("✅ WhatsApp Xpath003 fetched from database")
    
    start_time = time.time()
    while True:
        try:
            driver.find_element("xpath", whatsapp_xpath003)
            elapsed = time.time() - start_time
            sys.stdout.write(f'\r⏳ Message pending... ({int(elapsed)}s)')
            sys.stdout.flush()
            time.sleep(1)
        except NoSuchElementException:
            print("\n✅ Report sent successfully")
            close_chrome()
            return True
        except Exception as e:
            print(f"\n❌ Error checking message status: {str(e)}")
            break
    
    return False

# ================================
# FACEBOOK BIRTHDAY FUNCTIONS
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
    """IMPROVED VERSION: Check if Facebook Xpath010 or Xpath011 is available with timeout"""
    print("🔍 Checking for message delivery confirmation...")
    
    # Fetch XPaths
    xpath010 = fetch_xpath_from_firebase("Xpath010")
    xpath011 = fetch_xpath_from_firebase("Xpath011")
    print("✅ Facebook Xpath010 and Xpath011 fetched from database")
    
    start_time = time.time()
    max_wait_time = 60  # Reduced from 120 to 60 seconds
    
    while time.time() - start_time < max_wait_time:
        elapsed = time.time() - start_time
        
        # Check XPath010 first (message sent confirmation)
        try:
            element = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located(("xpath", xpath010))
            )
            print("✅ Facebook Xpath010 is available - message sent")
            return "xpath010_available"
        except TimeoutException:
            pass
        
        # Check XPath011 (alternative confirmation)
        try:
            element = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located(("xpath", xpath011))
            )
            print("✅ Facebook Xpath011 is available")
            return "xpath011_available"
        except TimeoutException:
            pass
        
        # Additional check: look for any sent message indicator
        try:
            sent_indicators = [
                "//div[contains(@class, 'message-out')]",
                "//div[contains(@aria-label, 'Message sent')]",
                "//span[contains(@data-icon, 'msg-dblcheck')]"
            ]
            for indicator in sent_indicators:
                try:
                    driver.find_element("xpath", indicator)
                    print("✅ Message sent indicator found")
                    return "xpath010_available"
                except NoSuchElementException:
                    continue
        except Exception:
            pass
        
        sys.stdout.write(f'\r⏳ Confirming message delivery... ({int(elapsed)}s)')
        sys.stdout.flush()
        time.sleep(1)
    
    print(f"\n⚠️ No confirmation found within {max_wait_time} seconds, assuming message sent")
    return "xpath010_available"  # Assume message was sent to prevent infinite loop

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
    """Save data to temporary file - CLEAN VERSION (NO LINKS, NO WISH MESSAGES)"""
    file_path = PATHS["temp_report"]
    current_datetime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    with open(file_path, 'a') as f:
        f.write(f"{person_index}.{current_datetime}\n")
        f.write(f"{person_details['name']}\n")
        
        if person_details['dob']:
            f.write(f"{person_details['dob']}\n")
            f.write(f"{person_details['age']}\n")
        else:
            f.write(f"Not available\n")
            f.write(f"Not available\n")
        
        f.write(f"{remark}\n\n")
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
            spreadsheet = client.open("facebook birthday wisher")
            worksheet = spreadsheet.worksheet("report")
            
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
                    field_order = ['name', 'dob', 'age', 'remark']
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
            
            # Transfer data to Google Sheets with corrected column names
            for record in records:
                row_data = [
                    record.get('datetime', ''),
                    record.get('name', ''),
                    record.get('dob', ''),
                    record.get('age', ''),
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

def close_browser_and_final_message():
    """Close browser and print final message"""
    close_chrome()
    print("All data stored in temporary file ready to upload sheets")
    
    # After closing browser, transfer data to Google Sheets
    transfer_data_to_google_sheets()
    
    # Start NEW WhatsApp report flow
    print("🚀 Starting NEW WhatsApp report flow...")
    if new_whatsapp_message_flow(has_birthdays=True):
        print("✅ WhatsApp report sent successfully!")
        return True
    else:
        print("❌ WhatsApp report failed")
        return False

def create_or_refresh_wishes_file(client):
    """Create or refresh the Wishes file and import from Google Sheets - UPDATED FOR 'wishes' WORKSHEET"""
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
            spreadsheet = client.open("facebook birthday wisher")
            worksheet = spreadsheet.worksheet("wishes")  # CHANGED: Using "wishes" worksheet
            
            messages = worksheet.col_values(1)[1:]  # Get all values from column A, skip header
            
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
            f.write(f"{current_person_details['name']}\n")
            
            if current_person_details.get('dob'):
                f.write(f"{current_person_details['dob']}\n")
                f.write(f"{current_person_details['age']}\n")
            else:
                f.write(f"Not available\n")
                f.write(f"Not available\n")
            
            f.write(f"Message button not available\n\n")
        
        # Step 53
        print(f"\nStep 53: {person_index}.{current_person_details['name']} data stored in temporary file")
        
        # Step 54
        print("\nStep 54: Continuing to Step 19 with next person")
        return "step19"

# ================================
# MAIN FLOW WITH ENHANCED CLICK HANDLING
# ================================

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
                
                # Step 3: Click birthday event page - WITH ENHANCED CLICK HANDLING
                xpath002 = fetch_xpath_from_firebase("Xpath002")
                if not xpath002 or not click_birthday_event_with_retry(xpath002):
                    print("❌ Failed to enter birthday page - restarting from Attempt #1")
                    close_chrome()
                    flow_vars['reset_attempt'] = True
                    continue
                
                # Step 4: Check for birthdays
                xpath003 = fetch_xpath_from_firebase("Xpath003")
                if check_element_availability(xpath003, "Today's birthdays found"):
                    # Reset attempt counter if birthdays found
                    flow_vars['attempt_count'] = 0
                    
                    # Create/refresh Wishes file - NOW USING "wishes" WORKSHEET
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
                                            save_report_to_temp_file(person_index, current_person_details, "", "Message button not available")
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
                                                            save_report_to_temp_file(person_index, current_person_details, "", "Message sent") # Step 40
                                                            print_person_data_stored(person_index, current_person_details['name']) # Step 41
                                                            click_xpath007() # Step 43
                                                            time.sleep(5) # Step 44
                                                            break  # Successfully sent - move to next person
                                                        elif xpath_status == "xpath011_available":
                                                            print("✅ Message sent (XPath011 confirmation)")
                                                            save_report_to_temp_file(person_index, current_person_details, "", "Message sent")
                                                            print_person_data_stored(person_index, current_person_details['name'])
                                                            click_xpath007()
                                                            time.sleep(5)
                                                            break
                                                        else:
                                                            print("⚠️ Message confirmation unclear, but continuing")
                                                            save_report_to_temp_file(person_index, current_person_details, "", "Message sent (confirmation unclear)")
                                                            print_person_data_stored(person_index, current_person_details['name'])
                                                            click_xpath007()
                                                            time.sleep(5)
                                                            break
                                                        
                                                else:
                                                    print("Failed to click XPath006")
                                                    retry_count += 1
                                                    continue
                                            elif xpath006_status == "xpath006_not_available":
                                                click_xpath007() # Step 63
                                                print("Message tab is closed")
                                                save_report_to_temp_file(person_index, current_person_details, "", "Message field not available (retry needed)")
                                                print_person_data_stored(person_index, current_person_details['name'])
                                                retry_count += 1
                                                continue
                                        
                                        elif emoji_check_status == "xpath008_found":
                                            print("User can't access this chat") # Step 57
                                            save_report_to_temp_file(person_index, current_person_details, "", "User can't access this chat") # Step 58
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
                                        save_report_to_temp_file(person_index, current_person_details, "", f"Error after {max_retries} retries")
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
                                
                                # Use NEW WhatsApp flow for no birthdays
                                if new_whatsapp_message_flow(has_birthdays=False):
                                    print("✅ WhatsApp notification successfully completed!")
                                    sys.exit(0)
                                else:
                                    print("❌ WhatsApp flow failed")
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
                            
                            # Use NEW WhatsApp flow for no birthdays
                            if new_whatsapp_message_flow(has_birthdays=False):
                                print("✅ WhatsApp notification successfully completed!")
                                sys.exit(0)
                            else:
                                print("❌ WhatsApp flow failed")
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
        close_chrome()
