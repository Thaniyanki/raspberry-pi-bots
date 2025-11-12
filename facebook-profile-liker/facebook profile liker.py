# facebook profile liker Python Script
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
from selenium.webdriver.common.by import By
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image

# ================================
# CONFIGURATION SECTION
# ================================

# Auto-detect user home directory
USER_HOME = os.path.expanduser("~")
# Extract username from home directory path
BASE_USER = os.path.basename(USER_HOME)

# Base directory structure - Auto-detected
BASE_DIR = os.path.join(USER_HOME, "bots")
CURRENT_BOT_DIR = os.path.join(BASE_DIR, "facebook profile liker")

# All file and directory paths - CENTRALIZED
PATHS = {
    # Firebase
    "firebase_credentials": os.path.join(CURRENT_BOT_DIR, "venv", "database access key.json"),
    
    # Google Sheets
    "google_sheets_credentials": os.path.join(CURRENT_BOT_DIR, "venv", "spread sheet access key.json"),
    
    # Data files
    "current_friends_file": os.path.join(CURRENT_BOT_DIR, "Current Friends"),
    "waiting_for_proceed_file": os.path.join(CURRENT_BOT_DIR, "Waiting for proceed"),
    "report_number_file": os.path.join(CURRENT_BOT_DIR, "venv", "report number"),
    
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
        os.path.dirname(PATHS["current_friends_file"]),
        os.path.dirname(PATHS["waiting_for_proceed_file"]),
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
        PATHS["report_number_file"]
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"❌ Required file not found: {file_path}")
            return False
    
    print("✅ All required files verified")
    return True

# ================================
# ORIGINAL FUNCTIONS (MODIFIED FOR CUSTOM PATHS)
# ================================

# Global variables
firebase_initialized = False
driver = None

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
        print("✅ Firebase initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Firebase initialization failed: {str(e)}")
        return False

def fetch_xpath_from_firebase(xpath_name, platform="Facebook"):
    """Fetch XPath from Firebase with retry logic"""
    while True:
        try:
            print(f"🔍 Fetching {xpath_name} from database...")
            ref = db.reference(f"{platform}/Xpath")
            xpaths = ref.get()
            
            if xpaths and xpath_name in xpaths:
                print(f"✅ {xpath_name} fetched from database")
                return xpaths[xpath_name]
            else:
                print(f"❌ {xpath_name} not found in database. Retrying in 1 second...")
                time.sleep(1)
        except Exception as e:
            print(f"❌ Error accessing database for {xpath_name}: {str(e)}. Retrying in 1 second...")
            time.sleep(1)

def fetch_url_from_firebase(url_name, platform="Facebook"):
    """Fetch URL from Firebase with retry logic"""
    while True:
        try:
            print(f"🔍 Fetching {url_name} from database...")
            ref = db.reference(f"{platform}/URL")
            urls = ref.get()
            
            if urls and url_name in urls:
                print(f"✅ {url_name} fetched from database")
                return urls[url_name]
            else:
                print(f"❌ {url_name} not found in database. Retrying in 1 second...")
                time.sleep(1)
        except Exception as e:
            print(f"❌ Error accessing database for {url_name}: {str(e)}. Retrying in 1 second...")
            time.sleep(1)

# ================================
# STEP 1: INTERNET CHECK
# ================================

def check_internet():
    """Check internet connection with ping method"""
    retry_count = 0
    while True:
        try:
            subprocess.run(['ping', '-c', '1', '-W', '1', '8.8.8.8'], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE, 
                          timeout=5,
                          check=True)
            sys.stdout.write('\r' + ' ' * 50 + '\r')
            print("🌐 Internet is present good to go")
            return True
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            sys.stdout.write(f'\r🔄 Internet is not available waiting for connection {retry_count}sec...')
            sys.stdout.flush()
            retry_count += 1
            time.sleep(1)

# ================================
# STEP 2: CHROME BROWSER CHECK
# ================================

def close_chrome():
    """Close Chrome browser if already open"""
    global driver
    browsers = ['chromium', 'chrome']
    
    # Close Selenium driver if exists
    if driver:
        try:
            driver.quit()
            driver = None
            print("✅ Chrome browser closed via Selenium")
        except Exception as e:
            print(f"⚠️ Error closing Selenium driver: {str(e)}")
    
    # Close any remaining Chrome/Chromium processes
    for browser in browsers:
        print(f"🔍 Checking for {browser} processes...")
        try:
            result = subprocess.run(['pgrep', '-f', browser], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  timeout=5)
            if result.stdout:
                print(f"🛑 Closing {browser} processes...")
                subprocess.run(['pkill', '-f', browser], 
                              check=True,
                              timeout=5)
                print(f"✅ {browser.capitalize()} processes closed")
        except Exception as e:
            print(f"⚠️ Error cleaning {browser}: {str(e)}")

def check_and_close_chrome():
    """Check if Chrome is open and close it"""
    print("🔍 Checking if Chrome browser is already open...")
    
    browsers = ['chromium', 'chrome']
    browser_found = False
    
    for browser in browsers:
        try:
            result = subprocess.run(['pgrep', '-f', browser], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  timeout=5)
            if result.stdout:
                browser_found = True
                print(f"✅ {browser.capitalize()} browser is already open")
                break
        except Exception as e:
            continue
    
    if browser_found:
        close_chrome()
        print("✅ Chrome browser closed, continuing with Step3")
    else:
        print("✅ Chrome browser not open, continuing with Step3")

# ================================
# STEP 3: LAUNCH CHROME
# ================================

def launch_chrome(url="https://www.facebook.com"):
    """Launch Chrome browser with specified profile"""
    global driver
    try:
        print("🚀 Launching Chrome browser...")
        options = Options()
        options.add_argument(f"--user-data-dir={PATHS['chrome_profile']}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        
        driver = webdriver.Chrome(
            service=Service(PATHS["chromedriver"]),
            options=options
        )
        driver.set_page_load_timeout(300)
        
        print("✅ Chrome browser ready")
        
        print(f"🌐 Navigating to {url}...")
        driver.get(url)
        print(f"✅ Facebook loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Browser error: {str(e)}")
        return False

# ================================
# STEP 4: WAIT FOR STABILITY
# ================================

def wait_for_stability(seconds=10):
    """Wait for specified seconds for stability"""
    print(f"⏳ Waiting {seconds} seconds for stability...")
    for i in range(seconds, 0, -1):
        sys.stdout.write(f'\r⏳ {i} seconds remaining...')
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write('\r' + ' ' * 30 + '\r')
    print(f"✅ {seconds} seconds wait completed")

# ================================
# STEP 5: CHECK AND CLICK XPATH012
# ================================

def check_and_click_xpath012_optimized(xpath012):
    """Optimized version using pre-fetched XPath"""
    print("⏳ Starting XPath012 check (50 seconds timeout)...")
    start_time = time.time()
    
    while time.time() - start_time <= 50:
        elapsed = int(time.time() - start_time)
        
        try:
            element = driver.find_element("xpath", xpath012)
            element.click()
            print(f"\n✅ Xpath012 found and clicked at {elapsed} seconds")
            return True
            
        except NoSuchElementException:
            sys.stdout.write(f'\r🔍 Checking XPath012... ({elapsed}/50 seconds)')
            sys.stdout.flush()
            time.sleep(1)
            
        except Exception as e:
            print(f"\n❌ Error clicking XPath012: {str(e)}")
            return False
    
    print(f"\n❌ XPath012 not found within 50 seconds")
    return False

# ================================
# STEP 6: WAIT FOR STABILITY
# ================================

def wait_3_seconds():
    """Wait 3 seconds for stability"""
    print("⏳ Waiting 3 seconds for stability...")
    time.sleep(3)
    print("✅ 3 seconds wait completed")

# ================================
# NEW FUNCTION: CHECK FOR "ADD TO STORY"
# ================================

def check_for_add_to_story():
    """Check every second for 'Add to story' keyword for up to 30 seconds"""
    print("🔍 Checking for 'Add to story' keyword...")
    start_time = time.time()
    
    while time.time() - start_time <= 30:
        elapsed = int(time.time() - start_time)
        
        try:
            # Check if page contains "Add to story" text
            page_source = driver.page_source.lower()
            if "add to story" in page_source:
                print(f"\n✅ 'Add to story' keyword found at {elapsed} seconds")
                return True
                
            # If not found, wait 1 second and check again
            sys.stdout.write(f'\r🔍 Checking for "Add to story"... ({elapsed}/30 seconds)')
            sys.stdout.flush()
            time.sleep(1)
            
        except Exception as e:
            print(f"\n❌ Error checking for 'Add to story': {str(e)}")
            return False
    
    # If we reach here, keyword wasn't found within 30 seconds
    print(f"\n❌ 'Add to story' keyword not found within 30 seconds")
    return False

# ================================
# STEP 7: COMBINE URL AND NAVIGATE
# ================================

def combine_url_and_navigate():
    """Combine main profile URL with friend list URL and navigate"""
    try:
        # Get current URL (main profile URL)
        current_url = driver.current_url
        print(f"🌐 Current profile URL: {current_url}")
        
        # Fetch friend list URL from Firebase
        print("🔍 Fetching Friend List URL from Firebase...")
        friend_list_url = fetch_url_from_firebase("URL2")
        
        # Remove leading & if present and ensure it starts with &
        if friend_list_url.startswith('&'):
            friend_list_param = friend_list_url
        else:
            friend_list_param = '&' + friend_list_url
        
        # Combine URLs based on whether current URL already has parameters
        if '?' in current_url:
            # If URL already has query parameters, append with &
            combined_url = current_url + friend_list_param
        else:
            # If no query parameters, replace & with ?
            combined_url = current_url + '?' + friend_list_param.lstrip('&')
        
        print(f"🔗 Combined URL: {combined_url}")
        
        # Navigate to combined URL
        print("🌐 Navigating to friend list page...")
        driver.get(combined_url)
        
        # Wait for page to load
        time.sleep(5)
        print("✅ Successfully navigated to friend list page")
        return True
        
    except Exception as e:
        print(f"❌ Error combining URLs or navigating: {str(e)}")
        return False

# ================================
# STEP 8: FIND XPATH013 WITH PAGE DOWN
# ================================

def find_xpath013_with_page_down_optimized(xpath013):
    """Optimized version using pre-fetched XPath"""
    print("⏳ Starting XPath013 search with Page Down (10 minutes timeout)...")
    start_time = time.time()
    attempt_count = 0
    
    while time.time() - start_time <= 600:
        attempt_count += 1
        elapsed = int(time.time() - start_time)
        minutes = elapsed // 60
        seconds = elapsed % 60
        
        try:
            element = driver.find_element("xpath", xpath013)
            print(f"\n✅ Xpath013 found at {minutes}m {seconds}s (attempt {attempt_count})")
            return True
            
        except NoSuchElementException:
            sys.stdout.write(f'\r🔍 XPath013 not found, pressing Page Down... ({minutes}m {seconds}s/10m, attempt {attempt_count})')
            sys.stdout.flush()
            
            driver.find_element("tag name", "body").send_keys(Keys.PAGE_DOWN)
            time.sleep(2)
            
        except Exception as e:
            print(f"\n❌ Error searching for XPath013: {str(e)}")
            return False
    
    print(f"\n❌ XPath013 not found within 10 minutes")
    return False

# ================================
# STEP 9: MANAGE CURRENT FRIENDS FILE
# ================================

def manage_current_friends_file():
    """Create or recreate Current Friends text file"""
    file_path = PATHS["current_friends_file"]
    
    try:
        # Check if file exists and delete it
        if os.path.exists(file_path):
            os.remove(file_path)
            print("✅ Old 'Current Friends' file deleted")
        
        # Create new file
        with open(file_path, 'w') as f:
            f.write("")  # Create empty file
        
        print("✅ New 'Current Friends' file created")
        return True
        
    except Exception as e:
        print(f"❌ Error managing 'Current Friends' file: {str(e)}")
        return False

# ================================
# STEP 10: COLLECT FRIENDS DATA
# ================================

def extract_raw_picture_id(profile_picture_url):
    """Extract raw picture ID from profile picture URL"""
    try:
        # Parse the URL
        parsed_url = urllib.parse.urlparse(profile_picture_url)
        
        # Get the path and extract filename
        path = parsed_url.path
        filename = os.path.basename(path)
        
        # Remove any query parameters from filename if present
        if '?' in filename:
            filename = filename.split('?')[0]
            
        return filename
    except Exception as e:
        print(f"❌ Error extracting raw picture ID: {str(e)}")
        return "Unknown"

def collect_friends_data_optimized(base_xpath):
    """Optimized version using pre-fetched XPath"""
    print("📝 Starting to collect friends data...")
    friend_count = 0
    file_path = PATHS["current_friends_file"]
    
    # Remove [] from base xpath if present
    if '[]' in base_xpath:
        base_xpath = base_xpath.replace('[]', '')
    
    index = 1
    
    while True:
        try:
            current_xpath = f"({base_xpath})[{index}]"
            profile_pic_element = driver.find_element("xpath", current_xpath)
            profile_picture_url = profile_pic_element.get_attribute("src")
            raw_picture_id = extract_raw_picture_id(profile_picture_url)
            
            try:
                parent_container = profile_pic_element.find_element("xpath", "./ancestor::a[1]")
                profile_link = parent_container.get_attribute("href")
            except Exception as e:
                profile_link = "Unknown"
            
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"{index}\n")
                f.write(f"Profile Link = {profile_link}\n")
                f.write(f"Profile Picture Link = {profile_picture_url}\n")
                f.write(f"Raw Picture ID = {raw_picture_id}\n")
                f.write("Remark = \n")
                f.write("\n")
            
            friend_count += 1
            print(f"✅ Collected data for friend {index}")
            index += 1
            
        except NoSuchElementException:
            if index == 1:
                print("❌ No friends found with the given XPath")
                return False
            else:
                print(f"✅ Finished collecting {friend_count} friends")
                return True
                
        except Exception as e:
            print(f"❌ Error collecting data for friend {index}: {str(e)}")
            return False

