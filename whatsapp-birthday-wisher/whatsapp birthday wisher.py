# WhatsApp Birthday Wisher Python Script
import psutil
import time
import subprocess
import os
import gspread
import firebase_admin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from firebase_admin import credentials, db
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ==================== CONFIGURABLE SETTINGS ====================
# Base directories - Auto-detected
USER_HOME = os.path.expanduser("~")  # Automatically detect user home directory
BOTS_DIR = os.path.join(USER_HOME, "bots")  # Main bots directory
WHATSAPP_BOT_DIR = os.path.join(BOTS_DIR, "whatsapp birthday wisher")  # WhatsApp bot directory

# File paths
SPREADSHEET_KEY = os.path.join(WHATSAPP_BOT_DIR, "venv", "spread sheet access key.json")
DATABASE_KEY = os.path.join(WHATSAPP_BOT_DIR, "venv", "database access key.json")
REPORT_NUMBER_FILE = os.path.join(WHATSAPP_BOT_DIR, "venv", "report number")
CONTACT_FILE = os.path.join(WHATSAPP_BOT_DIR, "Today birthday list contact")
WISHES_FILE = os.path.join(WHATSAPP_BOT_DIR, "wishes")
WHATSAPP_REPORT_FILE = os.path.join(WHATSAPP_BOT_DIR, "WhatsApp report")

# Browser settings
CHROMEDRIVER_PATH = "/usr/bin/chromedriver"
CHROME_PROFILE_PATH = os.path.join(USER_HOME, ".config", "chromium") 

# Application settings
SPREADSHEET_NAME = "whatsapp birthday wisher"
FIREBASE_DB_URL = "https://thaniyanki-xpath-manager-default-rtdb.firebaseio.com/"
# ==================== END CONFIGURABLE SETTINGS ====================

# Global variables
whatsapp_xpath001 = None
whatsapp_xpath002 = None
whatsapp_xpath003 = None
whatsapp_xpath004 = None
driver = None
next_step = None
step8_message = None
extracted_phone_number = None
skip_to_step31 = False
selected_wish_stored = None

