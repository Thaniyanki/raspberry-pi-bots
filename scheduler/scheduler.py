#!/usr/bin/env python3
"""
Scheduler Script for Managing Python Bots with Unlimited Retry
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

# Try to import required packages, install if missing
try:
    import gspread
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Installing required Google packages...")
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
    print("Installing Selenium...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "selenium"])
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:
    print("Installing Firebase Admin...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "firebase-admin"])
    import firebase_admin
    from firebase_admin import credentials, db

class BotScheduler:
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
        self.xpaths = {}
        
    def unlimited_retry_api_call(self, api_call_func, operation_name, max_retry_delay=300, initial_delay=5):
        """
        Unlimited retry decorator for Google Sheets API calls
        """
        delay = initial_delay
        attempt = 1
        
        while True:
            try:
                return api_call_func()
            except HttpError as e:
                if e.resp.status in [503, 500, 429]:  # Service unavailable, internal error, rate limit
                    print(f"{self.YELLOW}⚠ {operation_name} - Attempt {attempt}: API temporarily unavailable ({e.resp.status}){self.ENDC}")
                    print(f"{self.YELLOW}   Retrying in {delay} seconds...{self.ENDC}")
                    time.sleep(delay)
                    
                    # Exponential backoff with cap
                    delay = min(delay * 2, max_retry_delay)
                    attempt += 1
                else:
                    # Other HTTP errors (404, 403, etc.) should not be retried indefinitely
                    print(f"{self.RED}❌ {operation_name} - HTTP Error {e.resp.status}: {e}{self.ENDC}")
                    raise
            except Exception as e:
                print(f"{self.RED}❌ {operation_name} - Attempt {attempt}: Unexpected error: {e}{self.ENDC}")
                if attempt >= 3:  # Only retry unexpected errors a few times
                    raise
                print(f"{self.YELLOW}   Retrying in {delay} seconds...{self.ENDC}")
                time.sleep(delay)
                delay = min(delay * 2, max_retry_delay)
                attempt += 1

    def run_curl_command(self):
        """Run the curl command to setup bots with LIVE output"""
        print("Setting up bots using curl command...")
        try:
            # Run curl and pipe directly to python3 with LIVE output
            print("Starting bot installation... This may take several minutes.")
            print("=" * 60)
            
            process = subprocess.run(
                'curl -sL "https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main/all-in-one-venv/all%20in%20one%20venv.py" | python3',
                shell=True,
                stdout=None,  # Don't capture stdout - show live
                stderr=None,  # Don't capture stderr - show live
                text=True
            )
            
            print("=" * 60)
            
            if process.returncode == 0:
                print("Bots setup completed successfully")
            else:
                print(f"Setup completed with return code: {process.returncode}")
                
        except Exception as e:
            print(f"Error executing setup: {e}")
            
        sys.exit(0)
    
    def check_bots_folder(self):
        """Check if bots folder exists and has valid content"""
        if not self.bots_base_path.exists():
            print("Bots folder not found. Running setup...")
            self.run_curl_command()
            return False
            
        items = list(self.bots_base_path.iterdir())
        folders = [item for item in items if item.is_dir()]
        
        if not folders:
            print("Bots folder is empty. Running setup...")
            self.run_curl_command()
            return False
            
        return True
    
    def get_bot_folders(self):
        """Get all bot folders INCLUDING scheduler folder"""
        if not self.bots_base_path.exists():
            return []
            
        items = list(self.bots_base_path.iterdir())
        bot_folders = [item for item in items if item.is_dir()]
        return bot_folders
    
    def get_working_bot_folders(self):
        """Get all bot folders that need database keys (EXCLUDING scheduler)"""
        bot_folders = self.get_bot_folders()
        return [folder for folder in bot_folders if folder.name != self.scheduler_folder]
    
    def get_venv_path(self, bot_folder):
        """Get the venv path for a bot folder"""
        venv_path = bot_folder / "venv"
        return venv_path if venv_path.exists() and venv_path.is_dir() else None
    
    def check_report_numbers_exist(self, bot_folders):
        """Check if report number files exist in ALL bot folders' venv (INCLUDING scheduler)"""
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if not venv_path:
                return False
            report_file = venv_path / "report number"
            if not report_file.exists():
                return False
        return True
    
    def check_report_numbers_valid(self, bot_folders):
        """Check if all report number files have valid content (not empty) - INCLUDING scheduler"""
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                report_file = venv_path / "report number"
                if report_file.exists():
                    try:
                        with open(report_file, 'r') as f:
                            content = f.read().strip()
                        if not content:
                            return False  # Found empty report number file
                    except:
                        return False  # Error reading file
        return True
    
    def get_valid_report_number_from_bots(self, bot_folders):
        """Get a valid report number from any bot that has one (INCLUDING scheduler)"""
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                report_file = venv_path / "report number"
                if report_file.exists():
                    try:
                        with open(report_file, 'r') as f:
                            content = f.read().strip()
                        if content and self.is_valid_phone_number(content):
                            return content, folder.name
                    except:
                        continue
        return None, None
    
    def copy_report_numbers_from_valid_bots(self, bot_folders):
        """Copy report numbers from bots that have them to bots that don't (INCLUDING scheduler)"""
        print("Automatically copying report numbers from bots that have them...")
        
        # Find all valid report numbers
        valid_report_numbers = {}
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                report_file = venv_path / "report number"
                if report_file.exists():
                    try:
                        with open(report_file, 'r') as f:
                            content = f.read().strip()
                        if content and self.is_valid_phone_number(content):
                            valid_report_numbers[folder.name] = content
                    except:
                        continue
        
        if not valid_report_numbers:
            print("No valid report numbers found in any bot.")
            return False
        
        # Use the first valid report number found
        source_bot, report_number = next(iter(valid_report_numbers.items()))
        print(f"Found valid report number '{report_number}' in {source_bot}")
        
        # Copy to bots that don't have valid report numbers (INCLUDING scheduler)
        copied_count = 0
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                report_file = venv_path / "report number"
                needs_copy = False
                
                if report_file.exists():
                    try:
                        with open(report_file, 'r') as f:
                            content = f.read().strip()
                        if not content or not self.is_valid_phone_number(content):
                            needs_copy = True
                    except:
                        needs_copy = True
                else:
                    needs_copy = True
                
                if needs_copy:
                    try:
                        with open(report_file, 'w') as f:
                            f.write(report_number)
                        print(f"  ✓ Copied to {folder.name}/venv/")
                        copied_count += 1
                    except Exception as e:
                        print(f"  ✗ Failed to copy to {folder.name}/venv/: {e}")
        
        print(f"Successfully copied report number to {copied_count} bots")
        return True
    
    def delete_all_report_numbers(self, bot_folders):
        """Delete all report number files from venv folders (INCLUDING scheduler)"""
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                report_file = venv_path / "report number"
                if report_file.exists():
                    report_file.unlink()
                    print(f"Deleted report number from {folder.name}/venv/")
    
    def create_report_numbers(self, bot_folders, report_number):
        """Create report number files in all bot folders' venv (INCLUDING scheduler)"""
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                report_file = venv_path / "report number"
                try:
                    with open(report_file, 'w') as f:
                        f.write(report_number)
                    print(f"Created report number in {folder.name}/venv/")
                except Exception as e:
                    print(f"Error creating report number in {folder.name}/venv/: {e}")
    
    def is_valid_phone_number(self, phone_number):
        """Validate that the input contains only digits"""
        if not phone_number:
            return False
        
        # Remove common phone number characters (spaces, hyphens, plus sign, parentheses)
        cleaned_number = phone_number.replace(' ', '').replace('-', '').replace('+', '').replace('(', '').replace(')', '')
        
        # Check if all characters are digits
        if not cleaned_number.isdigit():
            return False
        
        # Check if the number has a reasonable length (usually 10-15 digits)
        if len(cleaned_number) < 10 or len(cleaned_number) > 15:
            return False
        
        return True
    
    def get_report_number_input(self):
        """Get report number input with validation and fallback for piped input"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            if not sys.stdin.isatty():
                # We're in a pipe, try to read from terminal directly
                try:
                    # Yellow colored prompt
                    print(f"{self.YELLOW}Enter the report number (phone number): {self.ENDC}", end='', flush=True)
                    with open('/dev/tty', 'r') as tty:
                        report_number = tty.readline().strip()
                    
                    if self.is_valid_phone_number(report_number):
                        return report_number
                    elif report_number:  # If user entered something but it's invalid
                        print(f"Error: '{report_number}' is not a valid phone number. Please enter only digits.")
                        if attempt < max_attempts - 1:
                            print(f"Attempt {attempt + 1} of {max_attempts}")
                        continue
                    else:
                        return None
                        
                except:
                    # If /dev/tty fails, provide instructions
                    print("\nCannot read input from pipe.")
                    print("Please download and run the script directly:")
                    print("curl -sL 'https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main/scheduler/scheduler.py' -o scheduler.py && python3 scheduler.py")
                    return None
            else:
                # Normal terminal input
                try:
                    # Yellow colored prompt
                    print(f"{self.YELLOW}Enter the report number (phone number): {self.ENDC}", end='', flush=True)
                    report_number = input().strip()
                    
                    if self.is_valid_phone_number(report_number):
                        return report_number
                    elif report_number:  # If user entered something but it's invalid
                        print(f"Error: '{report_number}' is not a valid phone number. Please enter only digits.")
                        if attempt < max_attempts - 1:
                            print(f"Attempt {attempt + 1} of {max_attempts}")
                        continue
                    else:
                        return None
                        
                except (KeyboardInterrupt, EOFError):
                    return None
        
        # If we've exhausted all attempts
        print("Maximum attempts reached. Please run the script again.")
        return None
    
    def handle_report_numbers(self, bot_folders):
        """Handle report number creation/modification - AUTO COPY from existing bots (INCLUDING scheduler)"""
        all_have_report_numbers = self.check_report_numbers_exist(bot_folders)
        all_report_numbers_valid = self.check_report_numbers_valid(bot_folders)
        
        # If some folders don't have report numbers OR some have empty report numbers
        if not all_have_report_numbers or not all_report_numbers_valid:
            if not all_have_report_numbers:
                print("Some bots are missing report numbers in their venv folders.")
            if not all_report_numbers_valid:
                print("Some bots have empty or invalid report numbers in their venv folders.")
            
            # First try to auto-copy from existing valid report numbers
            print("Attempting to auto-copy report numbers from bots that have them...")
            if self.copy_report_numbers_from_valid_bots(bot_folders):
                print("Auto-copy completed successfully!")
                return
            
            # If auto-copy failed, then ask for user input
            print("No valid report numbers found to copy from.")
            report_number = self.get_report_number_input()
            
            if report_number:
                self.create_report_numbers(bot_folders, report_number)
                print(f"Report number '{report_number}' set for all bots in their venv folders.")
            else:
                print("No valid report number provided. Please run the script again to set report numbers.")
                sys.exit(1)
            return
        
        # All folders have valid report numbers
        print("Report number already available in all bots folder's venv folders.")
        
        # Ask if user wants to modify
        if not sys.stdin.isatty():
            # Piped input - wait 10 seconds and continue
            print("Waiting 10 seconds... (Press Ctrl+C to modify)")
            try:
                for i in range(10, 0, -1):
                    print(f"\rContinuing in {i} seconds... ", end='', flush=True)
                    time.sleep(1)
                print("\r" + " " * 30 + "\r", end='', flush=True)
                print("Continuing with existing report numbers...")
            except KeyboardInterrupt:
                print("\n\nModification requested...")
                self.delete_all_report_numbers(bot_folders)
                report_number = self.get_report_number_input()
                if report_number:
                    self.create_report_numbers(bot_folders, report_number)
                    print(f"Report number updated to '{report_number}' in all venv folders")
                else:
                    print("No valid report number provided. Keeping existing setup.")
        else:
            # Normal terminal input
            try:
                response = input("Do you want to modify? y/n: ").strip().lower()
                if response == 'y':
                    self.delete_all_report_numbers(bot_folders)
                    report_number = self.get_report_number_input()
                    if report_number:
                        self.create_report_numbers(bot_folders, report_number)
                        print(f"Report number updated to '{report_number}' in all venv folders")
                else:
                    print("Continuing with existing report numbers...")
            except (KeyboardInterrupt, EOFError):
                print("\nContinuing with existing report numbers...")
    
    def list_bot_folders(self, bot_folders):
        """List all available bot folders with venv status"""
        if bot_folders:
            print("\nAvailable bot folders:")
            for folder in bot_folders:
                venv_path = self.get_venv_path(folder)
                if venv_path:
                    report_file = venv_path / "report number"
                    if report_file.exists():
                        try:
                            with open(report_file, 'r') as f:
                                content = f.read().strip()
                            if content and self.is_valid_phone_number(content):
                                status = f"✓ ({content})"
                            elif content:
                                status = "✗ (invalid)"
                            else:
                                status = "✗ (empty)"
                        except:
                            status = "✗ (error)"
                    else:
                        status = "✗"
                    venv_status = "✓"
                else:
                    status = "✗"
                    venv_status = "✗"
                
                print(f"  - {folder.name} [venv: {venv_status}] [report number: {status}]")
    
    def verify_report_numbers(self, bot_folders):
        """Verify that report numbers are properly set in venv folders (INCLUDING scheduler)"""
        print("\nVerifying report numbers in venv folders...")
        all_set = True
        empty_files_found = False
        
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                report_file = venv_path / "report number"
                if report_file.exists():
                    try:
                        with open(report_file, 'r') as f:
                            content = f.read().strip()
                        if content and self.is_valid_phone_number(content):
                            print(f"  ✓ {folder.name}/venv/: {content}")
                        else:
                            print(f"  ✗ {folder.name}/venv/: {'Empty' if not content else 'Invalid'} report number")
                            all_set = False
                            empty_files_found = True
                    except Exception as e:
                        print(f"  ✗ {folder.name}/venv/: Error reading - {e}")
                        all_set = False
                else:
                    print(f"  ✗ {folder.name}/venv/: No report number file")
                    all_set = False
            else:
                print(f"  ✗ {folder.name}: No venv folder found")
                all_set = False
        
        # If empty files found, try auto-copy first
        if empty_files_found:
            print("\nSome bots have empty or invalid report numbers. Attempting auto-copy...")
            if self.copy_report_numbers_from_valid_bots(bot_folders):
                print("Auto-copy completed successfully!")
                # Re-verify after update
                print("\nRe-verifying report numbers...")
                return self.verify_report_numbers(bot_folders)
            else:
                print("No valid report numbers found to copy from.")
                report_number = self.get_report_number_input()
                if report_number:
                    self.create_report_numbers(bot_folders, report_number)
                    print(f"Report number '{report_number}' updated for all bots.")
                    # Re-verify after update
                    print("\nRe-verifying report numbers...")
                    return self.verify_report_numbers(bot_folders)
                else:
                    print("No valid report number provided. Some bots may not work correctly.")
        
        return all_set

    def check_database_key_exists(self, bot_folders):
        """Check if database access key exists in any bot folder's venv (EXCLUDING scheduler)"""
        working_bots = [folder for folder in bot_folders if folder.name != self.scheduler_folder]
        
        for folder in working_bots:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                db_key_file = venv_path / "database access key.json"
                if db_key_file.exists():
                    return True, folder, db_key_file
        return False, None, None

    def check_all_bots_have_database_key(self, bot_folders):
        """Check if all bots have database access key (EXCLUDING scheduler)"""
        working_bots = [folder for folder in bot_folders if folder.name != self.scheduler_folder]
        
        for folder in working_bots:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                db_key_file = venv_path / "database access key.json"
                if not db_key_file.exists():
                    return False
            else:
                return False
        return True

    def copy_database_key_to_all_bots(self, source_key_file, bot_folders):
        """Copy database access key to all bot folders (EXCLUDING scheduler)"""
        print(f"Copying database access key to all bots (excluding scheduler)...")
        success_count = 0
        
        working_bots = [folder for folder in bot_folders if folder.name != self.scheduler_folder]
        
        for folder in working_bots:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                target_key_file = venv_path / "database access key.json"
                try:
                    # Skip copying to source folder
                    if source_key_file != target_key_file:
                        shutil.copy2(source_key_file, target_key_file)
                        print(f"  ✓ Copied to {folder.name}/venv/")
                        success_count += 1
                    else:
                        print(f"  ✓ Source folder: {folder.name}/venv/")
                        success_count += 1
                except Exception as e:
                    print(f"  ✗ Failed to copy to {folder.name}/venv/: {e}")
        
        return success_count

    def wait_for_database_key(self, bot_folders):
        """Wait for database access key to be available in any bot folder (EXCLUDING scheduler)"""
        print(f"{self.YELLOW}Database access key not available. Please paste 'database access key.json' in any bot folder's venv (excluding scheduler).{self.ENDC}")
        print("Waiting for database access key... (Checking every 2 seconds)")
        print("Press Ctrl+C to cancel and exit.")
        
        check_count = 0
        try:
            while True:
                check_count += 1
                key_exists, source_folder, source_key_file = self.check_database_key_exists(bot_folders)
                
                if key_exists:
                    print(f"\n{self.GREEN}✓ Database access key found in {source_folder.name}/venv/{self.ENDC}")
                    return source_key_file
                
                # Show waiting animation
                dots = "." * (check_count % 4)
                spaces = " " * (3 - len(dots))
                print(f"\rChecking{dots}{spaces} (Attempt {check_count})", end="", flush=True)
                time.sleep(2)
                
        except KeyboardInterrupt:
            print(f"\n\n{self.RED}Operation cancelled by user.{self.ENDC}")
            return None

    def run_step2(self):
        """Step 2: Database Access Key Management (EXCLUDING scheduler)"""
        print("\n" + "=" * 50)
        print("STEP 2: Database Access Key Management")
        print("=" * 50)
        
        bot_folders = self.get_bot_folders()
        if not bot_folders:
            print("No bot folders found!")
            return False
        
        # Check if all bots already have database key (excluding scheduler)
        if self.check_all_bots_have_database_key(bot_folders):
            print(f"{self.GREEN}✓ All bots (excluding scheduler) already have 'database access key.json' in their venv folders{self.ENDC}")
            return True
        
        # Check if any bot has database key (excluding scheduler)
        key_exists, source_folder, source_key_file = self.check_database_key_exists(bot_folders)
        
        if key_exists:
            print(f"{self.GREEN}✓ Database access key found in {source_folder.name}/venv/{self.ENDC}")
            print("Copying to all other bots (excluding scheduler)...")
        else:
            # Wait for user to provide database key
            source_key_file = self.wait_for_database_key(bot_folders)
            if not source_key_file:
                return False
        
        # Copy database key to all bots (excluding scheduler)
        working_bots = [folder for folder in bot_folders if folder.name != self.scheduler_folder]
        success_count = self.copy_database_key_to_all_bots(source_key_file, bot_folders)
        
        if success_count == len(working_bots):
            print(f"{self.GREEN}✓ Successfully copied database access key to all {len(working_bots)} bots (excluding scheduler){self.ENDC}")
            return True
        else:
            print(f"{self.YELLOW}⚠ Database access key copied to {success_count} out of {len(working_bots)} bots (excluding scheduler){self.ENDC}")
            return True  # Continue anyway

    def check_spreadsheet_key_exists(self, bot_folders):
        """Check if spreadsheet access key exists in any bot folder's venv (INCLUDING scheduler)"""
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                spreadsheet_key_file = venv_path / "spread sheet access key.json"
                if spreadsheet_key_file.exists():
                    return True, folder, spreadsheet_key_file
        return False, None, None

    def check_all_bots_have_spreadsheet_key(self, bot_folders):
        """Check if all bots have spreadsheet access key (INCLUDING scheduler)"""
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                spreadsheet_key_file = venv_path / "spread sheet access key.json"
                if not spreadsheet_key_file.exists():
                    return False
            else:
                return False
        return True

    def copy_spreadsheet_key_to_all_bots(self, source_key_file, bot_folders):
        """Copy spreadsheet access key to all bot folders (INCLUDING scheduler)"""
        print(f"Copying spreadsheet access key to all bots...")
        success_count = 0
        
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                target_key_file = venv_path / "spread sheet access key.json"
                try:
                    # Skip copying to source folder
                    if source_key_file != target_key_file:
                        shutil.copy2(source_key_file, target_key_file)
                        print(f"  ✓ Copied to {folder.name}/venv/")
                        success_count += 1
                    else:
                        print(f"  ✓ Source folder: {folder.name}/venv/")
                        success_count += 1
                except Exception as e:
                    print(f"  ✗ Failed to copy to {folder.name}/venv/: {e}")
        
        return success_count

    def wait_for_spreadsheet_key(self, bot_folders):
        """Wait for spreadsheet access key to be available in any bot folder (INCLUDING scheduler)"""
        print(f"{self.YELLOW}Spreadsheet access key not available. Please paste 'spread sheet access key.json' in any bot folder's venv.{self.ENDC}")
        print("Waiting for spreadsheet access key... (Checking every 1 second)")
        print("Press Ctrl+C to cancel and exit.")
        
        check_count = 0
        try:
            while True:
                check_count += 1
                key_exists, source_folder, source_key_file = self.check_spreadsheet_key_exists(bot_folders)
                
                if key_exists:
                    print(f"\n{self.GREEN}✓ Spreadsheet access key found in {source_folder.name}/venv/{self.ENDC}")
                    return source_key_file
                
                # Show waiting animation
                dots = "." * (check_count % 4)
                spaces = " " * (3 - len(dots))
                print(f"\rChecking{dots}{spaces} (Attempt {check_count})", end="", flush=True)
                time.sleep(1)  # Check every 1 second
                
        except KeyboardInterrupt:
            print(f"\n\n{self.RED}Operation cancelled by user.{self.ENDC}")
            return None

    def run_step3(self):
        """Step 3: Spreadsheet Access Key Management (INCLUDING scheduler)"""
        print("\n" + "=" * 50)
        print("STEP 3: Spreadsheet Access Key Management")
        print("=" * 50)
        
        bot_folders = self.get_bot_folders()
        if not bot_folders:
            print("No bot folders found!")
            return False
        
        # Check if all bots already have spreadsheet key (including scheduler)
        if self.check_all_bots_have_spreadsheet_key(bot_folders):
            print(f"{self.GREEN}✓ All bots (including scheduler) already have 'spread sheet access key.json' in their venv folders{self.ENDC}")
            return True
        
        # Check if any bot has spreadsheet key (including scheduler)
        key_exists, source_folder, source_key_file = self.check_spreadsheet_key_exists(bot_folders)
        
        if key_exists:
            print(f"{self.GREEN}✓ Spreadsheet access key found in {source_folder.name}/venv/{self.ENDC}")
            print("Copying to all other bots (including scheduler)...")
        else:
            # Wait for user to provide spreadsheet key
            source_key_file = self.wait_for_spreadsheet_key(bot_folders)
            if not source_key_file:
                return False
        
        # Copy spreadsheet key to all bots (including scheduler)
        success_count = self.copy_spreadsheet_key_to_all_bots(source_key_file, bot_folders)
        
        if success_count == len(bot_folders):
            print(f"{self.GREEN}✓ Successfully copied spreadsheet access key to all {len(bot_folders)} bots (including scheduler){self.ENDC}")
            return True
        else:
            print(f"{self.YELLOW}⚠ Spreadsheet access key copied to {success_count} out of {len(bot_folders)} bots{self.ENDC}")
            return True  # Continue anyway

    def wait_for_spreadsheet_key_for_step4(self, bot_folders):
        """Wait for spreadsheet access key to be available for Step 4 (continuous checking)"""
        print(f"{self.YELLOW}Spreadsheet access key not available for Step 4.{self.ENDC}")
        print("Waiting for spreadsheet access key... (Checking every 1 second)")
        print("Press Ctrl+C to cancel and exit.")
        
        check_count = 0
        try:
            while True:
                check_count += 1
                key_exists, source_folder, source_key_file = self.check_spreadsheet_key_exists(bot_folders)
                
                if key_exists:
                    print(f"\n{self.GREEN}✓ Spreadsheet access key found in {source_folder.name}/venv/{self.ENDC}")
                    return source_key_file
                
                # Show waiting animation
                dots = "." * (check_count % 4)
                spaces = " " * (3 - len(dots))
                print(f"\rChecking{dots}{spaces} (Attempt {check_count})", end="", flush=True)
                time.sleep(1)  # Check every 1 second
                
        except KeyboardInterrupt:
            print(f"\n\n{self.RED}Operation cancelled by user.{self.ENDC}")
            return None

    def run_step4(self):
        """Step 4: List Google Sheets with unlimited retry"""
        print("\n" + "=" * 50)
        print("STEP 4: Listing Google Sheets")
        print("=" * 50)
        
        bot_folders = self.get_bot_folders()
        if not bot_folders:
            print("No bot folders found!")
            return False
        
        # Find a bot that has the spreadsheet key - wait continuously if not found
        key_exists, source_folder, source_key_file = self.check_spreadsheet_key_exists(bot_folders)
        
        if not key_exists:
            print(f"{self.YELLOW}Spreadsheet access key not found. Waiting for it to become available...{self.ENDC}")
            source_key_file = self.wait_for_spreadsheet_key_for_step4(bot_folders)
            if not source_key_file:
                return False
        
        print(f"{self.GREEN}✓ Using spreadsheet access key from {source_folder.name}/venv/{self.ENDC}")
        
        def list_sheets():
            # Define scopes
            SCOPES = [
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly"
            ]
            
            print("Authorizing with Google Sheets API...")
            
            # Authorize service account
            creds = Credentials.from_service_account_file(
                str(source_key_file),
                scopes=SCOPES
            )
            gc = gspread.authorize(creds)
            
            # Get Google Drive API client
            drive = build("drive", "v3", credentials=creds)
            
            print(f"{self.GREEN}✓ Successfully authorized with Google Sheets API{self.ENDC}")
            print("\nSheets accessible by the Service Account:\n")
            
            # Search only for Google Sheets MIME type
            query = "mimeType='application/vnd.google-apps.spreadsheet'"
            
            page_token = None
            sheet_count = 0
            available_sheets = []
            
            while True:
                response = drive.files().list(
                    q=query,
                    spaces='drive',
                    fields="nextPageToken, files(id, name)",
                    pageToken=page_token
                ).execute()
                
                for file in response.get('files', []):
                    sheet_count += 1
                    sheet_info = {
                        'name': file['name'],
                        'id': file['id'],
                        'number': sheet_count
                    }
                    available_sheets.append(sheet_info)
                    print(f"{sheet_count:2d}. {file['name']}  ->  {file['id']}")
                
                page_token = response.get('nextPageToken', None)
                if not page_token:
                    break
            
            if sheet_count == 0:
                print(f"{self.YELLOW}No Google Sheets found accessible by this service account.{self.ENDC}")
            else:
                print(f"\n{self.GREEN}✓ Found {sheet_count} Google Sheet(s){self.ENDC}")
            
            # Store the sheets for Step 5 comparison
            self.available_sheets = available_sheets
            return True
        
        # Use unlimited retry for listing sheets
        return self.unlimited_retry_api_call(
            list_sheets, 
            "Listing Google Sheets",
            max_retry_delay=300,
            initial_delay=5
        )

    def run_step5(self):
        """Step 5: Compare Bot Folders with Google Sheets (EXACT alphabetical match)"""
        print("\n" + "=" * 50)
        print("STEP 5: Comparing Bot Folders with Google Sheets")
        print("=" * 50)
        print(f"{self.YELLOW}NOTE: Requiring EXACT alphabetical match (case-sensitive){self.ENDC}")
        
        bot_folders = self.get_bot_folders()
        if not bot_folders:
            print("No bot folders found!")
            return False, False  # Return False for both success and all_match
        
        if not hasattr(self, 'available_sheets') or not self.available_sheets:
            print(f"{self.RED}❌ No Google Sheets data available from Step 4{self.ENDC}")
            return False, False
        
        print("Bot folders on Raspberry Pi:")
        bot_folder_names = []
        for i, folder in enumerate(bot_folders, 1):
            print(f"  {i:2d}. {folder.name}")
            bot_folder_names.append(folder.name)
        
        print("\nGoogle Sheets available:")
        sheet_names = []
        for sheet in self.available_sheets:
            print(f"  {sheet['number']:2d}. {sheet['name']}")
            sheet_names.append(sheet['name'])
        
        print(f"\n{self.BOLD}Comparing bot folders with Google Sheets (EXACT match required)...{self.ENDC}")
        
        # Compare EXACT alphabetical matches (case-sensitive)
        missing_sheets = []
        all_match = True
        
        for bot_name in bot_folder_names:
            found = False
            matching_sheet = None
            
            for sheet_name in sheet_names:
                if bot_name == sheet_name:  # EXACT match (case-sensitive)
                    found = True
                    matching_sheet = sheet_name
                    break
            
            if found:
                print(f"{self.GREEN}  ✓ '{bot_name}' matches sheet '{matching_sheet}'{self.ENDC}")
            else:
                all_match = False
                missing_sheets.append(bot_name)
                # Check if there's a case-insensitive match to show as suggestion
                case_insensitive_match = None
                for sheet_name in sheet_names:
                    if bot_name.lower() == sheet_name.lower():
                        case_insensitive_match = sheet_name
                        break
                
                if case_insensitive_match:
                    print(f"{self.RED}  ✗ '{bot_name}' - No EXACT match (found '{case_insensitive_match}' but case doesn't match){self.ENDC}")
                else:
                    print(f"{self.RED}  ✗ '{bot_name}' - No matching Google Sheet found{self.ENDC}")
        
        # Check for extra sheets that don't have corresponding bot folders
        extra_sheets = []
        for sheet_name in sheet_names:
            found = False
            
            for bot_name in bot_folder_names:
                if sheet_name == bot_name:  # EXACT match (case-sensitive)
                    found = True
                    break
            
            if not found and sheet_name != "scheduler":  # Exclude scheduler from extra sheets
                extra_sheets.append(sheet_name)
        
        print(f"\n{self.BOLD}Comparison Results:{self.ENDC}")
        
        if all_match and not extra_sheets:
            print(f"{self.GREEN}✓ All bots have EXACT matching Google Sheets!{self.ENDC}")
            print(f"{self.GREEN}✓ No extra sheets found{self.ENDC}")
            return True, True  # Success and all match
        
        else:
            if missing_sheets:
                print(f"{self.YELLOW}⚠ Missing EXACT Google Sheets for these bots:{self.ENDC}")
                for missing in missing_sheets:
                    # Find case-insensitive matches to suggest
                    suggestions = []
                    for sheet_name in sheet_names:
                        if missing.lower() == sheet_name.lower():
                            suggestions.append(sheet_name)
                    
                    if suggestions:
                        print(f"  - '{missing}' (suggest renaming sheet to: {', '.join(suggestions)})")
                    else:
                        print(f"  - '{missing}'")
            
            if extra_sheets:
                print(f"{self.BLUE}ℹ️  Extra Google Sheets (no corresponding bot):{self.ENDC}")
                for extra in extra_sheets:
                    print(f"  - '{extra}'")
            
            print(f"\n{self.YELLOW}⚠ IMPORTANT: Folder names and Sheet names must match EXACTLY (case-sensitive){self.ENDC}")
            print(f"{self.YELLOW}   Please rename your Google Sheets to match the bot folder names exactly.{self.ENDC}")
            
            # Store missing sheets for Step 7
            self.missing_sheets = missing_sheets
            return True, False  # Success but not all match

    def get_github_bot_folders(self):
        """Get list of bot folders from GitHub repository"""
        print("Fetching bot information from GitHub repository...")
        
        try:
            # Get the main repository structure
            api_url = "https://api.github.com/repos/Thaniyanki/raspberry-pi-bots/contents/"
            response = requests.get(api_url)
            
            if response.status_code != 200:
                print(f"Error accessing GitHub repository: {response.status_code}")
                return []
            
            contents = response.json()
            bot_folders = []
            
            for item in contents:
                if item['type'] == 'dir':
                    folder_name = item['name']
                    # Skip only non-bot folders, include scheduler
                    if folder_name in ['all-in-one-venv', '.github']:  # Removed 'scheduler' from exclusion
                        continue
                    
                    # Check if this folder has both 'sheets format' folder and 'venv.sh'
                    folder_url = f"https://api.github.com/repos/Thaniyanki/raspberry-pi-bots/contents/{folder_name}"
                    folder_response = requests.get(folder_url)
                    
                    if folder_response.status_code == 200:
                        folder_contents = folder_response.json()
                        has_sheets_format = any(content['name'] == 'sheets format' and content['type'] == 'dir' for content in folder_contents)
                        has_venv_sh = any(content['name'] == 'venv.sh' for content in folder_contents)
                        
                        if has_sheets_format and has_venv_sh:
                            bot_folders.append(folder_name)
                            print(f"  ✓ Found bot: {folder_name}")
        
            print(f"{self.GREEN}✓ Found {len(bot_folders)} bots on GitHub{self.ENDC}")
            return bot_folders
            
        except Exception as e:
            print(f"{self.RED}❌ Error fetching GitHub repository: {e}{self.ENDC}")
            return []

    def get_sheets_format_files(self, bot_folder_name):
        """Get the list of CSV files from the 'sheets format' folder for a bot"""
        try:
            sheets_format_url = f"{self.github_raw_base}/{bot_folder_name}/sheets%20format"
            
            # Try to get the directory listing from GitHub
            api_url = f"https://api.github.com/repos/Thaniyanki/raspberry-pi-bots/contents/{bot_folder_name}/sheets%20format"
            response = requests.get(api_url)
            
            if response.status_code != 200:
                print(f"  Error accessing sheets format for {bot_folder_name}: {response.status_code}")
                return []
            
            contents = response.json()
            csv_files = []
            
            for item in contents:
                if item['name'].endswith('.csv'):
                    csv_files.append(item['name'])
                    print(f"    - Found CSV: {item['name']}")
            
            return csv_files
            
        except Exception as e:
            print(f"  Error getting sheets format for {bot_folder_name}: {e}")
            return []

    def download_csv_file(self, bot_folder_name, csv_file):
        """Download a CSV file from GitHub"""
        try:
            # URL encode the file name properly
            encoded_file = csv_file.replace(' ', '%20')
            csv_url = f"{self.github_raw_base}/{bot_folder_name}/sheets%20format/{encoded_file}"
            
            response = requests.get(csv_url)
            if response.status_code == 200:
                return response.text
            else:
                print(f"    Error downloading {csv_file}: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"    Error downloading {csv_file}: {e}")
            return None

    def get_google_sheet_worksheets(self, sheet_name, gc):
        """Get all worksheets from a Google Sheet with unlimited retry"""
        def get_worksheets():
            sheet = gc.open(sheet_name)
            worksheets = sheet.worksheets()
            return [worksheet.title for worksheet in worksheets]
        
        return self.unlimited_retry_api_call(
            lambda: get_worksheets(),
            f"Getting worksheets from '{sheet_name}'",
            max_retry_delay=300,
            initial_delay=5
        )

    def update_worksheet_from_csv(self, sheet_name, worksheet_name, csv_content, gc):
        """Update existing worksheet header row with CSV content with unlimited retry"""
        def update_worksheet():
            sheet = gc.open(sheet_name)
            worksheet = sheet.worksheet(worksheet_name)
            
            # Get current data from worksheet
            current_data = worksheet.get_all_values()
            
            # Parse CSV content
            csv_reader = csv.reader(csv_content.strip().splitlines())
            new_data = list(csv_reader)
            
            # Check if we have at least a header row in both current and new data
            if not current_data:
                print(f"      ⚠ Worksheet '{worksheet_name}' is empty, updating with new format...")
                worksheet.update(range_name='A1', values=new_data)
                print(f"      ✓ Updated worksheet '{worksheet_name}' with new format")
                return True
            
            if not new_data:
                print(f"      ⚠ CSV file for '{worksheet_name}' is empty, skipping update")
                return False
            
            # Compare headers (first row) only
            current_header = current_data[0]
            new_header = new_data[0]
            
            if current_header != new_header:
                print(f"      ⚠ Headers differ in '{worksheet_name}', updating header row only...")
                
                # Update only the header row (first row)
                worksheet.update(range_name='A1', values=[new_header])
                
                print(f"      ✓ Updated header row in worksheet '{worksheet_name}'")
                print(f"      Old header: {current_header}")
                print(f"      New header: {new_header}")
                return True
            else:
                print(f"      ✓ Worksheet '{worksheet_name}' already has correct header format")
                return False
        
        return self.unlimited_retry_api_call(
            update_worksheet,
            f"Updating worksheet '{worksheet_name}' in '{sheet_name}'",
            max_retry_delay=300,
            initial_delay=5
        )

    def create_worksheet_if_missing(self, sheet_name, worksheet_name, csv_content, gc):
        """Create a missing worksheet within an existing Google Sheet with unlimited retry"""
        def create_worksheet():
            sheet = gc.open(sheet_name)
            
            # Check if worksheet already exists
            try:
                sheet.worksheet(worksheet_name)
                print(f"      ✓ Worksheet '{worksheet_name}' already exists")
                return False  # Worksheet already exists
            except gspread.WorksheetNotFound:
                # Worksheet doesn't exist, create it
                print(f"      ⚠ Worksheet '{worksheet_name}' not found, creating...")
                
                # Parse CSV content
                csv_reader = csv.reader(csv_content.strip().splitlines())
                new_data = list(csv_reader)
                
                # Create new worksheet with CSV data
                worksheet = sheet.add_worksheet(title=worksheet_name, rows=100, cols=20)
                
                if new_data:
                    worksheet.update(range_name='A1', values=new_data)
                
                print(f"      ✓ Created worksheet '{worksheet_name}' with {len(new_data)} rows")
                return True
        
        return self.unlimited_retry_api_call(
            create_worksheet,
            f"Creating worksheet '{worksheet_name}' in '{sheet_name}'",
            max_retry_delay=300,
            initial_delay=5
        )

    def run_step6(self):
        """Step 6: Verify Google Sheets Format with unlimited retry"""
        print("\n" + "=" * 50)
        print("STEP 6: Verifying Google Sheets Format")
        print("=" * 50)
        
        # Get bot folders from GitHub
        github_bots = self.get_github_bot_folders()
        if not github_bots:
            print(f"{self.RED}❌ No bots found on GitHub repository{self.ENDC}")
            return False, False
        
        # Get local bot folders
        local_bot_folders = self.get_bot_folders()
        local_bot_names = [folder.name for folder in local_bot_folders]
        
        # Get spreadsheet key
        key_exists, source_folder, source_key_file = self.check_spreadsheet_key_exists(local_bot_folders)
        if not key_exists:
            print(f"{self.RED}❌ Spreadsheet access key not found{self.ENDC}")
            return False, False
        
        def process_sheets():
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
            missing_sheets = []
            all_sheets_available = True
            
            for github_bot in github_bots:
                # Convert GitHub folder name to local folder name format
                local_bot_name = github_bot.replace('-', ' ')
                
                if local_bot_name in local_bot_names:
                    print(f"\n{self.BOLD}Processing: {local_bot_name}{self.ENDC}")
                    
                    # Check if Google Sheet exists for this bot
                    sheet_exists = False
                    try:
                        gc.open(local_bot_name)
                        sheet_exists = True
                        print(f"  ✓ Google Sheet found: {local_bot_name}")
                    except gspread.SpreadsheetNotFound:
                        print(f"  ✗ Google Sheet not found: {local_bot_name}")
                        missing_sheets.append(local_bot_name)
                        all_sheets_available = False
                        continue
                    
                    # Get required CSV files from GitHub
                    csv_files = self.get_sheets_format_files(github_bot)
                    if not csv_files:
                        print(f"  ⚠ No CSV files found in sheets format for {github_bot}")
                        continue
                    
                    # Get existing worksheets from Google Sheet
                    existing_worksheets = self.get_google_sheet_worksheets(local_bot_name, gc)
                    print(f"  Existing worksheets: {existing_worksheets}")
                    
                    # Process each required CSV file
                    for csv_file in csv_files:
                        worksheet_name = csv_file.replace('.csv', '')
                        print(f"  Processing: {worksheet_name}")
                        
                        # Download CSV content from GitHub
                        csv_content = self.download_csv_file(github_bot, csv_file)
                        if not csv_content:
                            print(f"    ✗ Failed to download {csv_file}")
                            continue
                        
                        if worksheet_name in existing_worksheets:
                            # Worksheet exists, check and update header if needed
                            if self.update_worksheet_from_csv(local_bot_name, worksheet_name, csv_content, gc):
                                updated_count += 1
                        else:
                            # Worksheet doesn't exist, create it
                            if self.create_worksheet_if_missing(local_bot_name, worksheet_name, csv_content, gc):
                                created_count += 1
            
            # Summary
            print("\n" + "=" * 50)
            print("STEP 6 SUMMARY:")
            print("=" * 50)
            
            if updated_count > 0:
                print(f"{self.GREEN}✓ Updated {updated_count} worksheet(s) across all bots{self.ENDC}")
            
            if created_count > 0:
                print(f"{self.GREEN}✓ Created {created_count} missing worksheet(s) across all bots{self.ENDC}")
            
            if updated_count == 0 and created_count == 0:
                print(f"{self.GREEN}✓ All worksheets are up-to-date{self.ENDC}")
            
            if missing_sheets:
                print(f"{self.YELLOW}⚠ Missing Google Sheets for these bots:{self.ENDC}")
                for missing in missing_sheets:
                    print(f"  - {missing}")
                all_sheets_available = False
            
            if all_sheets_available:
                print(f"{self.GREEN}✓ All required sheets and worksheets are available{self.ENDC}")
                return True, True
            else:
                print(f"{self.YELLOW}⚠ Some sheets or worksheets are missing{self.ENDC}")
                return True, False
        
        # Use unlimited retry for the entire Step 6 process
        try:
            return self.unlimited_retry_api_call(
                process_sheets,
                "Step 6: Verifying Google Sheets Format",
                max_retry_delay=300,
                initial_delay=10
            )
        except Exception as e:
            print(f"{self.RED}❌ Step 6 failed after unlimited retries: {e}{self.ENDC}")
            return False, False

    def fetch_xpaths_from_database(self):
        """Fetch all XPaths from Firebase database"""
        print("Fetching XPaths from Firebase database...")
        
        # Find database access key from any bot (excluding scheduler)
        bot_folders = self.get_bot_folders()
        key_exists, source_folder, source_key_file = self.check_database_key_exists(bot_folders)
        
        if not key_exists:
            print(f"{self.RED}❌ Database access key not found in any bot folder{self.ENDC}")
            return False
        
        try:
            # Initialize Firebase app
            if not firebase_admin._apps:
                cred = credentials.Certificate(str(source_key_file))
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://your-firebase-project.firebaseio.com/'
                })
            
            # Fetch XPaths from Firebase
            ref = db.reference('WhatsApp/Xpath')
            xpaths_data = ref.get()
            
            if xpaths_data:
                self.xpaths = xpaths_data
                print(f"{self.GREEN}✓ Successfully fetched {len(xpaths_data)} XPaths from database{self.ENDC}")
                
                # Save XPaths to temporary local storage
                temp_file = Path("/tmp/whatsapp_xpaths.json")
                with open(temp_file, 'w') as f:
                    json.dump(xpaths_data, f, indent=2)
                print(f"{self.GREEN}✓ XPaths saved to temporary storage: {temp_file}{self.ENDC}")
                return True
            else:
                print(f"{self.RED}❌ No XPaths found in database{self.ENDC}")
                return False
                
        except Exception as e:
            print(f"{self.RED}❌ Error fetching XPaths from database: {e}{self.ENDC}")
            return False

    def check_internet_connection(self):
        """Check internet connection using ping"""
        try:
            # Try to ping Google DNS
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
        """Wait for internet connection to become available"""
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
        """Close the browser if open"""
        if self.driver:
            try:
                self.driver.quit()
                print("Browser closed")
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
                    # Press Shift+Enter for new line
                    actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT)
                actions.send_keys(line)
            
            actions.perform()
            
            print("Message typed successfully")
            return True
            
        except Exception as e:
            print(f"{self.RED}❌ Error sending message: {e}{self.ENDC}")
            return False

    def run_step7(self, missing_bots):
        """Step 7: Send WhatsApp notification for missing sheets"""
        print("\n" + "=" * 50)
        print("STEP 7: Sending WhatsApp Notification")
        print("=" * 50)
        
        # Step 7: Fetch XPaths from database
        if not self.fetch_xpaths_from_database():
            return False
        
        # Step 7a: Close browser if open and reopen
        self.close_browser()
        if not self.setup_selenium_driver():
            return False
        
        # Step 7b: Check internet connection
        if not self.check_internet_connection():
            print("Internet not available, waiting...")
            if not self.wait_for_internet():
                return False
        
        # Step 7c: Open WhatsApp Web
        print("Opening WhatsApp Web...")
        try:
            self.driver.get("https://web.whatsapp.com/")
            print("WhatsApp Web opened")
        except Exception as e:
            print(f"{self.RED}❌ Error opening WhatsApp: {e}{self.ENDC}")
            return False
        
        # Step 7d: Wait for XPath001 (search field)
        print("Waiting for search field (XPath001)...")
        xpath001 = self.xpaths.get('Xpath001')
        if not xpath001:
            print(f"{self.RED}❌ XPath001 not found in database{self.ENDC}")
            return False
        
        search_field = self.wait_for_xpath(xpath001, 120)
        if not search_field:
            print("Search field not found within 120 seconds")
            
            # Step 7f: Check for loading indicator
            xpath011 = self.xpaths.get('Xpath011')
            if xpath011 and self.check_xpath_present(xpath011):
                print("Loading indicator found, retrying...")
                return self.run_step7(missing_bots)  # Restart from 7a
            else:
                print("No loading indicator, restarting...")
                return self.run_step7(missing_bots)  # Restart from 7a
        
        # Step 7e: Click search field and check report number file
        print("Entered Mobile number search field")
        search_field.click()
        
        report_number = self.get_report_number()
        if not report_number:
            print("Report number file not available")
            return False
        print("Report number file available")
        
        # Step 7g: Check if phone number is valid
        if not self.is_valid_phone_number(report_number):
            print("Phone number is not available or invalid")
            return False
        print("Phone number is available")
        
        # Step 7h: Type phone number
        search_field.send_keys(report_number)
        print("Phone number entered")
        time.sleep(10)  # Wait for stability
        
        # Step 7i: Check if contact not found
        xpath004 = self.xpaths.get('Xpath004')
        if xpath004 and self.check_xpath_present(xpath004):
            print("Contact not found (XPath004 present)")
            if self.check_internet_connection():
                print("Invalid Mobile Number")
                return False
            else:
                print("No internet, restarting...")
                return self.run_step7(missing_bots)  # Restart from 7a
        
        # Step 7j: Select contact and enter message field
        search_field.send_keys(Keys.ARROW_DOWN)
        time.sleep(2)
        search_field.send_keys(Keys.ENTER)
        print("Entered Message Field")
        
        # Step 7k: Type error message
        if not self.send_whatsapp_message(missing_bots):
            return False
        
        # Step 7l: Send message
        time.sleep(2)
        search_field = self.driver.find_element(By.XPATH, xpath001)
        search_field.send_keys(Keys.ENTER)
        print("Message sent")
        
        # Step 7m: Wait for message to be delivered
        print("Waiting for message delivery...")
        xpath003 = self.xpaths.get('Xpath003')
        if xpath003:
            while self.check_xpath_present(xpath003):
                time.sleep(1)
        
        print("Error message sent successfully")
        return True

    def run_step8(self):
        """Step 8: All sheets available with correct format"""
        print("\n" + "=" * 50)
        print("STEP 8: All Sheets Available with Correct Format")
        print("=" * 50)
        print(f"{self.GREEN}✓ All Google Sheets are available with correct format!{self.ENDC}")
        print("Continuing with bot execution setup...")
        return True

    def run(self):
        """Main execution function"""
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
            print("✓ All report numbers are properly set in venv folders (including scheduler)")
        else:
            print("⚠ Step 1 completed with warnings")
            print("⚠ Some report numbers may not be set correctly in venv folders")
        
        print("=" * 50)
        
        # Run Step 2
        step2_success = self.run_step2()
        
        if step2_success:
            print("\n" + "=" * 50)
            print("✓ Step 2 completed successfully!")
            print("✓ All database access keys are properly set in venv folders (excluding scheduler)")
            print("=" * 50)
            
            # Run Step 3
            step3_success = self.run_step3()
            
            if step3_success:
                print("\n" + "=" * 50)
                print("✓ Step 3 completed successfully!")
                print("✓ All spreadsheet access keys are properly set in venv folders (including scheduler)")
                print("=" * 50)
                
                # Run Step 4
                step4_success = self.run_step4()
                
                if step4_success:
                    print("\n" + "=" * 50)
                    print("✓ Step 4 completed successfully!")
                    print("✓ Google Sheets listed successfully")
                    print("=" * 50)
                    
                    # Run Step 5
                    step5_success, all_match = self.run_step5()
                    
                    if step5_success:
                        print("\n" + "=" * 50)
                        print("✓ Step 5 completed successfully!")
                        print("=" * 50)
                        
                        if all_match:
                            # All bots have matching sheets - continue to Step 6
                            step6_success, all_sheets_available = self.run_step6()
                            if step6_success:
                                print("\n" + "=" * 50)
                                print("✓ Step 6 completed successfully!")
                                print("=" * 50)
                                
                                if all_sheets_available:
                                    # All sheets available with correct format - continue to Step 8
                                    step8_success = self.run_step8()
                                    if step8_success:
                                        print("\n" + "=" * 50)
                                        print("✓ Step 8 completed successfully!")
                                        print("✓ All Google Sheets verified and updated")
                                        print("=" * 50)
                                        # Continue to next steps...
                                    else:
                                        print(f"\n{self.RED}❌ Step 8 failed.{self.ENDC}")
                                        sys.exit(1)
                                else:
                                    # Some sheets missing - continue to Step 7
                                    missing_bots = getattr(self, 'missing_sheets', [])
                                    if not missing_bots:
                                        missing_bots = ["Unknown bot"]
                                    step7_success = self.run_step7(missing_bots)
                                    if step7_success:
                                        print("\n" + "=" * 50)
                                        print("✓ Step 7 completed successfully!")
                                        print("✓ WhatsApp notification sent")
                                        print("=" * 50)
                                        # Continue to Step 8 after sending notification
                                        step8_success = self.run_step8()
                                        if step8_success:
                                            print("\n" + "=" * 50)
                                            print("✓ Step 8 completed successfully!")
                                            print("=" * 50)
                                    else:
                                        print(f"\n{self.RED}❌ Step 7 failed.{self.ENDC}")
                                        sys.exit(1)
                            else:
                                print(f"\n{self.RED}❌ Step 6 failed.{self.ENDC}")
                                sys.exit(1)
                        else:
                            # Some bots missing matching sheets - continue to Step 7
                            missing_bots = getattr(self, 'missing_sheets', [])
                            if not missing_bots:
                                missing_bots = ["Unknown bot"]
                            step7_success = self.run_step7(missing_bots)
                            if step7_success:
                                print("\n" + "=" * 50)
                                print("✓ Step 7 completed successfully!")
                                print("✓ WhatsApp notification sent")
                                print("=" * 50)
                                # Continue to Step 8 after sending notification
                                step8_success = self.run_step8()
                                if step8_success:
                                    print("\n" + "=" * 50)
                                    print("✓ Step 8 completed successfully!")
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

def main():
    """Main function"""
    try:
        scheduler = BotScheduler()
        scheduler.run()
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