# ================================
# STEP 11: FILTER AND CLICK DEFAULT PICTURES
# ================================

def step11_filter_and_click_default_pictures():
    """Filter default profile pictures and unfriend deactivated accounts"""
    print("\n" + "=" * 40)
    print("STEP 11: Filtering and clicking default pictures...")
    print("=" * 40)
    
    def is_default_picture(raw_picture_id):
        """Check if the raw picture ID matches the default Facebook avatar"""
        DEFAULT_PICTURE_ID = "453178253_471506465671661_2781666950760530985_n.png"
        return raw_picture_id == DEFAULT_PICTURE_ID
    
    def is_valid_profile_link(profile_link):
        """Check if the profile link is a valid Facebook profile URL"""
        if not profile_link or profile_link.lower() == 'unknown':
            return False
            
        valid_patterns = [
            "https://www.facebook.com/",
            "https://facebook.com/",
            "https://web.facebook.com/",
            "https://m.facebook.com/"
        ]
        
        for pattern in valid_patterns:
            if profile_link.startswith(pattern):
                return True
        return False
    
    def update_remarks_in_file():
        """Update remarks in the Current Friends file - SIMPLE AND RELIABLE APPROACH"""
        try:
            file_path = PATHS["current_friends_file"]
            
            print("📖 Reading Current Friends file...")
            
            # Read the entire file
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Split by double newlines to get each friend block
            friend_blocks = content.strip().split('\n\n')
            updated_blocks = []
            
            print(f"🔍 Processing {len(friend_blocks)} friend blocks...")
            
            for block in friend_blocks:
                if not block.strip():
                    continue
                    
                lines = block.strip().split('\n')
                friend_data = {}
                new_block_lines = []
                
                # Parse the block and determine remark
                for line in lines:
                    line = line.strip()
                    
                    if line.isdigit():
                        friend_data['serial_number'] = int(line)
                        new_block_lines.append(line)
                    elif line.startswith("Profile Link = "):
                        friend_data['profile_link'] = line.replace("Profile Link = ", "").strip()
                        new_block_lines.append(line)
                    elif line.startswith("Profile Picture Link = "):
                        friend_data['profile_picture_link'] = line.replace("Profile Picture Link = ", "").strip()
                        new_block_lines.append(line)
                    elif line.startswith("Raw Picture ID = "):
                        friend_data['raw_picture_id'] = line.replace("Raw Picture ID = ", "").strip()
                        new_block_lines.append(line)
                    elif line.startswith("Remark = "):
                        # SKIP the original remark line completely
                        continue
                    else:
                        new_block_lines.append(line)
                
                # Determine the correct remark
                profile_link = friend_data.get('profile_link', '')
                raw_picture_id = friend_data.get('raw_picture_id', '')
                
                if profile_link.lower() == 'unknown':
                    remark = "Unknown"
                elif is_default_picture(raw_picture_id):
                    remark = "Default Profile Picture"
                else:
                    remark = "Unique Profile Picture"
                
                # Add the correct remark line
                new_block_lines.append(f"Remark = {remark}")
                
                # Add the updated block
                updated_blocks.append('\n'.join(new_block_lines))
            
            # Write the completely rebuilt file
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write('\n\n'.join(updated_blocks))
            
            print("✅ Successfully updated remarks in Current Friends file")
            
            # Count remarks for statistics
            remark_counts = {"Unknown": 0, "Default Profile Picture": 0, "Unique Profile Picture": 0}
            for block in updated_blocks:
                for line in block.split('\n'):
                    if line.startswith("Remark = "):
                        remark = line.replace("Remark = ", "").strip()
                        if remark in remark_counts:
                            remark_counts[remark] += 1
            
            print(f"📊 Remark Statistics:")
            for remark_type, count in remark_counts.items():
                print(f"   - {remark_type}: {count}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating remarks in file: {str(e)}")
            return False
    
    # STEP 1: Update remarks in the file FIRST
    print("🔄 Step 1: Updating remarks in Current Friends file...")
    if not update_remarks_in_file():
        print("❌ Failed to update remarks in file")
        return False
    
    print("ℹ️ No deactivated accounts (unknown profile links) found to unfriend")
    return True

# ================================
# STEP 12: UPLOAD TO GOOGLE SHEETS
# ================================

def step12_upload_to_google_sheets():
    """Upload data from Current Friends file to Google Sheets"""
    print("\n" + "=" * 40)
    print("STEP 12: Uploading data to Google Sheets...")
    print("=" * 40)
    
    # Configuration
    SPREADSHEET_NAME = "Facebook profile liker"
    CURRENT_FRIENDS_SHEET = "Current Friends"
    
    def setup_google_sheets_client():
        """Setup and authenticate Google Sheets client"""
        try:
            # Define the scope
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            
            # Check if credentials file exists
            if not os.path.exists(PATHS["google_sheets_credentials"]):
                raise Exception(f"Credentials file not found: {PATHS['google_sheets_credentials']}")
            
            # Authenticate and create client
            creds = Credentials.from_service_account_file(PATHS["google_sheets_credentials"], scopes=scope)
            client = gspread.authorize(creds)
            return client
        except Exception as e:
            raise Exception(f"Failed to setup Google Sheets client: {str(e)}")
    
    def parse_current_friends_file():
        """Parse Current Friends file and extract friend data with serial numbers"""
        file_path = PATHS["current_friends_file"]
        
        try:
            if not os.path.exists(file_path):
                print(f"❌ Current Friends file not found: {file_path}")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            friends_data = []
            current_friend = {}
            
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                
                if not line:
                    # Empty line indicates end of current friend data
                    if current_friend:
                        friends_data.append(current_friend)
                        current_friend = {}
                    continue
                
                # Check if line is a serial number (digits only)
                if line.isdigit():
                    current_friend['serial_number'] = int(line)
                elif line.startswith("Profile Link = "):
                    current_friend['profile_link'] = line.replace("Profile Link = ", "").strip()
                elif line.startswith("Profile Picture Link = "):
                    current_friend['profile_picture_link'] = line.replace("Profile Picture Link = ", "").strip()
                elif line.startswith("Raw Picture ID = "):
                    current_friend['raw_picture_id'] = line.replace("Raw Picture ID = ", "").strip()
                elif line.startswith("Remark = "):
                    current_friend['remark'] = line.replace("Remark = ", "").strip()
            
            # Add the last friend if exists
            if current_friend:
                friends_data.append(current_friend)
            
            print(f"✅ Parsed {len(friends_data)} friends from Current Friends file")
            return friends_data
            
        except Exception as e:
            raise Exception(f"Failed to parse Current Friends file: {str(e)}")
    
    def is_valid_profile_link(profile_link):
        """Check if the profile link is a valid Facebook profile URL"""
        if not profile_link or profile_link.lower() == 'unknown':
            return False
            
        valid_patterns = [
            "https://www.facebook.com/",
            "https://facebook.com/",
            "https://web.facebook.com/",
            "https://m.facebook.com/"
        ]
        
        for pattern in valid_patterns:
            if profile_link.startswith(pattern):
                return True
        return False
    
    def prepare_data_for_upload(friends_data):
        """Prepare data for Google Sheets upload with current timestamp"""
        current_datetime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        
        active_friends = []
        
        for friend in friends_data:
            # Get data with defaults
            serial_number = friend.get('serial_number', 0)
            profile_link = friend.get('profile_link', 'Unknown')
            profile_picture_link = friend.get('profile_picture_link', '')
            raw_picture_id = friend.get('raw_picture_id', '')
            remark = friend.get('remark', 'Unique Profile Picture')
            
            # Check if profile link is valid (active account)
            has_valid_link = is_valid_profile_link(profile_link)
            
            # Only include active accounts (skip deactivated/unknown)
            if has_valid_link:
                # Prepare row data with Remark
                row_data = [
                    current_datetime,      # Date-Time
                    serial_number,         # Serial Number
                    profile_link,          # Profile Link
                    profile_picture_link,  # Profile Picture Link
                    raw_picture_id,        # Raw Picture ID
                    remark                 # Remark
                ]
                
                active_friends.append(row_data)
        
        # Print summary
        print(f"📊 Account Analysis:")
        print(f"   - Active accounts: {len(active_friends)}")
        print(f"   - Deactivated accounts: {len(friends_data) - len(active_friends)}")
        print(f"   - Total accounts processed: {len(friends_data)}")
        
        # Count remark types
        remark_counts = {}
        for friend in active_friends:
            remark = friend[5]  # Remark is at index 5
            remark_counts[remark] = remark_counts.get(remark, 0) + 1
        
        print(f"📊 Remark Analysis:")
        for remark_type, count in remark_counts.items():
            print(f"   - {remark_type}: {count}")
        
        return active_friends
    
    def clear_sheet_data(worksheet):
        """Clear all data from worksheet except headers"""
        try:
            # Get all data from the worksheet
            all_data = worksheet.get_all_values()
            
            if len(all_data) <= 1:  # Only headers or empty
                print("ℹ️ No data to clear (only headers present)")
                return True
            
            # Calculate range to clear (from row 2 to end)
            rows_to_clear = len(all_data) - 1  # Exclude header row
            
            if rows_to_clear > 0:
                # Clear data from row 2 onwards
                range_to_clear = f"A2:F{len(all_data)}"
                worksheet.batch_clear([range_to_clear])
                print(f"✅ Cleared {rows_to_clear} rows of data from sheet")
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to clear sheet data: {str(e)}")
    
    def upload_to_sheet(client, sheet_name, data):
        """Upload data to specific worksheet after clearing existing data"""
        try:
            print(f"📤 Attempting to upload to {sheet_name}...")
            
            # Open the spreadsheet
            try:
                spreadsheet = client.open(SPREADSHEET_NAME)
                print(f"✅ Opened spreadsheet: {SPREADSHEET_NAME}")
            except gspread.exceptions.SpreadsheetNotFound:
                raise Exception(f"Spreadsheet '{SPREADSHEET_NAME}' not found. Please check the name and sharing permissions.")
            
            # Try to get the worksheet, create if it doesn't exist
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                print(f"✅ Found existing worksheet: {sheet_name}")
                
                # CLEAR EXISTING DATA before uploading new data
                print(f"🗑️ Clearing existing data from {sheet_name}...")
                if not clear_sheet_data(worksheet):
                    raise Exception(f"Failed to clear data from {sheet_name}")
                
            except gspread.exceptions.WorksheetNotFound:
                print(f"📝 Worksheet '{sheet_name}' not found, creating new one...")
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
                
                # Add headers if it's a new worksheet
                headers = ["Date-Time", "Serial Number", "Profile Link", "Profile Picture Link", "Raw Picture ID", "Remark"]
                worksheet.append_row(headers)
                print(f"✅ Added headers to new worksheet: {sheet_name}")
            
            # Upload data to worksheet
            if data:
                print(f"📊 Uploading {len(data)} rows to {sheet_name}...")
                
                # Use simple append_rows method
                worksheet.append_rows(data)
                print(f"✅ Successfully uploaded {len(data)} rows to {sheet_name}")
                return True
            else:
                print(f"ℹ️ No data to upload to {sheet_name}")
                return True
                
        except Exception as e:
            error_msg = str(e)
            # Check if it's actually a success (200 response)
            if "200" in error_msg:
                print(f"✅ Data successfully uploaded to {sheet_name} (received 200 response)")
                return True
            else:
                raise Exception(f"Failed to upload to {sheet_name}: {error_msg}")
    
    # Main execution with UNLIMITED retry logic
    retry_count = 0
    
    while True:  # Unlimited retries
        try:
            retry_count += 1
            print(f"🔄 Attempt {retry_count} to upload data to Google Sheets...")
            
            # Setup Google Sheets client
            client = setup_google_sheets_client()
            print("✅ Google Sheets client authenticated successfully")
            
            # Parse Current Friends file
            friends_data = parse_current_friends_file()
            if not friends_data:
                print("❌ No friend data found to upload")
                return False
            
            # Prepare data for upload (only active accounts)
            active_friends = prepare_data_for_upload(friends_data)
            
            # Upload active friends to "Current Friends" sheet
            upload_success = True
            
            if active_friends:
                print(f"📊 Uploading {len(active_friends)} active friends...")
                if not upload_to_sheet(client, CURRENT_FRIENDS_SHEET, active_friends):
                    print("❌ Failed to upload active friends")
                    upload_success = False
                else:
                    print("✅ Active friends uploaded successfully")
            else:
                print("ℹ️ No active friends to upload")
            
            if upload_success:
                print("✅ Step 12 completed successfully!")
                print("📋 Summary:")
                print(f"   - Active friends uploaded: {len(active_friends)}")
                print(f"   - Deactivated friends skipped: {len(friends_data) - len(active_friends)}")
                print(f"   - Total friends processed: {len(friends_data)}")
                return True
            else:
                raise Exception("Upload failure")
            
        except Exception as e:
            error_message = str(e)
            
            # Check if it's actually a success (200 response)
            if "200" in error_message:
                print("✅ Step 12 completed successfully (200 response detected)!")
                return True
                
            print(f"❌ Error during Step 12 (Attempt {retry_count}): {error_message}")
            
            wait_time = 10
            print(f"🔄 Retrying in {wait_time} seconds... (Attempt {retry_count + 1} - Unlimited retries)")
            time.sleep(wait_time)
    
    return False