def close_chrome():
    """Closes all running instances of Chrome, Chromium, and chromedriver."""
    global driver
    try:
        if driver:
            driver.quit()
            driver = None
        
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] in ['chrome', 'chromium', 'chromedriver']:
                try:
                    proc.kill()
                    print(f"Killed process: {proc.info['name']}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        
        print("Closed all Chrome/Chromium instances.")
        time.sleep(2)
    except Exception as e:
        print(f"Error closing Chrome: {str(e)}")

def check_internet():
    """Checks for an active internet connection."""
    try:
        subprocess.check_call(["ping", "-c", "1", "8.8.8.8"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
        
def wait_for_internet():
    """Waits for internet connection with countdown (retries forever)."""
    count = 1
    while True:
        if check_internet():
            print("Internet is restored good to go")
            break
        print(f"Internet is not present retry second(s) {count}...")
        time.sleep(1)
        count += 1

def check_file_exists(file_path):
    """Checks if a file exists."""
    return os.path.isfile(file_path)

def initialize_spreadsheet():
    """Initializes connection to Google Spreadsheet (retries forever)."""
    while True:
        try:
            scope = ["https://spreadsheets.google.com/feeds", 
                    "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(SPREADSHEET_KEY, scope)
            client = gspread.authorize(creds)
            spreadsheet = client.open(SPREADSHEET_NAME)
            return spreadsheet
        except Exception as e:
            print(f"Error initializing spreadsheet: {str(e)}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

def initialize_firebase():
    """Initializes Firebase connection (retries forever)."""
    while True:
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(DATABASE_KEY)
                firebase_admin.initialize_app(cred, {
                    "databaseURL": FIREBASE_DB_URL
                })
            print("Firebase initialized successfully")
            return True
        except Exception as e:
            print(f"Firebase initialization failed: {str(e)}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

def step7_remove_duplicates(spreadsheet):
    """Step 7: Remove duplicate rows from spreadsheet (retries forever)."""
    while True:
        try:
            worksheet = spreadsheet.worksheet("birthday list")
            records = worksheet.get_all_records()
            
            seen = set()
            duplicate_rows = []
            
            for i, row in enumerate(records, start=2):
                # Use the correct column name from your spreadsheet: 'Counrty Code' (with typo)
                country_code = str(row.get('Counrty Code', '')).strip()
                whatsapp_number = str(row.get('WhatsApp Number', '')).strip()
                
                # Create a unique key combining both country code AND WhatsApp number
                key = f"{country_code}-{whatsapp_number}"
                
                if key in seen:
                    duplicate_rows.append(i)
                else:
                    seen.add(key)
            
            if not duplicate_rows:
                print("No duplicate rows found.")
                return
            
            for row_num in sorted(duplicate_rows, reverse=True):
                worksheet.delete_rows(row_num)
                print(f"Deleted duplicate row {row_num}")
            
            print("Duplicate removal completed.")
            break
            
        except Exception as e:
            print(f"Error during step7: {str(e)}")
            print("Retrying...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)
                
def step8_filter_birthdays(spreadsheet):
    """Step 8: Filter today's birthdays and count (retries forever)."""
    global next_step, step8_message
    while True:
        try:
            today = datetime.now()
            current_day_month = today.strftime("%d-%m")
            
            worksheet = spreadsheet.worksheet("birthday list")
            all_records = worksheet.get_all_records()
            
            birthday_today = []
            for record in all_records:
                dob = record.get('Date of Birth', '')
                if dob.startswith(current_day_month):
                    birthday_today.append(record)
            
            count = len(birthday_today)
            
            if count == 0:
                step8_message = "No more birthday today"
                print(step8_message)
                next_step = "step9a"
                return step8_message
            elif count > 100:
                step8_message = f"Warning - More than limit {count} people have birthday today it may consider as spam so drop the process"
                print(step8_message)
                next_step = "step9a"
                return step8_message
            else:
                print(f"{count} people(s) birthday today")
                next_step = "step10"
                return f"{count} birthdays today"
                
        except Exception as e:
            print(f"Error during step8: {str(e)}")
            print("Retrying...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step9a_open_whatsapp_web():
    """Step 9a: Open WhatsApp Web with persistent profile (retries forever)."""
    global driver
    while True:
        try:
            close_chrome()
            
            # Configure Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_PATH}")
            
            # Initialize WebDriver
            service = Service(executable_path=CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get("https://web.whatsapp.com/")
            
            print("Entered WhatsApp Web")
            
            # Wait for QR scan with new logic
            start_time = time.time()
            qr_scanned = False
            
            while time.time() - start_time <= 120:  # Wait up to 120 seconds
                try:
                    # Check if logged in by looking for chat list
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Chat list']")))
                    print("WhatsApp Web is ready - QR scanned successfully")
                    qr_scanned = True
                    break
                except TimeoutException:
                    # Wait 1 second and continue checking
                    time.sleep(1)
                    continue
            
            if qr_scanned:
                return True
            else:
                # After 120 seconds, check for "Loading your chats" keyword
                print("120 seconds completed - checking for 'Loading your chats' status")
                
                # Check if "Loading your chats" is present at 121st second
                loading_found = False
                try:
                    # Look for loading indicator or text
                    loading_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Loading your chats')]")
                    if loading_elements:
                        loading_found = True
                        print("'Loading your chats' keyword found - starting internet monitoring")
                except:
                    pass
                
                if loading_found:
                    # Wait for loading to disappear with internet monitoring
                    loading_disappeared = False
                    check_count = 1
                    internet_check_count = 0
                    
                    while True:
                        try:
                            # Check if loading is still present
                            loading_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Loading your chats')]")
                            if not loading_elements:
                                loading_disappeared = True
                                print("'Loading your chats' disappeared - WhatsApp is ready")
                                break
                            else:
                                print(f"Still loading... check {check_count}")
                                check_count += 1
                                
                                # Check internet every 5 checks (approximately 5 seconds)
                                if check_count % 5 == 0:
                                    internet_check_count += 1
                                    print(f"Internet check {internet_check_count}...")
                                    if not check_internet():
                                        print("Internet lost during loading - refreshing page")
                                        driver.refresh()
                                        time.sleep(5)
                                        # Break to restart the entire process
                                        break
                                
                        except Exception as e:
                            print(f"Error checking loading status: {str(e)}")
                        
                        time.sleep(1)  # Check every second
                    
                    if loading_disappeared:
                        return True
                    else:
                        # If we broke due to internet loss, continue to restart
                        print("Restarting due to internet loss during loading")
                        continue
                else:
                    # "Loading your chats" not found at 121st second - refresh
                    print("'Loading your chats' not found - refreshing page")
                    driver.refresh()
                    time.sleep(5)
                    continue
                    
        except Exception as e:
            print(f"Error opening WhatsApp Web: {str(e)}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

def step9b_check_database_key():
    """Step 9b: Check for database access key file (exits if missing)."""
    while True:
        if not os.path.isfile(DATABASE_KEY):
            print("xpath manager client key is missing")
            close_chrome()
            print("Closing script.")
            exit()
        else:
            print("Database access key found")
            return True

def step9c_fetch_xpath():
    """Step 9c: Fetch WhatsApp Xpath001 from Firebase (retries forever)."""
    global whatsapp_xpath001
    while True:
        try:
            if not initialize_firebase():
                raise Exception("Failed to initialize Firebase")
            
            whatsapp_ref = db.reference("WhatsApp/Xpath")
            xpath_data = whatsapp_ref.get()
            
            if not xpath_data or "Xpath001" not in xpath_data:
                raise Exception("Xpath001 not found in database")
            
            whatsapp_xpath001 = xpath_data["Xpath001"]
            print("WhatsApp Xpath001 fetched from database")
            return True
            
        except Exception as e:
            print(f"Error fetching WhatsApp Xpath001: {str(e)}")
            print("Retrying...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step9d_find_and_click_xpath():
    """Step 9d: Find and click WhatsApp Xpath001 (silently refreshes every 120s if not found)."""
    global driver, whatsapp_xpath001
    while True:
        try:
            start_time = time.time()
            
            while True:
                try:
                    element = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.XPATH, whatsapp_xpath001)))
                    element.click()
                    print("WhatsApp Xpath001 is clicked ready to search phone number")
                    return True
                    
                except (NoSuchElementException, TimeoutException):
                    if time.time() - start_time > 120:
                        # Silently refresh after 120 seconds
                        driver.refresh()
                        time.sleep(5)
                        break
                    time.sleep(1)
                    continue
                    
        except Exception as e:
            print(f"Error during Xpath001 search: {str(e)}")
            print("Retrying...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step9e_check_report_number_file():
    """Step 9e: Check for Report number file (exits if missing)."""
    report_file_path = REPORT_NUMBER_FILE
    if not os.path.isfile(report_file_path):
        print("Report number file is missing")
        close_chrome()
        print("Closing script.")
        exit()
    else:
        print("Report number file is available")
        return True

def step9f_verify_report_number():
    """Step 9f: Verify report number exists in the file (exits if missing)."""
    report_file_path = REPORT_NUMBER_FILE
    try:
        with open(report_file_path, 'r') as file:
            first_line = file.readline().strip()
            
            # Check if the line contains only digits (phone number)
            if first_line and first_line.isdigit():
                print(f"Report number is {first_line}")
                return True
            else:
                print("Report number is unavailable inside the Report number file")
                close_chrome()
                print("Closing script.")
                exit()
                
    except Exception as e:
        print(f"Error reading Report number file: {str(e)}")
        close_chrome()
        print("Closing script.")
        exit()

def step9g_paste_report_number():
    """Step 9g: Paste report number into WhatsApp search field (retries forever until success)."""
    report_file_path = REPORT_NUMBER_FILE
    
    while True:
        try:
            # Read the report number from file
            with open(report_file_path, 'r') as file:
                report_number = file.readline().strip()
            
            # Find search field
            search_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))
            
            # Clear field and input number directly
            search_field.clear()
            time.sleep(0.5)
            
            # Type number character by character
            search_field.send_keys(report_number)
            time.sleep(1)
            
            # Verify number was entered
            if report_number in search_field.text:
                print("Mobile number transferred from Report number file to WhatsApp phone number search field")
                return True
            else:
                raise Exception("Number not entered correctly")
                
        except Exception as e:
            print(f"Error during number input: {str(e)}")
            print("Retrying step9g...")
            time.sleep(2)

def step9h_wait_and_press_down():
    """Step 9h: Wait for stability and press down arrow key."""
    try:
        # Wait 10 seconds for stability
        print("Waiting 10 seconds for stability...")
        time.sleep(10)
        
        # Focus on the search field first
        search_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
        )
        search_field.click()
        time.sleep(1)
        
        # Press down arrow key using ActionChains for more reliability
        actions = ActionChains(driver)
        actions.send_keys(Keys.ARROW_DOWN)
        actions.perform()
        print("Down arrow key pressed successfully")
        
        # ADD ENTER KEY PRESS
        print("Waiting 1 second before pressing Enter...")
        time.sleep(1)
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        print("Enter key pressed successfully")
        
        return True
        
    except Exception as e:
        print(f"Error during step9h: {str(e)}")
        return False

def step9i_fetch_xpath002():
    """Step 9i: Fetch WhatsApp Xpath002 from Firebase (retries forever)."""
    global whatsapp_xpath002
    while True:
        try:
            if not initialize_firebase():
                raise Exception("Failed to initialize Firebase")
            
            whatsapp_ref = db.reference("WhatsApp/Xpath")
            xpath_data = whatsapp_ref.get()
            
            if not xpath_data or "Xpath002" not in xpath_data:
                raise Exception("Xpath002 not found in database")
            
            whatsapp_xpath002 = xpath_data["Xpath002"]
            print("WhatsApp Xpath002 fetched from database")
            return True
            
        except Exception as e:
            print(f"Error fetching WhatsApp Xpath002: {str(e)}")
            print("Retrying step9i...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step9j_find_and_click_xpath002():
    """Step 9j: Find and click WhatsApp Xpath002 with retry logic."""
    global driver, whatsapp_xpath002
    
    while True:
        try:
            # Start timer for 120 second timeout
            start_time = time.time()
            found = False
            
            while time.time() - start_time < 120:
                try:
                    # Search for Xpath002 every second
                    element = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.XPATH, whatsapp_xpath002)))
                    element.click()
                    print("Entered into Type a message field")
                    found = True
                    return True
                    
                except (NoSuchElementException, TimeoutException):
                    # Wait 1 second before trying again
                    time.sleep(1)
                    continue
            
            if not found:
                # If 120 seconds passed without finding Xpath002
                print("Xpath002 not found within 120 seconds - restarting process")
                close_chrome()
                return False
                
        except Exception as e:
            print(f"Error during Xpath002 search: {str(e)}")
            close_chrome()
            return False

def step9k_type_message():
    """Step 9k: Type the admin message with prefix based on step8 output."""
    global step8_message
    
    while True:
        try:
            # Only proceed if we have one of the two specific cases
            if "No more birthday today" in step8_message:
                message = "WhatsApp birthday bot - No more birthday today"
            elif "Warning - More than limit" in step8_message:
                # Extract the number from the warning message
                num = step8_message.split("limit ")[1].split(" ")[0]
                message = f"WhatsApp birthday bot - Warning! More than limit {num} people have birthday today it may consider as spam so drop the process"
            else:
                # For normal cases, just continue without typing
                print("Normal case - no admin message needed")
                return True
                
            # Find the message input field
            message_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']")))
            
            # Clear and type the message
            message_field.clear()
            time.sleep(0.5)
            message_field.send_keys(message)
            time.sleep(1)
            
            # Verify message was typed
            if message in message_field.text:
                print(f"Admin message typed: '{message}'")
                return True
            else:
                raise Exception("Admin message not typed correctly")
                
        except Exception as e:
            print(f"Error during admin message typing: {str(e)}")
            print("Restarting process from step9a...")
            close_chrome()
            return False

def step9l_wait_and_press_enter():
    """Step 9l: Wait 1 second, press Enter, and fetch Xpath003."""
    global whatsapp_xpath003
    
    try:
        # Wait 1 second for stability
        print("Waiting 1 second for stability...")
        time.sleep(1)
        
        # Press Enter key
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        print("Enter key pressed")
        
        # Fetch Xpath003 from Firebase (retry until success)
        while True:
            try:
                if not initialize_firebase():
                    raise Exception("Failed to initialize Firebase")
                
                whatsapp_ref = db.reference("WhatsApp/Xpath")
                xpath_data = whatsapp_ref.get()
                
                if not xpath_data or "Xpath003" not in xpath_data:
                    raise Exception("Xpath003 not found in database")
                
                whatsapp_xpath003 = xpath_data["Xpath003"]
                print("WhatsApp Xpath003 fetched from database")
                return True
                
            except Exception as e:
                print(f"Error fetching WhatsApp Xpath003: {str(e)}")
                print("Retrying step9l...")
                time.sleep(1)
                
    except Exception as e:
        print(f"Error during step9l: {str(e)}")
        return False

def step9m_check_message_status():
    """Step 9m: Check message status by monitoring Xpath003."""
    try:
        start_time = time.time()
        timeout = 120  # 120 seconds timeout
        check_interval = 1  # Check every 1 second
        
        while time.time() - start_time < timeout:
            try:
                # Check if Xpath003 exists
                WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, whatsapp_xpath003)))
                
                # If found, print countdown
                elapsed = int(time.time() - start_time)
                remaining = timeout - elapsed
                print(f"Message pending at {elapsed} seconds... (Remaining: {remaining}s)")
                time.sleep(check_interval)
                
            except (NoSuchElementException, TimeoutException):
                # Xpath003 disappeared - message sent
                print("WhatsApp Xpath003 is not available - message is sent")
                print("Closing browser in 5 seconds...")
                time.sleep(5)
                close_chrome()
                print("Script completed successfully.")
                exit()
        
        # If we get here, timeout was reached
        print("Xpath003 still present after 120 seconds - closing browser")
        close_chrome()
        return True  # Continue to step9n
        
    except Exception as e:
        print(f"Error during step9m: {str(e)}")
        close_chrome()
        return False

def step9n_open_whatsapp_web():
    """Step 9n: Open WhatsApp Web again."""
    global driver
    try:
        close_chrome()
        
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_PATH}")
        
        # Initialize WebDriver
        service = Service(executable_path=CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://web.whatsapp.com/")
        
        print("Entered WhatsApp Web")
        return True
        
    except Exception as e:
        print(f"Error opening WhatsApp Web: {str(e)}")
        return False

def step9o_check_database_key():
    """Step 9o: Check for database access key file."""
    while True:
        if not os.path.isfile(DATABASE_KEY):
            print("xpath manager client key is missing")
            close_chrome()
            print("Closing script.")
            exit()
        else:
            print("Database access key found")
            return True

def step9p_fetch_xpath001():
    """Step 9p: Fetch WhatsApp Xpath001 from Firebase (retries forever)."""
    global whatsapp_xpath001
    while True:
        try:
            if not initialize_firebase():
                raise Exception("Failed to initialize Firebase")
            
            whatsapp_ref = db.reference("WhatsApp/Xpath")
            xpath_data = whatsapp_ref.get()
            
            if not xpath_data or "Xpath001" not in xpath_data:
                raise Exception("Xpath001 not found in database")
            
            whatsapp_xpath001 = xpath_data["Xpath001"]
            print("WhatsApp Xpath001 fetched from database")
            return True
            
        except Exception as e:
            print(f"Error fetching WhatsApp Xpath001: {str(e)}")
            print("Retrying step9p...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step9q_find_and_click_xpath001():
    """Step 9q: Find and click WhatsApp Xpath001 with refresh logic."""
    global driver, whatsapp_xpath001
    
    while True:
        try:
            start_time = time.time()
            
            while True:
                try:
                    element = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.XPATH, whatsapp_xpath001)))
                    element.click()
                    print("WhatsApp Xpath001 is clicked ready to search phone number")
                    return True
                    
                except (NoSuchElementException, TimeoutException):
                    if time.time() - start_time > 120:
                        # Refresh after 120 seconds
                        driver.refresh()
                        print("Refreshing page after 120 seconds")
                        time.sleep(5)
                        break
                    time.sleep(1)
                    continue
                    
        except Exception as e:
            print(f"Error during Xpath001 search: {str(e)}")
            print("Retrying step9q...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step9r_check_report_number_file():
    """Step 9r: Check for Report number file."""
    report_file_path = os.path.join(BOTS_DIR, "Report number")
    if not os.path.isfile(report_file_path):
        print("Report number file is missing")
        close_chrome()
        print("Closing script.")
        exit()
    else:
        print("Report number file is available")
        return True

def step9s_verify_report_number():
    """Step 9s: Verify report number exists in the file."""
    report_file_path = os.path.join(BOTS_DIR, "venv", "report number")
    try:
        with open(report_file_path, 'r') as file:
            first_line = file.readline().strip()
            
            if first_line and first_line.isdigit():
                print(f"Report number is {first_line}")
                return True
            else:
                print("Report number is unavailable inside the Report number file")
                close_chrome()
                print("Closing script.")
                exit()
                
    except Exception as e:
        print(f"Error reading Report number file: {str(e)}")
        close_chrome()
        print("Closing script.")
        exit()

def step9t_paste_report_number():
    """Step 9t: Paste report number into WhatsApp search field."""
    report_file_path = os.path.join(BOTS_DIR, "venv", "report number")
    
    while True:
        try:
            # Read the report number from file
            with open(report_file_path, 'r') as file:
                report_number = file.readline().strip()
            
            # Find search field
            search_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))
            
            # Clear field and input number directly
            search_field.clear()
            time.sleep(0.5)
            
            # Type number character by character
            search_field.send_keys(report_number)
            time.sleep(1)
            
            # Verify number was entered
            if report_number in search_field.text:
                print("Mobile number transferred from Report number file to WhatsApp phone number search field")
                return True
            else:
                raise Exception("Number not entered correctly")
                
        except Exception as e:
            print(f"Error during number input: {str(e)}")
            print("Retrying step9t...")
            time.sleep(2)

