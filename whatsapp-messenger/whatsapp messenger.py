import psutil
import time
import subprocess
import os
import gspread
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from google.oauth2.service_account import Credentials
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db

# ==================== CONFIGURABLE SETTINGS ====================
# Automatically detect Raspberry Pi username
USER_HOME = os.path.expanduser("~")  # This automatically gets the current user's home directory
BOTS_DIR = os.path.join(USER_HOME, "bots")
WHATSAPP_BOT_DIR = os.path.join(BOTS_DIR, "whatsapp messenger")

# File paths
SPREADSHEET_KEY_FILE = os.path.join(WHATSAPP_BOT_DIR, "venv", "spread sheet access key.json")
FIREBASE_CREDENTIALS = os.path.join(WHATSAPP_BOT_DIR, "venv", "database access key.json")  # CORRECTED PATH
REPORT_NUMBER_FILE = os.path.join(WHATSAPP_BOT_DIR, "venv", "report number")

# Browser settings
CHROMEDRIVER_PATH = "/usr/bin/chromedriver"
CHROME_PROFILE_PATH = os.path.join(USER_HOME, ".config", "chromium")

# Application settings
SPREADSHEET_NAME = "whatsapp messenger"

# Firebase settings
FIREBASE_DB_URL = "https://thaniyanki-xpath-manager-default-rtdb.firebaseio.com/"  # Update with your actual Firebase URL

# XPath file
XPATH_FILE = os.path.join(WHATSAPP_BOT_DIR, "whatsapp_xpaths.txt")
# ==================== END CONFIGURABLE SETTINGS ====================

# Global driver variable
driver = None
# Global variable to store program start time
PROGRAM_START_TIME = None
# Global dictionary to store all XPaths
XPATH_CACHE = {}

def initialize_firebase():
    """Initialize Firebase app"""
    try:
        # Check if already initialized
        if not firebase_admin._apps:
            if not os.path.exists(FIREBASE_CREDENTIALS):
                print(f"❌ Firebase credentials file not found: {FIREBASE_CREDENTIALS}")
                return False
            cred = credentials.Certificate(FIREBASE_CREDENTIALS)
            firebase_admin.initialize_app(cred, {
                'databaseURL': FIREBASE_DB_URL
            })
            print("✅ Firebase initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Error initializing Firebase: {str(e)}")
        return False

def import_all_xpaths_from_database():
    """Import all XPaths from Firebase database and save to local file"""
    global XPATH_CACHE
    
    try:
        print("🔄 Importing all XPaths from database...")
        
        # Initialize Firebase
        if not initialize_firebase():
            print("❌ Failed to initialize Firebase")
            return False
        
        # Get reference to WhatsApp XPaths
        whatsapp_ref = db.reference("WhatsApp/Xpath")
        xpath_data = whatsapp_ref.get()
        
        if not xpath_data:
            print("❌ No XPath data found in Firebase")
            return False
        
        # Store in global cache
        XPATH_CACHE = xpath_data.copy()
        print(f"✅ Loaded {len(XPATH_CACHE)} XPaths into memory")
        
        # Delete existing XPath file if it exists
        if os.path.exists(XPATH_FILE):
            os.remove(XPATH_FILE)
            print("✅ Deleted existing XPath file")
        
        # Save to local file
        with open(XPATH_FILE, 'w', encoding='utf-8') as file:
            for key, value in xpath_data.items():
                file.write(f"{key}={value}\n")
        
        print(f"✅ Successfully imported {len(xpath_data)} XPaths and saved to {XPATH_FILE}")
        return True
        
    except Exception as e:
        print(f"❌ Error importing XPaths from database: {str(e)}")
        return False