# ================================
# STEP 13: COMPARE AND CREATE WAITING FILE
# ================================

def step13_compare_and_create_waiting_file():
    """Compare Current Friends with Report sheet and create waiting file - OPTIMIZED VERSION"""
    print("\n" + "=" * 40)
    print("STEP 13: Comparing sheets and creating waiting file...")
    print("=" * 40)
    
    # Configuration
    SPREADSHEET_NAME = "Facebook profile liker"
    CURRENT_FRIENDS_SHEET = "Current Friends"
    REPORT_SHEET = "Report"
    
    def setup_google_sheets_client():
        """Setup and authenticate Google Sheets client"""
        try:
            # Define the scope
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            
            # Check if credentials file exists
            if not os.path.exists(PATHS["google_sheets_credentials"]):
                raise Exception(f"Credentials file not found: {PATHS['google_sheets_credentials']}")
            
            # Authenticate and create client
            creds = Credentials.from_service_account_file(PATHS["google_sheets_credentials"], scopes=scope)
            client = gspread.authorize(creds)
            return client
        except Exception as e:
            raise Exception(f"Failed to setup Google Sheets client: {str(e)}")
    
    def get_unique_profile_pictures(client):
        """Get only Unique Profile Pictures from Current Friends sheet"""
        try:
            print("📖 Reading Unique Profile Pictures from Current Friends sheet...")
            
            # Open the spreadsheet and worksheet
            spreadsheet = client.open(SPREADSHEET_NAME)
            worksheet = spreadsheet.worksheet(CURRENT_FRIENDS_SHEET)
            
            # Get ALL data from the sheet
            all_data = worksheet.get_all_values()
            
            if len(all_data) <= 1:  # Only headers or empty
                print("ℹ️ No data found in Current Friends sheet")
                return []
            
            # Filter only rows with "Unique Profile Picture" in Remark column (Column F, index 5)
            unique_profile_pictures = []
            default_picture_count = 0
            
            for i, row in enumerate(all_data[1:], start=2):  # Skip header, start from row 2
                if len(row) >= 6:  # Ensure row has all columns (A-F)
                    remark = row[5].strip()  # Column F (index 5) - Remark
                    
                    if remark == "Unique Profile Picture":
                        serial_number = row[1].strip()  # Column B (index 1)
                        profile_link = row[2].strip()   # Column C (index 2)
                        profile_picture_link = row[3].strip()  # Column D (index 3)
                        raw_picture_id = row[4].strip()  # Column E (index 4)
                        
                        # Only include if profile link is valid (not Unknown)
                        if (profile_link and 
                            profile_link.lower() != "unknown" and 
                            raw_picture_id and 
                            raw_picture_id.lower() != "raw picture id"):
                            
                            unique_profile_pictures.append({
                                'serial_number': serial_number,
                                'profile_link': profile_link,
                                'profile_picture_link': profile_picture_link,
                                'raw_picture_id': raw_picture_id
                            })
                    
                    elif remark == "Default Profile Picture":
                        default_picture_count += 1
            
            print(f"✅ Found {len(unique_profile_pictures)} Unique Profile Pictures")
            print(f"📊 Default Profile Picture rows: {default_picture_count}")
            
            return unique_profile_pictures
            
        except gspread.exceptions.WorksheetNotFound:
            print(f"❌ Worksheet '{CURRENT_FRIENDS_SHEET}' not found")
            return []
        except Exception as e:
            raise Exception(f"Failed to get Unique Profile Pictures: {str(e)}")
    
    def get_report_raw_picture_ids(client):
        """Get only Raw Picture IDs from Report sheet"""
        try:
            print("📖 Reading Raw Picture IDs from Report sheet...")
            
            # Open the spreadsheet and worksheet
            spreadsheet = client.open(SPREADSHEET_NAME)
            worksheet = spreadsheet.worksheet(REPORT_SHEET)
            
            # Get ALL data from the sheet
            all_data = worksheet.get_all_values()
            
            if len(all_data) <= 1:  # Only headers or empty
                print("ℹ️ No data found in Report sheet")
                return set()
            
            # Extract only Raw Picture IDs from Column E
            report_raw_picture_ids = set()
            
            for row in all_data[1:]:  # Skip header row
                if len(row) >= 5:  # Ensure row has at least Column E
                    raw_picture_id = row[4].strip()  # Column E (index 4)
                    if (raw_picture_id and 
                        raw_picture_id.lower() != "raw picture id" and 
                        raw_picture_id.lower() != "unknown"):
                        report_raw_picture_ids.add(raw_picture_id)
            
            print(f"✅ Found {len(report_raw_picture_ids)} unique Raw Picture IDs in Report sheet")
            return report_raw_picture_ids
            
        except gspread.exceptions.WorksheetNotFound:
            print(f"❌ Worksheet '{REPORT_SHEET}' not found")
            return set()
        except Exception as e:
            raise Exception(f"Failed to get Report Raw Picture IDs: {str(e)}")
    
    def filter_new_unique_pictures(unique_profile_pictures, report_raw_picture_ids):
        """Filter out Unique Profile Pictures that are already in Report sheet"""
        print("\n🔍 Comparing Unique Profile Pictures with Report sheet...")
        
        new_unique_pictures = []
        
        for friend in unique_profile_pictures:
            raw_picture_id = friend['raw_picture_id']
            
            # Only include if NOT found in Report sheet
            if raw_picture_id not in report_raw_picture_ids:
                new_unique_pictures.append(friend)
        
        print(f"📊 Comparison Results:")
        print(f"   - Total Unique Profile Pictures: {len(unique_profile_pictures)}")
        print(f"   - Already in Report sheet: {len(unique_profile_pictures) - len(new_unique_pictures)}")
        print(f"   - New Unique Profile Pictures: {len(new_unique_pictures)}")
        
        return new_unique_pictures
    
    def create_waiting_for_proceed_file(new_unique_pictures):
        """Create Waiting for proceed file with new unique friends"""
        file_path = PATHS["waiting_for_proceed_file"]
        
        try:
            # Delete existing file if it exists
            if os.path.exists(file_path):
                os.remove(file_path)
                print("✅ Old 'Waiting for proceed' file deleted")
            
            if not new_unique_pictures:
                print("ℹ️ No new Unique Profile Pictures to process - creating empty waiting file")
                # Create empty file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("")
                return True
            
            # Create new file with friend data
            with open(file_path, 'w', encoding='utf-8') as f:
                for friend in new_unique_pictures:
                    f.write(f"{friend['serial_number']}\n")
                    f.write(f"Profile Link = {friend['profile_link']}\n")
                    f.write(f"Profile Picture Link = {friend['profile_picture_link']}\n")
                    f.write(f"Raw Picture ID = {friend['raw_picture_id']}\n")
                    f.write("\n")  # Empty line between friends
            
            print(f"✅ Created 'Waiting for proceed' file with {len(new_unique_pictures)} new friends")
            print(f"📁 File location: {file_path}")
            
            # Print sample entries for verification
            print(f"\n📋 Sample entries in waiting file:")
            for i, friend in enumerate(new_unique_pictures[:3]):  # Show first 3
                print(f"   {i+1}. Serial: {friend['serial_number']}")
                print(f"      Profile: {friend['profile_link'][:50]}...")
                print(f"      Raw ID: {friend['raw_picture_id'][:30]}...")
            if len(new_unique_pictures) > 3:
                print(f"   ... and {len(new_unique_pictures) - 3} more")
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to create waiting file: {str(e)}")
    
    # Main execution with retry logic
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            retry_count += 1
            print(f"🔄 Attempt {retry_count} to compare sheets and create waiting file...")
            
            # Setup Google Sheets client
            client = setup_google_sheets_client()
            print("✅ Google Sheets client authenticated successfully")
            
            # STEP 1: Get only Unique Profile Pictures from Current Friends sheet
            unique_profile_pictures = get_unique_profile_pictures(client)
            
            if not unique_profile_pictures:
                print("❌ No Unique Profile Pictures found in Current Friends sheet")
                # Create empty waiting file
                create_waiting_for_proceed_file([])
                return True
            
            # STEP 2: Get only Raw Picture IDs from Report sheet
            report_raw_picture_ids = get_report_raw_picture_ids(client)
            
            # STEP 3: Filter out pictures that are already in Report sheet
            new_unique_pictures = filter_new_unique_pictures(unique_profile_pictures, report_raw_picture_ids)
            
            # STEP 4: Create waiting file
            if create_waiting_for_proceed_file(new_unique_pictures):
                print("✅ Step 13 completed successfully!")
                if new_unique_pictures:
                    print(f"🎯 {len(new_unique_pictures)} new friends waiting for processing")
                else:
                    print("🎯 No new friends to process - waiting file is empty")
                return True
            else:
                raise Exception("Failed to create waiting file")
            
        except Exception as e:
            error_message = str(e)
            print(f"❌ Error during Step 13 (Attempt {retry_count}): {error_message}")
            
            if retry_count < max_retries:
                wait_time = 10
                print(f"🔄 Retrying in {wait_time} seconds... (Attempt {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"❌ Failed to complete Step 13 after {max_retries} attempts")
                return False
    
    return False

# ================================
# STEP 14: PROCESS PROFILES FROM WAITING FILE
# ================================

def step14_process_profiles_from_waiting_file(XPATHS):
    """Step 14: Process profiles from Waiting for proceed file"""
    print("\n" + "=" * 40)
    print("STEP 14: Processing profiles from waiting file")
    print("=" * 40)
    
    def wait_5_seconds():
        """Wait 5 seconds for stability"""
        print("⏳ Waiting 5 seconds for stability...")
        for i in range(5, 0, -1):
            sys.stdout.write(f'\r⏳ {i} seconds remaining...')
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write('\r' + ' ' * 30 + '\r')
        print("✅ 5 seconds wait completed")
    
    def get_profiles_without_status():
        """Get profiles that don't have Status keyword"""
        file_path = PATHS["waiting_for_proceed_file"]
        
        try:
            if not os.path.exists(file_path):
                print("❌ Waiting for proceed file not found")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read().strip()
            
            # If file is empty, return empty list
            if not content:
                print("ℹ️ Waiting for proceed file is empty")
                return []
            
            profiles = []
            current_profile = {}
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                
                if not line:
                    # Empty line indicates end of current friend data
                    if current_profile:
                        profiles.append(current_profile)
                        current_profile = {}
                    continue
                
                if line.isdigit():
                    current_profile['serial_number'] = line
                elif line.startswith("Profile Link = "):
                    current_profile['profile_link'] = line.replace("Profile Link = ", "").strip()
                elif line.startswith("Profile Picture Link = "):
                    current_profile['profile_picture_link'] = line.replace("Profile Picture Link = ", "").strip()
                elif line.startswith("Raw Picture ID = "):
                    current_profile['raw_picture_id'] = line.replace("Raw Picture ID = ", "").strip()
                elif line.startswith("Status = "):
                    current_profile['status'] = line.replace("Status = ", "").strip()
            
            # Add the last profile if exists
            if current_profile:
                profiles.append(current_profile)
            
            # Filter profiles without status (Category 1: 4 lines per person)
            profiles_without_status = []
            for profile in profiles:
                # Check if profile has exactly 4 keys (serial_number, profile_link, profile_picture_link, raw_picture_id)
                # and no status key
                keys = list(profile.keys())
                if len(keys) == 4 and 'status' not in keys:
                    profiles_without_status.append(profile)
            
            print(f"📊 Found {len(profiles_without_status)} profiles without status (Category 1)")
            return profiles_without_status
            
        except Exception as e:
            print(f"❌ Error reading waiting file: {str(e)}")
            return []
    
    def check_all_profiles_have_status():
        """Check if all profiles in waiting file have status"""
        file_path = PATHS["waiting_for_proceed_file"]
        
        try:
            if not os.path.exists(file_path):
                return True  # No file means nothing to process
            
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read().strip()
            
            if not content:
                return True  # Empty file means nothing to process
            
            profiles = []
            current_profile = {}
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                
                if not line:
                    if current_profile:
                        profiles.append(current_profile)
                        current_profile = {}
                    continue
                
                if line.isdigit():
                    current_profile['serial_number'] = line
                elif line.startswith("Profile Link = "):
                    current_profile['profile_link'] = line.replace("Profile Link = ", "").strip()
                elif line.startswith("Profile Picture Link = "):
                    current_profile['profile_picture_link'] = line.replace("Profile Picture Link = ", "").strip()
                elif line.startswith("Raw Picture ID = "):
                    current_profile['raw_picture_id'] = line.replace("Raw Picture ID = ", "").strip()
                elif line.startswith("Status = "):
                    current_profile['status'] = line.replace("Status = ", "").strip()
            
            if current_profile:
                profiles.append(current_profile)
            
            # Check if all profiles have status
            for profile in profiles:
                if 'status' not in profile:
                    return False  # Found at least one profile without status
            
            return True  # All profiles have status
            
        except Exception as e:
            print(f"❌ Error checking profiles status: {str(e)}")
            return False
    
    def navigate_to_profile(profile_link):
        """Navigate to profile link"""
        try:
            print(f"🌐 Navigating to profile: {profile_link}")
            driver.get(profile_link)
            
            # Wait for page to load completely
            WebDriverWait(driver, 30).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            print("✅ Page loaded successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error navigating to profile: {str(e)}")
            return False
    
    def check_xpaths_simultaneously(XPATHS):
        """Check XPath017, XPath018, XPath020 simultaneously every second for 20 seconds"""
        print("🔍 Checking XPath017, XPath018, XPath020 simultaneously...")
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time <= 20:
            check_count += 1
            elapsed = int(time.time() - start_time)
            
            # Check XPath017 first
            try:
                element_017 = driver.find_element("xpath", XPATHS['xpath017'])
                print(f"✅ XPath017 found at {elapsed} seconds - User not put story")
                element_017.click()
                print("✅ XPath017 clicked")
                return "xpath017_found"
            except NoSuchElementException:
                pass
            
            # Check XPath018 second
            try:
                element_018 = driver.find_element("xpath", XPATHS['xpath018'])
                print(f"✅ XPath018 found at {elapsed} seconds - User put story not yet watched")
                element_018.click()
                print("✅ XPath018 clicked")
                return "xpath018_found"
            except NoSuchElementException:
                pass
            
            # Check XPath020 third
            try:
                element_020 = driver.find_element("xpath", XPATHS['xpath020'])
                print(f"✅ XPath020 found at {elapsed} seconds - User put story already watched")
                element_020.click()
                print("✅ XPath020 clicked")
                return "xpath020_found"
            except NoSuchElementException:
                pass
            
            sys.stdout.write(f'\r🔍 Checking XPaths... ({elapsed}/20 seconds, check {check_count})')
            sys.stdout.flush()
            time.sleep(1)
        
        print(f"\n❌ All 3 XPaths not found within 20 seconds")
        return "all_not_found"
    
    def step14c_initial_check(XPATHS):
        """Step 14c: Initial check for XPaths"""
        print("\n" + "-" * 30)
        print("STEP 14c: Initial XPath check")
        print("-" * 30)
        
        # Wait 5 seconds for stability
        wait_5_seconds()
        
        # Check XPaths simultaneously
        result = check_xpaths_simultaneously(XPATHS)
        
        if result == "xpath017_found":
            print("🎯 Continuing with step 15...")
            return "continue_step15"
        elif result == "xpath018_found" or result == "xpath020_found":
            print("🎯 Continuing with step 16...")
            return "continue_step16"
        else:
            # All XPaths not found, check internet
            print("🔄 All XPaths not found, checking internet connection...")
            if check_internet():
                print("✅ Internet is present, continuing with step14d")
                return "continue_step14d"
            else:
                print("❌ Internet not available, waiting for connection...")
                while not check_internet():
                    print("⏳ Waiting 2 seconds for internet connection...")
                    time.sleep(2)
                print("✅ Internet connection restored, refreshing page...")
                driver.refresh()
                return "restart_step14c"
    
    def step14d_retry_check(XPATHS):
        """Step 14d: Retry check after refresh"""
        print("\n" + "-" * 30)
        print("STEP 14d: Retry XPath check after refresh")
        print("-" * 30)
        
        # Refresh page
        print("🔄 Refreshing page...")
        driver.refresh()
        
        # Wait 5 seconds for stability
        wait_5_seconds()
        
        # Check XPaths simultaneously again
        result = check_xpaths_simultaneously(XPATHS)
        
        if result == "xpath017_found":
            print("🎯 Continuing with step 15...")
            return "continue_step15"
        elif result == "xpath018_found" or result == "xpath020_found":
            print("🎯 Continuing with step 16...")
            return "continue_step16"
        else:
            # All XPaths not found again, check internet
            print("🔄 All XPaths not found again, checking internet connection...")
            if check_internet():
                print("✅ Internet is present, continuing with step17e")
                return "continue_step17e"
            else:
                print("❌ Internet not available, waiting for connection...")
                while not check_internet():
                    print("⏳ Waiting 2 seconds for internet connection...")
                    time.sleep(2)
                print("✅ Internet connection restored, refreshing page...")
                driver.refresh()
                return "restart_step14c"
    
    def update_profile_status_in_file(profile_data, status):
        """Update profile status in waiting file"""
        file_path = PATHS["waiting_for_proceed_file"]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            profiles = content.strip().split('\n\n')
            
            # Find the profile to update
            for i, profile_block in enumerate(profiles):
                lines = profile_block.strip().split('\n')
                current_profile_data = {}
                
                for line in lines:
                    line = line.strip()
                    if line.isdigit():
                        current_profile_data['serial_number'] = line
                    elif line.startswith("Profile Link = "):
                        current_profile_data['profile_link'] = line.replace("Profile Link = ", "").strip()
                    elif line.startswith("Profile Picture Link = "):
                        current_profile_data['profile_picture_link'] = line.replace("Profile Picture Link = ", "").strip()
                    elif line.startswith("Raw Picture ID = "):
                        current_profile_data['raw_picture_id'] = line.replace("Raw Picture ID = ", "").strip()
                
                # Check if this is the profile we want to update
                if (current_profile_data.get('serial_number') == profile_data.get('serial_number') and
                    current_profile_data.get('profile_link') == profile_data.get('profile_link') and
                    current_profile_data.get('raw_picture_id') == profile_data.get('raw_picture_id')):
                    
                    # Remove existing status line if present
                    new_lines = [line for line in lines if not line.startswith("Status = ")]
                    
                    # Add new status line
                    new_lines.append(f"Status = {status}")
                    
                    profiles[i] = '\n'.join(new_lines)
                    
                    # Write the updated content back to file
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write('\n\n'.join(profiles))
                    
                    print(f"✅ Updated status to: {status}")
                    return True
            
            print(f"❌ Profile not found in file")
            return False
                
        except Exception as e:
            print(f"❌ Error updating status: {str(e)}")
            return False
    
    # Step 14a: Check waiting file
    print("STEP 14a: Checking waiting file...")
    
    # Check if all profiles already have status
    if check_all_profiles_have_status():
        print("✅ All profiles already have status, continuing with step18")
        return "continue_step18"
    
    # Get profiles without status
    profiles_to_process = get_profiles_without_status()
    
    if not profiles_to_process:
        print("ℹ️ No profiles to process, continuing with step18")
        return "continue_step18"
    
    print(f"🎯 Found {len(profiles_to_process)} profiles to process")
    
    # Process only the first profile without status
    profile = profiles_to_process[0]
    
    print(f"\n{'='*50}")
    print(f"Processing Profile: {profile['serial_number']}")
    print(f"Profile Link: {profile['profile_link'][:50]}...")
    print(f"{'='*50}")
    
    # Step 14b: Open profile
    print("STEP 14b: Opening profile...")
    if not navigate_to_profile(profile['profile_link']):
        print("❌ Failed to navigate to profile")
        return "continue_step14a"
    
    # Step 14c: Initial XPath check
    result_14c = step14c_initial_check(XPATHS)
    
    if result_14c == "continue_step15":
        # Continue with step 15
        step15_result = step15_like_profile_picture(profile, profile, XPATHS)
        return "continue_step14a"
    
    elif result_14c == "continue_step16":
        # Continue with step 16
        step16_result = step16_open_profile_picture(profile, profile, XPATHS)
        return "continue_step14a"
    
    elif result_14c == "continue_step14d":
        # Continue with step 14d
        result_14d = step14d_retry_check(XPATHS)
        
        if result_14d == "continue_step15":
            step15_result = step15_like_profile_picture(profile, profile, XPATHS)
            return "continue_step14a"
        
        elif result_14d == "continue_step16":
            step16_result = step16_open_profile_picture(profile, profile, XPATHS)
            return "continue_step14a"
        
        elif result_14d == "continue_step17e":
            # Update status for step17e
            update_profile_status_in_file(profile, "Can't open profile picture or story")
            print("🔄 Continuing with step 14a...")
            return "continue_step14a"
        
        elif result_14d == "restart_step14c":
            # Restart from step14c
            return step14_process_profiles_from_waiting_file(XPATHS)
    
    elif result_14c == "restart_step14c":
        # Restart from step14c
        return step14_process_profiles_from_waiting_file(XPATHS)
    
    return "continue_step14a"

# ================================
# STEP 15: LIKE PROFILE PICTURE
# ================================

def step15_like_profile_picture(profile, profile_data, XPATHS):
    """Step 15: Like profile picture after opening"""
    print("\n" + "=" * 40)
    print("STEP 15: Liking profile picture")
    print("=" * 40)
    
    def wait_5_seconds():
        """Wait 5 seconds for stability"""
        print("⏳ Waiting 5 seconds for stability...")
        for i in range(5, 0, -1):
            sys.stdout.write(f'\r⏳ {i} seconds remaining...')
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write('\r' + ' ' * 30 + '\r')
        print("✅ 5 seconds wait completed")
    
    def check_like_keyword():
        """Check every second for 'Like' keyword on the web page"""
        print("🔍 Checking for 'Like' keyword...")
        start_time = time.time()
        
        while time.time() - start_time <= 30:
            elapsed = int(time.time() - start_time)
            
            try:
                page_source = driver.page_source
                if "Like" in page_source:
                    print(f"\n✅ 'Like' keyword found at {elapsed} seconds")
                    return True
                
                sys.stdout.write(f'\r🔍 Checking for "Like"... ({elapsed}/30 seconds)')
                sys.stdout.flush()
                time.sleep(1)
                
            except Exception as e:
                error_msg = str(e)
                if "tab crashed" in error_msg.lower() or "session info" in error_msg.lower():
                    print(f"\n❌ Browser tab crashed, need to restart browser")
                    raise Exception("BROWSER_CRASHED")
                else:
                    print(f"\n❌ Error checking for 'Like' keyword: {str(e)}")
                    return False
        
        print(f"\n❌ 'Like' keyword not found within 30 seconds")
        return False
    
    def check_xpath021_and_xpath022_simultaneously():
        """Check XPath021 and XPath022 simultaneously every second for 30 seconds"""
        print("🔍 Checking XPath021 and XPath022 simultaneously...")
        start_time = time.time()
        
        while time.time() - start_time <= 30:
            elapsed = int(time.time() - start_time)
            
            # Check XPath021 first
            try:
                element_021 = driver.find_element("xpath", XPATHS['xpath021'])
                print(f"\n✅ XPath021 found at {elapsed} seconds - Profile picture not yet liked")
                return "xpath021_found"
            except NoSuchElementException:
                pass
            except Exception as e:
                error_msg = str(e)
                if "tab crashed" in error_msg.lower() or "session info" in error_msg.lower():
                    print(f"\n❌ Browser tab crashed, need to restart browser")
                    raise Exception("BROWSER_CRASHED")
            
            # Check XPath022 second
            try:
                element_022 = driver.find_element("xpath", XPATHS['xpath022'])
                print(f"\n✅ XPath022 found at {elapsed} seconds - Profile picture already liked")
                return "xpath022_found"
            except NoSuchElementException:
                pass
            except Exception as e:
                error_msg = str(e)
                if "tab crashed" in error_msg.lower() or "session info" in error_msg.lower():
                    print(f"\n❌ Browser tab crashed, need to restart browser")
                    raise Exception("BROWSER_CRASHED")
            
            sys.stdout.write(f'\r🔍 Checking XPath021 & XPath022... ({elapsed}/30 seconds)')
            sys.stdout.flush()
            time.sleep(1)
        
        print(f"\n❌ Both XPath021 and XPath022 not found within 30 seconds")
        return "both_not_found"
    
    def click_xpath021():
        """Click XPath021 to like the profile picture"""
        try:
            element = driver.find_element("xpath", XPATHS['xpath021'])
            element.click()
            print("✅ XPath021 clicked - Profile picture liked")
            return True
        except Exception as e:
            print(f"❌ Error clicking XPath021: {str(e)}")
            return False
    
    def handle_both_xpaths_not_found():
        """Handle case when both XPaths are not found"""
        print("🔄 Both XPaths not found, checking internet connection...")
        
        if check_internet():
            print("✅ Internet is present, refreshing page...")
            driver.refresh()
            wait_5_seconds()
            
            # Check XPaths again after refresh
            result = check_xpath021_and_xpath022_simultaneously()
            
            if result == "xpath021_found":
                if click_xpath021():
                    update_profile_status_in_file(profile_data, "Profile picture liked")
                    print("🔄 Continuing with step 14a...")
                    return True
                else:
                    return False
            elif result == "xpath022_found":
                update_profile_status_in_file(profile_data, "Already Liked")
                print("🔄 Continuing with step 14a...")
                return True
            else:
                update_profile_status_in_file(profile_data, "Like option not available user may restricted")
                print("🔄 Continuing with step 14a...")
                return True
        else:
            print("❌ Internet not available, waiting for connection...")
            while not check_internet():
                print("⏳ Waiting 2 seconds for internet connection...")
                time.sleep(2)
            print("✅ Internet connection restored, refreshing page...")
            driver.refresh()
            return step15_like_profile_picture(profile, profile_data, XPATHS)
    
    def handle_like_keyword_not_found():
        """Handle case when Like keyword is not found"""
        print("🔄 Like keyword not found after refresh, checking internet connection...")
        
        if check_internet():
            print("✅ Internet is present, going to step17c")
            update_profile_status_in_file(profile_data, "Like option not available user may restricted")
            print("🔄 Continuing with step 14a...")
            return True
        else:
            print("❌ Internet not available, waiting for connection...")
            while not check_internet():
                print("⏳ Waiting 2 seconds for internet connection...")
                time.sleep(2)
            print("✅ Internet connection restored, refreshing page...")
            driver.refresh()
            return step15_like_profile_picture(profile, profile_data, XPATHS)
    
    def handle_browser_crash():
        """Handle browser crash by restarting from step14"""
        print("🔄 Browser crashed, restarting from step14...")
        try:
            driver.quit()
        except:
            pass
        
        time.sleep(2)
        
        if not launch_chrome("https://www.facebook.com"):
            print("❌ Failed to restart browser, need full restart")
            raise Exception("BROWSER_RESTART_FAILED")
        
        print("✅ Browser restarted successfully, continuing from step14")
        return "RESTART_FROM_STEP14"
    
    # Step 15: Wait 5 seconds for stability
    try:
        wait_5_seconds()
    except Exception as e:
        if "BROWSER_CRASHED" in str(e):
            return handle_browser_crash()
        else:
            raise
    
    # Immediately check for "Like" keyword
    try:
        like_keyword_found = check_like_keyword()
    except Exception as e:
        if "BROWSER_CRASHED" in str(e):
            return handle_browser_crash()
        else:
            raise
    
    if like_keyword_found:
        # Step 15a: Check XPath021 and XPath022 simultaneously
        try:
            result = check_xpath021_and_xpath022_simultaneously()
        except Exception as e:
            if "BROWSER_CRASHED" in str(e):
                return handle_browser_crash()
            else:
                raise
        
        if result == "xpath021_found":
            # Step 15c: Click XPath021 and continue with step17a
            try:
                if click_xpath021():
                    update_profile_status_in_file(profile_data, "Profile picture liked")
                    print("🔄 Continuing with step 14a...")
                    return True
                else:
                    return False
            except Exception as e:
                if "BROWSER_CRASHED" in str(e):
                    return handle_browser_crash()
                else:
                    raise
                
        elif result == "xpath022_found":
            # Continue with step17b
            try:
                update_profile_status_in_file(profile_data, "Already Liked")
                print("🔄 Continuing with step 14a...")
                return True
            except Exception as e:
                if "BROWSER_CRASHED" in str(e):
                    return handle_browser_crash()
                else:
                    raise
            
        elif result == "both_not_found":
            # Check internet and refresh if needed
            try:
                return handle_both_xpaths_not_found()
            except Exception as e:
                if "BROWSER_CRASHED" in str(e):
                    return handle_browser_crash()
                else:
                    raise
    
    else:
        # Step 15b: Refresh page and wait 5 seconds
        print("🔄 Refreshing page...")
        try:
            driver.refresh()
        except Exception as e:
            if "tab crashed" in str(e).lower() or "session info" in str(e).lower():
                return handle_browser_crash()
            else:
                raise
        
        # Wait 5 seconds for stability after refresh
        try:
            wait_5_seconds()
        except Exception as e:
            if "BROWSER_CRASHED" in str(e):
                return handle_browser_crash()
            else:
                raise
        
        # Check for "Like" keyword again
        try:
            like_keyword_found_after_refresh = check_like_keyword()
        except Exception as e:
            if "BROWSER_CRASHED" in str(e):
                return handle_browser_crash()
            else:
                raise
        
        if like_keyword_found_after_refresh:
            # Continue with step15a
            try:
                result = check_xpath021_and_xpath022_simultaneously()
            except Exception as e:
                if "BROWSER_CRASHED" in str(e):
                    return handle_browser_crash()
                else:
                    raise
            
            if result == "xpath021_found":
                try:
                    if click_xpath021():
                        update_profile_status_in_file(profile_data, "Profile picture liked")
                        print("🔄 Continuing with step 14a...")
                        return True
                    else:
                        return False
                except Exception as e:
                    if "BROWSER_CRASHED" in str(e):
                        return handle_browser_crash()
                    else:
                        raise
                    
            elif result == "xpath022_found":
                try:
                    update_profile_status_in_file(profile_data, "Already Liked")
                    print("🔄 Continuing with step 14a...")
                    return True
                except Exception as e:
                    if "BROWSER_CRASHED" in str(e):
                        return handle_browser_crash()
                    else:
                        raise
                    
            elif result == "both_not_found":
                try:
                    return handle_both_xpaths_not_found()
                except Exception as e:
                    if "BROWSER_CRASHED" in str(e):
                        return handle_browser_crash()
                    else:
                        raise
                    
        else:
            # Like keyword not found after refresh - go to step17c
            try:
                return handle_like_keyword_not_found()
            except Exception as e:
                if "BROWSER_CRASHED" in str(e):
                    return handle_browser_crash()
                else:
                    raise
    
    return True

# ================================
# STEP 16: OPEN PROFILE PICTURE
# ================================

def step16_open_profile_picture(profile, profile_data, XPATHS):
    """Step 16: Open profile picture from story"""
    print("\n" + "=" * 40)
    print("STEP 16: Opening profile picture")
    print("=" * 40)
    
    def wait_3_seconds():
        """Wait 3 seconds for stability"""
        print("⏳ Waiting 3 seconds for stability...")
        time.sleep(3)
        print("✅ 3 seconds wait completed")
    
    def check_see_profile_picture_keyword():
        """Check every second for 'See profile picture' keyword"""
        print("🔍 Checking for 'See profile picture' keyword...")
        start_time = time.time()
        
        while time.time() - start_time <= 30:
            elapsed = int(time.time() - start_time)
            
            try:
                page_source = driver.page_source
                if "See profile picture" in page_source:
                    print(f"\n✅ 'See profile picture' keyword found at {elapsed} seconds")
                    return True
                
                sys.stdout.write(f'\r🔍 Checking for "See profile picture"... ({elapsed}/30 seconds)')
                sys.stdout.flush()
                time.sleep(1)
                
            except Exception as e:
                print(f"\n❌ Error checking for 'See profile picture' keyword: {str(e)}")
                return False
        
        print(f"\n❌ 'See profile picture' keyword not found within 30 seconds")
        return False
    
    def check_xpath019():
        """Check for XPath019 every second for 30 seconds"""
        print("🔍 Checking for XPath019...")
        start_time = time.time()
        
        while time.time() - start_time <= 30:
            elapsed = int(time.time() - start_time)
            
            try:
                element = driver.find_element("xpath", XPATHS['xpath019'])
                print(f"\n✅ XPath019 found at {elapsed} seconds - Profile picture open button found")
                element.click()
                print("✅ XPath019 clicked - Entered profile picture")
                return True
            except NoSuchElementException:
                sys.stdout.write(f'\r🔍 Checking XPath019... ({elapsed}/30 seconds)')
                sys.stdout.flush()
                time.sleep(1)
            except Exception as e:
                print(f"\n❌ Error clicking XPath019: {str(e)}")
                return False
        
        print(f"\n❌ XPath019 not found within 30 seconds")
        return False
    
    def handle_keyword_not_found():
        """Handle case when 'See profile picture' keyword is not found"""
        print("🔄 'See profile picture' keyword not found, checking internet connection...")
        
        # Check internet connection
        if check_internet():
            print("✅ Internet is present, going to step17d")
            update_profile_status_in_file(profile_data, "See profile picture option not available user may restricted")
            print("🔄 Continuing with step 14a...")
            return True
        else:
            print("❌ Internet not available, refreshing page and continuing with step14...")
            driver.refresh()
            # Continue with step14
            return step14_process_profiles_from_waiting_file(XPATHS)
    
    def handle_xpath019_not_found():
        """Handle case when XPath019 is not found"""
        print("🔄 XPath019 not found, checking internet connection...")
        
        # Check internet connection
        if check_internet():
            print("✅ Internet is present, going to step17d")
            update_profile_status_in_file(profile_data, "See profile picture option not available user may restricted")
            print("🔄 Continuing with step 14a...")
            return True
        else:
            print("❌ Internet not available, refreshing page and continuing with step14...")
            driver.refresh()
            # Continue with step14
            return step14_process_profiles_from_waiting_file(XPATHS)
    
    def update_profile_status_in_file(profile_data, status):
        """Update profile status in waiting file"""
        file_path = PATHS["waiting_for_proceed_file"]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            profiles = content.strip().split('\n\n')
            
            # Find the profile to update
            for i, profile_block in enumerate(profiles):
                lines = profile_block.strip().split('\n')
                current_profile_data = {}
                
                for line in lines:
                    line = line.strip()
                    if line.isdigit():
                        current_profile_data['serial_number'] = line
                    elif line.startswith("Profile Link = "):
                        current_profile_data['profile_link'] = line.replace("Profile Link = ", "").strip()
                    elif line.startswith("Profile Picture Link = "):
                        current_profile_data['profile_picture_link'] = line.replace("Profile Picture Link = ", "").strip()
                    elif line.startswith("Raw Picture ID = "):
                        current_profile_data['raw_picture_id'] = line.replace("Raw Picture ID = ", "").strip()
                
                # Check if this is the profile we want to update
                if (current_profile_data.get('serial_number') == profile_data.get('serial_number') and
                    current_profile_data.get('profile_link') == profile_data.get('profile_link') and
                    current_profile_data.get('raw_picture_id') == profile_data.get('raw_picture_id')):
                    
                    # Remove existing status line if present
                    new_lines = [line for line in lines if not line.startswith("Status = ")]
                    
                    # Add new status line
                    new_lines.append(f"Status = {status}")
                    
                    profiles[i] = '\n'.join(new_lines)
                    
                    # Write the updated content back to file
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write('\n\n'.join(profiles))
                    
                    print(f"✅ Updated status to: {status}")
                    return True
            
            print(f"❌ Profile not found in file")
            return False
                
        except Exception as e:
            print(f"❌ Error updating status: {str(e)}")
            return False
    
    # Step 16: Wait 3 seconds for stability
    wait_3_seconds()
    
    # Check for "See profile picture" keyword
    keyword_found = check_see_profile_picture_keyword()
    
    if keyword_found:
        # Step 16a: Check for XPath019
        xpath019_found = check_xpath019()
        
        if xpath019_found:
            # Continue with step15
            return step15_like_profile_picture(profile, profile_data, XPATHS)
        else:
            # XPath019 not found
            return handle_xpath019_not_found()
    else:
        # Keyword not found
        return handle_keyword_not_found()
    
    return True

# ================================
# STEP 17: UPDATE STATUS IN WAITING FILE
# ================================

def update_profile_status_in_file(profile_data, status):
    """Update profile status in waiting file - Step 17"""
    file_path = PATHS["waiting_for_proceed_file"]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        profiles = content.strip().split('\n\n')
        
        # Find the profile to update
        for i, profile_block in enumerate(profiles):
            lines = profile_block.strip().split('\n')
            current_profile_data = {}
            
            for line in lines:
                line = line.strip()
                if line.isdigit():
                    current_profile_data['serial_number'] = line
                elif line.startswith("Profile Link = "):
                    current_profile_data['profile_link'] = line.replace("Profile Link = ", "").strip()
                elif line.startswith("Profile Picture Link = "):
                    current_profile_data['profile_picture_link'] = line.replace("Profile Picture Link = ", "").strip()
                elif line.startswith("Raw Picture ID = "):
                    current_profile_data['raw_picture_id'] = line.replace("Raw Picture ID = ", "").strip()
            
            # Check if this is the profile we want to update
            if (current_profile_data.get('serial_number') == profile_data.get('serial_number') and
                current_profile_data.get('profile_link') == profile_data.get('profile_link') and
                current_profile_data.get('raw_picture_id') == profile_data.get('raw_picture_id')):
                
                # Remove existing status line if present
                new_lines = [line for line in lines if not line.startswith("Status = ")]
                
                # Add new status line
                new_lines.append(f"Status = {status}")
                
                profiles[i] = '\n'.join(new_lines)
                
                # Write the updated content back to file
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write('\n\n'.join(profiles))
                
                print(f"✅ Step 17: Updated status to: {status}")
                return True
        
        print(f"❌ Profile not found in file")
        return False
            
    except Exception as e:
        print(f"❌ Error updating status: {str(e)}")
        return False

# ================================
# STEP 18: WHATSAPP REPORT FOR INVALID DATA
# ================================

def step18_whatsapp_report_invalid_data():
    """Step 18: Send WhatsApp report for invalid data in waiting file"""
    print("\n" + "=" * 40)
    print("STEP 18: WhatsApp Report for Invalid Data")
    print("=" * 40)
    
    def check_waiting_file_condition():
        """Check if waiting file is empty or has profiles without status"""
        file_path = PATHS["waiting_for_proceed_file"]
        
        try:
            if not os.path.exists(file_path):
                print("✅ Waiting file does not exist - continuing with step18")
                return True
            
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read().strip()
            
            if not content:
                print("✅ Waiting file is empty - continuing with step18")
                return True
            
            # Check if all profiles have status
            profiles = []
            current_profile = {}
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                
                if not line:
                    if current_profile:
                        profiles.append(current_profile)
                        current_profile = {}
                    continue
                
                if line.isdigit():
                    current_profile['serial_number'] = line
                elif line.startswith("Profile Link = "):
                    current_profile['profile_link'] = line.replace("Profile Link = ", "").strip()
                elif line.startswith("Profile Picture Link = "):
                    current_profile['profile_picture_link'] = line.replace("Profile Picture Link = ", "").strip()
                elif line.startswith("Raw Picture ID = "):
                    current_profile['raw_picture_id'] = line.replace("Raw Picture ID = ", "").strip()
                elif line.startswith("Status = "):
                    current_profile['status'] = line.replace("Status = ", "").strip()
            
            if current_profile:
                profiles.append(current_profile)
            
            # Check if any profile doesn't have status
            for profile in profiles:
                if 'status' not in profile:
                    print("✅ Profiles without status found - continuing with step18")
                    return True
            
            print("❌ All profiles have status - skipping step18, going to step19")
            return False
            
        except Exception as e:
            print(f"❌ Error checking waiting file: {str(e)}")
            return True
    
    def step18a_close_and_reopen_browser():
        """Step 18a: Close browser if open and reopen"""
        print("\n" + "-" * 30)
        print("STEP 18a: Closing and reopening browser")
        print("-" * 30)
        
        close_chrome()
        time.sleep(2)
        
        if not launch_chrome():
            print("❌ Failed to launch Chrome")
            return False
        return True
    
    def step18b_check_internet():
        """Step 18b: Check internet connection"""
        print("\n" + "-" * 30)
        print("STEP 18b: Checking internet connection")
        print("-" * 30)
        
        return check_internet()
    
    def step18c_open_whatsapp():
        """Step 18c: Open WhatsApp Web"""
        print("\n" + "-" * 30)
        print("STEP 18c: Opening WhatsApp Web")
        print("-" * 30)
        
        try:
            driver.get("https://web.whatsapp.com/")
            print("✅ WhatsApp Web opened successfully")
            return True
        except Exception as e:
            print(f"❌ Error opening WhatsApp: {str(e)}")
            return False
    
    def step18d_check_xpath001():
        """Step 18d: Check for XPath001 for 120 seconds"""
        print("\n" + "-" * 30)
        print("STEP 18d: Checking for XPath001 (search field)")
        print("-" * 30)
        
        # Fetch only needed XPath
        whatsapp_xpath001 = fetch_xpath_from_firebase("Xpath001", "WhatsApp")
        
        start_time = time.time()
        
        while time.time() - start_time <= 120:
            elapsed = int(time.time() - start_time)
            
            try:
                element = driver.find_element("xpath", whatsapp_xpath001)
                print(f"✅ XPath001 found at {elapsed} seconds")
                element.click()
                print("✅ Clicked XPath001 - Entered mobile number search field")
                return True
            except NoSuchElementException:
                sys.stdout.write(f'\r🔍 Checking XPath001... ({elapsed}/120 seconds)')
                sys.stdout.flush()
                time.sleep(1)
            except Exception as e:
                print(f"\n❌ Error with XPath001: {str(e)}")
                return False
        
        print(f"\n❌ XPath001 not found within 120 seconds")
        return False
    
    def step18e_check_report_number_file():
        """Step 18e: Check Report number file"""
        print("\n" + "-" * 30)
        print("STEP 18e: Checking Report number file")
        print("-" * 30)
        
        file_path = PATHS["report_number_file"]
        
        if not os.path.exists(file_path):
            print("❌ Report number file not available")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                first_line = file.readline().strip()
            
            if first_line:
                print("✅ Report number file available")
                print(f"✅ Phone number is available: {first_line}")
                return first_line
            else:
                print("❌ Phone number is not available in file")
                return False
                
        except Exception as e:
            print(f"❌ Error reading report number file: {str(e)}")
            return False
    
    def step18f_check_xpath011():
        """Step 18f: Check for XPath011 (Loading chats)"""
        print("\n" + "-" * 30)
        print("STEP 18f: Checking for XPath011 (Loading chats)")
        print("-" * 30)
        
        # Fetch only needed XPath
        whatsapp_xpath011 = fetch_xpath_from_firebase("Xpath011", "WhatsApp")
        
        try:
            element = driver.find_element("xpath", whatsapp_xpath011)
            print("✅ XPath011 found - Loading your chats")
            return True
        except NoSuchElementException:
            print("❌ XPath011 not found")
            return False
        except Exception as e:
            print(f"❌ Error with XPath011: {str(e)}")
            return False
    
    def step18g_paste_phone_number(phone_number):
        """Step 18g: Paste phone number in search field"""
        print("\n" + "-" * 30)
        print("STEP 18g: Pasting phone number")
        print("-" * 30)
        
        try:
            # Clear any existing text and paste the number
            actions = ActionChains(driver)
            actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.DELETE).perform()
            actions.send_keys(phone_number).perform()
            
            print("✅ Phone number pasted successfully")
            
            # Wait 10 seconds for stability
            print("⏳ Waiting 10 seconds for stability...")
            time.sleep(10)
            
            return True
            
        except Exception as e:
            print(f"❌ Error pasting phone number: {str(e)}")
            return False
    
    def step18h_check_xpath004():
        """Step 18h: Check for XPath004 (No chats found)"""
        print("\n" + "-" * 30)
        print("STEP 18h: Checking for XPath004 (No chats found)")
        print("-" * 30)
        
        # Fetch only needed XPath
        whatsapp_xpath004 = fetch_xpath_from_firebase("Xpath004", "WhatsApp")
        
        try:
            element = driver.find_element("xpath", whatsapp_xpath004)
            print("✅ XPath004 found - No chats, contacts or messages found")
            
            # Check internet connection
            if check_internet():
                print("❌ Invalid Mobile Number")
                return "invalid_number"
            else:
                print("❌ Internet not available")
                return "no_internet"
                
        except NoSuchElementException:
            print("✅ XPath004 not found - valid number")
            return "valid_number"
        except Exception as e:
            print(f"❌ Error with XPath004: {str(e)}")
            return "error"
    
    def step18i_press_down_enter():
        """Step 18i: Press down arrow and enter"""
        print("\n" + "-" * 30)
        print("STEP 18i: Pressing down arrow and enter")
        print("-" * 30)
        
        try:
            # Press down arrow
            actions = ActionChains(driver)
            actions.send_keys(Keys.ARROW_DOWN).perform()
            print("✅ Down arrow pressed")
            
            # Wait 2 seconds
            time.sleep(2)
            
            # Press enter
            actions.send_keys(Keys.ENTER).perform()
            print("✅ Enter pressed - Entered Message Field")
            
            return True
            
        except Exception as e:
            print(f"❌ Error pressing keys: {str(e)}")
            return False
    
    def step18j_type_message():
        """Step 18j: Type the message with Shift+Enter for newlines"""
        print("\n" + "-" * 30)
        print("STEP 18j: Typing message with proper formatting")
        print("-" * 30)
        
        try:
            current_date = datetime.now().strftime("%d-%m-%Y")
            
            # First line
            first_line = f"Facebook profile liker ({current_date})"
            # Second line
            second_line = "There is no new picture available today"
            
            # Type first line
            actions = ActionChains(driver)
            actions.send_keys(first_line).perform()
            print(f"✅ Typed: {first_line}")
            
            # Press Shift+Enter for newline (NOT send)
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
            print("✅ Pressed Shift+Enter for newline")
            
            # Type second line
            actions.send_keys(second_line).perform()
            print(f"✅ Typed: {second_line}")
            
            print("✅ Complete message typed with proper formatting")
            return True
            
        except Exception as e:
            print(f"❌ Error typing message: {str(e)}")
            return False
    
    def step18k_press_enter():
        """Step 18k: Press enter to send message"""
        print("\n" + "-" * 30)
        print("STEP 18k: Pressing enter to send message")
        print("-" * 30)
        
        try:
            # Wait 2 seconds
            time.sleep(2)
            
            # Press enter to send the complete message
            actions = ActionChains(driver)
            actions.send_keys(Keys.ENTER).perform()
            print("✅ Enter pressed - complete message sent")
            
            # Wait 2 seconds
            time.sleep(2)
            
            return True
            
        except Exception as e:
            print(f"❌ Error sending message: {str(e)}")
            return False
    
    def step18l_check_message_sent():
        """Step 18l: Check if message is sent (XPath003 disappears)"""
        print("\n" + "-" * 30)
        print("STEP 18l: Checking if message is sent")
        print("-" * 30)
        
        # Fetch only needed XPath
        whatsapp_xpath003 = fetch_xpath_from_firebase("Xpath003", "WhatsApp")
        
        start_time = time.time()
        
        while time.time() - start_time <= 300:  # 5 minutes timeout
            elapsed = int(time.time() - start_time)
            
            try:
                # Check if XPath003 (pending icon) exists
                driver.find_element("xpath", whatsapp_xpath003)
                sys.stdout.write(f'\r🔍 Message still pending... ({elapsed}/300 seconds)')
                sys.stdout.flush()
                time.sleep(1)
            except NoSuchElementException:
                print(f"\n✅ XPath003 disappeared - Report sent successfully at {elapsed} seconds")
                return True
            except Exception as e:
                print(f"\n❌ Error checking message status: {str(e)}")
                return False
        
        print(f"\n❌ Message still pending after 5 minutes")
        return False
    
    # Main Step 18 execution
    if not check_waiting_file_condition():
        print("🔄 Skipping step18 - all profiles have status, going to step19")
        return "continue_step19"
    
    # Step 18a: Close and reopen browser
    if not step18a_close_and_reopen_browser():
        return "error"
    
    # Step 18b: Check internet
    if not step18b_check_internet():
        return "error"
    
    # Step 18c: Open WhatsApp
    if not step18c_open_whatsapp():
        return "error"
    
    # Step 18d: Check XPath001
    xpath001_found = step18d_check_xpath001()
    
    if not xpath001_found:
        # Step 18f: Check XPath011
        xpath011_found = step18f_check_xpath011()
        if xpath011_found:
            # Retry step18d
            xpath001_found = step18d_check_xpath001()
            if not xpath001_found:
                # Restart from step18a
                return step18_whatsapp_report_invalid_data()
        else:
            # Restart from step18a
            return step18_whatsapp_report_invalid_data()
    
    # Step 18e: Check report number file
    phone_number = step18e_check_report_number_file()
    if not phone_number:
        print("❌ Stopping script - Report number file issue")
        return "stop_script"
    
    # Step 18g: Paste phone number
    if not step18g_paste_phone_number(phone_number):
        return "error"
    
    # Step 18h: Check XPath004
    xpath004_result = step18h_check_xpath004()
    
    if xpath004_result == "invalid_number":
        print("❌ Stopping script - Invalid mobile number")
        return "stop_script"
    elif xpath004_result == "no_internet":
        # Restart from step18a
        return step18_whatsapp_report_invalid_data()
    elif xpath004_result == "error":
        return "error"
    
    # Step 18i: Press down arrow and enter
    if not step18i_press_down_enter():
        return "error"
    
    # Step 18j: Type message
    if not step18j_type_message():
        return "error"
    
    # Step 18k: Press enter to send
    if not step18k_press_enter():
        return "error"
    
    # Step 18l: Check message sent
    if not step18l_check_message_sent():
        return "error"
    
    print("✅ Step 18 completed successfully!")
    return "stop_script"