def step9u_wait_and_press_down():
    """Step 9u: Wait for stability and press down arrow key."""
    try:
        # Wait 10 seconds for stability
        print("Waiting 10 seconds for stability...")
        time.sleep(10)
        
        # Focus on the search field first
        search_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
        )
        search_field.click()
        time.sleep(1)
        
        # Press down arrow key using ActionChains
        actions = ActionChains(driver)
        actions.send_keys(Keys.ARROW_DOWN)
        actions.perform()
        print("Down arrow key pressed successfully")
        
        # ADD ENTER KEY PRESS
        print("Waiting 1 second before pressing Enter...")
        time.sleep(1)
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        print("Enter key pressed successfully")
        
        return True
        
    except Exception as e:
        print(f"Error during step9u: {str(e)}")
        return False

def step10_check_and_delete_contact_file():
    """Step 10: Check and delete 'Today birthday list contact' file if it exists."""
    contact_file = CONTACT_FILE
    
    try:
        if os.path.exists(contact_file):
            os.remove(contact_file)
            print("Deleted existing 'Today birthday list contact' file")
        else:
            print("'Today birthday list contact' file not found (no need to delete)")
        return True
    except Exception as e:
        print(f"Error during file deletion: {str(e)}")
        return False

def step11_create_contact_file():
    """Step 11: Create new 'Today birthday list contact' file."""
    contact_file = CONTACT_FILE
    
    try:
        with open(contact_file, 'w') as f:
            pass  # Just create empty file
        print("Created new 'Today birthday list contact' file")
        return True
    except Exception as e:
        print(f"Error creating file: {str(e)}")
        return False

def step12_transfer_birthday_data(spreadsheet):
    """Step 12: Transfer today's birthday data to contact file with validation."""
    today = datetime.now()
    current_day_month = today.strftime("%d-%m")
    contact_file = CONTACT_FILE
    
    while True:
        try:
            # Get today's birthdays from spreadsheet
            worksheet = spreadsheet.worksheet("birthday list")
            all_records = worksheet.get_all_records()
            
            birthday_today = []
            skipped_count = 0
            
            for record in all_records:
                # Try different possible column names for Date of Birth
                dob = record.get('Date of Birth', '') or record.get('Date of birth', '') or record.get('DOB', '') or record.get('dob', '')
                
                # Check if date of birth matches today (accepts both DD-MM and DD-MM-YYYY formats)
                if not str(dob).startswith(current_day_month):
                    skipped_count += 1
                    continue
                
                # Try different possible column names for Country Code
                country_code = str(record.get('Country Code', '') or record.get('country code', '') or record.get('Country code', '') or record.get('Counrty Code', '')).strip()
                if not country_code or not country_code.isdigit():
                    skipped_count += 1
                    continue
                
                # Try different possible column names for WhatsApp Number
                whatsapp_num = str(record.get('WhatsApp Number', '') or record.get('Whatsapp Number', '') or record.get('whatsapp number', '') or record.get('Phone', '')).strip()
                if not whatsapp_num or not whatsapp_num.isdigit():
                    skipped_count += 1
                    continue
                
                # Try different possible column names for Name
                name = str(record.get('Name', '') or record.get('name', '')).strip()
                if not name:
                    name = "unavailable"
                
                # Handle different date formats
                dob_str = str(dob)
                if len(dob_str) == 5 and dob_str[2] == '-':  # DD-MM format
                    full_dob = dob_str + "-" + str(today.year)  # Add current year
                elif len(dob_str) == 10 and dob_str[2] == '-' and dob_str[5] == '-':  # DD-MM-YYYY format
                    full_dob = dob_str  # Use as-is
                else:
                    skipped_count += 1
                    continue
                
                # Format the WhatsApp URL
                whatsapp_url = f"https://wa.me/{country_code} {whatsapp_num}|"
                
                # Create the line to write
                line = f"{full_dob} {name} {whatsapp_url}\n"
                birthday_today.append(line)
            
            # Write to file
            with open(contact_file, 'w') as f:
                f.writelines(birthday_today)
            
            print(f"Transferred {len(birthday_today)} birthdays to Today birthday list contact")
            if skipped_count > 0:
                print(f"Skipped {skipped_count} records due to validation errors")
            return True
            
        except Exception as e:
            print(f"Error during data transfer: {str(e)}")
            print("Retrying step12...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step13_check_and_delete_wishes_file():
    """Step 13: Check and delete 'wishes' file if it exists."""
    wishes_file = WISHES_FILE
    
    try:
        if os.path.exists(wishes_file):
            os.remove(wishes_file)
            print("Deleted existing 'wishes' file")
            return "step14"  # File existed and was deleted
        else:
            print("'wishes' file not found")
            return "step15"  # File didn't exist, skip to step15
    except Exception as e:
        print(f"Error during wishes file handling: {str(e)}")
        return "step15"  # On error, continue with step15

def step14_create_wishes_file():
    """Step 14: Create new 'wishes' file."""
    wishes_file = WISHES_FILE
    
    try:
        with open(wishes_file, 'w') as f:
            pass  # Just create empty file
        print("Created new 'wishes' file")
        return True
    except Exception as e:
        print(f"Error creating wishes file: {str(e)}")
        return False

def step15_process_wishes_from_sheets(spreadsheet):
    """Step 15: Process wishes from Google Sheets, remove duplicates, and transfer to file."""
    wishes_file = WISHES_FILE
    
    while True:
        try:
            # Access the wishes worksheet
            worksheet = spreadsheet.worksheet("wishes")
            
            # Get all values from column A (skip header row)
            column_a_data = worksheet.col_values(1)
            
            if len(column_a_data) <= 1:  # Only header or empty
                print("No wishes data found in sheets")
                return True
                
            # Remove header and get only the wish text
            wishes = column_a_data[1:]
            
            # Remove duplicates while preserving order
            unique_wishes = []
            seen = set()
            for wish in wishes:
                if wish and wish not in seen:  # Skip empty and duplicates
                    unique_wishes.append(wish)
                    seen.add(wish)
            
            # Remove duplicate rows from the worksheet
            if len(wishes) != len(unique_wishes):
                # Clear existing data (keeping header)
                worksheet.batch_clear(["A2:A" + str(len(wishes) + 1)])
                
                # Write back unique wishes starting from row 2
                if unique_wishes:
                    cell_list = worksheet.range(f"A2:A{len(unique_wishes) + 1}")
                    for i, cell in enumerate(cell_list):
                        cell.value = unique_wishes[i]
                    worksheet.update_cells(cell_list)
            
            # Write unique wishes to file
            with open(wishes_file, 'w') as f:
                for wish in unique_wishes:
                    f.write(wish + "\n")
            
            print(f"Transferred {len(unique_wishes)} unique wishes to wishes file")
            return True
            
        except Exception as e:
            print(f"Error processing wishes from sheets: {str(e)}")
            print("Retrying step15...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)
                
def step16_open_whatsapp_web():
    """Step 16: Open WhatsApp Web in Chromium browser."""
    global driver
    try:
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_PATH}")
        
        # Initialize WebDriver
        service = Service(executable_path=CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://web.whatsapp.com/")
        
        print("Entered WhatsApp Web")
        return True
        
    except Exception as e:
        print(f"Error opening WhatsApp Web: {str(e)}")
        return False

def step17_check_database_key():
    """Step 17: Check for database access key file."""
    if not os.path.isfile(DATABASE_KEY):
        print("xpath manager client key is missing")
        close_chrome()
        print("Closing script.")
        exit()
    else:
        print("Database access key found")
        return True

def step18_fetch_xpath001():
    """Step 18: Fetch WhatsApp Xpath001 from Firebase (retries forever)."""
    global whatsapp_xpath001
    while True:
        try:
            if not initialize_firebase():
                raise Exception("Failed to initialize Firebase")
            
            whatsapp_ref = db.reference("WhatsApp/Xpath")
            xpath_data = whatsapp_ref.get()
            
            if not xpath_data or "Xpath001" not in xpath_data:
                raise Exception("Xpath001 not found in database")
            
            whatsapp_xpath001 = xpath_data["Xpath001"]
            print("WhatsApp Xpath001 fetched from database")
            return True
            
        except Exception as e:
            print(f"Error fetching WhatsApp Xpath001: {str(e)}")
            print("Retrying step18...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step19_find_and_click_xpath001():
    """Step 19: Find and click WhatsApp Xpath001 with refresh logic."""
    global driver, whatsapp_xpath001
    
    while True:
        try:
            start_time = time.time()
            
            while True:
                try:
                    # Search for Xpath001 every second
                    element = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.XPATH, whatsapp_xpath001)))
                    element.click()
                    print("WhatsApp Xpath001 is clicked ready to search phone number")
                    return True
                    
                except (NoSuchElementException, TimeoutException):
                    if time.time() - start_time > 120:
                        # Refresh after 120 seconds
                        driver.refresh()
                        print("Refreshing page after 120 seconds")
                        time.sleep(5)
                        break
                    time.sleep(1)
                    continue
                    
        except Exception as e:
            print(f"Error during Xpath001 search: {str(e)}")
            print("Retrying step19...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step20_check_contact_file():
    """Step 20: Check for Today birthday list contact file."""
    contact_file = CONTACT_FILE
    if not os.path.isfile(contact_file):
        print("Today birthday list contact file is missing")
        close_chrome()
        print("Closing script.")
        exit()
    else:
        print("Today birthday list contact file is available")
        return True

def check_and_reopen_browser_if_needed():
    """Check if browser is open, reopen if needed."""
    global driver
    
    try:
        # Try to get current URL to check if browser is still open
        driver.current_url
        print("Browser is already open")
        return True  # Browser is still open
    except:
        # Browser is closed, need to reopen
        print("Browser is closed, reopening WhatsApp Web...")
        if step16_open_whatsapp_web():
            if step17_check_database_key():
                if step18_fetch_xpath001():
                    if step19_find_and_click_xpath001():
                        print("Browser reopened successfully")
                        return True
        return False

def step21_process_contact_file():
    """Step 21: Process contact file and extract phone numbers."""
    global driver, extracted_phone_number
    
    contact_file = CONTACT_FILE
    
    while True:
        try:
            # Read the contact file
            with open(contact_file, 'r') as file:
                lines = file.readlines()
            
            # Check if file is empty
            if not lines:
                print("No valid data in Today birthday list contact file")
                close_chrome()
                exit()
            
            # Check if all wishes are sent
            all_wishes_sent = True
            for line in lines:
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) < 2 or not parts[1].strip():
                        all_wishes_sent = False
                        break
                else:
                    all_wishes_sent = False
                    break
            
            if all_wishes_sent:
                print("All wishes are sent")
                return "step35", None
            
            # Find phone number to process
            phone_number = None
            for line in lines:
                line_lower = line.lower()
                if "|" in line and "wa.me/" in line_lower:
                    parts = line.split("|")
                    if len(parts) < 2 or not parts[1].strip():
                        wa_me_index = line_lower.find("wa.me/")
                        if wa_me_index != -1:
                            after_wa_me = line[wa_me_index + 6:]
                            phone_end = after_wa_me.find("|")
                            if phone_end != -1:
                                phone_number = after_wa_me[:phone_end].strip()
                                break
                            else:
                                phone_number = after_wa_me.strip()
                                break
            
            if not phone_number:
                print("No phone number found in contact file")
                close_chrome()
                exit()
            
            # Clean and format phone number
            cleaned_phone = ''.join(c for c in phone_number if c.isdigit() or c == '+' or c == ' ')
            
            print(f"Extracted phone number: {cleaned_phone}")
            
            # Check if browser needs to be reopened
            if not check_and_reopen_browser_if_needed():
                raise Exception("Failed to reopen browser")
            
            # Find search field and input number
            search_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))
            
            search_field.clear()
            time.sleep(0.5)
            search_field.send_keys(cleaned_phone)
            time.sleep(1)
            
            # Verify number was entered
            entered_text = search_field.text.replace(" ", "")
            expected_text = cleaned_phone.replace(" ", "")
            
            if expected_text in entered_text:
                print("Mobile number transferred from Today birthday list contact to WhatsApp phone number search field")
                extracted_phone_number = cleaned_phone  # Store the phone number
                return True, cleaned_phone
            else:
                raise Exception("Number not entered correctly")
                
        except Exception as e:
            print(f"Error during step21: {str(e)}")
            print("Retrying step21...")
            time.sleep(2)