def load_xpaths_from_file():
    """Load XPaths from local file into memory"""
    global XPATH_CACHE
    
    try:
        if not os.path.exists(XPATH_FILE):
            print(f"❌ XPath file not found: {XPATH_FILE}")
            return False
        
        XPATH_CACHE = {}
        with open(XPATH_FILE, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    XPATH_CACHE[key.strip()] = value.strip()
        
        print(f"✅ Loaded {len(XPATH_CACHE)} XPaths from local file")
        return True
        
    except Exception as e:
        print(f"❌ Error loading XPaths from file: {str(e)}")
        return False

def delete_xpath_file():
    """Delete the local XPath file after bot completion"""
    try:
        if os.path.exists(XPATH_FILE):
            os.remove(XPATH_FILE)
            print("✅ Deleted local XPath file after bot completion")
        return True
    except Exception as e:
        print(f"❌ Error deleting XPath file: {str(e)}")
        return False

def get_xpath_from_cache(xpath_number):
    """Get XPath selector from local cache (memory)"""
    global XPATH_CACHE
    
    try:
        # Construct the XPath key (e.g., "Xpath001", "Xpath002")
        xpath_key = f"Xpath{xpath_number.zfill(3)}"  # This will convert "1" to "Xpath001", "2" to "Xpath002", etc.
        
        # Get the requested XPath from cache
        xpath_selector = XPATH_CACHE.get(xpath_key)
        
        if xpath_selector:
            print(f"📋 Using {xpath_key} from local cache")
            return xpath_selector
        else:
            print(f"❌ {xpath_key} not found in local cache")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching Xpath{xpath_number} from cache: {str(e)}")
        return None

def initialize_xpaths():
    """Initialize XPaths - import from database or load from file"""
    # First try to load from local file (if it exists from previous run)
    if os.path.exists(XPATH_FILE):
        print("📁 Found existing XPath file, loading from local file...")
        if load_xpaths_from_file():
            return True
        else:
            print("❌ Failed to load from local file, importing from database...")
    
    # If local file doesn't exist or failed to load, import from database
    print("🌐 Importing XPaths from database...")
    return import_all_xpaths_from_database()

def step1_close_chromium_browser():
    """Step 1: Check if Chromium browser is open and close it."""
    print("\n=== Step 1: Checking and closing Chromium browser ===")
    
    try:
        chromium_closed = False
        
        # Check for Chromium processes
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                process_name = proc.info['name'].lower()
                process_pid = proc.info['pid']
                
                # Close Chromium browser processes
                if process_name in ['chromium', 'chromium-browser', 'chrome']:
                    try:
                        proc.kill()
                        print(f"Closed {process_name} process (PID: {process_pid})")
                        chromium_closed = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        print(f"Could not close {process_name} (PID: {process_pid}): {e}")
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if chromium_closed:
            print("Chromium browser closed successfully.")
        else:
            print("No Chromium browser processes found running.")
        
        # Wait 2 seconds to ensure processes are fully terminated
        time.sleep(2)
        return True
        
    except Exception as e:
        print(f"Error during Step 1: {str(e)}")
        return False

def step2_check_internet_connection():
    """Step 2: Check internet connection using ping method."""
    print("\n=== Step 2: Checking internet connection ===")
    
    def check_internet():
        """Checks for an active internet connection using ping."""
        try:
            subprocess.check_call(["ping", "-c", "1", "8.8.8.8"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False
    
    # Check internet immediately first
    if check_internet():
        print("Internet is present good to go")
        return True
    else:
        # If no internet, wait and retry every second with single-line count
        count = 1
        print("Internet is not present waiting upto...1", end="", flush=True)
        
        while True:
            if check_internet():
                print("\nInternet is present good to go")
                return True
            
            time.sleep(1)  # Wait 1 second before next check
            count += 1
            print(f"\rInternet is not present waiting upto...{count}", end="", flush=True)

def step3_import_spreadsheet_data():
    """Step 3: Import data from Google Spreadsheet to Receiver list.txt"""
    print("\n=== Step 3: Importing data from spreadsheet ===")
    
    # Use centralized configuration
    OUTPUT_FILE = os.path.join(WHATSAPP_BOT_DIR, "Receiver list.txt")
    SHEET_NAME = "Receiver list"
    
    def setup_google_sheets_client():
        """Setup and authenticate Google Sheets client"""
        try:
            # Define the scope
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            
            # Authenticate and create client
            creds = Credentials.from_service_account_file(SPREADSHEET_KEY_FILE, scopes=scope)
            client = gspread.authorize(creds)
            return client
        except Exception as e:
            raise Exception(f"Failed to setup Google Sheets client: {str(e)}")
    
    def get_spreadsheet_data(client):
        """Get data from the spreadsheet"""
        try:
            # Open the spreadsheet
            spreadsheet = client.open(SPREADSHEET_NAME)
            
            # Select the specific worksheet
            worksheet = spreadsheet.worksheet(SHEET_NAME)
            
            # Get all values from the worksheet
            all_data = worksheet.get_all_values()
            
            return all_data
        except Exception as e:
            raise Exception(f"Failed to get spreadsheet data: {str(e)}")
    
    def format_data_for_output(all_data):
        """Format the spreadsheet data for text file output - SKIP ROWS without Country Code or WhatsApp Number"""
        formatted_lines = []
        
        # Check if we have data (including header)
        if len(all_data) == 0:
            return ["No data found in spreadsheet"]
        
        # Skip the header row (index 0) and start from actual data (index 1)
        data_rows = all_data[1:] if len(all_data) > 1 else []
        
        if len(data_rows) == 0:
            return ["No data rows found (only header row present)"]
        
        print(f"Processing {len(data_rows)} data rows (excluding header)")
        
        # Process each data row - SKIP ROWS without Country Code or WhatsApp Number
        skipped_rows = 0
        for row_index, row in enumerate(data_rows):
            # Ensure row has at least 10 columns, pad with empty strings if needed
            while len(row) < 10:
                row.append("")
            
            # Get individual values with default for empty cells
            date_time = row[0] if row[0].strip() else "Empty Cell"
            name = row[1] if row[1].strip() else "Empty Cell"
            country_code = row[2] if row[2].strip() else "Empty Cell"
            whatsapp_number = row[3] if row[3].strip() else "Empty Cell"
            message = row[4] if row[4].strip() else "Empty Cell"
            image_path = row[5] if row[5].strip() else "Empty Cell"
            document_path = row[6] if row[6].strip() else "Empty Cell"
            audio_path = row[7] if row[7].strip() else "Empty Cell"
            video_path = row[8] if row[8].strip() else "Empty Cell"
            remark = row[9] if row[9].strip() else "Empty Cell"
            
            # SKIP ROW if Country Code or WhatsApp Number is empty
            if country_code == "Empty Cell" or whatsapp_number == "Empty Cell":
                print(f"⚠️ Skipping Row{row_index + 2} - Missing Country Code or WhatsApp Number")
                skipped_rows += 1
                continue
            
            # Format the output for this row (Row index starts from 2 since we skipped header)
            formatted_lines.append(f"Row{row_index + 2}:")
            formatted_lines.append(f"Date-Time = {date_time}")
            formatted_lines.append(f"Name = {name}")
            formatted_lines.append(f"Country Code = {country_code}")
            formatted_lines.append(f"WhatsApp Number = {whatsapp_number}")
            formatted_lines.append(f"Message = {message}")
            formatted_lines.append(f"Image | Photo Path = {image_path}")
            formatted_lines.append(f"Document Path = {document_path}")
            formatted_lines.append(f"Audio Path = {audio_path}")
            formatted_lines.append(f"Video Path = {video_path}")
            formatted_lines.append(f"Remark = {remark}")
            formatted_lines.append("")  # Empty line between rows
        
        print(f"✅ Imported {len(data_rows) - skipped_rows} valid rows, skipped {skipped_rows} invalid rows")
        return formatted_lines
    
    def save_to_text_file(formatted_lines):
        """Save formatted data to text file"""
        try:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as file:
                for line in formatted_lines:
                    file.write(line + '\n')
            print(f"Data successfully saved to {OUTPUT_FILE}")
            return True
        except Exception as e:
            raise Exception(f"Failed to save data to file: {str(e)}")
    
    # Main execution with continuous retry on errors
    retry_count = 0
    max_retries = 10  # Maximum number of retries
    
    while retry_count < max_retries:
        try:
            print(f"Attempt {retry_count + 1} to fetch spreadsheet data...")
            
            # Setup Google Sheets client
            client = setup_google_sheets_client()
            print("Google Sheets client authenticated successfully")
            
            # Get data from spreadsheet
            all_data = get_spreadsheet_data(client)
            print(f"Retrieved {len(all_data)} total rows from spreadsheet (including header)")
            
            # Format data for output
            formatted_lines = format_data_for_output(all_data)
            print("Data formatted successfully")
            
            # Save to text file
            if save_to_text_file(formatted_lines):
                print("Step 3 completed successfully!")
                return True
            
        except Exception as e:
            retry_count += 1
            error_message = str(e)
            print(f"Error during Step 3 (Attempt {retry_count}): {error_message}")
            
            # Check if we should continue retrying
            if retry_count < max_retries:
                print(f"Retrying in 5 seconds... (Attempt {retry_count + 1}/{max_retries})")
                time.sleep(5)
            else:
                print(f"Maximum retries ({max_retries}) reached. Failed to complete Step 3.")
                return False
    
    return False

def update_row_status_in_receiver_list(row_number, status):
    """Update Row line with status like 'Row2:Processed successfully' or 'Row2:Invalid WhatsApp Number'"""
    try:
        RECEIVER_LIST_FILE = os.path.join(WHATSAPP_BOT_DIR, "Receiver list.txt")
        
        if not os.path.isfile(RECEIVER_LIST_FILE):
            print(f"Receiver list file '{RECEIVER_LIST_FILE}' not found")
            return False
        
        # Read the current file
        with open(RECEIVER_LIST_FILE, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        updated = False
        
        # Find and update the Row line
        for i, line in enumerate(lines):
            if line.startswith(f"Row{row_number}:"):
                # Update the Row line with status
                lines[i] = f"Row{row_number}:{status}\n"
                updated = True
                print(f"Updated Row{row_number} status to: {status}")
                break
        
        if updated:
            # Write the updated content back to the file
            with open(RECEIVER_LIST_FILE, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            print(f"✅ Successfully updated Row{row_number} status in Receiver list.txt")
            return True
        else:
            print(f"❌ Could not find Row{row_number} to update")
            return False
            
    except Exception as e:
        print(f"❌ Error updating Row status: {str(e)}")
        return False

def get_caption_for_media(media_file_path):
    """Get a random caption from Caption.txt file in the same location as media file"""
    try:
        if not media_file_path:
            return None
            
        # Get the directory of the media file
        media_directory = os.path.dirname(media_file_path)
        caption_file_path = os.path.join(media_directory, "Caption.txt")
        
        # Check if Caption.txt exists in the same directory
        if os.path.exists(caption_file_path):
            with open(caption_file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # Filter out empty lines and get non-empty captions
            captions = [line.strip() for line in lines if line.strip()]
            
            if captions:
                # Select a random caption
                random_caption = random.choice(captions)
                print(f"📝 Selected random caption from {caption_file_path}")
                return random_caption
            else:
                print(f"ℹ️ Caption.txt found but no captions available in {caption_file_path}")
                return None
        else:
            print(f"ℹ️ No Caption.txt found in {media_directory}")
            return None
            
    except Exception as e:
        print(f"❌ Error reading caption file: {str(e)}")
        return None

def find_media_file(base_path):
    """
    Enhanced media file finding logic:
    1. If base_path is a specific file: Use it directly
    2. If base_path is a directory:
       a. First check for current date folder (DD-MM-YYYY)
       b. If current date folder exists and has files: Use random file from there
       c. If current date folder doesn't exist or is empty: Use random file from base directory
    3. If no files found anywhere: Return None
    """
    try:
        print(f"🔍 Searching for media file in: {base_path}")
        
        # Scenario 1: Specific file path
        if os.path.isfile(base_path):
            print(f"✅ Using specific file: {base_path}")
            return base_path
        
        # Scenario 2: Directory path
        if os.path.isdir(base_path):
            # Get current date in DD-MM-YYYY format
            current_date = datetime.now().strftime("%d-%m-%Y")
            date_folder_path = os.path.join(base_path, current_date)
            
            # Determine file extensions based on directory name and path structure
            dir_name = base_path.lower()
            if 'image' in dir_name or 'photo' in dir_name:
                valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
                media_type = "image"
            elif 'document' in dir_name:
                valid_extensions = {'.pdf', '.doc', '.docx', '.txt', '.ppt', '.pptx', '.xls', '.xlsx'}
                media_type = "document"
            elif 'audio' in dir_name:
                valid_extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.aac'}
                media_type = "audio"
            elif 'video' in dir_name:
                valid_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.3gp'}
                media_type = "video"
            else:
                # If cannot determine type from directory name, check the actual path structure
                if '/Image/' in base_path or '/image/' in base_path:
                    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
                    media_type = "image"
                elif '/Document/' in base_path or '/document/' in base_path:
                    valid_extensions = {'.pdf', '.doc', '.docx', '.txt', '.ppt', '.pptx', '.xls', '.xlsx'}
                    media_type = "document"
                elif '/Audio/' in base_path or '/audio/' in base_path:
                    valid_extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.aac'}
                    media_type = "audio"
                elif '/Video/' in base_path or '/video/' in base_path:
                    valid_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.3gp'}
                    media_type = "video"
                else:
                    # Default to no extensions if cannot determine type
                    valid_extensions = set()
                    media_type = "unknown"
                    print(f"⚠️ Cannot determine media type from path: {base_path}")
            
            print(f"📁 Looking for {media_type} files with extensions: {valid_extensions}")
            
            # Priority 1: Check current date folder first
            search_directories = []
            
            if os.path.exists(date_folder_path) and os.path.isdir(date_folder_path):
                print(f"📁 Found current date folder: {date_folder_path}")
                search_directories.append(date_folder_path)
            else:
                print(f"📁 Current date folder not found: {date_folder_path}")
            
            # Priority 2: Always check base directory as fallback
            search_directories.append(base_path)
            print(f"📁 Also checking base directory: {base_path}")
            
            # Search in all directories (priority order: date folder -> base directory)
            for search_directory in search_directories:
                media_files = []
                try:
                    if not os.path.exists(search_directory):
                        print(f"❌ Directory does not exist: {search_directory}")
                        continue
                        
                    for file in os.listdir(search_directory):
                        file_path = os.path.join(search_directory, file)
                        if os.path.isfile(file_path):
                            file_ext = os.path.splitext(file)[1].lower()
                            if file_ext in valid_extensions:
                                media_files.append(file_path)
                    
                    if media_files:
                        # Select a random file from this directory
                        selected_file = random.choice(media_files)
                        print(f"🎯 Selected {media_type} file from {search_directory}: {selected_file}")
                        return selected_file
                    else:
                        print(f"ℹ️ No {media_type} files found in {search_directory}")
                        # List available files for debugging
                        available_files = [f for f in os.listdir(search_directory) if os.path.isfile(os.path.join(search_directory, f))]
                        if available_files:
                            print(f"ℹ️ Available files in {search_directory}: {available_files}")
                        else:
                            print(f"ℹ️ No files found in {search_directory}")
                        
                except Exception as e:
                    print(f"❌ Error reading directory {search_directory}: {e}")
                    continue
            
            # If we reach here, no files were found in any directory
            print(f"❌ No {media_type} files found in any search location")
            return None
        else:
            print(f"❌ Path does not exist: {base_path}")
            return None
            
    except Exception as e:
        print(f"❌ Error finding media file: {str(e)}")
        return None

def wait_for_xpath006_presence():
    """Wait for Xpath006 to be present (media fully loaded and cursor in caption field) - UNLIMITED WAIT"""
    global driver
    try:
        print("🔍 Checking for Xpath006 presence every second (unlimited wait)...")
        
        # Fetch Xpath006 from cache (caption input field)
        xpath006_selector = get_xpath_from_cache("006")
        if not xpath006_selector:
            print("❌ Could not fetch Xpath006 from cache")
            return False
        
        check_count = 0
        
        while True:  # Unlimited wait
            check_count += 1
            
            # Check Xpath006 selector every second
            try:
                elements = driver.find_elements(By.XPATH, xpath006_selector)
                # Check if any element is visible and enabled
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        print(f"✅ Xpath006 is present - Media fully loaded and cursor in caption field")
                        print("⏳ Waiting 20 seconds before typing caption...")
                        time.sleep(20)  # Wait 20 seconds after Xpath006 appears
                        return True  # Xpath006 found
            except Exception:
                pass
            
            print(f"⏳ Check {check_count}: Xpath006 not present yet...")
            time.sleep(1)  # Wait 1 second before next check
        
    except Exception as e:
        print(f"❌ Error checking Xpath006 presence: {str(e)}")
        return False

def wait_for_xpath003_disappear():
    """Wait for Xpath003 to disappear - wait 5 seconds first, then search every second until it's gone, then wait 2 seconds - UNLIMITED WAIT"""
    global driver
    try:
        print("⏳ Waiting 5 seconds before checking Xpath003...")
        time.sleep(5)  # Wait 5 seconds first
        
        print("🔍 Starting Xpath003 disappearance check (unlimited wait)...")
        
        # Fetch Xpath003 from cache (pending icon)
        xpath003_selector = get_xpath_from_cache("003")
        if not xpath003_selector:
            print("❌ Could not fetch Xpath003 from cache")
            return True  # Continue even if Xpath003 not found
        
        check_count = 0
        
        while True:  # Unlimited wait
            check_count += 1
            xpath003_found = False
            
            # Check Xpath003 selector every second
            try:
                elements = driver.find_elements(By.XPATH, xpath003_selector)
                # Check if any element is visible
                visible_elements = [elem for elem in elements if elem.is_displayed()]
                if visible_elements:
                    xpath003_found = True
                    print(f"⏳ Check {check_count}: Xpath003 still present")
            except Exception:
                pass
            
            if not xpath003_found:
                print("✅ Xpath003 disappeared")
                # Wait 2 seconds after disappearance
                print("⏳ Waiting 2 seconds after Xpath003 disappearance...")
                time.sleep(2)
                return True
            
            # Wait 1 second before next check
            time.sleep(5)
        
    except Exception as e:
        print(f"❌ Error waiting for Xpath003: {str(e)}")
        return True  # Continue even if there's an error

def upload_media_file(file_path, file_type):
    """Upload media file to WhatsApp using Xpath005 from cache"""
    global driver
    try:
        print(f"Uploading {file_type}: {file_path}")
        
        # Find the attachment button using Xpath005 from cache
        attachment_button = None
        
        # Fetch Xpath005 from cache (attachment button)
        xpath005_selector = get_xpath_from_cache("005")
        if not xpath005_selector:
            print("❌ Could not fetch Xpath005 from cache")
            return False
        
        try:
            attachment_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath005_selector)))
            print(f"Found attachment button with Xpath005 from cache")
            
            # Use JavaScript click to avoid element interception
            driver.execute_script("arguments[0].click();", attachment_button)
            print("Clicked attachment button using JavaScript (Xpath005)")
            
        except Exception as e:
            print(f"Could not find or click attachment button with Xpath005: {str(e)}")
            return False
        
        time.sleep(1)
        
        # Find the file input element - using cache XPath
        file_input = None
        
        # Fetch file input XPath from cache
        xpath_file_input_selector = get_xpath_from_cache("008")  # Assuming 008 is for file input
        if xpath_file_input_selector:
            try:
                file_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, xpath_file_input_selector)))
                print(f"Found file input with Xpath008 from cache")
            except:
                print("Could not find file input with Xpath008, trying fallback selectors")
                file_input = None
        
        # Fallback selectors if cache XPath doesn't work
        if not file_input:
            file_input_selectors = [
                "//input[@type='file'][@accept='image/*,video/mp4,video/3gpp,video/quicktime']",
                "//input[@type='file']",
                "//input[@accept='image/*,video/mp4,video/3gpp,video/quicktime']"
            ]
            
            for selector in file_input_selectors:
                try:
                    file_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, selector)))
                    print(f"Found file input with fallback selector")
                    break
                except:
                    continue
        
        if not file_input:
            print("Could not find file input")
            return False
        
        # Make the file input visible
        driver.execute_script("arguments[0].style.display = 'block';", file_input)
        driver.execute_script("arguments[0].style.visibility = 'visible';", file_input)
        driver.execute_script("arguments[0].style.opacity = '1';", file_input)
        
        # Get absolute path and send file
        absolute_path = os.path.abspath(file_path)
        print(f"Sending file path: {absolute_path}")
        file_input.send_keys(absolute_path)
        print(f"{file_type} file selected and uploaded")
        
        # Wait for upload preview
        print("Waiting for file upload...")
        time.sleep(3)
        
        return True
        
    except Exception as e:
        print(f"Error uploading {file_type}: {str(e)}")
        return False