# ================================
# STEP 19: UPLOAD TO REPORT SHEET AND WHATSAPP
# ================================

def step19_upload_to_report_and_whatsapp():
    """Step 19: Upload data to Report sheet and send WhatsApp summary"""
    print("\n" + "=" * 40)
    print("STEP 19: Upload to Report Sheet and WhatsApp")
    print("=" * 40)
    
    def parse_waiting_file():
        """Parse Waiting for proceed file and extract all profiles with status"""
        file_path = PATHS["waiting_for_proceed_file"]
        
        try:
            if not os.path.exists(file_path):
                print("❌ Waiting for proceed file not found")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read().strip()
            
            if not content:
                print("ℹ️ Waiting for proceed file is empty")
                return []
            
            profiles = []
            current_profile = {}
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                
                if not line:
                    # Empty line indicates end of current friend data
                    if current_profile:
                        profiles.append(current_profile)
                        current_profile = {}
                    continue
                
                if line.isdigit():
                    current_profile['serial_number'] = line
                elif line.startswith("Profile Link = "):
                    current_profile['profile_link'] = line.replace("Profile Link = ", "").strip()
                elif line.startswith("Profile Picture Link = "):
                    current_profile['profile_picture_link'] = line.replace("Profile Picture Link = ", "").strip()
                elif line.startswith("Raw Picture ID = "):
                    current_profile['raw_picture_id'] = line.replace("Raw Picture ID = ", "").strip()
                elif line.startswith("Status = "):
                    current_profile['status'] = line.replace("Status = ", "").strip()
            
            # Add the last profile if exists
            if current_profile:
                profiles.append(current_profile)
            
            print(f"✅ Parsed {len(profiles)} profiles from waiting file")
            return profiles
            
        except Exception as e:
            print(f"❌ Error parsing waiting file: {str(e)}")
            return []
    
    def upload_to_report_sheet(profiles):
        """Upload profiles data to Report sheet"""
        print("\n" + "-" * 30)
        print("Uploading to Report Sheet")
        print("-" * 30)
        
        # Configuration
        SPREADSHEET_NAME = "Facebook profile liker"
        REPORT_SHEET = "Report"
        
        def setup_google_sheets_client():
            """Setup and authenticate Google Sheets client"""
            try:
                scope = [
                    "https://spreadsheets.google.com/feeds",
                    "https://www.googleapis.com/auth/drive"
                ]
                
                if not os.path.exists(PATHS["google_sheets_credentials"]):
                    raise Exception(f"Credentials file not found: {PATHS['google_sheets_credentials']}")
                
                creds = Credentials.from_service_account_file(PATHS["google_sheets_credentials"], scopes=scope)
                client = gspread.authorize(creds)
                return client
            except Exception as e:
                raise Exception(f"Failed to setup Google Sheets client: {str(e)}")
        
        def prepare_data_for_upload(profiles):
            """Prepare data for Report sheet upload"""
            current_datetime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            
            report_data = []
            
            for profile in profiles:
                serial_number = profile.get('serial_number', '')
                profile_link = profile.get('profile_link', '')
                profile_picture_link = profile.get('profile_picture_link', '')
                raw_picture_id = profile.get('raw_picture_id', '')
                status = profile.get('status', '')
                
                # Prepare row data for Report sheet (7 columns)
                row_data = [
                    current_datetime,      # Column A: Date-Time
                    serial_number,         # Column B: Serial Number
                    profile_link,          # Column C: Profile Link
                    profile_picture_link,  # Column D: Profile Picture Link
                    raw_picture_id,        # Column E: Raw Picture ID
                    status,                # Column F: Status
                    ""                     # Column G: Remark (leave empty)
                ]
                
                report_data.append(row_data)
            
            print(f"📊 Prepared {len(report_data)} rows for Report sheet")
            return report_data
        
        # Unlimited retry logic for upload
        retry_count = 0
        
        while True:
            try:
                retry_count += 1
                print(f"🔄 Attempt {retry_count} to upload to Report sheet...")
                
                # Setup client
                client = setup_google_sheets_client()
                print("✅ Google Sheets client authenticated")
                
                # Prepare data
                report_data = prepare_data_for_upload(profiles)
                if not report_data:
                    print("❌ No data to upload")
                    return False
                
                # Open spreadsheet and worksheet
                spreadsheet = client.open(SPREADSHEET_NAME)
                
                try:
                    worksheet = spreadsheet.worksheet(REPORT_SHEET)
                    print("✅ Found existing Report worksheet")
                except gspread.exceptions.WorksheetNotFound:
                    print("📝 Creating new Report worksheet...")
                    worksheet = spreadsheet.add_worksheet(title=REPORT_SHEET, rows=1000, cols=10)
                    
                    # Add headers
                    headers = ["Date-Time", "Serial Number", "Profile Link", "Profile Picture Link", "Raw Picture ID", "Status", "Remark"]
                    worksheet.append_row(headers)
                    print("✅ Added headers to new Report worksheet")
                
                # Upload data (append to existing data)
                worksheet.append_rows(report_data)
                print(f"✅ Successfully uploaded {len(report_data)} rows to Report sheet")
                return True
                
            except Exception as e:
                error_message = str(e)
                if "200" in error_message:
                    print("✅ Upload successful (200 response detected)")
                    return True
                
                print(f"❌ Error during upload (Attempt {retry_count}): {error_message}")
                print("🔄 Retrying in 10 seconds...")
                time.sleep(10)
    
    def analyze_status_counts(profiles):
        """Analyze status counts for WhatsApp message"""
        status_counts = {
            "Profile picture liked": 0,
            "Already Liked": 0,
            "Like option not available user may restricted": 0,
            "See profile picture option not available user may restricted": 0,
            "Can't open profile picture or story": 0
        }
        
        for profile in profiles:
            status = profile.get('status', '')
            if status in status_counts:
                status_counts[status] += 1
        
        print("📊 Status Analysis:")
        for status, count in status_counts.items():
            print(f"   - {status}: {count}")
        
        return status_counts
    
    def step19_whatsapp_report(status_counts):
        """Step 19 WhatsApp reporting with proper message formatting"""
        print("\n" + "=" * 30)
        print("STEP 19 WhatsApp Report")
        print("=" * 30)
        
        def step19a_close_and_reopen_browser():
            """Step 19a: Close browser if open and reopen"""
            print("\n" + "-" * 20)
            print("STEP 19a: Closing and reopening browser")
            print("-" * 20)
            
            close_chrome()
            time.sleep(2)
            
            if not launch_chrome():
                print("❌ Failed to launch Chrome")
                return False
            return True
        
        def step19b_check_internet():
            """Step 19b: Check internet connection"""
            print("\n" + "-" * 20)
            print("STEP 19b: Checking internet connection")
            print("-" * 20)
            
            return check_internet()
        
        def step19c_open_whatsapp():
            """Step 19c: Open WhatsApp Web"""
            print("\n" + "-" * 20)
            print("STEP 19c: Opening WhatsApp Web")
            print("-" * 20)
            
            try:
                driver.get("https://web.whatsapp.com/")
                print("✅ WhatsApp Web opened successfully")
                return True
            except Exception as e:
                print(f"❌ Error opening WhatsApp: {str(e)}")
                return False
        
        def step19d_check_xpath001():
            """Step 19d: Check for XPath001 for 120 seconds"""
            print("\n" + "-" * 20)
            print("STEP 19d: Checking for XPath001 (search field)")
            print("-" * 20)
            
            # Fetch only needed XPath
            whatsapp_xpath001 = fetch_xpath_from_firebase("Xpath001", "WhatsApp")
            
            start_time = time.time()
            
            while time.time() - start_time <= 120:
                elapsed = int(time.time() - start_time)
                
                try:
                    element = driver.find_element("xpath", whatsapp_xpath001)
                    print(f"✅ XPath001 found at {elapsed} seconds")
                    element.click()
                    print("✅ Clicked XPath001 - Entered mobile number search field")
                    return True
                except NoSuchElementException:
                    sys.stdout.write(f'\r🔍 Checking XPath001... ({elapsed}/120 seconds)')
                    sys.stdout.flush()
                    time.sleep(1)
                except Exception as e:
                    print(f"\n❌ Error with XPath001: {str(e)}")
                    return False
            
            print(f"\n❌ XPath001 not found within 120 seconds")
            return False
        
        def step19e_check_report_number_file():
            """Step 19e: Check Report number file"""
            print("\n" + "-" * 20)
            print("STEP 19e: Checking Report number file")
            print("-" * 20)
            
            file_path = PATHS["report_number_file"]
            
            if not os.path.exists(file_path):
                print("❌ Report number file not available")
                return False
            
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    first_line = file.readline().strip()
                
                if first_line:
                    print("✅ Report number file available")
                    print(f"✅ Phone number is available: {first_line}")
                    return first_line
                else:
                    print("❌ Phone number is not available in file")
                    return False
                    
            except Exception as e:
                print(f"❌ Error reading report number file: {str(e)}")
                return False
        
        def step19f_check_xpath011():
            """Step 19f: Check for XPath011 (Loading chats)"""
            print("\n" + "-" * 20)
            print("STEP 19f: Checking for XPath011 (Loading chats)")
            print("-" * 20)
            
            # Fetch only needed XPath
            whatsapp_xpath011 = fetch_xpath_from_firebase("Xpath011", "WhatsApp")
            
            try:
                element = driver.find_element("xpath", whatsapp_xpath011)
                print("✅ XPath011 found - Loading your chats")
                return True
            except NoSuchElementException:
                print("❌ XPath011 not found")
                return False
            except Exception as e:
                print(f"❌ Error with XPath011: {str(e)}")
                return False
        
        def step19g_paste_phone_number(phone_number):
            """Step 19g: Paste phone number in search field"""
            print("\n" + "-" * 20)
            print("STEP 19g: Pasting phone number")
            print("-" * 20)
            
            try:
                # Clear any existing text and paste the number
                actions = ActionChains(driver)
                actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.DELETE).perform()
                actions.send_keys(phone_number).perform()
                
                print("✅ Phone number pasted successfully")
                
                # Wait 10 seconds for stability
                print("⏳ Waiting 10 seconds for stability...")
                time.sleep(10)
                
                return True
                
            except Exception as e:
                print(f"❌ Error pasting phone number: {str(e)}")
                return False
        
        def step19h_check_xpath004():
            """Step 19h: Check for XPath004 (No chats found)"""
            print("\n" + "-" * 20)
            print("STEP 19h: Checking for XPath004 (No chats found)")
            print("-" * 20)
            
            # Fetch only needed XPath
            whatsapp_xpath004 = fetch_xpath_from_firebase("Xpath004", "WhatsApp")
            
            try:
                element = driver.find_element("xpath", whatsapp_xpath004)
                print("✅ XPath004 found - No chats, contacts or messages found")
                
                # Check internet connection
                if check_internet():
                    print("❌ Invalid Mobile Number")
                    return "invalid_number"
                else:
                    print("❌ Internet not available")
                    return "no_internet"
                    
            except NoSuchElementException:
                print("✅ XPath004 not found - valid number")
                return "valid_number"
            except Exception as e:
                print(f"❌ Error with XPath004: {str(e)}")
                return "error"
        
        def step19i_press_down_enter():
            """Step 19i: Press down arrow and enter"""
            print("\n" + "-" * 20)
            print("STEP 19i: Pressing down arrow and enter")
            print("-" * 20)
            
            try:
                # Press down arrow
                actions = ActionChains(driver)
                actions.send_keys(Keys.ARROW_DOWN).perform()
                print("✅ Down arrow pressed")
                
                # Wait 2 seconds
                time.sleep(2)
                
                # Press enter
                actions.send_keys(Keys.ENTER).perform()
                print("✅ Enter pressed - Entered Message Field")
                
                return True
                
            except Exception as e:
                print(f"❌ Error pressing keys: {str(e)}")
                return False
        
        def step19j_type_message(status_counts):
            """Step 19j: Type the summary message with Shift+Enter for newlines"""
            print("\n" + "-" * 20)
            print("STEP 19j: Typing summary message with proper formatting")
            print("-" * 20)
            
            try:
                current_date = datetime.now().strftime("%d-%m-%Y")
                
                # Use double quotes for the f-string to avoid single quote issues
                cant_open_key = "Can't open profile picture or story"
                
                # Build message lines
                message_lines = [
                    f"Facebook profile liker ({current_date})",
                    f"Profile picture liked = {status_counts['Profile picture liked']}",
                    f"Already Liked = {status_counts['Already Liked']}",
                    f"Like option not available user may restricted = {status_counts['Like option not available user may restricted']}",
                    f"See profile picture option not available user may restricted = {status_counts['See profile picture option not available user may restricted']}",
                    f"Can't open profile picture or story = {status_counts[cant_open_key]}"
                ]
                
                # Type each line with Shift+Enter for newlines
                actions = ActionChains(driver)
                
                # Type first line
                actions.send_keys(message_lines[0]).perform()
                print(f"✅ Typed: {message_lines[0]}")
                
                # Type remaining lines with Shift+Enter before each
                for i in range(1, len(message_lines)):
                    # Press Shift+Enter for newline (NOT send)
                    actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
                    print("✅ Pressed Shift+Enter for newline")
                    
                    # Type the line
                    actions.send_keys(message_lines[i]).perform()
                    print(f"✅ Typed: {message_lines[i]}")
                
                print("✅ Complete summary message typed with proper formatting")
                return True
                
            except Exception as e:
                print(f"❌ Error typing message: {str(e)}")
                return False
        
        def step19k_press_enter():
            """Step 19k: Press enter to send message"""
            print("\n" + "-" * 20)
            print("STEP 19k: Pressing enter to send message")
            print("-" * 20)
            
            try:
                # Wait 2 seconds
                time.sleep(2)
                
                # Press enter to send the complete message
                actions = ActionChains(driver)
                actions.send_keys(Keys.ENTER).perform()
                print("✅ Enter pressed - complete summary message sent")
                
                # Wait 2 seconds
                time.sleep(2)
                
                return True
                
            except Exception as e:
                print(f"❌ Error sending message: {str(e)}")
                return False
        
        def step19l_check_message_sent():
            """Step 19l: Check if message is sent (XPath003 disappears)"""
            print("\n" + "-" * 20)
            print("STEP 19l: Checking if message is sent")
            print("-" * 20)
            
            # Fetch only needed XPath
            whatsapp_xpath003 = fetch_xpath_from_firebase("Xpath003", "WhatsApp")
            
            start_time = time.time()
            
            while time.time() - start_time <= 300:  # 5 minutes timeout
                elapsed = int(time.time() - start_time)
                
                try:
                    # Check if XPath003 (pending icon) exists
                    driver.find_element("xpath", whatsapp_xpath003)
                    sys.stdout.write(f'\r🔍 Message still pending... ({elapsed}/300 seconds)')
                    sys.stdout.flush()
                    time.sleep(1)
                except NoSuchElementException:
                    print(f"\n✅ XPath003 disappeared - Summary report sent successfully at {elapsed} seconds")
                    return True
                except Exception as e:
                    print(f"\n❌ Error checking message status: {str(e)}")
                    return False
            
            print(f"\n❌ Message still pending after 5 minutes")
            return False
        
        # Step 19a: Close and reopen browser
        if not step19a_close_and_reopen_browser():
            return False
        
        # Step 19b: Check internet
        if not step19b_check_internet():
            return False
        
        # Step 19c: Open WhatsApp
        if not step19c_open_whatsapp():
            return False
        
        # Step 19d: Check XPath001
        xpath001_found = step19d_check_xpath001()
        
        if not xpath001_found:
            # Step 19f: Check XPath011
            xpath011_found = step19f_check_xpath011()
            if xpath011_found:
                # Retry step19d
                xpath001_found = step19d_check_xpath001()
                if not xpath001_found:
                    # Restart from step19a
                    return step19_whatsapp_report(status_counts)
            else:
                # Restart from step19a
                return step19_whatsapp_report(status_counts)
        
        # Step 19e: Check report number file
        phone_number = step19e_check_report_number_file()
        if not phone_number:
            print("❌ Stopping script - Report number file issue")
            return False
        
        # Step 19g: Paste phone number
        if not step19g_paste_phone_number(phone_number):
            return False
        
        # Step 19h: Check XPath004
        xpath004_result = step19h_check_xpath004()
        
        if xpath004_result == "invalid_number":
            print("❌ Stopping script - Invalid mobile number")
            return False
        elif xpath004_result == "no_internet":
            # Restart from step19a
            return step19_whatsapp_report(status_counts)
        elif xpath004_result == "error":
            return False
        
        # Step 19i: Press down arrow and enter
        if not step19i_press_down_enter():
            return False
        
        # Step 19j: Type message
        if not step19j_type_message(status_counts):
            return False
        
        # Step 19k: Press enter to send
        if not step19k_press_enter():
            return False
        
        # Step 19l: Check message sent
        if not step19l_check_message_sent():
            return False
        
        print("✅ Step 19 WhatsApp report completed successfully!")
        return True
    
    # Main Step 19 execution
    # Step 1: Parse waiting file
    profiles = parse_waiting_file()
    if not profiles:
        print("❌ No profiles found in waiting file")
        return False
    
    # Step 2: Upload to Report sheet
    if not upload_to_report_sheet(profiles):
        print("❌ Failed to upload to Report sheet")
        return False
    
    # Step 3: Analyze status counts
    status_counts = analyze_status_counts(profiles)
    
    # Step 4: Send WhatsApp report
    if not step19_whatsapp_report(status_counts):
        print("❌ Failed to send WhatsApp report")
        return False
    
    print("✅ Step 19 completed successfully!")
    return True