def step22_wait_and_check_internet():
    """Step 22: Wait 5 seconds and check internet connection."""
    print("Waiting 5 seconds...")
    time.sleep(5)
    
    if not check_internet():
        count = 1
        while not check_internet():
            print(f"Internet is not available waiting for connection {count}(s)...")
            time.sleep(1)
            count += 1
    
    print("Internet is available")
    return True

def step23_fetch_xpath004():
    """Step 23: Fetch WhatsApp Xpath004 from Firebase (retries forever)."""
    global whatsapp_xpath004
    while True:
        try:
            if not initialize_firebase():
                raise Exception("Failed to initialize Firebase")
            
            whatsapp_ref = db.reference("WhatsApp/Xpath")
            xpath_data = whatsapp_ref.get()
            
            if not xpath_data or "Xpath004" not in xpath_data:
                raise Exception("Xpath004 not found in database")
            
            whatsapp_xpath004 = xpath_data["Xpath004"]
            print("WhatsApp Xpath004 fetched from database")
            return True
            
        except Exception as e:
            print(f"Error fetching WhatsApp Xpath004: {str(e)}")
            print("Retrying step23...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step24_search_xpath004():
    """Step 24: Search for WhatsApp Xpath004 and handle results."""
    global driver, whatsapp_xpath004
    
    try:
        # Get current timestamp
        current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        
        # Try to find Xpath004 immediately
        try:
            element = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.XPATH, whatsapp_xpath004)))
            
            # If found, print message with current datetime
            print(f'"{current_time} No chats, contacts or messages found"')
            return "step24a", current_time
            
        except (NoSuchElementException, TimeoutException):
            # Xpath004 not found
            return "step25", current_time
            
    except Exception as e:
        print(f"Error during step24: {str(e)}")
        current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        return "step25", current_time  # On error, continue with step25

def step24a_close_browser():
    """Step 24a: Close the browser."""
    global driver
    try:
        close_chrome()
        print("Browser closed")
        return True
    except Exception as e:
        print(f"Error closing browser: {str(e)}")
        return False

def step24b_check_contact_file():
    """Step 24b: Check if Today birthday list contact file exists."""
    contact_file = CONTACT_FILE
    
    if not os.path.isfile(contact_file):
        print("Today birthday list contact file is missing")
        exit()
    else:
        print("Today birthday list contact file is available")
        return True

def step24c_update_contact_file(phone_number, timestamp_message):
    """Step 24c: Update the contact file with the timestamp and status."""
    contact_file = CONTACT_FILE
    
    try:
        # Read the contact file
        with open(contact_file, 'r') as file:
            lines = file.readlines()
        
        # Find the line containing the phone number with | symbol
        search_pattern = f"{phone_number}|"
        line_found = None
        line_index = -1
        
        for i, line in enumerate(lines):
            if search_pattern in line:
                line_found = line
                line_index = i
                break
        
        if line_found is None:
            print(f"Line with {search_pattern} not found in contact file")
            return False
        
        # Add timestamp at the beginning and status at the end
        updated_line = f"{timestamp_message} {line_found.strip()} No chats, contacts or messages found\n"
        lines[line_index] = updated_line
        
        # Write the updated content back to the file
        with open(contact_file, 'w') as file:
            file.writelines(lines)
        
        print("Data updated on Today birthday list contact")
        return True
        
    except Exception as e:
        print(f"Error updating contact file: {str(e)}")
        return False

def step25_wait_and_press_down():
    """Step 25: Wait 10 seconds for stability and press down arrow key."""
    try:
        # Wait 10 seconds for stability
        print("Waiting 10 seconds for stability...")
        time.sleep(10)
        
        # Press down arrow key using ActionChains
        actions = ActionChains(driver)
        actions.send_keys(Keys.ARROW_DOWN)
        actions.perform()
        print("Down arrow key pressed successfully")
        
        # ADD ENTER KEY PRESS
        print("Waiting 1 second before pressing Enter...")
        time.sleep(1)
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        print("Enter key pressed successfully")
        
        return True
        
    except Exception as e:
        print(f"Error during step25: {str(e)}")
        return False

def step26_fetch_xpath002():
    """Step 26: Fetch WhatsApp Xpath002 from Firebase (retries forever)."""
    global whatsapp_xpath002
    while True:
        try:
            if not initialize_firebase():
                raise Exception("Failed to initialize Firebase")
            
            whatsapp_ref = db.reference("WhatsApp/Xpath")
            xpath_data = whatsapp_ref.get()
            
            if not xpath_data or "Xpath002" not in xpath_data:
                raise Exception("Xpath002 not found in database")
            
            whatsapp_xpath002 = xpath_data["Xpath002"]
            print("WhatsApp Xpath002 fetched from database")
            return True
            
        except Exception as e:
            print(f"Error fetching WhatsApp Xpath002: {str(e)}")
            print("Retrying step26...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step27_find_and_click_xpath002():
    """Step 27: Find and click WhatsApp Xpath002 with timeout."""
    global driver, whatsapp_xpath002
    
    try:
        # Start timer for 120 second timeout
        start_time = time.time()
        
        while time.time() - start_time < 120:
            try:
                # Search for Xpath002 every second
                element = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, whatsapp_xpath002)))
                element.click()
                print("Entered into Type a message field")
                return True
                
            except (NoSuchElementException, TimeoutException):
                # Wait 1 second before trying again
                time.sleep(1)
                continue
        
        # If 120 seconds passed without finding Xpath002
        print("Xpath002 not found within 120 seconds - closing browser")
        close_chrome()
        return False
        
    except Exception as e:
        print(f"Error during step27: {str(e)}")
        close_chrome()
        return False

def step28_check_wishes_file():
    """Step 28: Check wishes file exists and has content."""
    wishes_file = WISHES_FILE
    
    # Check if file exists
    if not os.path.isfile(wishes_file):
        print("wishes file is missing")
        close_chrome()
        print("Closing script.")
        exit()
    
    # Check if file has content
    try:
        with open(wishes_file, 'r') as file:
            wishes = file.readlines()
        
        # Remove empty lines and whitespace
        wishes = [wish.strip() for wish in wishes if wish.strip()]
        
        if not wishes:
            print("No more wishes inside the Wishes file")
            close_chrome()
            print("Closing script.")
            exit()
        
        print(f"Found {len(wishes)} wishes in wishes file")
        return wishes
        
    except Exception as e:
        print(f"Error reading wishes file: {str(e)}")
        close_chrome()
        print("Closing script.")
        exit()

def step29_type_random_wish(wishes):
    """Step 29: Type random wish into message field (using direct typing)."""
    try:
        # Select a random wish
        import random
        random_wish = random.choice(wishes)
        print(f"Selected wish: {random_wish[:1000]}...")  # Show first 1000 chars
        
        # Find the message input field
        message_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']")))
        
        # Clear and type the message character by character (like mobile number transfer)
        message_field.clear()
        time.sleep(0.5)
        
        # Type the wish character by character (same method as mobile number transfer)
        message_field.send_keys(random_wish)
        time.sleep(1)
        
        # Verify message was typed
        if random_wish in message_field.text:
            print("wishes message is typed")
            return True, random_wish  # Return both success status and the wish
        else:
            raise Exception("Wish not typed correctly")
            
    except Exception as e:
        print(f"Error during step29: {str(e)}")
        return False, None

def step30_wait_and_press_enter():
    """Step 30: Wait 1 second and press Enter key."""
    try:
        # Wait 1 second for stability
        print("Waiting 1 second for stability...")
        time.sleep(1)
        
        # Press Enter key
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        print("Enter key pressed")
        return True
        
    except Exception as e:
        print(f"Error during step30: {str(e)}")
        return False