def type_caption_and_send(caption):
    """Type caption and press Enter (cursor should already be in caption field)"""
    global driver
    try:
        print("Typing caption...")
        
        # Just type the caption (cursor should already be in the field from Xpath006 wait)
        actions = ActionChains(driver)
        actions.send_keys(caption)
        actions.perform()
        print("✅ Caption typed successfully")
        
        # Wait for stability
        time.sleep(1)
        
        # Press Enter to send
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        print("✅ Enter key pressed - media with caption sent")
        
        # Wait 2 seconds, then start checking for Xpath003 disappearance, then wait 3 seconds
        if wait_for_xpath003_disappear():
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Error typing caption: {str(e)}")
        return False

def send_with_enter_only():
    """Press Enter to send and wait for Xpath003 to disappear"""
    global driver
    try:
        # Press Enter key
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        print("✅ Enter key pressed - media sent")
        
        # Wait 2 seconds, then start checking for Xpath003 disappearance, then wait 3 seconds
        if wait_for_xpath003_disappear():
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Error pressing Enter: {str(e)}")
        return False

def send_text_message_flow(message_text, current_row_number):
    """Send text message following exact flow: copy and paste → Press Enter → wait 2 second → fetch Xpath003 and search every second → once it disappears → wait 3 seconds → Then proceed with status updates"""
    global driver
    try:
        print(f"\n--- Sending Message ---")
        print(f"Message: {message_text}")
        
        # Find the message input field - Fetch Xpath007 from cache for message field
        xpath007_selector = get_xpath_from_cache("007")
        if not xpath007_selector:
            print("❌ Could not fetch Xpath007 from cache for message field")
            return False
            
        message_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath007_selector)))
        
        # Clear and type the message
        message_field.clear()
        time.sleep(0.5)
        message_field.send_keys(message_text)
        time.sleep(1)
        
        # Verify message was typed
        if message_text in message_field.text:
            print("✅ Message typed successfully")
            
            # Press Enter key
            actions = ActionChains(driver)
            actions.send_keys(Keys.ENTER)
            actions.perform()
            print("✅ Enter key pressed - message sent")
            
            # Wait 2 seconds, then start checking for Xpath003 disappearance, then wait 3 seconds
            if wait_for_xpath003_disappear():
                print("✅ Message send completed")
                return True  # Status will be updated in Remark line at the end
            else:
                print("❌ Xpath003 wait failed")
                return False
        else:
            print("❌ Failed to type message")
            return False
            
    except Exception as e:
        print(f"❌ Error sending text message: {str(e)}")
        return False

def send_image_with_caption_flow(image_path, current_row_number):
    """Send image following enhanced file finding logic"""
    global driver
    try:
        print(f"🖼️ Image Path: {image_path}")
        
        # Find image file using the enhanced logic
        image_file = find_media_file(image_path)
        if not image_file:
            print("❌ No image file found - marking as not sent")
            return False
        
        # Verify the file is actually an image file
        if image_file:
            valid_image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            file_ext = os.path.splitext(image_file)[1].lower()
            if file_ext not in valid_image_extensions:
                print(f"❌ Selected file is not an image: {image_file}")
                return False
        
        # Upload image file
        if not upload_media_file(image_file, "Image"):
            return False
        
        # Wait for Xpath006 presence
        print("🔍 Waiting for Xpath006 presence after image upload...")
        if not wait_for_xpath006_presence():
            print("❌ Xpath006 not found for image")
            return False
        
        # Check for caption in the same location as the media file
        caption = get_caption_for_media(image_file)
        
        if caption:
            print("📝 Caption exists - typing caption to image")
            if type_caption_and_send(caption):
                print("✅ Image sent with caption")
                return True
            else:
                print("❌ Failed to send image with caption")
                return False
        else:
            print("📝 No caption available - sending image without caption")
            if send_with_enter_only():
                print("✅ Image sent successfully")
                return True
            else:
                print("❌ Failed to send image")
                return False
            
    except Exception as e:
        print(f"❌ Error in image flow: {str(e)}")
        return False

def send_document_with_caption_flow(document_path, current_row_number):
    """Send document following enhanced file finding logic"""
    global driver
    try:
        print(f"📄 Document Path: {document_path}")
        
        # Find document file using the enhanced logic
        document_file = find_media_file(document_path)
        if not document_file:
            print("❌ No document file found - marking as not sent")
            return False
        
        # Verify the file is actually a document file
        if document_file:
            valid_document_extensions = {'.pdf', '.doc', '.docx', '.txt', '.ppt', '.pptx', '.xls', '.xlsx'}
            file_ext = os.path.splitext(document_file)[1].lower()
            if file_ext not in valid_document_extensions:
                print(f"❌ Selected file is not a document: {document_file}")
                return False
        
        # Upload document file
        if not upload_media_file(document_file, "Document"):
            return False
        
        # Wait for Xpath006 presence
        print("🔍 Waiting for Xpath006 presence after document upload...")
        if not wait_for_xpath006_presence():
            print("❌ Xpath006 not found for document")
            return False
        
        # Check for caption in the same location as the media file
        caption = get_caption_for_media(document_file)
        
        if caption:
            print("📝 Caption exists - typing caption to document")
            if type_caption_and_send(caption):
                print("✅ Document sent with caption")
                return True
            else:
                print("❌ Failed to send document with caption")
                return False
        else:
            print("📝 No caption available - sending document without caption")
            if send_with_enter_only():
                print("✅ Document sent successfully")
                return True
            else:
                print("❌ Failed to send document")
                return False
            
    except Exception as e:
        print(f"❌ Error in document flow: {str(e)}")
        return False

def send_audio_without_caption_flow(audio_path, current_row_number):
    """Send audio following enhanced file finding logic (no caption for audio)"""
    global driver
    try:
        print(f"🔊 Audio Path: {audio_path}")
        
        # Find audio file using the enhanced logic
        audio_file = find_media_file(audio_path)
        if not audio_file:
            print("❌ No audio file found - marking as not sent")
            return False
        
        # Verify the file is actually an audio file
        if audio_file:
            valid_audio_extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.aac'}
            file_ext = os.path.splitext(audio_file)[1].lower()
            if file_ext not in valid_audio_extensions:
                print(f"❌ Selected file is not an audio file: {audio_file}")
                return False
        
        # Upload audio file
        if not upload_media_file(audio_file, "Audio"):
            return False
        
        # Audio has no caption option - send directly
        if send_with_enter_only():
            print("✅ Audio sent successfully")
            return True
        else:
            print("❌ Failed to send audio")
            return False
            
    except Exception as e:
        print(f"❌ Error in audio flow: {str(e)}")
        return False

def send_video_with_caption_flow(video_path, current_row_number):
    """Send video following enhanced file finding logic"""
    global driver
    try:
        print(f"🎥 Video Path: {video_path}")
        
        # Find video file using the enhanced logic
        video_file = find_media_file(video_path)
        if not video_file:
            print("❌ No video file found - marking as not sent")
            return False
        
        # Verify the file is actually a video file
        if video_file:
            valid_video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.3gp'}
            file_ext = os.path.splitext(video_file)[1].lower()
            if file_ext not in valid_video_extensions:
                print(f"❌ Selected file is not a video: {video_file}")
                return False
        
        # Upload video file
        if not upload_media_file(video_file, "Video"):
            return False
        
        # Wait for Xpath006 presence
        print("🔍 Waiting for Xpath006 presence after video upload...")
        if not wait_for_xpath006_presence():
            print("❌ Xpath006 not found for video")
            return False
        
        # Check for caption in the same location as the media file
        caption = get_caption_for_media(video_file)
        
        if caption:
            print("📝 Caption exists - typing caption to video")
            if type_caption_and_send(caption):
                print("✅ Video sent with caption")
                return True
            else:
                print("❌ Failed to send video with caption")
                return False
        else:
            print("📝 No caption available - sending video without caption")
            if send_with_enter_only():
                print("✅ Video sent successfully")
                return True
            else:
                print("❌ Failed to send video")
                return False
            
    except Exception as e:
        print(f"❌ Error in video flow: {str(e)}")
        return False