# ================================
# IMPROVED MAIN EXECUTION FLOW
# ================================

def main():
    """Main execution flow for Facebook Profile Liker Bot"""
    print("=" * 60)
    print("🚀 STARTING FACEBOOK PROFILE LIKER BOT")
    print("=" * 60)
    
    # Create required directories first
    create_required_directories()
    
    # Verify required files exist
    if not verify_required_files():
        print("❌ Required files missing. Please check configuration.")
        sys.exit(1)
    
    # Initialize Firebase
    if not initialize_firebase():
        print("❌ Cannot continue without Firebase connection")
        return
    
    # Fetch ONLY NEEDED XPaths to avoid unnecessary Firebase calls
    print("🔍 Fetching required XPaths from Firebase...")
    try:
        XPATHS = {
            'xpath012': fetch_xpath_from_firebase("Xpath012"),
            'xpath013': fetch_xpath_from_firebase("Xpath013"),
            'xpath014': fetch_xpath_from_firebase("Xpath014"),
            'xpath017': fetch_xpath_from_firebase("Xpath017"),
            'xpath018': fetch_xpath_from_firebase("Xpath018"),
            'xpath019': fetch_xpath_from_firebase("Xpath019"),
            'xpath020': fetch_xpath_from_firebase("Xpath020"),
            'xpath021': fetch_xpath_from_firebase("Xpath021"),
            'xpath022': fetch_xpath_from_firebase("Xpath022")
        }
        print("✅ Required XPaths fetched successfully")
    except Exception as e:
        print(f"❌ Failed to fetch XPaths: {str(e)}")
        return
    
    # Track if we need to restart from step14
    restart_from_step14 = False
    
    # Main loop - restart from Step1 if needed
    while True:
        try:
            if not restart_from_step14:
                # Normal flow - start from Step 1
                # STEP 1: Check internet connection
                print("\n" + "=" * 40)
                print("STEP 1: Checking internet connection...")
                print("=" * 40)
                check_internet()
                
                # STEP 2: Check and close Chrome if open
                print("\n" + "=" * 40)
                print("STEP 2: Checking Chrome browser status...")
                print("=" * 40)
                check_and_close_chrome()
                
                # STEP 3: Launch Chrome with Facebook
                print("\n" + "=" * 40)
                print("STEP 3: Launching Chrome browser...")
                print("=" * 40)
                if not launch_chrome():
                    print("❌ Failed to launch Chrome, restarting from Step 1...")
                    continue
                
                # STEP 4: Wait for stability
                print("\n" + "=" * 40)
                print("STEP 4: Waiting for stability...")
                print("=" * 40)
                wait_for_stability(10)
                
                # STEP 5: Check and click XPath012
                print("\n" + "=" * 40)
                print("STEP 5: Checking XPath012 availability...")
                print("=" * 40)
                xpath012_clicked = check_and_click_xpath012_optimized(XPATHS['xpath012'])
                
                if not xpath012_clicked:
                    print("❌ XPath012 not found within 50 seconds, restarting from Step 1...")
                    close_chrome()
                    continue
                
                # STEP 6: Wait for stability
                print("\n" + "=" * 40)
                print("STEP 6: Waiting for stability...")
                print("=" * 40)
                wait_3_seconds()
                
                # NEW CHECK: Look for "Add to story" keyword
                print("\n" + "=" * 40)
                print("CHECKING FOR 'ADD TO STORY' KEYWORD...")
                print("=" * 40)
                add_to_story_found = check_for_add_to_story()
                
                if not add_to_story_found:
                    print("❌ 'Add to story' keyword not found within 30 seconds, restarting from Step 1...")
                    close_chrome()
                    continue
                
                # STEP 7: Combine URLs and navigate
                print("\n" + "=" * 40)
                print("STEP 7: Combining URLs and navigating...")
                print("=" * 40)
                if not combine_url_and_navigate():
                    print("❌ Failed to combine URLs, restarting from Step 1...")
                    close_chrome()
                    continue
                
                # STEP 8: Find XPath013 with Page Down
                print("\n" + "=" * 40)
                print("STEP 8: Finding XPath013 with Page Down...")
                print("=" * 40)
                xpath013_found = find_xpath013_with_page_down_optimized(XPATHS['xpath013'])
                
                if not xpath013_found:
                    print("❌ XPath013 not found within 10 minutes, restarting from Step 1...")
                    close_chrome()
                    continue
                
                # STEP 9: Manage Current Friends File
                print("\n" + "=" * 40)
                print("STEP 9: Managing Current Friends file...")
                print("=" * 40)
                if not manage_current_friends_file():
                    print("❌ Failed to manage Current Friends file, restarting from Step 1...")
                    close_chrome()
                    continue
                
                # STEP 10: Collect Friends Data
                print("\n" + "=" * 40)
                print("STEP 10: Collecting friends data...")
                print("=" * 40)
                if not collect_friends_data_optimized(XPATHS['xpath014']):
                    print("❌ Failed to collect friends data, restarting from Step 1...")
                    close_chrome()
                    continue

                # STEP 11: Filter and click default pictures
                print("\n" + "=" * 40)
                print("STEP 11: Filtering and clicking default pictures...")
                print("=" * 40)
                if not step11_filter_and_click_default_pictures():
                    print("❌ Failed to process default pictures, restarting from Step 1...")
                    close_chrome()
                    continue

                # STEP 12: Upload to Google Sheets
                print("\n" + "=" * 40)
                print("STEP 12: Uploading to Google Sheets...")
                print("=" * 40)
                if not step12_upload_to_google_sheets():
                    print("❌ Failed to upload to Google Sheets, restarting from Step 1...")
                    close_chrome()
                    continue

                # STEP 13: Compare and create waiting file
                print("\n" + "=" * 40)
                print("STEP 13: Comparing sheets and creating waiting file...")
                print("=" * 40)
                if not step13_compare_and_create_waiting_file():
                    print("❌ Failed to compare sheets and create waiting file, restarting from Step 1...")
                    close_chrome()
                    continue

            # Reset the flag
            restart_from_step14 = False

            # STEP 14-17: Process profiles from waiting file
            print("\n" + "=" * 40)
            print("STEP 14-17: Processing profiles from waiting file...")
            print("=" * 40)
            
            # Keep processing profiles until all have status
            while True:
                result = step14_process_profiles_from_waiting_file(XPATHS)
                
                if result == "continue_step18":
                    print("✅ All profiles processed, continuing with step18")
                    break
                elif result == "continue_step14a":
                    print("🔄 Continuing to process next profile...")
                    continue
                elif result == "RESTART_FROM_STEP14":
                    print("🔄 Browser crashed, restarting from step14...")
                    restart_from_step14 = True
                    break
                else:
                    print("🔄 Continuing to process profiles...")
                    continue
            
            # If we need to restart from step14, continue the outer loop
            if restart_from_step14:
                continue

            print(f"\n🎉 BOT COMPLETED SUCCESSFULLY UP TO STEP 17!")
            print("📊 All profiles processed and status updated in waiting file")
            
            # STEP 18: WhatsApp Report for Invalid Data
            print("\n" + "=" * 40)
            print("STEP 18: WhatsApp Report for Invalid Data")
            print("=" * 40)
            
            step18_result = step18_whatsapp_report_invalid_data()
            
            if step18_result == "continue_step19":
                print("🔄 Continuing with step19...")
            elif step18_result == "stop_script":
                print("🛑 Script stopped as requested")
                break
            elif step18_result == "error":
                print("❌ Error in step18, restarting from step1...")
                continue
            
            # STEP 19: Upload to Report Sheet and WhatsApp Summary
            print("\n" + "=" * 40)
            print("STEP 19: Upload to Report Sheet and WhatsApp Summary")
            print("=" * 40)
            
            if step19_upload_to_report_and_whatsapp():
                print("🎉 BOT COMPLETED ALL STEPS SUCCESSFULLY!")
                break
            else:
                print("❌ Error in step19, restarting from step1...")
                continue
            
        except KeyboardInterrupt:
            print("\n🛑 Process interrupted by user")
            break
        except Exception as e:
            error_msg = str(e)
            if "BROWSER_CRASHED" in error_msg:
                print("🔄 Browser crashed, restarting from step14...")
                restart_from_step14 = True
                continue
            elif "tab crashed" in error_msg.lower() or "session info" in error_msg.lower():
                print("🔄 Browser tab crashed, restarting from step14...")
                restart_from_step14 = True
                continue
            else:
                print(f"❌ Unexpected error in main flow: {str(e)}")
                print("🔄 Restarting from Step 1...")
                close_chrome()
                continue

# ================================
# CLEANUP FUNCTION
# ================================

def cleanup():
    """Cleanup function to close browser and exit"""
    print("\n🧹 Performing cleanup...")
    close_chrome()
    print("✅ Cleanup completed")

# ================================
# EXECUTION
# ================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Script stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
    finally:
        cleanup()