def step31_fetch_xpath003():
    """Step 31: Fetch WhatsApp Xpath003 from Firebase (retries forever)."""
    global whatsapp_xpath003
    
    while True:
        try:
            if not initialize_firebase():
                raise Exception("Failed to initialize Firebase")
            
            whatsapp_ref = db.reference("WhatsApp/Xpath")
            xpath_data = whatsapp_ref.get()
            
            if not xpath_data or "Xpath003" not in xpath_data:
                raise Exception("Xpath003 not found in database")
            
            whatsapp_xpath003 = xpath_data["Xpath003"]
            print("WhatsApp Xpath003 fetched from database")
            return True
            
        except Exception as e:
            print(f"Error fetching WhatsApp Xpath003: {str(e)}")
            print("Retrying step31...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step32_check_message_status():
    """Step 32: Check message status by monitoring Xpath003."""
    try:
        # Wait 5 seconds first
        print("Waiting 5 seconds before checking message status...")
        time.sleep(5)
        
        start_time = time.time()
        timeout = 120  # 120 seconds timeout
        check_interval = 1  # Check every 1 second
        current_second = 0
        
        while time.time() - start_time < timeout:
            try:
                # Check if Xpath003 exists
                WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, whatsapp_xpath003)))
                
                # If found, update the count on the same line
                current_second = int(time.time() - start_time) + 1
                print(f"\rMessage pending at {current_second}(s)", end="", flush=True)
                
                time.sleep(check_interval)
                
            except (NoSuchElementException, TimeoutException):
                # Xpath003 disappeared - message sent
                current_datetime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                print(f"\nWhatsApp Xpath003 is not available - message is sent at {current_datetime}")
                print("Closing browser...")
                close_chrome()
                return "step36", current_datetime  # Return both next step and timestamp
        
        # If we get here, timeout was reached
        current_datetime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        print(f"\nXpath003 still present after {current_second} seconds at {current_datetime} - closing browser")
        close_chrome()
        return "step33", current_datetime  # Return both next step and timestamp
        
    except Exception as e:
        current_datetime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        print(f"\nError during step32 at {current_datetime}: {str(e)}")
        close_chrome()
        return "step33", current_datetime

def step33_redo_steps_16_to_22():
    """Step 33: Redo steps 16 to 22 only."""
    print("\n=== Step 33: Redoing steps 16 to 22 ===")
    
    # Step 16: Open WhatsApp Web
    if not step16_open_whatsapp_web():
        return False
    
    # Step 17: Check database key
    if not step17_check_database_key():
        return False
    
    # Step 18: Fetch Xpath001
    if not step18_fetch_xpath001():
        return False
    
    # Step 19: Find and click Xpath001
    if not step19_find_and_click_xpath001():
        return False
    
    # Step 20: Check contact file
    if not step20_check_contact_file():
        return False
    
    # Step 21: Process contact file
    result, phone_number = step21_process_contact_file()
    if result != True:
        return False
    
    # Step 22: Wait and check internet
    if not step22_wait_and_check_internet():
        return False
    
    return "step34"  # Continue with step34

def step34_wait_and_press_down():
    """Step 34: Wait 10 seconds for stability and press down arrow key."""
    try:
        # Wait 10 seconds for stability
        print("Waiting 10 seconds for stability...")
        time.sleep(10)
        
        # Press down arrow key using ActionChains
        actions = ActionChains(driver)
        actions.send_keys(Keys.ARROW_DOWN)
        actions.perform()
        print("Down arrow key pressed successfully")
        
        # ADD ENTER KEY PRESS
        print("Waiting 1 second before pressing Enter...")
        time.sleep(1)
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        print("Enter key pressed successfully")
        
        return True
        
    except Exception as e:
        print(f"Error during step34: {str(e)}")
        return False

def step35_all_wishes_sent():
    """Step 35: All wishes are sent - final step."""
    print("\n=== Step 35: All wishes are sent ===")
    close_chrome()
    print("Script completed successfully.")
    exit()

def step36_check_contact_file():
    """Step 36: Check if Today birthday list contact file exists."""
    contact_file = CONTACT_FILE
    
    if not os.path.isfile(contact_file):
        print("Today birthday list contact file is missing")
        close_chrome()
        print("Closing script.")
        exit()
    else:
        print("Today birthday list contact file is available")
        return True

def step37_update_contact_file(phone_number, timestamp, wish_message):
    """Step 37: Update the contact file with timestamp and wish message."""
    contact_file = CONTACT_FILE
    
    try:
        # Read the contact file
        with open(contact_file, 'r') as file:
            lines = file.readlines()
        
        # Find the line containing the phone number with | symbol
        search_pattern = f"{phone_number}|"
        line_found = None
        line_index = -1
        
        for i, line in enumerate(lines):
            if search_pattern in line:
                line_found = line
                line_index = i
                break
        
        if line_found is None:
            print(f"Line with {search_pattern} not found in contact file")
            return False
        
        # Extract the original content (remove any existing timestamp or wish)
        original_content = line_found.strip()
        
        # Add timestamp at the beginning and wish message at the end
        updated_line = f"{timestamp} {original_content} {wish_message}\n"
        lines[line_index] = updated_line
        
        # Write the updated content back to the file
        with open(contact_file, 'w') as file:
            file.writelines(lines)
        
        print("Data updated on Today birthday list contact")
        return True
        
    except Exception as e:
        print(f"Error updating contact file: {str(e)}")
        return False

def step36_process_next_contact():
    """Step 36: Process the next contact after successful message sending."""
    global extracted_phone_number
    
    try:
        contact_file = os.path.join(WHATSAPP_BOT_DIR, "Today birthday list contact")
        
        # Read the contact file
        with open(contact_file, 'r') as file:
            lines = file.readlines()
        
        # Find and mark the current phone number as processed
        phone_found = False
        for i, line in enumerate(lines):
            if extracted_phone_number.replace(" ", "") in line.replace(" ", ""):
                # Add a marker to indicate this contact has been processed
                if "|" not in line:
                    lines[i] = line.strip() + "|processed\n"
                    phone_found = True
                break
        
        if not phone_found:
            print(f"Phone number {extracted_phone_number} not found in contact file")
            return "step20"
        
        # Write the updated content back to the file
        with open(contact_file, 'w') as file:
            file.writelines(lines)
        
        print(f"Marked {extracted_phone_number} as processed")
        extracted_phone_number = None  # Reset for next contact
        
        # Check if all contacts have been processed
        all_processed = True
        for line in lines:
            if "|" not in line and line.strip():  # If any line doesn't have the processed marker
                all_processed = False
                break
        
        if all_processed:
            print("All contacts have been processed successfully!")
            return "step35"
        else:
            print("Moving to next contact...")
            return "step20"  # Continue with next contact
        
    except Exception as e:
        print(f"Error during step36: {str(e)}")
        return "step20"  # Continue with next contact even on error