def update_receiver_list_timestamp(current_row_number):
    """Update Date-Time in Receiver list with current timestamp"""
    try:
        RECEIVER_LIST_FILE = os.path.join(WHATSAPP_BOT_DIR, "Receiver list.txt")
        
        if not current_row_number:
            print("No current row number to update")
            return False
        
        # Read the current file
        with open(RECEIVER_LIST_FILE, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Find and update the Date-Time line
        updated = False
        for i, line in enumerate(lines):
            if (line.startswith(f"Row{current_row_number}:") or 
                (f"Row{current_row_number}:" in line and (i == 0 or lines[i-1].startswith("Row")))):
                # Found the row, now find the Date-Time line
                for j in range(i, min(i+10, len(lines))):
                    if lines[j].startswith("Date-Time = "):
                        # Update with current datetime
                        current_datetime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        lines[j] = f"Date-Time = {current_datetime}\n"
                        updated = True
                        print(f"Updated Date-Time for Row{current_row_number} to {current_datetime}")
                        break
                break
        
        if updated:
            # Write the updated content back to the file
            with open(RECEIVER_LIST_FILE, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            return True
        else:
            print(f"Could not find Date-Time line for Row{current_row_number} to update")
            return False
            
    except Exception as e:
        print(f"Error updating Receiver list timestamp: {str(e)}")
        return False

def update_remark_based_on_media(current_row_number, processed_media, current_person_data):
    """Update Remark field with timestamp and all person data with | separators"""
    try:
        RECEIVER_LIST_FILE = os.path.join(WHATSAPP_BOT_DIR, "Receiver list.txt")
        
        if not current_row_number:
            print("No current row number to update in remark")
            return False
        
        # Read the current file
        with open(RECEIVER_LIST_FILE, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Get current timestamp
        current_timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        
        # Get person data with defaults
        name = current_person_data.get('name', 'Empty Cell')
        country_code = current_person_data.get('country_code', 'Empty Cell')
        whatsapp_number = current_person_data.get('phone_number', 'Empty Cell')
        message = current_person_data.get('message', 'Empty Cell')
        
        # Find and update the Remark line
        updated = False
        for i, line in enumerate(lines):
            if (line.startswith(f"Row{current_row_number}:") or 
                (f"Row{current_row_number}:" in line and (i == 0 or lines[i-1].startswith("Row")))):
                # Found the row, now find the Remark line
                for j in range(i, min(i+15, len(lines))):
                    if lines[j].startswith("Remark = "):
                        # Update remark with timestamp, person data, and processed media status with | separators
                        if processed_media:
                            # Join all status items with | separator
                            status_text = " | ".join(processed_media)
                            # Only include person data once, then media status
                            remark_text = f"{current_timestamp} | {name} | {country_code} | {whatsapp_number} | {message} | {status_text}"
                        else:
                            remark_text = f"{current_timestamp} | {name} | {country_code} | {whatsapp_number} | {message} | No media processed"
                        lines[j] = f"Remark = {remark_text}\n"
                        updated = True
                        print(f"Updated Remark for Row{current_row_number}")
                        break
                break
        
        if updated:
            # Write the updated content back to the file
            with open(RECEIVER_LIST_FILE, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            return True
        else:
            print(f"Could not find Remark line for Row{current_row_number} to update")
            return False
            
    except Exception as e:
        print(f"Error updating Remark: {str(e)}")
        return False

def update_remark_for_invalid_number(current_row_number, current_person_data):
    """Update Remark field for invalid WhatsApp number with full person data and failed media status"""
    try:
        RECEIVER_LIST_FILE = os.path.join(WHATSAPP_BOT_DIR, "Receiver list.txt")
        
        if not current_row_number:
            print("No current row number to update")
            return False
        
        # Read the current file
        with open(RECEIVER_LIST_FILE, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Get current timestamp
        current_timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        
        # Get person data with defaults
        name = current_person_data.get('name', 'Empty Cell')
        country_code = current_person_data.get('country_code', 'Empty Cell')
        whatsapp_number = current_person_data.get('phone_number', 'Empty Cell')
        message = current_person_data.get('message', 'Empty Cell')
        
        # Find and update the Remark line
        updated = False
        for i, line in enumerate(lines):
            if (line.startswith(f"Row{current_row_number}:") or 
                (f"Row{current_row_number}:" in line and (i == 0 or lines[i-1].startswith("Row")))):
                # Found the row, now find the Remark line
                for j in range(i, min(i+15, len(lines))):
                    if lines[j].startswith("Remark = "):
                        # Update remark with timestamp, person data, and failed media status with | separators
                        remark_text = f"{current_timestamp} | {name} | {country_code} | {whatsapp_number} | {message} | Failed to send Image | Failed to send document | Failed to send audio | Failed to send video | Invalid WhatsApp Number"
                        lines[j] = f"Remark = {remark_text}\n"
                        updated = True
                        print(f"Updated Remark for Row{current_row_number}")
                        break
                break
        
        if updated:
            # Write the updated content back to the file
            with open(RECEIVER_LIST_FILE, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            print(f"✅ Successfully updated Remark for invalid number with full data")
            return True
        else:
            print(f"❌ Could not find Remark line for Row{current_row_number} to update")
            return False
                
    except Exception as e:
        print(f"❌ Error updating Remark for invalid number: {str(e)}")
        return False

def process_all_media_for_person(current_person_data, current_row_number):
    """Process ALL available media for the same person - SKIP EMPTY CELLS"""
    global driver
    print("\n=== Processing ALL Media for Same Person ===")
    print(f"Person: {current_person_data.get('name', 'Unknown')}")
    
    if not current_person_data:
        print("No person data available")
        return False
    
    media_sent = False
    processed_media = []
    
    try:
        # Step 1: Send Message if available and NOT Empty Cell
        if (current_person_data.get('message') and 
            current_person_data['message'] != "Empty Cell" and 
            current_person_data['message'].strip()):
            
            print("\n📨 Processing Message...")
            if send_text_message_flow(current_person_data['message'], current_row_number):
                print("✅ Message sent successfully")
                media_sent = True
                processed_media.append("Message")
            else:
                print("❌ Failed to send message")
                processed_media.append("Failed to send message")
        else:
            print("📨 Skipping Message - Empty Cell")
            # DON'T add "Empty Cell" for Message since it's already in person data
        
        # Step 2: Send Image/Photo if available and NOT Empty Cell
        if (current_person_data.get('image_path') and 
            current_person_data['image_path'] != "Empty Cell" and 
            current_person_data['image_path'].strip()):
            
            print("\n🖼️ Processing Image...")
            image_sent = send_image_with_caption_flow(current_person_data['image_path'], current_row_number)
            if image_sent:
                print("✅ Image sent successfully")
                media_sent = True
                processed_media.append("Image")
            else:
                print("❌ Failed to send image")
                processed_media.append("Failed to send image")
        else:
            print("🖼️ Skipping Image - Empty Cell")
            processed_media.append("Empty Cell")
        
        # Step 3: Send Document if available and NOT Empty Cell
        if (current_person_data.get('document_path') and 
            current_person_data['document_path'] != "Empty Cell" and 
            current_person_data['document_path'].strip()):
            
            print("\n📄 Processing Document...")
            document_sent = send_document_with_caption_flow(current_person_data['document_path'], current_row_number)
            if document_sent:
                print("✅ Document sent successfully")
                media_sent = True
                processed_media.append("Document")
            else:
                print("❌ Failed to send document")
                processed_media.append("Failed to send document")
        else:
            print("📄 Skipping Document - Empty Cell")
            processed_media.append("Empty Cell")
        
        # Step 4: Send Audio if available and NOT Empty Cell
        if (current_person_data.get('audio_path') and 
            current_person_data['audio_path'] != "Empty Cell" and 
            current_person_data['audio_path'].strip()):
            
            print("\n🔊 Processing Audio...")
            audio_sent = send_audio_without_caption_flow(current_person_data['audio_path'], current_row_number)
            if audio_sent:
                print("✅ Audio sent successfully")
                media_sent = True
                processed_media.append("Audio")
            else:
                print("❌ Failed to send audio")
                processed_media.append("Failed to send audio")
        else:
            print("🔊 Skipping Audio - Empty Cell")
            processed_media.append("Empty Cell")
        
        # Step 5: Send Video if available and NOT Empty Cell
        if (current_person_data.get('video_path') and 
            current_person_data['video_path'] != "Empty Cell" and 
            current_person_data['video_path'].strip()):
            
            print("\n🎥 Processing Video...")
            video_sent = send_video_with_caption_flow(current_person_data['video_path'], current_row_number)
            if video_sent:
                print("✅ Video sent successfully")
                media_sent = True
                processed_media.append("Video")
            else:
                print("❌ Failed to send video")
                processed_media.append("Failed to send video")
        else:
            print("🎥 Skipping Video - Empty Cell")
            processed_media.append("Empty Cell")
        
        # Update Remark with timestamp, person data and all media status
        update_remark_based_on_media(current_row_number, processed_media, current_person_data)
        
        # Final timestamp update
        if update_receiver_list_timestamp(current_row_number):
            print("Final timestamp updated")
        
        if media_sent:
            print(f"\n🎉 SUCCESS: Processed media types")
            return True
        else:
            print("\n⚠️ No media was processed for this person")
            return False
            
    except Exception as e:
        print(f"❌ Error processing all media: {str(e)}")
        processed_media.append("Error in processing")
        update_remark_based_on_media(current_row_number, processed_media, current_person_data)
        return False

def create_manual_export_backup():
    """Create a backup file with export data for manual processing"""
    try:
        RECEIVER_LIST_FILE = os.path.join(WHATSAPP_BOT_DIR, "Receiver list.txt")
        MANUAL_EXPORT_FILE = os.path.join(WHATSAPP_BOT_DIR, "Manual_Export_Backup.txt")
        
        if not os.path.exists(RECEIVER_LIST_FILE):
            print("❌ No Receiver list file found for manual backup")
            return False
        
        # Copy the Receiver list file as backup
        import shutil
        shutil.copy2(RECEIVER_LIST_FILE, MANUAL_EXPORT_FILE)
        print(f"✅ Created manual export backup: {MANUAL_EXPORT_FILE}")
        print("📝 You can manually copy this data to Google Sheets Sent Report")
        return True
        
    except Exception as e:
        print(f"❌ Error creating manual export backup: {str(e)}")
        return False

def step5_export_to_google_sheets():
    """Step 5: Export data from Receiver list.txt to Google Sheets Sent Report"""
    print("\n=== Step 5: Exporting data to Google Sheets Sent Report ===")
    
    # Use centralized configuration
    SHEET_NAME = "Sent Report"
    RECEIVER_LIST_FILE = os.path.join(WHATSAPP_BOT_DIR, "Receiver list.txt")
    
    def setup_google_sheets_client():
        """Setup and authenticate Google Sheets client"""
        try:
            # Define the scope
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            
            # Authenticate and create client
            creds = Credentials.from_service_account_file(SPREADSHEET_KEY_FILE, scopes=scope)
            client = gspread.authorize(creds)
            return client
        except Exception as e:
            raise Exception(f"Failed to setup Google Sheets client: {str(e)}")
    
    def parse_receiver_list_file():
        """Parse Receiver list.txt file and extract all processed data"""
        try:
            if not os.path.isfile(RECEIVER_LIST_FILE):
                print(f"Receiver list file '{RECEIVER_LIST_FILE}' not found")
                return []
            
            with open(RECEIVER_LIST_FILE, 'r', encoding='utf-8') as file:
                content = file.read()
            
            lines = content.split('\n')
            rows_data = []
            current_row = {}
            current_row_number = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith("Row"):
                    # Save previous row if exists
                    if current_row and current_row_number:
                        rows_data.append((current_row_number, current_row))
                        # Debug output
                        print(f"DEBUG - Parsed Row{current_row_number}: Name='{current_row.get('name', 'NOT FOUND')}'")
                    
                    # Start new row
                    current_row_number = line.replace("Row", "").replace(":", "").replace("Processed successfully", "").replace("Invalid WhatsApp Number", "").strip()
                    current_row = {}
                
                elif line.startswith("Date-Time = "):
                    current_row['date_time'] = line.replace("Date-Time = ", "").strip()
                elif line.startswith("Name = "):
                    current_row['name'] = line.replace("Name = ", "").strip()
                elif line.startswith("Country Code = "):
                    current_row['country_code'] = line.replace("Country Code = ", "").strip()
                elif line.startswith("WhatsApp Number = "):
                    current_row['whatsapp_number'] = line.replace("WhatsApp Number = ", "").strip()
                elif line.startswith("Message = "):
                    current_row['message'] = line.replace("Message = ", "").strip()
                elif line.startswith("Image | Photo Path = "):
                    current_row['image_path'] = line.replace("Image | Photo Path = ", "").strip()
                elif line.startswith("Document Path = "):
                    current_row['document_path'] = line.replace("Document Path = ", "").strip()
                elif line.startswith("Audio Path = "):
                    current_row['audio_path'] = line.replace("Audio Path = ", "").strip()
                elif line.startswith("Video Path = "):
                    current_row['video_path'] = line.replace("Video Path = ", "").strip()
                elif line.startswith("Remark = "):
                    current_row['remark'] = line.replace("Remark = ", "").strip()
            
            # Add the last row
            if current_row and current_row_number:
                rows_data.append((current_row_number, current_row))
                # Debug output for last row
                print(f"DEBUG - Parsed Row{current_row_number}: Name='{current_row.get('name', 'NOT FOUND')}'")
            
            print(f"Parsed {len(rows_data)} rows from Receiver list.txt")
            return rows_data
            
        except Exception as e:
            raise Exception(f"Failed to parse Receiver list file: {str(e)}")
    
    def process_remark_data(remark_text, row_data):
        """Process remark text and return data for all columns - FIXED VERSION with Empty Cell handling (except Remark)"""
        # Use original row data as primary source, fallback to remark data
        # Ensure ALL empty cells are filled with "Empty Cell" EXCEPT Remark column
        col_a = row_data.get('date_time', 'Empty Cell')  # Date-Time from original data
        col_b = row_data.get('name', 'Empty Cell')       # Name from original data
        col_c = row_data.get('country_code', 'Empty Cell')  # Country Code from original data
        col_d = row_data.get('whatsapp_number', 'Empty Cell')  # WhatsApp Number from original data
        col_e = row_data.get('message', 'Empty Cell')    # Message from original data
        col_f = "Empty Cell"  # Image status - default to Empty Cell
        col_g = "Empty Cell"  # Document status - default to Empty Cell
        col_h = "Empty Cell"  # Audio status - default to Empty Cell
        col_i = "Empty Cell"  # Video status - default to Empty Cell
        col_j = ""  # Final remark - DO NOT use "Empty Cell" for Remark column
        
        # If we have remark data, use it to update media status and final remark
        if remark_text:
            if "Invalid WhatsApp Number" in remark_text:
                # For invalid numbers - parse the full remark format
                parts = remark_text.split(" | ")
                if len(parts) >= 10:  # Full format with all data
                    # Only update media status from remark, keep original person data
                    col_f = parts[5] if parts[5] and parts[5].strip() else "Empty Cell"  # Image status
                    col_g = parts[6] if parts[6] and parts[6].strip() else "Empty Cell"  # Document status
                    col_h = parts[7] if parts[7] and parts[7].strip() else "Empty Cell"  # Audio status
                    col_i = parts[8] if parts[8] and parts[8].strip() else "Empty Cell"  # Video status
                    col_j = parts[9] if parts[9] and parts[9].strip() else ""  # Invalid WhatsApp Number - keep empty if blank
                else:
                    # Fallback for old format
                    col_j = "Invalid WhatsApp Number"
            else:
                # For processed successfully - extract media status from remark
                parts = remark_text.split(" | ")
                if len(parts) >= 5:
                    # Process media status (parts 5 and beyond)
                    for i in range(5, len(parts)):
                        status = parts[i]
                        if status == "Image":
                            col_f = "Image sent successfully"
                        elif status == "Failed to send image":
                            col_f = "Failed to send image"
                        elif status == "Document":
                            col_g = "Document sent successfully"
                        elif status == "Failed to send document":
                            col_g = "Failed to send document"
                        elif status == "Audio":
                            col_h = "Audio sent successfully"
                        elif status == "Failed to send audio":
                            col_h = "Failed to send audio"
                        elif status == "Video":
                            col_i = "Video sent successfully"
                        elif status == "Failed to send video":
                            col_i = "Failed to send video"
                        elif status == "Message":
                            # Message is already handled in col_e
                            pass
                        elif status == "Failed to send message":
                            # Message failure is already handled in col_e
                            pass
                        elif status == "Empty Cell":
                            # Keep as "Empty Cell" for empty media types
                            if col_f == "Empty Cell":
                                col_f = "Empty Cell"
                            elif col_g == "Empty Cell":
                                col_g = "Empty Cell"
                            elif col_h == "Empty Cell":
                                col_h = "Empty Cell"
                            elif col_i == "Empty Cell":
                                col_i = "Empty Cell"
        
        # Ensure all empty values are replaced with "Empty Cell" EXCEPT for Remark column
        col_a = "Empty Cell" if not col_a or col_a.strip() == "" else col_a
        col_b = "Empty Cell" if not col_b or col_b.strip() == "" else col_b
        col_c = "Empty Cell" if not col_c or col_c.strip() == "" else col_c
        col_d = "Empty Cell" if not col_d or col_d.strip() == "" else col_d
        col_e = "Empty Cell" if not col_e or col_e.strip() == "" else col_e
        col_f = "Empty Cell" if not col_f or col_f.strip() == "" else col_f
        col_g = "Empty Cell" if not col_g or col_g.strip() == "" else col_g
        col_h = "Empty Cell" if not col_h or col_h.strip() == "" else col_h
        col_i = "Empty Cell" if not col_i or col_i.strip() == "" else col_i
        # col_j (Remark) is left as empty string if blank - DO NOT replace with "Empty Cell"
        
        # Debug output to verify data
        print(f"DEBUG - Row Data: Name='{col_b}', Country='{col_c}', Number='{col_d}', Remark='{col_j}'")
        
        return [col_a, col_b, col_c, col_d, col_e, col_f, col_g, col_h, col_i, col_j]
    
    def export_to_sheet(client, rows_data):
        """Export data to Google Sheets with retry logic"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Open the spreadsheet
                spreadsheet = client.open(SPREADSHEET_NAME)
                
                # Try to get the Sent Report worksheet, create if it doesn't exist
                try:
                    worksheet = spreadsheet.worksheet(SHEET_NAME)
                    print(f"Found existing worksheet: {SHEET_NAME}")
                except gspread.exceptions.WorksheetNotFound:
                    print(f"Worksheet '{SHEET_NAME}' not found, creating new one...")
                    worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=20)
                    
                    # Add headers
                    headers = ["Date-Time", "Name", "Country Code", "WhatsApp Number", "Message", 
                              "Image | Photo Path", "Document Path", "Audio Path", "Video Path", "Remark"]
                    worksheet.append_row(headers)
                    print("Added headers to new worksheet")
                
                # Prepare data for export
                data_to_export = []
                
                for row_number, row_data in rows_data:
                    if 'remark' in row_data:
                        row_export = process_remark_data(row_data['remark'], row_data)
                        data_to_export.append(row_export)
                        print(f"Prepared Row{row_number} for export")
                
                # Export data to sheet
                if data_to_export:
                    worksheet.append_rows(data_to_export)
                    print(f"✅ Successfully exported {len(data_to_export)} rows to {SHEET_NAME}")
                    return True
                else:
                    print("No data to export")
                    return False
                    
            except Exception as e:
                retry_count += 1
                print(f"❌ Error exporting to sheet (Attempt {retry_count}/{max_retries}): {str(e)}")
                
                if retry_count < max_retries:
                    print(f"🔄 Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    raise Exception(f"Failed to export data to sheet after {max_retries} attempts: {str(e)}")
        
        return False
    
    # Main execution with enhanced error handling
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            print(f"🔄 Attempt {retry_count + 1} to export data to Google Sheets...")
            
            # Setup Google Sheets client
            client = setup_google_sheets_client()
            print("Google Sheets client authenticated successfully")
            
            # Parse Receiver list.txt
            rows_data = parse_receiver_list_file()
            if not rows_data:
                print("No data found in Receiver list.txt to export")
                return False
            
            # Export to Google Sheets
            if export_to_sheet(client, rows_data):
                print("Step 5 completed successfully!")
                return True
            else:
                print("Failed to export data to Google Sheets")
                return False
                
        except Exception as e:
            retry_count += 1
            error_message = str(e)
            print(f"❌ Error during Step 5 (Attempt {retry_count}): {error_message}")
            
            # Check if we should continue retrying
            if retry_count < max_retries:
                print(f"🔄 Retrying in 10 seconds... (Attempt {retry_count + 1}/{max_retries})")
                time.sleep(10)
            else:
                print(f"❌ Maximum retries ({max_retries}) reached. Failed to complete Step 5.")
                print("⚠️ Data is still available in Receiver list.txt for manual export")
                return False
    
    return False

def get_report_numbers():
    """Get the count of persons from Receiver list and Sent Report sheets"""
    global PROGRAM_START_TIME  # Add global declaration here
    
    try:
        def setup_google_sheets_client():
            """Setup and authenticate Google Sheets client"""
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = Credentials.from_service_account_file(SPREADSHEET_KEY_FILE, scopes=scope)
            client = gspread.authorize(creds)
            return client
        
        # Setup client
        client = setup_google_sheets_client()
        spreadsheet = client.open(SPREADSHEET_NAME)
        
        # Count persons in Receiver list (rows from 2 to N)
        receiver_worksheet = spreadsheet.worksheet("Receiver list")
        receiver_data = receiver_worksheet.get_all_values()
        # Subtract 1 for header row, count only rows with data
        receiver_count = len([row for row in receiver_data[1:] if any(cell.strip() for cell in row)])
        
        # Count persons in Sent Report (only rows after program start time)
        try:
            sent_report_worksheet = spreadsheet.worksheet("Sent Report")
            sent_report_data = sent_report_worksheet.get_all_values()
            
            # Count rows that have Date-Time after program start time (excluding header)
            sent_count = 0
            for row in sent_report_data[1:]:  # Skip header
                if row and row[0]:  # Check if Date-Time column has data
                    try:
                        # Parse the Date-Time from the row
                        row_datetime_str = row[0]
                        # Convert to datetime object for comparison
                        row_datetime = datetime.strptime(row_datetime_str, "%d-%m-%Y %H:%M:%S")
                        
                        # Compare with program start time
                        if row_datetime >= PROGRAM_START_TIME:
                            sent_count += 1
                    except ValueError:
                        # If date parsing fails, skip this row
                        continue
        except gspread.exceptions.WorksheetNotFound:
            sent_count = 0
        
        print(f"📊 Report numbers - Receiver List: {receiver_count}, Sent Report (after {PROGRAM_START_TIME.strftime('%d-%m-%Y %H:%M:%S')}): {sent_count}")
        return receiver_count, sent_count
        
    except Exception as e:
        print(f"❌ Error getting report numbers: {str(e)}")
        return 0, 0

def send_whatsapp_report():
    """Send WhatsApp report after all data is updated in sheets"""
    global driver
    
    print("\n=== Sending WhatsApp Report ===")
    
    def read_report_number():
        """Read phone number from Report number file"""
        try:
            with open(REPORT_NUMBER_FILE, 'r') as file:
                phone_number = file.readline().strip()
                if phone_number:
                    print(f"📱 Report number: {phone_number}")
                    return phone_number
                else:
                    raise ValueError("Phone number not found in file")
        except Exception as e:
            print(f"❌ Error reading report number: {str(e)}")
            return None
    
    def open_whatsapp_web_for_report():
        """Open WhatsApp Web for sending report"""
        global driver
        
        # Close existing browsers
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] in ['chrome', 'chromium', 'chromedriver']:
                try:
                    proc.kill()
                except:
                    pass
        
        time.sleep(2)
        
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
        
        print("Entered WhatsApp Web for report")
        
        # Wait for QR scan or login
        start_time = time.time()
        while time.time() - start_time <= 120:
            try:
                # Use cache XPath for chat list
                xpath_chat_list_selector = get_xpath_from_cache("009")  # Assuming 009 is for chat list
                if xpath_chat_list_selector:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath_chat_list_selector)))
                    print("WhatsApp Web is ready - QR scanned successfully")
                    return True
                else:
                    # Fallback to generic chat list
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Chat list']")))
                    print("WhatsApp Web is ready - QR scanned successfully")
                    return True
            except TimeoutException:
                time.sleep(1)
                continue
        
        # Check for loading status
        try:
            loading_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Loading your chats')]")
            if loading_elements:
                print("'Loading your chats' found - waiting for completion")
                
                while True:
                    try:
                        loading_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Loading your chats')]")
                        if not loading_elements:
                            print("Loading completed - WhatsApp is ready")
                            return True
                        time.sleep(1)
                    except:
                        time.sleep(1)
        except:
            pass
        
        return False
    
    def find_and_click_search_field():
        """Find and click WhatsApp search field using cache XPath"""
        global driver
        while True:
            try:
                # Fetch search field XPath from cache
                xpath_search_selector = get_xpath_from_cache("010")  # Assuming 010 is for search field
                if xpath_search_selector:
                    search_field = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, xpath_search_selector)))
                    search_field.click()
                    print("WhatsApp search field is clicked (from cache)")
                    return True
                else:
                    # Fallback to generic search field
                    search_field = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))
                    search_field.click()
                    print("WhatsApp search field is clicked (fallback)")
                    return True
            except Exception as e:
                print(f"Error finding search field: {str(e)}")
                time.sleep(1)
    
    def paste_phone_number(phone_number):
        """Paste phone number into search field"""
        global driver
        while True:
            try:
                # Fetch search field XPath from cache
                xpath_search_selector = get_xpath_from_cache("010")  # Assuming 010 is for search field
                if xpath_search_selector:
                    search_field = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, xpath_search_selector)))
                else:
                    # Fallback to generic search field
                    search_field = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))
                
                search_field.clear()
                time.sleep(0.5)
                search_field.send_keys(phone_number)
                time.sleep(1)
                
                if phone_number.replace("+", "").replace(" ", "") in search_field.text.replace(" ", ""):
                    print("Mobile number transferred to WhatsApp search field")
                    return True
                else:
                    raise Exception("Number not entered correctly")
                    
            except Exception as e:
                print(f"Error during number input: {str(e)}")
                time.sleep(2)
    
    def wait_for_search_completion():
        """Wait for search to complete"""
        global driver
        try:
            print("🔍 Waiting for search completion...")
            
            # Wait for "Looking for chats..." to appear and disappear
            check_count = 0
            while True:
                check_count += 1
                
                try:
                    looking_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Looking for chats, contacts or messages')]")
                    
                    if looking_elements:
                        print(f"⏳ Check {check_count}: Still searching...")
                    else:
                        print("✅ Search completed")
                        return True
                        
                except Exception as e:
                    print(f"Error checking search status: {str(e)}")
                
                time.sleep(1)
                
        except Exception as e:
            print(f"❌ Error during search completion: {str(e)}")
            return True
    
    def press_down_enter_and_wait():
        """Press down arrow and enter, then wait for message field"""
        global driver
        try:
            # Focus on search field and press down
            xpath_search_selector = get_xpath_from_cache("010")  # Assuming 010 is for search field
            if xpath_search_selector:
                search_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, xpath_search_selector))
                )
            else:
                search_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
                )
            
            search_field.click()
            time.sleep(1)
            
            # Press down arrow key
            actions = ActionChains(driver)
            actions.send_keys(Keys.ARROW_DOWN)
            actions.perform()
            print("✅ Down arrow key pressed")
            
            # Press Enter key
            time.sleep(2)
            actions = ActionChains(driver)
            actions.send_keys(Keys.ENTER)
            actions.perform()
            print("✅ Enter key pressed")
            
            # NEW: Wait 5 seconds AFTER pressing Enter
            print("⏳ Waiting 5 seconds after pressing Enter...")
            time.sleep(5)  # ADDED THIS LINE
            
            # Wait for message field - Fetch Xpath007 from cache
            xpath007_selector = get_xpath_from_cache("007")
            if not xpath007_selector:
                print("❌ Could not fetch Xpath007 from cache for message field")
                return False
                
            message_field = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, xpath007_selector)))
            message_field.click()
            print("✅ Entered message input field using Xpath007 from cache")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during down/enter: {str(e)}")
            return False
    
    def create_report_message():
        """Create the report message with counts or no data message"""
        receiver_count, sent_count = get_report_numbers()
        current_date = datetime.now().strftime("%d-%m-%Y")
        
        # Check if there are any valid numbers in Receiver list
        if receiver_count > 0:
            report_message = f"""whatsapp messenger({current_date})

Receiver List = {receiver_count}
Sent Report = {sent_count}

The Sent Report filtered after starting time"""
        else:
            report_message = f"""whatsapp messenger({current_date})

No More Valid Data on Receiver List"""

        print("📝 Report message created")
        return report_message
    
    def send_report_message():
        """Send the report message as a single message"""
        global driver
        try:
            # Create report message
            report_message = create_report_message()
            
            # Find message field - Fetch Xpath007 from cache
            xpath007_selector = get_xpath_from_cache("007")
            if not xpath007_selector:
                print("❌ Could not fetch Xpath007 from cache for message field")
                return False
                
            message_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath007_selector)))
            
            # Clear the field first
            message_field.clear()
            time.sleep(0.5)
            
            # Send the entire message as one (using proper newline handling)
            lines = report_message.split('\n')
            for i, line in enumerate(lines):
                message_field.send_keys(line)
                if i < len(lines) - 1:  # Add Shift+Enter for all lines except last
                    message_field.send_keys(Keys.SHIFT + Keys.ENTER)
            
            time.sleep(1)
            
            # Press Enter to send the complete message
            actions = ActionChains(driver)
            actions.send_keys(Keys.ENTER)
            actions.perform()
            print("✅ Report message sent as single message")
            
            # Wait for message to be sent
            time.sleep(5)
            
            return True
            
        except Exception as e:
            print(f"❌ Error sending report message: {str(e)}")
            return False
    
    def wait_for_message_delivery():
        """Wait for message delivery confirmation"""
        global driver
        try:
            print("⏳ Waiting for message delivery...")
            
            # Wait for send status to clear (similar to Xpath003 logic)
            time.sleep(10)
            
            # Check if message was delivered by looking for the message in chat
            try:
                # Look for the report message in the chat
                report_message = create_report_message()
                message_elements = driver.find_elements(By.XPATH, f"//span[contains(text(), '{report_message.split()[0]}')]")
                if message_elements:
                    print("✅ Report message delivered successfully")
                    return True
            except:
                pass
            
            print("✅ Assuming message delivered")
            return True
            
        except Exception as e:
            print(f"❌ Error checking delivery: {str(e)}")
            return True
    
    # Main report sending flow
    try:
        # Step 1: Read report number
        phone_number = read_report_number()
        if not phone_number:
            print("❌ No report number found")
            return False
        
        # Step 2: Open WhatsApp Web
        if not open_whatsapp_web_for_report():
            print("❌ Failed to open WhatsApp Web")
            return False
        
        # Step 3: Find and click search field
        if not find_and_click_search_field():
            print("❌ Failed to find search field")
            return False
        
        # Step 4: Paste phone number
        if not paste_phone_number(phone_number):
            print("❌ Failed to paste phone number")
            return False
        
        # Step 5: Wait for search completion
        if not wait_for_search_completion():
            print("❌ Search failed to complete")
            return False
        
        # Step 6: Press down, enter and wait for message field
        if not press_down_enter_and_wait():
            print("❌ Failed to enter chat")
            return False
        
        # Step 7: Send report message
        if not send_report_message():
            print("❌ Failed to send report message")
            return False
        
        # Step 8: Wait for delivery
        if not wait_for_message_delivery():
            print("⚠️ Message delivery check failed")
        
        # Close browser
        if driver:
            driver.quit()
            driver = None
        
        print("✅ WhatsApp report sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error in WhatsApp report flow: {str(e)}")
        # Close browser on error
        if driver:
            try:
                driver.quit()
                driver = None
            except:
                pass
        return False

def step4_open_chrome_and_enter_phone_number():
    """Step 4: Open Chrome browser and enter WhatsApp phone number from Receiver list.txt"""
    global driver
    print("\n=== Step 4: Opening Chrome and entering WhatsApp phone number ===")
    
    # Use centralized configuration
    RECEIVER_LIST_FILE = os.path.join(WHATSAPP_BOT_DIR, "Receiver list.txt")
    
    current_phone_number = None
    current_row_number = None
    current_person_data = None
    
    def close_chrome_browsers():
        """Close all Chrome/Chromium browsers"""
        try:
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
        """Check internet connection"""
        try:
            subprocess.check_call(["ping", "-c", "1", "8.8.8.8"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def wait_for_internet():
        """Wait for internet connection"""
        count = 1
        while True:
            if check_internet():
                print("Internet is present good to go")
                break
            print(f"Internet is not present waiting upto...{count}")
            time.sleep(1)
            count += 1
    
    def open_whatsapp_web():
        """Open WhatsApp Web with persistent profile"""
        global driver
        
        while True:
            try:
                close_chrome_browsers()
                
                # Configure Chrome options - using centralized configuration
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
                
                # Wait for QR scan with same logic as your earlier project
                start_time = time.time()
                qr_scanned = False
                
                while time.time() - start_time <= 120:  # Wait up to 120 seconds
                    try:
                        # Check if logged in by looking for chat list using cache XPath
                        xpath_chat_list_selector = get_xpath_from_cache("009")  # Assuming 009 is for chat list
                        if xpath_chat_list_selector:
                            WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, xpath_chat_list_selector)))
                            print("WhatsApp Web is ready - QR scanned successfully (cache XPath)")
                            qr_scanned = True
                            break
                        else:
                            # Fallback to generic chat list
                            WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Chat list']")))
                            print("WhatsApp Web is ready - QR scanned successfully (fallback)")
                            qr_scanned = True
                            break
                    except TimeoutException:
                        time.sleep(1)
                        continue
                
                if qr_scanned:
                    return True
                else:
                    # After 120 seconds, check for "Loading your chats" keyword
                    print("120 seconds completed - checking for 'Loading your chats' status")
                    
                    loading_found = False
                    try:
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
                                loading_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Loading your chats')]")
                                if not loading_elements:
                                    loading_disappeared = True
                                    print("'Loading your chats' disappeared - WhatsApp is ready")
                                    break
                                else:
                                    print(f"Still loading... check {check_count}")
                                    check_count += 1
                                    
                                    if check_count % 5 == 0:
                                        internet_check_count += 1
                                        print(f"Internet check {internet_check_count}...")
                                        if not check_internet():
                                            print("Internet lost during loading - refreshing page")
                                            driver.refresh()
                                            time.sleep(5)
                                            break
                                
                            except Exception as e:
                                print(f"Error checking loading status: {str(e)}")
                            
                            time.sleep(1)
                        
                        if loading_disappeared:
                            return True
                        else:
                            print("Restarting due to internet loss during loading")
                            continue
                    else:
                        print("'Loading your chats' not found - refreshing page")
                        driver.refresh()
                        time.sleep(5)
                        continue
                        
            except Exception as e:
                print(f"Error opening WhatsApp Web: {str(e)}")
                print("Retrying in 5 seconds...")
                time.sleep(5)
    
    def find_and_click_search_field():
        """Find and click the search field using cache XPath"""
        global driver
        while True:
            try:
                # Fetch search field XPath from cache
                xpath_search_selector = get_xpath_from_cache("010")  # Assuming 010 is for search field
                if xpath_search_selector:
                    search_field = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, xpath_search_selector)))
                    search_field.click()
                    print("WhatsApp search field is clicked ready to search phone number (cache XPath)")
                    return True
                else:
                    # Fallback to generic search field
                    search_field = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))
                    search_field.click()
                    print("WhatsApp search field is clicked ready to search phone number (fallback)")
                    return True
                    
            except Exception as e:
                print(f"Error finding search field: {str(e)}")
                print("Retrying...")
                time.sleep(1)
    
    def clear_search_field():
        """Clear the search field completely"""
        global driver
        try:
            # Find search field using cache XPath
            xpath_search_selector = get_xpath_from_cache("010")  # Assuming 010 is for search field
            if xpath_search_selector:
                search_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, xpath_search_selector)))
            else:
                # Fallback to generic search field
                search_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))
            
            # Clear the field by selecting all and deleting
            search_field.click()
            time.sleep(0.5)
            
            # Select all text and delete
            actions = ActionChains(driver)
            actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)
            actions.send_keys(Keys.DELETE)
            actions.perform()
            
            time.sleep(0.5)
            print("✅ Search field cleared successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error clearing search field: {str(e)}")
            return False
    
    def read_phone_number_from_receiver_list(last_processed_row=None):
        """Read next phone number from Receiver list.txt file - finds next valid number after last_processed_row"""
        nonlocal current_phone_number, current_row_number, current_person_data
        
        try:
            if not os.path.isfile(RECEIVER_LIST_FILE):
                print(f"Receiver list file '{RECEIVER_LIST_FILE}' not found")
                return None
            
            with open(RECEIVER_LIST_FILE, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Find the next valid phone number in the file that hasn't been processed yet
            lines = content.split('\n')
            phone_number = None
            country_code = None
            current_row = None
            found_last_row = last_processed_row is None  # If no last processed row, start from first
            skip_current_row = False
            
            # Store person data
            person_data = {}
            
            for i, line in enumerate(lines):
                if line.startswith("Row"):
                    current_row = line.replace("Row", "").replace(":", "").replace("Processed successfully", "").replace("Invalid WhatsApp Number", "").strip()
                    
                    # Check if we should start processing from this row
                    if found_last_row:
                        current_row_number = current_row
                        person_data = {'row': current_row}
                        skip_current_row = False
                    elif current_row == last_processed_row:
                        found_last_row = True
                        continue
                    else:
                        continue
                
                if found_last_row and not skip_current_row:
                    if line.startswith("Country Code = ") and "Empty Cell" not in line:
                        country_code = line.replace("Country Code = ", "").strip()
                        person_data['country_code'] = country_code
                    
                    if line.startswith("WhatsApp Number = ") and "Empty Cell" not in line:
                        whatsapp_number_line = line
                        whatsapp_number = line.replace("WhatsApp Number = ", "").strip()
                        
                        # Check if this row has already been processed (Row line contains status)
                        row_line_index = i
                        while row_line_index >= 0 and not lines[row_line_index].startswith("Row"):
                            row_line_index -= 1
                        
                        if row_line_index >= 0 and ("Processed successfully" in lines[row_line_index] or "Invalid WhatsApp Number" in lines[row_line_index]):
                            # This row has already been processed, skip it and continue to next row
                            print(f"Row {current_row} already processed, skipping...")
                            skip_current_row = True
                            # Reset for next row but keep looking
                            country_code = None
                            whatsapp_number = None
                            person_data = {}
                            continue
                        
                        # Only process if we have both country code and whatsapp number
                        if country_code and whatsapp_number:
                            # Format as +countrycode whatsappnumber (with space)
                            phone_number = f"+{country_code} {whatsapp_number}"
                            current_phone_number = whatsapp_number  # Store the raw number for updating
                            
                            # Store all person data
                            person_data['phone_number'] = whatsapp_number
                            person_data['formatted_phone'] = phone_number
                            
                            print(f"Found valid phone number in {current_row}: {phone_number}")
                            
                            # Read the rest of the person's data
                            for j in range(i, min(i+20, len(lines))):
                                if lines[j].startswith("Name = "):
                                    person_data['name'] = lines[j].replace("Name = ", "").strip()
                                elif lines[j].startswith("Message = "):
                                    person_data['message'] = lines[j].replace("Message = ", "").strip()
                                elif lines[j].startswith("Image | Photo Path = "):
                                    person_data['image_path'] = lines[j].replace("Image | Photo Path = ", "").strip()
                                elif lines[j].startswith("Document Path = "):
                                    person_data['document_path'] = lines[j].replace("Document Path = ", "").strip()
                                elif lines[j].startswith("Audio Path = "):
                                    person_data['audio_path'] = lines[j].replace("Audio Path = ", "").strip()
                                elif lines[j].startswith("Video Path = "):
                                    person_data['video_path'] = lines[j].replace("Video Path = ", "").strip()
                                elif lines[j].startswith("Remark = "):
                                    person_data['remark'] = lines[j].replace("Remark = ", "").strip()
                                elif lines[j].startswith("Row") and j > i:
                                    break
                            
                            current_person_data = person_data
                            return phone_number
                        else:
                            # Skip this row - missing either country code or phone number
                            print(f"Skipping {current_row} - Missing Country Code or WhatsApp Number")
                            # Reset for next row but keep looking
                            country_code = None
                            whatsapp_number = None
                            person_data = {}
                            skip_current_row = True
            
            print("No more valid phone numbers found in Receiver list.txt")
            return None
                
        except Exception as e:
            print(f"Error reading phone number from Receiver list: {str(e)}")
            return None
    
    def paste_phone_number(phone_number):
        """Paste phone number into WhatsApp search field"""
        global driver
        while True:
            try:
                # Find search field using cache XPath
                xpath_search_selector = get_xpath_from_cache("010")  # Assuming 010 is for search field
                if xpath_search_selector:
                    search_field = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, xpath_search_selector)))
                else:
                    # Fallback to generic search field
                    search_field = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))
                
                # Clear field and input number directly (same method as your earlier project)
                search_field.clear()
                time.sleep(0.5)
                
                # Type number character by character
                search_field.send_keys(phone_number)
                time.sleep(1)
                
                # Verify number was entered
                if phone_number.replace("+", "").replace(" ", "") in search_field.text.replace(" ", ""):
                    print("Mobile number transferred from Receiver list to WhatsApp phone number search field")
                    return True
                else:
                    raise Exception("Number not entered correctly")
                    
            except Exception as e:
                print(f"Error during number input: {str(e)}")
                print("Retrying...")
                time.sleep(2)
    
    def check_looking_for_chats_keyword():
        """Check if 'Looking for chats, contacts or messages...' keyword is present and wait for it to disappear - UNLIMITED WAIT"""
        global driver
        try:
            print("🔍 Checking for 'Looking for chats, contacts or messages...' keyword (unlimited wait)...")
            
            check_count = 0
            looking_for_chats_found = False
            
            # Check every second for the "Looking for chats, contacts or messages..." keyword - UNLIMITED
            while True:
                check_count += 1
                
                try:
                    # Look for the "Looking for chats, contacts or messages..." keyword
                    looking_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Looking for chats, contacts or messages')]")
                    
                    if looking_elements:
                        # Keyword found - wait for it to disappear
                        if not looking_for_chats_found:
                            print("✅ 'Looking for chats, contacts or messages...' keyword found - waiting for it to disappear")
                            looking_for_chats_found = True
                        
                        print(f"⏳ Check {check_count}: Still looking for chats...")
                    else:
                        # Keyword disappeared
                        if looking_for_chats_found:
                            print("✅ 'Looking for chats, contacts or messages...' keyword disappeared")
                            return True
                        else:
                            # Keyword was never found, which means search completed immediately
                            print("✅ 'Looking for chats, contacts or messages...' keyword never appeared - search completed")
                            return True
                            
                except Exception as e:
                    print(f"Error checking for 'Looking for chats' keyword: {str(e)}")
                
                # Wait 1 second before next check
                time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error during 'Looking for chats' check: {str(e)}")
            return True  # Continue even if there's an error
    
    def check_no_chats_keyword():
        """Check if 'No chats, contacts or messages found' keyword is present using Xpath004 from cache"""
        global driver
        try:
            # After "Looking for chats..." disappears, check for the final result keyword
            print("🔍 Checking for final result keyword using Xpath004 from cache...")
            
            # Wait 2 seconds for stability after search completes
            time.sleep(2)
            
            # Check for the keyword "No chats, contacts or messages found" using Xpath004 from cache
            keyword_found = False
            try:
                # Fetch Xpath004 from cache (no chats found message)
                xpath004_selector = get_xpath_from_cache("004")
                if not xpath004_selector:
                    print("❌ Could not fetch Xpath004 from cache")
                    return False
                
                # Look for the keyword using Xpath004
                no_chats_elements = driver.find_elements(By.XPATH, xpath004_selector)
                if no_chats_elements:
                    keyword_found = True
                    print("✅ Keyword 'No chats, contacts or messages found' is available (Xpath004 from cache)")
                else:
                    print("❌ Keyword 'No chats, contacts or messages found' is not available")
            except Exception as e:
                print(f"Error checking for keyword using Xpath004: {str(e)}")
                keyword_found = False
            
            return keyword_found
            
        except Exception as e:
            print(f"❌ Error during keyword check: {str(e)}")
            return False

    def wait_and_press_down():
        """Wait for stability and press down arrow key"""
        global driver
        try:
            # Focus on the search field first using cache XPath
            xpath_search_selector = get_xpath_from_cache("010")  # Assuming 010 is for search field
            if xpath_search_selector:
                search_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, xpath_search_selector))
                )
            else:
                search_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
                )
            
            search_field.click()
            time.sleep(1)
            
            # Press down arrow key using ActionChains
            actions = ActionChains(driver)
            actions.send_keys(Keys.ARROW_DOWN)
            actions.perform()
            print("✅ Down arrow key pressed successfully")
            
            # Press Enter key
            print("⏳ Waiting 2 second before pressing Enter...")
            time.sleep(2)
            actions = ActionChains(driver)
            actions.send_keys(Keys.ENTER)
            actions.perform()
            print("✅ Enter key pressed successfully")
            
            # NEW: Wait 5 seconds AFTER pressing Enter before proceeding
            print("⏳ Waiting 5 seconds after pressing Enter...")
            time.sleep(5)  # ADDED THIS LINE - wait AFTER Enter
            
            return True
            
        except Exception as e:
            print(f"❌ Error during wait and press down: {str(e)}")
            return False
    
    def find_and_click_message_field():
        """Find and click the message input field using Xpath007 from cache - UNLIMITED WAIT"""
        global driver
        while True:
            try:
                # Fetch Xpath007 from cache for message field
                xpath007_selector = get_xpath_from_cache("007")
                if not xpath007_selector:
                    print("❌ Could not fetch Xpath007 from cache for message field")
                    return False
                    
                # Unlimited wait for message field
                while True:
                    try:
                        # Search for message field every second using Xpath007 from cache
                        message_field = WebDriverWait(driver, 1).until(
                            EC.presence_of_element_located((By.XPATH, xpath007_selector)))
                        message_field.click()
                        print("✅ Entered into Type a message field using Xpath007 from cache")
                        return True
                        
                    except (NoSuchElementException, TimeoutException):
                        # Wait 1 second before trying again
                        time.sleep(1)
                        continue
            
            except Exception as e:
                print(f"❌ Error during message field search: {str(e)}")
                return False
    
    def process_next_person(last_processed_row=None):
        """Process the next person after completing current one without closing browser"""
        nonlocal current_phone_number, current_row_number, current_person_data
        
        # Reset current values
        current_phone_number = None
        current_row_number = None
        current_person_data = None
        
        # Wait a moment before processing next
        time.sleep(2)
        
        # Process next person
        return process_single_person(last_processed_row)
    
    def process_single_person(last_processed_row=None):
        """Process a single person - main logic for Step 4"""
        global driver
        
        # Step 1: Wait for internet
        wait_for_internet()
        
        # Step 2: Read phone number from Receiver list.txt
        phone_number = read_phone_number_from_receiver_list(last_processed_row)
        if not phone_number:
            print("No more valid phone numbers found to process")
            return False
        
        # Step 3: If this is the first person, open WhatsApp Web
        if driver is None:
            if not open_whatsapp_web():
                raise Exception("Failed to open WhatsApp Web")
        else:
            # For subsequent persons, just ensure we're on WhatsApp and clear search field
            try:
                # Clear any existing text in search field first
                if not clear_search_field():
                    print("Failed to clear search field, reopening WhatsApp...")
                    if not open_whatsapp_web():
                        raise Exception("Failed to reopen WhatsApp Web")
            except Exception as e:
                print(f"Error refreshing WhatsApp: {str(e)}")
                # If refresh fails, reopen WhatsApp
                if not open_whatsapp_web():
                    raise Exception("Failed to reopen WhatsApp Web")
        
        # Step 4: Find and click search field
        if not find_and_click_search_field():
            raise Exception("Failed to find search field")
        
        # Step 5: Paste phone number
        if not paste_phone_number(phone_number):
            raise Exception("Failed to paste phone number")
        
        # Step 6: NEW LOGIC - Check for "Looking for chats, contacts or messages..." first
        print("🔄 Starting new search flow...")
        if not check_looking_for_chats_keyword():
            print("❌ Failed in 'Looking for chats' check")
            return False
        
        # Step 7: After "Looking for chats..." disappears, check for final result using Xpath004 from cache
        keyword_found = check_no_chats_keyword()
        
        if keyword_found:
            # WhatsApp number not found - mark as invalid and skip processing
            print("❌ Invalid WhatsApp Number - skipping media processing")
            # Update Row status to "Invalid WhatsApp Number"
            if update_row_status_in_receiver_list(current_row_number, "Invalid WhatsApp Number"):
                # Update Remark with full person data and failed media status
                if update_remark_for_invalid_number(current_row_number, current_person_data):
                    print("✅ Successfully marked as invalid. Moving to next person...")
                    return process_next_person(current_row_number)
            else:
                print("❌ Failed to update file. Moving to next person...")
                return process_next_person(current_row_number)
        else:
            # Keyword not found, continue with normal process
            print("✅ Contact found! Continuing with normal process...")
            if not wait_and_press_down():
                raise Exception("Failed in wait and press down step")
            
            # Step 8: Find and click message field using Xpath007 from cache
            print("🔍 Looking for message input field using Xpath007 from cache...")
            if not find_and_click_message_field():
                raise Exception("Failed to find message input field")
            
            # Step 9: Process ALL media for the same person
            print("🚀 Processing ALL media files for this person...")
            success = process_all_media_for_person(current_person_data, current_row_number)
            
            # Update Row status to "Processed successfully" regardless of individual media success
            if update_row_status_in_receiver_list(current_row_number, "Processed successfully"):
                if success:
                    print("🎉 Person processed successfully! All media sent and timestamps updated.")
                else:
                    print("⚠️ Person processed with some failures - marked as processed anyway")
            
            # Process next person
            return process_next_person(current_row_number)
    
    # Main execution with continuous retry
    retry_count = 0
    max_retries = 10
    
    while retry_count < max_retries:
        try:
            print(f"🔄 Attempt {retry_count + 1} to open Chrome and enter phone number...")
            
            result = process_single_person()
            if not result:
                # If process_single_person returns False, it means no more valid numbers
                print("✅ No more valid phone numbers to process - stopping bot")
                # Close browser when done
                if driver:
                    driver.quit()
                    driver = None
                return True
                
        except Exception as e:
            retry_count += 1
            error_message = str(e)
            print(f"❌ Error during Step 4 (Attempt {retry_count}): {error_message}")
            
            # Close browser if open
            if driver:
                try:
                    driver.quit()
                    driver = None
                except:
                    pass
            
            if retry_count < max_retries:
                print(f"🔄 Retrying in 5 seconds... (Attempt {retry_count + 1}/{max_retries})")
                time.sleep(5)
            else:
                print(f"❌ Maximum retries ({max_retries}) reached. Failed to complete Step 4.")
                return False
    
    return False

# Main execution
if __name__ == "__main__":
    try:
        # Set global program start time at the very beginning
        PROGRAM_START_TIME = datetime.now()
        
        print("=== WhatsApp Messenger Bot - Starting Process ===")
        print(f"📅 Program started at: {PROGRAM_START_TIME.strftime('%d-%m-%Y %H:%M:%S')}")
        
        # Step 0: Initialize XPaths (import from database or load from file)
        if not initialize_xpaths():
            print("❌ Failed to initialize XPaths. Exiting...")
            exit(1)
        
        # Track if we should send report
        should_send_report = True
        
        # Step 1: Close Chromium browser
        if step1_close_chromium_browser():
            # Step 2: Check internet connection
            if step2_check_internet_connection():
                # Step 3: Import spreadsheet data
                if step3_import_spreadsheet_data():
                    # Step 4: Open Chrome and enter phone number
                    step4_result = step4_open_chrome_and_enter_phone_number()
                    
                    # Step 5: Export to Google Sheets Sent Report (with retry logic)
                    step5_success = step5_export_to_google_sheets()
                    
                    # If Step 5 fails, create manual backup
                    if not step5_success:
                        print("🔄 Creating manual export backup due to Google Sheets connection issues...")
                        create_manual_export_backup()
                    
                    # ALWAYS send WhatsApp report regardless of previous steps
                    print("\n=== Proceeding to send WhatsApp Report ===")
                    send_whatsapp_report()
        
        # Final step: Delete XPath file after bot completion
        print("\n=== Cleaning up XPath files ===")
        delete_xpath_file()
        
        print("=== Process Completed ===")
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        # Clean up XPath file on interrupt
        delete_xpath_file()
    except Exception as e:
        print(f"Unexpected error in main execution: {str(e)}")
        # Clean up XPath file on error
        delete_xpath_file()