def step35_transfer_to_sheets():
    """Step 35: Transfer data to Google Sheets 'sent message' sheet."""
    while True:
        try:
            # Initialize spreadsheet connection
            scope = ["https://spreadsheets.google.com/feeds", 
                    "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(SPREADSHEET_KEY, scope)
            client = gspread.authorize(creds)
            spreadsheet = client.open(SPREADSHEET_NAME)
            
            # Access the "sent message" worksheet
            worksheet = spreadsheet.worksheet("sent message")
            print("Reached sheets ready to upload")
            return worksheet
            
        except Exception as e:
            print(f"Error accessing Google Sheets: {str(e)}")
            print("Retrying step35...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step38_process_contact_data(worksheet):
    """Step 38: Process contact file data and transfer to Google Sheets."""
    contact_file = os.path.join(WHATSAPP_BOT_DIR, "Today birthday list contact")
    
    while True:
        try:
            # Read the contact file
            with open(contact_file, 'r') as file:
                lines = file.readlines()
            
            # Prepare data for Google Sheets
            data_to_append = []
            
            for line in lines:
                if not line.strip():
                    continue
                    
                try:
                    # Extract datetime (first 19 characters)
                    datetime_str = line[:19].strip()
                    
                    # Extract date of birth (next 10 characters after datetime)
                    dob_start = 20  # After first space
                    dob_end = dob_start + 10
                    dob_str = line[dob_start:dob_end].strip()
                    
                    # Extract name (between DOB and https://wa.me/)
                    name_start = dob_end + 1
                    wa_me_index = line.find("https://wa.me/")
                    name_str = line[name_start:wa_me_index].strip()
                    
                    # Extract country code and WhatsApp number
                    after_wa_me = line[wa_me_index + 14:]  # After "https://wa.me/"
                    pipe_index = after_wa_me.find("|")
                    
                    if pipe_index == -1:
                        continue
                        
                    # Get the full string before the pipe
                    before_pipe = after_wa_me[:pipe_index].strip()
                    
                    # Find the last space to separate country code and WhatsApp number
                    last_space_index = before_pipe.rfind(" ")
                    
                    if last_space_index == -1:
                        # No space found, treat entire string as WhatsApp number
                        whatsapp_num = before_pipe
                        country_code = ""
                    else:
                        # Extract WhatsApp number (after last space)
                        whatsapp_num = before_pipe[last_space_index+1:].strip()
                        
                        # Extract country code (before last space)
                        country_code = before_pipe[:last_space_index].strip()
                    
                    # Extract sent message (after pipe)
                    after_pipe = after_wa_me[pipe_index+1:].strip()
                    
                    # Append data to list
                    data_to_append.append([
                        datetime_str,    # Column A: Date-Time
                        dob_str,        # Column B: Date of Birth
                        name_str,       # Column C: Name
                        country_code,   # Column D: Country Code
                        whatsapp_num,   # Column E: WhatsApp Number
                        after_pipe      # Column F: Sent Message
                    ])
                    
                except Exception as e:
                    print(f"Error parsing line: {line.strip()} - {str(e)}")
                    continue
            
            # Append data to Google Sheets (skip header row)
            if data_to_append:
                # Get the next available row
                next_row = len(worksheet.get_all_values()) + 1
                
                # Update the worksheet
                cell_range = f"A{next_row}:F{next_row + len(data_to_append) - 1}"
                cell_list = worksheet.range(cell_range)
                
                # Fill the cells with data
                cell_index = 0
                for row in data_to_append:
                    for value in row:
                        cell_list[cell_index].value = value
                        cell_index += 1
                
                worksheet.update_cells(cell_list)
                print("All data transferred to sheets")
            else:
                print("No data to transfer")
                
            return True
            
        except Exception as e:
            print(f"Error during step38: {str(e)}")
            print("Retrying step38...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)
                
def step39_check_whatsapp_report():
    """Step 39: Check and create/delete WhatsApp report file."""
    whatsapp_report_file = WHATSAPP_REPORT_FILE
    
    try:
        if os.path.exists(whatsapp_report_file):
            os.remove(whatsapp_report_file)
            print("Deleted existing WhatsApp report file")
        
        # Create new file
        with open(whatsapp_report_file, 'w') as f:
            pass
        print("Created new WhatsApp report file")
        return True
        
    except Exception as e:
        print(f"Error during step39: {str(e)}")
        return False

def step40_process_report():
    """Step 40: Process Today birthday list contact and create WhatsApp report."""
    contact_file = CONTACT_FILE
    whatsapp_report_file = WHATSAPP_REPORT_FILE
    
    try:
        # Check if contact file exists
        if not os.path.isfile(contact_file):
            print("Today birthday list contact file is missing")
            exit()
        
        # Read the contact file
        with open(contact_file, 'r') as file:
            lines = file.readlines()
        
        # Count total lines and keyword occurrences
        total_lines = len(lines)
        keyword_count = 0
        
        for line in lines:
            if "No chats, contacts or messages found" in line:
                keyword_count += 1
        
        # Calculate sent messages
        sent_messages = total_lines - keyword_count
        
        # Get current date
        current_date = datetime.now().strftime("%d-%m-%Y")
        
        # Create report content
        report_content = f"""WhatsApp birthday bot({current_date})

Today birthday(s)  = {total_lines}
Contact not found = {keyword_count}
-----------------------
sent message       = {sent_messages}
-----------------------"""
        
        # Write to WhatsApp report file
        with open(whatsapp_report_file, 'w') as file:
            file.write(report_content)
        
        print("WhatsApp report is ready")
        return True
        
    except Exception as e:
        print(f"Error during step40: {str(e)}")
        return False

def step41_open_whatsapp_web():
    """Step 41: Open WhatsApp Web in Chromium browser."""
    global driver
    try:
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_PATH}")
        
        # Initialize WebDriver
        service = Service(executable_path=CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://web.whatsapp.com/")
        
        print("Entered WhatsApp Web")
        return True
        
    except Exception as e:
        print(f"Error opening WhatsApp Web: {str(e)}")
        return False

def step42_check_database_key():
    """Step 42: Check for database access key file."""
    if not os.path.isfile(DATABASE_KEY):
        print("xpath manager client key is missing")
        close_chrome()
        print("Closing script.")
        exit()
    else:
        print("Database access key found")
        return True

def step43_fetch_xpath001():
    """Step 43: Fetch WhatsApp Xpath001 from Firebase (retries forever)."""
    global whatsapp_xpath001
    while True:
        try:
            if not initialize_firebase():
                raise Exception("Failed to initialize Firebase")
            
            whatsapp_ref = db.reference("WhatsApp/Xpath")
            xpath_data = whatsapp_ref.get()
            
            if not xpath_data or "Xpath001" not in xpath_data:
                raise Exception("Xpath001 not found in database")
            
            whatsapp_xpath001 = xpath_data["Xpath001"]
            print("WhatsApp Xpath001 fetched from database")
            return True
            
        except Exception as e:
            print(f"Error fetching WhatsApp Xpath001: {str(e)}")
            print("Retrying step43...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step44_find_and_click_xpath001():
    """Step 44: Find and click WhatsApp Xpath001 with refresh logic."""
    global driver, whatsapp_xpath001
    
    while True:
        try:
            start_time = time.time()
            
            while True:
                try:
                    # Search for Xpath001 every second
                    element = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.XPATH, whatsapp_xpath001)))
                    element.click()
                    print("WhatsApp Xpath001 is clicked ready to search phone number")
                    return True
                    
                except (NoSuchElementException, TimeoutException):
                    if time.time() - start_time > 120:
                        # Refresh after 120 seconds
                        driver.refresh()
                        print("Refreshing page after 120 seconds")
                        time.sleep(5)
                        break
                    time.sleep(1)
                    continue
                    
        except Exception as e:
            print(f"Error during Xpath001 search: {str(e)}")
            print("Retrying step44...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step45_check_report_number_file():
    """Step 45: Check for Report number file."""
    report_file_path = REPORT_NUMBER_FILE
    if not os.path.isfile(report_file_path):
        print("Report number file is missing")
        close_chrome()
        print("Closing script.")
        exit()
    else:
        print("Report number file is available")
        return True

def step46_verify_report_number():
    """Step 46: Verify report number exists in the file."""
    report_file_path = REPORT_NUMBER_FILE
    try:
        with open(report_file_path, 'r') as file:
            first_line = file.readline().strip()
            
            if first_line and first_line.isdigit():
                print(f"Report number is {first_line}")
                return True
            else:
                print("Report number is unavailable inside the Report number file")
                close_chrome()
                print("Closing script.")
                exit()
                
    except Exception as e:
        print(f"Error reading Report number file: {str(e)}")
        close_chrome()
        print("Closing script.")
        exit()

def step47_paste_report_number():
    """Step 47: Paste report number into WhatsApp search field."""
    report_file_path = REPORT_NUMBER_FILE
    
    while True:
        try:
            # Read the report number from file
            with open(report_file_path, 'r') as file:
                report_number = file.readline().strip()
            
            # Find search field
            search_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))
            
            # Clear field and input number directly
            search_field.clear()
            time.sleep(0.5)
            
            # Type number character by character
            search_field.send_keys(report_number)
            time.sleep(1)
            
            # Verify number was entered
            if report_number in search_field.text:
                print("Mobile number transferred from Report number file to WhatsApp phone number search field")
                return True
            else:
                raise Exception("Number not entered correctly")
                
        except Exception as e:
            print(f"Error during number input: {str(e)}")
            print("Retrying step47...")
            time.sleep(2)

def step48_wait_and_press_down():
    """Step 48: Wait 10 seconds for stability and press down arrow key."""
    try:
        # Wait 10 seconds for stability
        print("Waiting 10 seconds for stability...")
        time.sleep(10)
        
        # Press down arrow key using ActionChains
        actions = ActionChains(driver)
        actions.send_keys(Keys.ARROW_DOWN)
        actions.perform()
        print("Down arrow key pressed successfully")
        
        # ADD ENTER KEY PRESS
        print("Waiting 1 second before pressing Enter...")
        time.sleep(1)
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        print("Enter key pressed successfully")
        
        return True
        
    except Exception as e:
        print(f"Error during step48: {str(e)}")
        return False

def step49_fetch_xpath002():
    """Step 49: Fetch WhatsApp Xpath002 from Firebase (retries forever)."""
    global whatsapp_xpath002
    while True:
        try:
            if not initialize_firebase():
                raise Exception("Failed to initialize Firebase")
            
            whatsapp_ref = db.reference("WhatsApp/Xpath")
            xpath_data = whatsapp_ref.get()
            
            if not xpath_data or "Xpath002" not in xpath_data:
                raise Exception("Xpath002 not found in database")
            
            whatsapp_xpath002 = xpath_data["Xpath002"]
            print("WhatsApp Xpath002 fetched from database")
            return True
            
        except Exception as e:
            print(f"Error fetching WhatsApp Xpath002: {str(e)}")
            print("Retrying step49...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step50_find_and_click_xpath002():
    """Step 50: Find and click WhatsApp Xpath002 with timeout."""
    global driver, whatsapp_xpath002
    
    while True:
        try:
            # Start timer for 120 second timeout
            start_time = time.time()
            
            while time.time() - start_time < 120:
                try:
                    # Search for Xpath002 every second
                    element = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.XPATH, whatsapp_xpath002)))
                    element.click()
                    print("Entered into Type a message field")
                    return True
                    
                except (NoSuchElementException, TimeoutException):
                    # Wait 1 second before trying again
                    time.sleep(1)
                    continue
            
            # If 120 seconds passed without finding Xpath002
            print("Xpath002 not found within 120 seconds - restarting from step41")
            close_chrome()
            return False  # This will restart from step41
            
        except Exception as e:
            print(f"Error during step50: {str(e)}")
            close_chrome()
            return False

def step51_transfer_report_content():
    """Step 51: Transfer WhatsApp report content to message field as SINGLE MESSAGE."""
    whatsapp_report_file = WHATSAPP_REPORT_FILE
    
    # Check if file exists
    if not os.path.isfile(whatsapp_report_file):
        print("WhatsApp report is missing")
        close_chrome()
        print("Closing script.")
        exit()
    
    try:
        # Read the report content
        with open(whatsapp_report_file, 'r') as file:
            content = file.read()
        
        # Find the message input field
        message_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']")))
        
        # Clear the field first
        message_field.clear()
        time.sleep(0.5)
        
        # Send the entire content as a single message
        # Use SHIFT+ENTER for newlines within the same message
        lines = content.split('\n')
        for i, line in enumerate(lines):
            message_field.send_keys(line)
            if i < len(lines) - 1:  # Add newline for all but last line
                message_field.send_keys(Keys.SHIFT + Keys.ENTER)
        
        time.sleep(1)
        
        # Verify content was typed (check first part to avoid long comparisons)
        if content[:100] in message_field.text:
            print("WhatsApp report content transferred as single message")
            return True
        else:
            raise Exception("Report content not transferred correctly")
            
    except Exception as e:
        print(f"Error during step51: {str(e)}")
        return False

def step52_wait_and_press_enter():
    """Step 52: Wait 1 second, press Enter, and fetch Xpath003."""
    global whatsapp_xpath003
    
    try:
        # Wait 1 second for stability
        print("Waiting 1 second for stability...")
        time.sleep(1)
        
        # Press Enter key
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        print("Enter key pressed")
        
        # Fetch Xpath003 from Firebase (retry until success)
        while True:
            try:
                if not initialize_firebase():
                    raise Exception("Failed to initialize Firebase")
                
                whatsapp_ref = db.reference("WhatsApp/Xpath")
                xpath_data = whatsapp_ref.get()
                
                if not xpath_data or "Xpath003" not in xpath_data:
                    raise Exception("Xpath003 not found in database")
                
                whatsapp_xpath003 = xpath_data["Xpath003"]
                print("WhatsApp Xpath003 fetched from database")
                return True
                
            except Exception as e:
                print(f"Error fetching WhatsApp Xpath003: {str(e)}")
                print("Retrying step52...")
                time.sleep(1)
                
    except Exception as e:
        print(f"Error during step52: {str(e)}")
        return False

def step53_check_message_status():
    """Step 53: Check message status by monitoring Xpath003."""
    try:
        # Wait 5 seconds first
        print("Waiting 5 seconds before checking message status...")
        time.sleep(5)
        
        start_time = time.time()
        timeout = 120  # 120 seconds timeout
        check_interval = 1  # Check every 1 second
        current_second = 0
        
        while time.time() - start_time < timeout:
            try:
                # Check if Xpath003 exists
                WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, whatsapp_xpath003)))
                
                # If found, update the count on the same line
                current_second = int(time.time() - start_time) + 1
                print(f"\rMessage pending at {current_second}(s)", end="", flush=True)
                
                time.sleep(check_interval)
                
            except (NoSuchElementException, TimeoutException):
                # Xpath003 disappeared - message sent
                print("\nWhatsApp Xpath003 is not available - message is sent")
                print("Closing browser in 5 seconds...")
                time.sleep(5)
                close_chrome()
                print("Script completed successfully.")
                exit()
        
        # If we get here, timeout was reached
        print("\nXpath003 still present after 120 seconds - closing browser")
        close_chrome()
        return True  # Continue with step54
        
    except Exception as e:
        print(f"\nError during step53: {str(e)}")
        close_chrome()
        return False

def step54_open_whatsapp_web():
    """Step 54: Open WhatsApp Web in Chromium browser."""
    global driver
    try:
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_PATH}")
        
        # Initialize WebDriver
        service = Service(executable_path=CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://web.whatsapp.com/")
        
        print("Entered WhatsApp Web")
        return True
        
    except Exception as e:
        print(f"Error opening WhatsApp Web: {str(e)}")
        return False

def step55_check_database_key():
    """Step 55: Check for database access key file."""
    if not os.path.isfile(DATABASE_KEY):
        print("xpath manager client key is missing")
        close_chrome()
        print("Closing script.")
        exit()
    else:
        print("Database access key found")
        return True

def step56_fetch_xpath001():
    """Step 56: Fetch WhatsApp Xpath001 from Firebase (retries forever)."""
    global whatsapp_xpath001
    while True:
        try:
            if not initialize_firebase():
                raise Exception("Failed to initialize Firebase")
            
            whatsapp_ref = db.reference("WhatsApp/Xpath")
            xpath_data = whatsapp_ref.get()
            
            if not xpath_data or "Xpath001" not in xpath_data:
                raise Exception("Xpath001 not found in database")
            
            whatsapp_xpath001 = xpath_data["Xpath001"]
            print("WhatsApp Xpath001 fetched from database")
            return True
            
        except Exception as e:
            print(f"Error fetching WhatsApp Xpath001: {str(e)}")
            print("Retrying step56...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step57_find_and_click_xpath001():
    """Step 57: Find and click WhatsApp Xpath001 with refresh logic."""
    global driver, whatsapp_xpath001
    
    while True:
        try:
            start_time = time.time()
            
            while True:
                try:
                    # Search for Xpath001 every second
                    element = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.XPATH, whatsapp_xpath001)))
                    element.click()
                    print("WhatsApp Xpath001 is clicked ready to search phone number")
                    return True
                    
                except (NoSuchElementException, TimeoutException):
                    if time.time() - start_time > 120:
                        # Refresh after 120 seconds
                        driver.refresh()
                        print("Refreshing page after 120 seconds")
                        time.sleep(5)
                        break
                    time.sleep(1)
                    continue
                    
        except Exception as e:
            print(f"Error during Xpath001 search: {str(e)}")
            print("Retrying step57...")
            if not check_internet():
                wait_for_internet()
            else:
                time.sleep(1)

def step58_check_report_number_file():
    """Step 58: Check for Report number file."""
    report_file_path = REPORT_NUMBER_FILE
    if not os.path.isfile(report_file_path):
        print("Report number file is missing")
        close_chrome()
        print("Closing script.")
        exit()
    else:
        print("Report number file is available")
        return True

def step59_verify_report_number():
    """Step 59: Verify report number exists in the file."""
    report_file_path = REPORT_NUMBER_FILE
    try:
        with open(report_file_path, 'r') as file:
            first_line = file.readline().strip()
            
            if first_line and first_line.isdigit():
                print(f"Report number is {first_line}")
                return True
            else:
                print("Report number is unavailable inside the Report number file")
                close_chrome()
                print("Closing script.")
                exit()
                
    except Exception as e:
        print(f"Error reading Report number file: {str(e)}")
        close_chrome()
        print("Closing script.")
        exit()

def step60_paste_report_number():
    """Step 60: Paste report number into WhatsApp search field."""
    report_file_path = REPORT_NUMBER_FILE
    
    while True:
        try:
            # Read the report number from file
            with open(report_file_path, 'r') as file:
                report_number = file.readline().strip()
            
            # Find search field
            search_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))
            
            # Clear field and input number directly
            search_field.clear()
            time.sleep(0.5)
            
            # Type number character by character
            search_field.send_keys(report_number)
            time.sleep(1)
            
            # Verify number was entered
            if report_number in search_field.text:
                print("Mobile number transferred from Report number file to WhatsApp phone number search field")
                return True
            else:
                raise Exception("Number not entered correctly")
                
        except Exception as e:
            print(f"Error during number input: {str(e)}")
            print("Retrying step60...")
            time.sleep(2)

def step61_wait_and_press_down():
    """Step 61: Wait 10 seconds for stability and press down arrow key."""
    try:
        # Wait 10 seconds for stability
        print("Waiting 10 seconds for stability...")
        time.sleep(10)
        
        # Press down arrow key using ActionChains
        actions = ActionChains(driver)
        actions.send_keys(Keys.ARROW_DOWN)
        actions.perform()
        print("Down arrow key pressed successfully")
        
        # ADD ENTER KEY PRESS
        print("Waiting 1 second before pressing Enter...")
        time.sleep(1)
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        print("Enter key pressed successfully")
        
        return True
        
    except Exception as e:
        print(f"Error during step61: {str(e)}")
        return False

# Main execution loop
if __name__ == "__main__":
    # Global variable to store extracted phone number
    extracted_phone_number = None
    skip_to_step31 = False
    selected_wish_stored = None
    
    # Main execution loop
    while True:
        try:
            # Check if we need to skip to step31
            if skip_to_step31:
                print("\n=== Step 31: Fetching Xpath003 ===")
                if step31_fetch_xpath003():
                    print("\n=== Step 32: Checking message status ===")
                    next_step_after_32, timestamp = step32_check_message_status()
                    
                    if next_step_after_32 == "step36":
                        print("\n=== Step 36: Checking contact file ===")
                        if step36_check_contact_file():
                            print("\n=== Step 37: Updating contact file ===")
                            if step37_update_contact_file(extracted_phone_number, timestamp, selected_wish_stored):
                                next_step = step36_process_next_contact()
                                if next_step == "step35":
                                    # ADD STEP 35 HERE
                                    print("\n=== Step 35: Transferring data to Google Sheets ===")
                                    worksheet = step35_transfer_to_sheets()
                                    
                                    # ADD STEP 38 HERE
                                    print("\n=== Step 38: Processing contact data ===")
                                    if step38_process_contact_data(worksheet):
                                        # ADD STEP 39 HERE
                                        print("\n=== Step 39: Checking WhatsApp report file ===")
                                        if step39_check_whatsapp_report():
                                            # ADD STEP 40 HERE
                                            print("\n=== Step 40: Processing report ===")
                                            if step40_process_report():
                                                # ADD STEPS 41-53 HERE
                                                print("\n=== Step 41: Opening WhatsApp Web ===")
                                                if step41_open_whatsapp_web():
                                                    print("\n=== Step 42: Checking database key ===")
                                                    if step42_check_database_key():
                                                        print("\n=== Step 43: Fetching Xpath001 ===")
                                                        if step43_fetch_xpath001():
                                                            print("\n=== Step 44: Finding and clicking Xpath001 ===")
                                                            if step44_find_and_click_xpath001():
                                                                print("\n=== Step 45: Checking report number file ===")
                                                                if step45_check_report_number_file():
                                                                    print("\n=== Step 46: Verifying report number ===")
                                                                    if step46_verify_report_number():
                                                                        print("\n=== Step 47: Pasting report number ===")
                                                                        if step47_paste_report_number():
                                                                            print("\n=== Step 48: Waiting and pressing down ===")
                                                                            if step48_wait_and_press_down():
                                                                                print("\n=== Step 49: Fetching Xpath002 ===")
                                                                                if step49_fetch_xpath002():
                                                                                    print("\n=== Step 50: Finding and clicking Xpath002 ===")
                                                                                    if step50_find_and_click_xpath002():
                                                                                        print("\n=== Step 51: Transferring report content ===")
                                                                                        if step51_transfer_report_content():
                                                                                            print("\n=== Step 52: Waiting and pressing enter ===")
                                                                                            if step52_wait_and_press_enter():
                                                                                                print("\n=== Step 53: Checking message status ===")
                                                                                                if step53_check_message_status():
                                                                                                    # ADD STEPS 54-61 HERE
                                                                                                    print("\n=== Step 54: Opening WhatsApp Web ===")
                                                                                                    if step54_open_whatsapp_web():
                                                                                                        print("\n=== Step 55: Checking database key ===")
                                                                                                        if step55_check_database_key():
                                                                                                            print("\n=== Step 56: Fetching Xpath001 ===")
                                                                                                            if step56_fetch_xpath001():
                                                                                                                print("\n=== Step 57: Finding and clicking Xpath001 ===")
                                                                                                                if step57_find_and_click_xpath001():
                                                                                                                    print("\n=== Step 58: Checking report number file ===")
                                                                                                                    if step58_check_report_number_file():
                                                                                                                        print("\n=== Step 59: Verifying report number ===")
                                                                                                                        if step59_verify_report_number():
                                                                                                                            print("\n=== Step 60: Pasting report number ===")
                                                                                                                            if step60_paste_report_number():
                                                                                                                                print("\n=== Step 61: Waiting and pressing down ===")
                                                                                                                                if step61_wait_and_press_down():
                                                                                                                                    # Continue with step52
                                                                                                                                    print("Continue with step52")
                                                                                                                                    step35_all_wishes_sent()
                                elif next_step == "step20":
                                    skip_to_step31 = False
                                    selected_wish_stored = None
                                    continue
                    elif next_step_after_32 == "step33":
                        print("\n=== Step 33: Redoing steps 16 to 22 ===")
                        result = step33_redo_steps_16_to_22()
                        
                        if result == "step34":
                            print("\n=== Step 34: Waiting and pressing down ===")
                            if step34_wait_and_press_down():
                                # Set flag to go back to step31
                                skip_to_step31 = True
                                continue
                        else:
                            # If any step fails, restart the process
                            print("Error in step33, restarting process...")
                            close_chrome()
                            time.sleep(5)
                            continue
                
                skip_to_step31 = False  # Reset the flag
                selected_wish_stored = None
                continue
            
            # First part: Steps 1-19 (only run once)
            if extracted_phone_number is None:
                # Step 1: Close Chrome if open
                print("\n=== Step 1: Checking for and closing open Chrome browsers ===")
                close_chrome()
                
                # Step 2: Check internet connection (retries forever)
                print("\n=== Step 2: Checking internet connection ===")
                wait_for_internet()
                    
                # Step 3: Check spreadsheet access key (exits if missing)
                print("\n=== Step 3: Checking for the spreadsheet access key ===")
                if not check_file_exists(SPREADSHEET_KEY):
                    print("Spread sheet access key is not available")
                    print("Closing browser and script.")
                    exit()
                else:
                    print("Spread sheet access key is available")
                    
                    # Step 5: Access Google Spreadsheet (retries forever)
                    print("\n=== Step 5: Accessing Google Spreadsheet ===")
                    spreadsheet = initialize_spreadsheet()
                    print("Reached the spread sheet")
                    
                    # Step 7: Remove duplicates (retries forever)
                    print("\n=== Step 7: Removing duplicate rows ===")
                    step7_remove_duplicates(spreadsheet)
                    
                    # Step 8: Filter birthdays (retries forever)
                    print("\n=== Step 8: Filtering today's birthdays ===")
                    step8_output = step8_filter_birthdays(spreadsheet)
                    
                    if next_step == "step9a":
                        print("\n=== Step 9a: Opening WhatsApp Web ===")
                        if step9a_open_whatsapp_web():
                            print("\n=== Step 9b: Checking database key ===")
                            if step9b_check_database_key():
                                print("\n=== Step 9c: Fetching Xpath001 ===")
                                if step9c_fetch_xpath():
                                    print("\n=== Step 9d: Finding and clicking Xpath001 ===")
                                    if step9d_find_and_click_xpath():
                                        print("\n=== Step 9e: Checking report number file ===")
                                        if step9e_check_report_number_file():
                                            print("\n=== Step 9f: Verifying report number ===")
                                            if step9f_verify_report_number():
                                                print("\n=== Step 9g: Pasting report number ===")
                                                if step9g_paste_report_number():
                                                    print("\n=== Step 9h: Waiting and pressing down ===")
                                                    if step9h_wait_and_press_down():
                                                        print("\n=== Step 9i: Fetching Xpath002 ===")
                                                        if step9i_fetch_xpath002():
                                                            print("\n=== Step 9j: Finding and clicking Xpath002 ===")
                                                            if step9j_find_and_click_xpath002():
                                                                print("\n=== Step 9k: Typing admin message ===")
                                                                if step9k_type_message():
                                                                    print("\n=== Step 9l: Waiting and pressing enter ===")
                                                                    if step9l_wait_and_press_enter():
                                                                        print("\n=== Step 9m: Checking message status ===")
                                                                        if step9m_check_message_status():
                                                                            # Message sent successfully, exit
                                                                            exit()
                    
                    elif next_step == "step10":
                        print("\n=== Step 10: Checking and deleting contact file ===")
                        if step10_check_and_delete_contact_file():
                            print("\n=== Step 11: Creating new contact file ===")
                            if step11_create_contact_file():
                                print("\n=== Step 12: Transferring birthday data ===")
                                if step12_transfer_birthday_data(spreadsheet):
                                    
                                    # Step 13: Check and delete wishes file
                                    print("\n=== Step 13: Checking wishes file ===")
                                    next_step_after_13 = step13_check_and_delete_wishes_file()
                                    
                                    if next_step_after_13 == "step14":
                                        print("\n=== Step 14: Creating new wishes file ===")
                                        if step14_create_wishes_file():
                                            print("\n=== Step 15: Processing wishes from sheets ===")
                                            if step15_process_wishes_from_sheets(spreadsheet):
                                                print("\n=== Step 16: Opening WhatsApp Web ===")
                                                if step16_open_whatsapp_web():
                                                    print("\n=== Step 17: Checking database key ===")
                                                    if step17_check_database_key():
                                                        print("\n=== Step 18: Fetching Xpath001 ===")
                                                        if step18_fetch_xpath001():
                                                            print("\n=== Step 19: Finding and clicking Xpath001 ===")
                                                            if step19_find_and_click_xpath001():
                                                                # Continue to step20 below
                                                                pass
                                    else:  # step15
                                        print("\n=== Step 15: Processing wishes from sheets ===")
                                        if step15_process_wishes_from_sheets(spreadsheet):
                                            print("\n=== Step 16: Opening WhatsApp Web ===")
                                            if step16_open_whatsapp_web():
                                                print("\n=== Step 17: Checking database key ===")
                                                if step17_check_database_key():
                                                    print("\n=== Step 18: Fetching Xpath001 ===")
                                                    if step18_fetch_xpath001():
                                                        print("\n=== Step 19: Finding and clicking Xpath001 ===")
                                                        if step19_find_and_click_xpath001():
                                                            # Continue to step20 below
                                                            pass
            
            # Step 20: Checking contact file
            print("\n=== Step 20: Checking contact file ===")
            if step20_check_contact_file():
                print("\n=== Step 21: Processing contact file ===")
                result, phone_number = step21_process_contact_file()
                
                if result == "step35":
                    # ADD STEP 35 HERE
                    print("\n=== Step 35: Transferring data to Google Sheets ===")
                    worksheet = step35_transfer_to_sheets()
                    
                    # ADD STEP 38 HERE
                    print("\n=== Step 38: Processing contact data ===")
                    if step38_process_contact_data(worksheet):
                        # ADD STEP 39 HERE
                        print("\n=== Step 39: Checking WhatsApp report file ===")
                        if step39_check_whatsapp_report():
                            # ADD STEP 40 HERE
                            print("\n=== Step 40: Processing report ===")
                            if step40_process_report():
                                # ADD STEPS 41-53 HERE
                                print("\n=== Step 41: Opening WhatsApp Web ===")
                                if step41_open_whatsapp_web():
                                    print("\n=== Step 42: Checking database key ===")
                                    if step42_check_database_key():
                                        print("\n=== Step 43: Fetching Xpath001 ===")
                                        if step43_fetch_xpath001():
                                            print("\n=== Step 44: Finding and clicking Xpath001 ===")
                                            if step44_find_and_click_xpath001():
                                                print("\n=== Step 45: Checking report number file ===")
                                                if step45_check_report_number_file():
                                                    print("\n=== Step 46: Verifying report number ===")
                                                    if step46_verify_report_number():
                                                        print("\n=== Step 47: Pasting report number ===")
                                                        if step47_paste_report_number():
                                                            print("\n=== Step 48: Waiting and pressing down ===")
                                                            if step48_wait_and_press_down():
                                                                print("\n=== Step 49: Fetching Xpath002 ===")
                                                                if step49_fetch_xpath002():
                                                                    print("\n=== Step 50: Finding and clicking Xpath002 ===")
                                                                    if step50_find_and_click_xpath002():
                                                                        print("\n=== Step 51: Transferring report content ===")
                                                                        if step51_transfer_report_content():
                                                                            print("\n=== Step 52: Waiting and pressing enter ===")
                                                                            if step52_wait_and_press_enter():
                                                                                print("\n=== Step 53: Checking message status ===")
                                                                                if step53_check_message_status():
                                                                                    # ADD STEPS 54-61 HERE
                                                                                    print("\n=== Step 54: Opening WhatsApp Web ===")
                                                                                    if step54_open_whatsapp_web():
                                                                                        print("\n=== Step 55: Checking database key ===")
                                                                                        if step55_check_database_key():
                                                                                            print("\n=== Step 56: Fetching Xpath001 ===")
                                                                                            if step56_fetch_xpath001():
                                                                                                print("\n=== Step 57: Finding and clicking Xpath001 ===")
                                                                                                if step57_find_and_click_xpath001():
                                                                                                    print("\n=== Step 58: Checking report number file ===")
                                                                                                    if step58_check_report_number_file():
                                                                                                        print("\n=== Step 59: Verifying report number ===")
                                                                                                        if step59_verify_report_number():
                                                                                                            print("\n=== Step 60: Pasting report number ===")
                                                                                                            if step60_paste_report_number():
                                                                                                                print("\n=== Step 61: Waiting and pressing down ===")
                                                                                                                if step61_wait_and_press_down():
                                                                                                                    # Continue with step52
                                                                                                                    print("Continue with step52")
                                                                                                                    step35_all_wishes_sent()
                elif result:
                    # Store the phone number for later use
                    extracted_phone_number = phone_number
                    print("\n=== Step 22: Waiting and checking internet ===")
                    if step22_wait_and_check_internet():
                        print("\n=== Step 23: Fetching Xpath004 ===")
                        if step23_fetch_xpath004():
                            print("\n=== Step 24: Searching for Xpath004 ===")
                            result, timestamp = step24_search_xpath004()
                            
                            if result == "step24a":
                                print("\n=== Step 24a: Closing browser ===")
                                if step24a_close_browser():
                                    print("\n=== Step 24b: Checking contact file ===")
                                    if step24b_check_contact_file():
                                        print("\n=== Step 24c: Updating contact file ===")
                                        if step24c_update_contact_file(extracted_phone_number, timestamp):
                                            print("\n=== Returning to step20 ===")
                                            # Instead of restarting, continue with step20
                                            continue  # This will continue with the next iteration of the loop
                            
                            elif result == "step25":
                                print("\n=== Step 25: Waiting and pressing down ===")
                                if step25_wait_and_press_down():
                                    print("\n=== Step 26: Fetching Xpath002 ===")
                                    if step26_fetch_xpath002():
                                        print("\n=== Step 27: Finding and clicking Xpath002 ===")
                                        result = step27_find_and_click_xpath002()
                                        
                                        if result is False:
                                            # Xpath002 not found within 120 seconds, continue with step16
                                            print("Xpath002 not found, continuing with step16...")
                                            if step16_open_whatsapp_web():
                                                if step17_check_database_key():
                                                    if step18_fetch_xpath001():
                                                        if step19_find_and_click_xpath001():
                                                            continue  # Return to step20
                                        elif result:
                                            print("\n=== Step 28: Checking wishes file ===")
                                            wishes = step28_check_wishes_file()
                                            
                                            if wishes:
                                                print("\n=== Step 29: Typing random wish ===")
                                                result, selected_wish = step29_type_random_wish(wishes)
                                                
                                                if result:
                                                    print("\n=== Step 30: Waiting and pressing enter ===")
                                                    if step30_wait_and_press_enter():
                                                        # Set flag to go to step31 in next iteration
                                                        skip_to_step31 = True
                                                        selected_wish_stored = selected_wish
                                                        continue
            
        except KeyboardInterrupt:
            print("\nScript interrupted by user")
            close_chrome()
            exit()
        except Exception as e:
            print(f"\nUnexpected error in main loop: {str(e)}")
            print("Restarting the process...")
            close_chrome()
            time.sleep(5)
