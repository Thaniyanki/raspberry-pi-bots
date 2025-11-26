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
import threading
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
        
        # Bot management
        self.bot_processes = {}
        self.schedule_data = {}
        self.last_sync_time = None
        
        # Browser management
        self.driver = None
        self.xpaths = {}
        self.missing_sheets = []
        self.firebase_initialized = False
        
        # XPath mapping - Hidden from user
        self._xpath_mapping = {
            "search_field": "Xpath001",
            "message_input": "Xpath002", 
            "pending_indicator": "Xpath003",
            "contact_not_found": "Xpath004"
        }
        
        # New variables for step 9a-9d
        self.local_schedule_data = {}  # Store local copy of schedule data
        self.bot_execution_status = {}  # Track bot execution status
        
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
                
                # Save XPaths to temporary local storage
                temp_xpath_file = Path("/tmp/whatsapp_xpaths.json")
                with open(temp_xpath_file, 'w') as f:
                    json.dump(xpaths_data, f, indent=2)
                print(f"✅ XPaths saved to {temp_xpath_file}")
                
                # Display generic info about fetched XPaths (not the actual values)
                print(f"\n{self.BLUE}Fetched XPath elements:{self.ENDC}")
                for xpath_name in sorted(self.xpaths.keys()):
                    print(f"  • {xpath_name}: [HIDDEN]")
                    
                return True
            else:
                print(f"{self.RED}❌ No XPaths found in database{self.ENDC}")
                return False
                
        except Exception as e:
            print(f"{self.RED}❌ Error fetching XPaths: {e}{self.ENDC}")
            return False

    def _get_xpath(self, element_type):
        """Get XPath value by element type - hidden from user"""
        if element_type in self._xpath_mapping:
            xpath_key = self._xpath_mapping[element_type]
            return self.xpaths.get(xpath_key)
        return None

    def run_curl_command(self):
        """Run the curl command to setup bots with LIVE output"""
        print("Setting up bots using curl command...")
        try:
            print("Starting bot installation... This may take several minutes.")
            print("=" * 60)
            
            process = subprocess.run(
                'curl -sL "https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main/all-in-one-venv/all%20in%20one%20venv.py" | python3',
                shell=True,
                stdout=None,
                stderr=None,
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
                            return False
                    except:
                        return False
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
        
        source_bot, report_number = next(iter(valid_report_numbers.items()))
        print(f"Found valid report number '{report_number}' in {source_bot}")
        
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
        
        cleaned_number = phone_number.replace(' ', '').replace('-', '').replace('+', '').replace('(', '').replace(')', '')
        
        if not cleaned_number.isdigit():
            return False
        
        if len(cleaned_number) < 10 or len(cleaned_number) > 15:
            return False
        
        return True
    
    def get_report_number_input(self):
        """Get report number input with validation and fallback for piped input"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            if not sys.stdin.isatty():
                try:
                    print(f"{self.YELLOW}Enter the report number (phone number): {self.ENDC}", end='', flush=True)
                    with open('/dev/tty', 'r') as tty:
                        report_number = tty.readline().strip()
                    
                    if self.is_valid_phone_number(report_number):
                        return report_number
                    elif report_number:
                        print(f"Error: '{report_number}' is not a valid phone number. Please enter only digits.")
                        if attempt < max_attempts - 1:
                            print(f"Attempt {attempt + 1} of {max_attempts}")
                        continue
                    else:
                        return None
                        
                except:
                    print("\nCannot read input from pipe.")
                    print("Please download and run the script directly:")
                    print("curl -sL 'https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main/scheduler/scheduler.py' -o scheduler.py && python3 scheduler.py")
                    return None
            else:
                try:
                    print(f"{self.YELLOW}Enter the report number (phone number): {self.ENDC}", end='', flush=True)
                    report_number = input().strip()
                    
                    if self.is_valid_phone_number(report_number):
                        return report_number
                    elif report_number:
                        print(f"Error: '{report_number}' is not a valid phone number. Please enter only digits.")
                        if attempt < max_attempts - 1:
                            print(f"Attempt {attempt + 1} of {max_attempts}")
                        continue
                    else:
                        return None
                        
                except (KeyboardInterrupt, EOFError):
                    return None
        
        print("Maximum attempts reached. Please run the script again.")
        return None
    
    def handle_report_numbers(self, bot_folders):
        """Handle report number creation/modification - AUTO COPY from existing bots (INCLUDING scheduler)"""
        all_have_report_numbers = self.check_report_numbers_exist(bot_folders)
        all_report_numbers_valid = self.check_report_numbers_valid(bot_folders)
        
        if not all_have_report_numbers or not all_report_numbers_valid:
            if not all_have_report_numbers:
                print("Some bots are missing report numbers in their venv folders.")
            if not all_report_numbers_valid:
                print("Some bots have empty or invalid report numbers in their venv folders.")
            
            print("Attempting to auto-copy report numbers from bots that have them...")
            if self.copy_report_numbers_from_valid_bots(bot_folders):
                print("Auto-copy completed successfully!")
                return
            
            print("No valid report numbers found to copy from.")
            report_number = self.get_report_number_input()
            
            if report_number:
                self.create_report_numbers(bot_folders, report_number)
                print(f"Report number '{report_number}' set for all bots in their venv folders.")
            else:
                print("No valid report number provided. Please run the script again to set report numbers.")
                sys.exit(1)
            return
        
        print("Report number already available in all bots folder's venv folders.")
        
        if not sys.stdin.isatty():
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
        
        if empty_files_found:
            print("\nSome bots have empty or invalid report numbers. Attempting auto-copy...")
            if self.copy_report_numbers_from_valid_bots(bot_folders):
                print("Auto-copy completed successfully!")
                print("\nRe-verifying report numbers...")
                return self.verify_report_numbers(bot_folders)
            else:
                print("No valid report numbers found to copy from.")
                report_number = self.get_report_number_input()
                if report_number:
                    self.create_report_numbers(bot_folders, report_number)
                    print(f"Report number '{report_number}' updated for all bots.")
                    print("\nRe-verifying report numbers...")
                    return self.verify_report_numbers(bot_folders)
                else:
                    print("No valid report number provided. Some bots may not work correctly.")
        
        return all_set

    def check_database_key_exists(self, bot_folders):
        """Check if database access key exists in any bot folder's venv (EXCLUDING scheduler)"""
        for folder in bot_folders:
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
        
        if self.check_all_bots_have_database_key(bot_folders):
            print(f"{self.GREEN}✓ All bots (excluding scheduler) already have 'database access key.json' in their venv folders{self.ENDC}")
            return True
        
        key_exists, source_folder, source_key_file = self.check_database_key_exists(bot_folders)
        
        if key_exists:
            print(f"{self.GREEN}✓ Database access key found in {source_folder.name}/venv/{self.ENDC}")
            print("Copying to all other bots (excluding scheduler)...")
        else:
            source_key_file = self.wait_for_database_key(bot_folders)
            if not source_key_file:
                return False
        
        working_bots = [folder for folder in bot_folders if folder.name != self.scheduler_folder]
        success_count = self.copy_database_key_to_all_bots(source_key_file, bot_folders)
        
        if success_count == len(working_bots):
            print(f"{self.GREEN}✓ Successfully copied database access key to all {len(working_bots)} bots (excluding scheduler){self.ENDC}")
            return True
        else:
            print(f"{self.YELLOW}⚠ Database access key copied to {success_count} out of {len(working_bots)} bots (excluding scheduler){self.ENDC}")
            return True

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
                
                dots = "." * (check_count % 4)
                spaces = " " * (3 - len(dots))
                print(f"\rChecking{dots}{spaces} (Attempt {check_count})", end="", flush=True)
                time.sleep(1)
                
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
        
        if self.check_all_bots_have_spreadsheet_key(bot_folders):
            print(f"{self.GREEN}✓ All bots (including scheduler) already have 'spread sheet access key.json' in their venv folders{self.ENDC}")
            return True
        
        key_exists, source_folder, source_key_file = self.check_spreadsheet_key_exists(bot_folders)
        
        if key_exists:
            print(f"{self.GREEN}✓ Spreadsheet access key found in {source_folder.name}/venv/{self.ENDC}")
            print("Copying to all other bots (including scheduler)...")
        else:
            source_key_file = self.wait_for_spreadsheet_key(bot_folders)
            if not source_key_file:
                return False
        
        success_count = self.copy_spreadsheet_key_to_all_bots(source_key_file, bot_folders)
        
        if success_count == len(bot_folders):
            print(f"{self.GREEN}✓ Successfully copied spreadsheet access key to all {len(bot_folders)} bots (including scheduler){self.ENDC}")
            return True
        else:
            print(f"{self.YELLOW}⚠ Spreadsheet access key copied to {success_count} out of {len(bot_folders)} bots{self.ENDC}")
            return True

    def run_step4(self):
        """Step 4: List Google Sheets"""
        print("\n" + "=" * 50)
        print("STEP 4: Listing Google Sheets")
        print("=" * 50)
        
        bot_folders = self.get_bot_folders()
        if not bot_folders:
            print("No bot folders found!")
            return False
        
        key_exists, source_folder, source_key_file = self.check_spreadsheet_key_exists(bot_folders)
        
        if not key_exists:
            print(f"{self.YELLOW}Spreadsheet access key not found. Waiting for it to become available...{self.ENDC}")
            check_count = 0
            while True:
                check_count += 1
                key_exists, source_folder, source_key_file = self.check_spreadsheet_key_exists(bot_folders)
                if key_exists:
                    break
                dots = "." * (check_count % 4)
                spaces = " " * (3 - len(dots))
                print(f"\rChecking{dots}{spaces} (Attempt {check_count})", end="", flush=True)
                time.sleep(1)
        
        print(f"{self.GREEN}✓ Using spreadsheet access key from {source_folder.name}/venv/{self.ENDC}")
        
        try:
            SCOPES = [
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly"
            ]
            
            print("Authorizing with Google Sheets API...")
            
            creds = Credentials.from_service_account_file(
                str(source_key_file),
                scopes=SCOPES
            )
            gc = gspread.authorize(creds)
            
            drive = build("drive", "v3", credentials=creds)
            
            print(f"{self.GREEN}✓ Successfully authorized with Google Sheets API{self.ENDC}")
            print("\nSheets accessible by the Service Account:\n")
            
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
            
            self.available_sheets = available_sheets
            return True
            
        except ImportError as e:
            print(f"{self.RED}❌ Required libraries not installed: {e}{self.ENDC}")
            print("Please install required packages:")
            print("pip install gspread google-auth google-api-python-client")
            return False
            
        except Exception as e:
            print(f"{self.RED}❌ Error listing Google Sheets: {e}{self.ENDC}")
            return False

    def run_step5(self):
        """Step 5: Compare Bot Folders with Google Sheets (EXACT alphabetical match)"""
        print("\n" + "=" * 50)
        print("STEP 5: Comparing Bot Folders with Google Sheets")
        print("=" * 50)
        print(f"{self.YELLOW}NOTE: Requiring EXACT alphabetical match (case-sensitive){self.ENDC}")
        
        bot_folders = self.get_bot_folders()
        if not bot_folders:
            print("No bot folders found!")
            return False, False
        
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
        
        missing_sheets = []
        all_match = True
        
        for bot_name in bot_folder_names:
            found = False
            matching_sheet = None
            
            for sheet_name in sheet_names:
                if bot_name == sheet_name:
                    found = True
                    matching_sheet = sheet_name
                    break
            
            if found:
                print(f"{self.GREEN}  ✓ '{bot_name}' matches sheet '{matching_sheet}'{self.ENDC}")
            else:
                all_match = False
                missing_sheets.append(bot_name)
                case_insensitive_match = None
                for sheet_name in sheet_names:
                    if bot_name.lower() == sheet_name.lower():
                        case_insensitive_match = sheet_name
                        break
                
                if case_insensitive_match:
                    print(f"{self.RED}  ✗ '{bot_name}' - No EXACT match (found '{case_insensitive_match}' but case doesn't match){self.ENDC}")
                else:
                    print(f"{self.RED}  ✗ '{bot_name}' - No matching Google Sheet found{self.ENDC}")
        
        extra_sheets = []
        for sheet_name in sheet_names:
            found = False
            
            for bot_name in bot_folder_names:
                if sheet_name == bot_name:
                    found = True
                    break
            
            if not found and sheet_name != "scheduler":
                extra_sheets.append(sheet_name)
        
        print(f"\n{self.BOLD}Comparison Results:{self.ENDC}")
        
        if all_match and not extra_sheets:
            print(f"{self.GREEN}✓ All bots have EXACT matching Google Sheets!{self.ENDC}")
            print(f"{self.GREEN}✓ No extra sheets found{self.ENDC}")
            return True, True
        
        else:
            if missing_sheets:
                print(f"{self.YELLOW}⚠ Missing EXACT Google Sheets for these bots:{self.ENDC}")
                for missing in missing_sheets:
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
            
            self.missing_sheets = missing_sheets
            return True, False

    def get_github_bot_folders(self):
        """Get list of bot folders from GitHub repository"""
        print("Fetching bot information from GitHub repository...")
        
        try:
            # Get the main repository structure
            api_url = "https://api.github.com/repos/Thaniyanki/raspberry-pi-bots/contents/"
            response = requests.get(api_url, timeout=30)
            
            if response.status_code != 200:
                print(f"Error accessing GitHub repository: {response.status_code}")
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
            print(f"{self.RED}❌ Error fetching GitHub repository: {e}{self.ENDC}")
            return []

    def get_csv_files_from_github(self, bot_folder_name):
        """Get the list of CSV files from the 'sheets format' folder for a bot"""
        try:
            # Try to get the directory listing from GitHub
            api_url = f"https://api.github.com/repos/Thaniyanki/raspberry-pi-bots/contents/{bot_folder_name}/sheets%20format"
            response = requests.get(api_url, timeout=30)
            
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

    def download_csv_header_with_retry(self, bot_folder_name, csv_file, max_retries=3):
        """Download only the header row from a CSV file with retry logic"""
        for attempt in range(1, max_retries + 1):
            try:
                # URL encode the file name properly
                encoded_file = csv_file.replace(' ', '%20')
                csv_url = f"{self.github_raw_base}/{bot_folder_name}/sheets%20format/{encoded_file}"
                
                print(f"    Download attempt {attempt} for {csv_file}...")
                response = requests.get(csv_url, timeout=30)
                
                if response.status_code == 200:
                    # Read only the first line (header)
                    first_line = response.text.split('\n')[0]
                    csv_reader = csv.reader([first_line])
                    header = next(csv_reader)
                    print(f"    ✓ Successfully downloaded header for {csv_file}")
                    return header
                else:
                    print(f"    Error downloading {csv_file}: HTTP {response.status_code}")
                    
            except requests.exceptions.ConnectionError as e:
                print(f"    Connection error on attempt {attempt} for {csv_file}: {e}")
            except requests.exceptions.Timeout:
                print(f"    Timeout error on attempt {attempt} for {csv_file}")
            except Exception as e:
                print(f"    Error downloading {csv_file} on attempt {attempt}: {e}")
            
            # Wait before retrying (exponential backoff)
            if attempt < max_retries:
                wait_time = 2 ** attempt  # 2, 4, 8 seconds
                print(f"    Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        print(f"    ✗ Failed to download header for {csv_file} after {max_retries} attempts")
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
            print(f"    Error accessing Google Sheet '{sheet_name}': {e}")
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
                    print(f"      ✓ Worksheet '{worksheet_name}' header matches CSV")
                    return False  # No update needed
                else:
                    print(f"      ⚠ Worksheet '{worksheet_name}' header differs from CSV")
                    print(f"        Current: {current_header}")
                    print(f"        CSV: {csv_header}")
                    
                    # Update the header row
                    worksheet.update(range_name='A1', values=[csv_header])
                    print(f"      ✓ Updated worksheet '{worksheet_name}' header")
                    return True  # Updated
            else:
                # Create new worksheet with CSV header
                print(f"      ⚠ Creating missing worksheet: {worksheet_name}")
                worksheet = sheet.add_worksheet(title=worksheet_name, rows=100, cols=len(csv_header))
                worksheet.update(range_name='A1', values=[csv_header])
                print(f"      ✓ Created worksheet '{worksheet_name}' with CSV header")
                return True  # Created
                
        except Exception as e:
            print(f"      ❌ Error updating worksheet '{worksheet_name}': {e}")
            return False

    def run_step6(self):
        """Step 6: Compare CSV headers with Google Sheets and create/update worksheets"""
        print("\n" + "=" * 50)
        print("STEP 6: Comparing CSV Headers with Google Sheets")
        print("=" * 50)
        print(f"{self.YELLOW}Note: Comparing CSV headers from GitHub with Google Sheets worksheets{self.ENDC}")
        
        try:
            # Get bot folders from GitHub
            github_bots = self.get_github_bot_folders()
            if not github_bots:
                print(f"{self.RED}❌ No bots with sheets format found on GitHub repository{self.ENDC}")
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
            
            for github_bot in github_bots:
                # Convert GitHub folder name to local folder name format
                # GitHub: whatsapp-messenger -> Local: whatsapp messenger
                local_bot_name = github_bot.replace('-', ' ')
                
                if local_bot_name in local_bot_names:
                    print(f"\n{self.BOLD}Processing: {local_bot_name}{self.ENDC}")
                    processed_bots.append(local_bot_name)
                    
                    try:
                        # Check if Google Sheet exists for this bot
                        try:
                            sheet = gc.open(local_bot_name)
                            print(f"  ✓ Google Sheet found: {local_bot_name}")
                        except gspread.SpreadsheetNotFound:
                            print(f"  ✗ Google Sheet not found: {local_bot_name}")
                            error_count += 1
                            continue
                        
                        # Get CSV files from GitHub
                        csv_files = self.get_csv_files_from_github(github_bot)
                        if not csv_files:
                            print(f"  ⚠ No CSV files found for {github_bot}")
                            continue
                        
                        print(f"  CSV files to process: {csv_files}")
                        
                        # Process each CSV file
                        for csv_file in csv_files:
                            worksheet_name = csv_file.replace('.csv', '')
                            print(f"  Processing: {worksheet_name}")
                            
                            # Download CSV header from GitHub with retry logic
                            csv_header = self.download_csv_header_with_retry(github_bot, csv_file)
                            if not csv_header:
                                print(f"    ✗ Failed to download header for {csv_file} after retries")
                                error_count += 1
                                continue
                            
                            print(f"    CSV Header: {csv_header}")
                            
                            # Compare and update worksheet
                            if self.compare_and_update_worksheet(sheet, worksheet_name, csv_header, gc):
                                if worksheet_name in [ws.title for ws in sheet.worksheets()]:
                                    updated_count += 1
                                else:
                                    created_count += 1
                    
                    except Exception as e:
                        print(f"  ❌ Error processing bot '{local_bot_name}': {e}")
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
            
            if error_count > 0:
                print(f"{self.YELLOW}⚠ Encountered {error_count} error(s){self.ENDC}")
            
            if created_count == 0 and updated_count == 0 and error_count == 0:
                print(f"{self.GREEN}✓ All worksheets are up-to-date with CSV headers{self.ENDC}")
                return True, True
            elif error_count == 0:
                print(f"{self.GREEN}✓ Worksheets synchronized successfully{self.ENDC}")
                return True, True
            else:
                print(f"{self.YELLOW}⚠ Worksheets synchronization completed with some errors{self.ENDC}")
                return True, False
            
        except Exception as e:
            print(f"{self.RED}❌ Error in Step 6: {e}{self.ENDC}")
            print(f"{self.YELLOW}⚠ Continuing to next step despite Step 6 errors{self.ENDC}")
            return False, False

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
                    print(f"  ✓ Internet connection available (ping to {target} successful)")
                    return True
                    
            except subprocess.TimeoutExpired:
                print(f"  ⚠ Ping to {target} timed out")
                continue
            except Exception as e:
                print(f"  ⚠ Ping to {target} failed: {e}")
                continue
        
        print("  ✗ No internet connection available")
        return False

    def wait_for_internet_connection(self):
        """Wait for internet connection to become available, checking every 2 seconds"""
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
        print("Closing Chrome browser if open...")
        
        browsers = ['chromium', 'chrome']
        
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                print("✅ Chrome browser closed via Selenium")
            except Exception as e:
                print(f"⚠️ Error closing Selenium driver: {str(e)}")
        
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

    def setup_selenium_driver(self):
        """Setup Selenium WebDriver with Chrome options"""
        print("Setting up Selenium WebDriver...")
        
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
            
            print(f"{self.GREEN}✅ WebDriver setup completed{self.ENDC}")
            return True
            
        except Exception as e:
            print(f"{self.RED}❌ Error setting up WebDriver: {e}{self.ENDC}")
            return False

    def wait_for_element(self, element_type, timeout=120, check_interval=1):
        """Wait for element to be present using XPath from database - HIDDEN from user"""
        xpath = self._get_xpath(element_type)
        if not xpath:
            print(f"{self.RED}❌ XPath for '{element_type}' not found in database{self.ENDC}")
            return None
        
        print(f"Waiting for {element_type} (timeout: {timeout}s)...")
        
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < timeout:
            check_count += 1
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                if element.is_displayed():
                    print(f"  ✓ {element_type} found after {check_count} checks")
                    return element
            except NoSuchElementException:
                pass
            
            elapsed = int(time.time() - start_time)
            if check_count % 10 == 0:
                print(f"  Checking... {elapsed}s elapsed")
            
            time.sleep(check_interval)
        
        print(f"  ✗ {element_type} not found within {timeout} seconds")
        return None

    def check_element_present(self, element_type):
        """Check if element is present using XPath from database - HIDDEN from user"""
        xpath = self._get_xpath(element_type)
        if not xpath:
            return False
        
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
        """Step 7: Main step 7 execution - Send WhatsApp notification for missing sheets"""
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
                print(f"\n{self.BLUE}Browser Management{self.ENDC}")
                self.close_chrome_browser()
                time.sleep(3)
                if not self.setup_selenium_driver():
                    print("❌ Browser setup failed, restarting...")
                    continue
                
                # Check internet
                print(f"\n{self.BLUE}Internet Connection Check{self.ENDC}")
                if not self.check_internet_connection():
                    if not self.wait_for_internet_connection():
                        print("❌ No internet connection, restarting...")
                        continue
                
                # Open WhatsApp
                print(f"\n{self.BLUE}WhatsApp Web Setup{self.ENDC}")
                try:
                    self.driver.get("https://web.whatsapp.com/")
                    print("✓ WhatsApp Web opened")
                except Exception as e:
                    print(f"❌ Error opening WhatsApp Web: {e}")
                    continue
                
                # Check search field
                print(f"\n{self.BLUE}Checking Search Field{self.ENDC}")
                search_field = self.wait_for_element("search_field", timeout=120)
                if not search_field:
                    print("❌ Search field not found, restarting...")
                    continue
                print("✓ Entered Mobile number search field")
                
                # Get report number
                print(f"\n{self.BLUE}Checking Report Number{self.ENDC}")
                report_number = self.get_report_number()
                if not report_number:
                    print("❌ Report number not available")
                    return False
                print(f"✓ Phone number: {report_number}")
                
                # Enter phone number
                print(f"\n{self.BLUE}Entering Phone Number{self.ENDC}")
                try:
                    search_field.clear()
                    search_field.send_keys(report_number)
                    print(f"✓ Phone number entered: {report_number}")
                    time.sleep(2)
                    search_field.send_keys(Keys.ENTER)
                    print("✓ Enter key pressed")
                    time.sleep(10)
                except Exception as e:
                    print(f"❌ Error entering phone number: {e}")
                    continue
                
                # Check contact existence
                print(f"\n{self.BLUE}Checking Contact Existence{self.ENDC}")
                if self.check_element_present("contact_not_found"):
                    print("❌ Contact not found")
                    if self.check_internet_connection():
                        print("✗ Invalid Mobile Number")
                        return False
                    else:
                        print("No internet connection, restarting...")
                        continue
                else:
                    print("✓ Contact found")
                
                # Select contact
                print(f"\n{self.BLUE}Selecting Contact{self.ENDC}")
                try:
                    time.sleep(10)
                    body = self.driver.find_element(By.TAG_NAME, 'body')
                    body.send_keys(Keys.ARROW_DOWN)
                    print("✓ Down arrow pressed")
                    time.sleep(2)
                    body.send_keys(Keys.ENTER)
                    print("✓ Enter pressed - Entered Message Field")
                except Exception as e:
                    print(f"❌ Error selecting contact: {e}")
                    continue
                
                # Type error message
                print(f"\n{self.BLUE}Composing Error Message{self.ENDC}")
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
                    
                    print("✓ Error message composed")
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
                print(f"\n{self.BLUE}Waiting for Message Delivery{self.ENDC}")
                try:
                    time.sleep(2)
                    print("Monitoring message delivery...")
                    
                    start_time = time.time()
                    check_count = 0
                    pending_indicator_was_present = False
                    
                    while time.time() - start_time < 300:
                        check_count += 1
                        elapsed_time = int(time.time() - start_time)
                        
                        pending_indicator_present = self.check_element_present("pending_indicator")
                        
                        if pending_indicator_present:
                            if not pending_indicator_was_present:
                                print(f"  ✓ Message is pending delivery (check {check_count})")
                                pending_indicator_was_present = True
                            
                            if check_count % 10 == 0:
                                print(f"  ⏳ Still pending... {elapsed_time}s elapsed")
                        else:
                            if pending_indicator_was_present:
                                print(f"  ✓ Message delivered after {elapsed_time}s!")
                                print("✓ Error message sent successfully")
                                return True
                            else:
                                print(f"  ✓ Message delivered instantly after {elapsed_time}s")
                                print("✓ Error message sent successfully")
                                return True
                        
                        time.sleep(1)
                    
                    print(f"✗ Message delivery timeout after 300 seconds")
                    return False
                    
                except Exception as e:
                    print(f"❌ Error in delivery monitoring: {e}")
                    return False
                
            except Exception as e:
                print(f"{self.RED}❌ Unexpected error in attempt {attempt}: {e}{self.ENDC}")
                continue
            
            finally:
                if self.driver:
                    self.driver.quit()
                    self.driver = None
        
        print(f"\n{self.RED}❌ FAILED TO SEND WHATSAPP NOTIFICATION AFTER {max_attempts} ATTEMPTS{self.ENDC}")
        return False

    def check_github_bot_requirements(self, bot_folder_name):
        """Check if a GitHub bot folder has all required files (venv.sh, sheets format folder, README.md)"""
        try:
            # Check if bot folder exists on GitHub
            api_url = f"https://api.github.com/repos/Thaniyanki/raspberry-pi-bots/contents/{bot_folder_name}"
            response = requests.get(api_url, timeout=30)
            
            if response.status_code != 200:
                return False
            
            contents = response.json()
            
            # Check for required files/folders
            has_venv_sh = any(content['name'] == 'venv.sh' and content['type'] == 'file' for content in contents)
            has_sheets_format = any(content['name'] == 'sheets format' and content['type'] == 'dir' for content in contents)
            has_readme = any(content['name'] == 'README.md' and content['type'] == 'file' for content in contents)
            
            return has_venv_sh and has_sheets_format and has_readme
            
        except Exception as e:
            print(f"  Error checking requirements for {bot_folder_name}: {e}")
            return False

    def get_completed_github_bots(self):
        """Get list of completed bots from GitHub that have all required files"""
        print("Fetching completed bots from GitHub repository...")
        
        try:
            # Get the main repository structure
            api_url = "https://api.github.com/repos/Thaniyanki/raspberry-pi-bots/contents/"
            response = requests.get(api_url, timeout=30)
            
            if response.status_code != 200:
                print(f"Error accessing GitHub repository: {response.status_code}")
                return []
            
            contents = response.json()
            completed_bots = []
            
            for item in contents:
                if item['type'] == 'dir':
                    folder_name = item['name']
                    # Skip non-bot folders
                    if folder_name in ['all-in-one-venv', '.github']:
                        continue
                    
                    # Check if this bot has all required files
                    if self.check_github_bot_requirements(folder_name):
                        completed_bots.append(folder_name)
                        print(f"  ✓ Completed bot: {folder_name}")
                    else:
                        print(f"  ⚠ Incomplete bot (missing files): {folder_name}")
            
            print(f"{self.GREEN}✓ Found {len(completed_bots)} completed bots on GitHub{self.ENDC}")
            return completed_bots
            
        except Exception as e:
            print(f"{self.RED}❌ Error fetching GitHub repository: {e}{self.ENDC}")
            return []

    def convert_github_to_local_name(self, github_name):
        """Convert GitHub bot name to local bot name format"""
        # GitHub: whatsapp-messenger -> Local: whatsapp messenger
        return github_name.replace('-', ' ')

    def install_new_bot(self, github_bot_name):
        """Install a new bot using its venv.sh script"""
        print(f"\n{self.BOLD}Installing new bot: {github_bot_name}{self.ENDC}")
        
        try:
            # Construct the venv.sh URL
            venv_sh_url = f"https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main/{github_bot_name}/venv.sh"
            
            print(f"Running installation command...")
            print(f"URL: {venv_sh_url}")
            
            # Download and execute the script in two separate steps
            # This is more compatible than bash <(curl) syntax
            temp_script = Path("/tmp/install_bot.sh")
            
            # Download the script first
            download_cmd = f'curl -sL {venv_sh_url} -o {temp_script}'
            print(f"Downloading script: {download_cmd}")
            
            download_process = subprocess.run(
                download_cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            if download_process.returncode != 0:
                print(f"{self.RED}❌ Failed to download script: {download_process.stderr}{self.ENDC}")
                return False
            
            # Make the script executable
            chmod_process = subprocess.run(
                f'chmod +x {temp_script}',
                shell=True,
                capture_output=True,
                text=True
            )
            
            if chmod_process.returncode != 0:
                print(f"{self.RED}❌ Failed to make script executable: {chmod_process.stderr}{self.ENDC}")
                return False
            
            # Execute the script with live output
            print(f"Executing installation script...")
            execute_cmd = f'bash {temp_script}'
            
            # Use subprocess with live output
            process = subprocess.Popen(
                execute_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Print live output
            for line in process.stdout:
                print(line, end='')
            
            # Wait for process to complete
            process.wait()
            
            # Clean up temporary script
            try:
                temp_script.unlink()
            except:
                pass
            
            if process.returncode == 0:
                print(f"{self.GREEN}✓ Successfully installed {github_bot_name}{self.ENDC}")
                return True
            else:
                print(f"{self.RED}❌ Failed to install {github_bot_name} with return code: {process.returncode}{self.ENDC}")
                return False
                
        except Exception as e:
            print(f"{self.RED}❌ Error installing {github_bot_name}: {e}{self.ENDC}")
            return False

    def run_step8_whatsapp_notification(self, new_bots):
        """Send WhatsApp notification for new bots detected"""
        print(f"\n{self.BOLD}Sending WhatsApp notification for new bots...{self.ENDC}")
        
        # Fetch all WhatsApp XPaths from database first
        if not self.fetch_all_whatsapp_xpaths():
            return False
        
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            print(f"\n{self.BOLD}=== ATTEMPT {attempt} OF {max_attempts} ==={self.ENDC}")
            
            try:
                # Step 8a: Close and reopen browser
                print(f"\n{self.BLUE}Step 8a: Browser Management{self.ENDC}")
                self.close_chrome_browser()
                time.sleep(3)
                if not self.setup_selenium_driver():
                    print("❌ Browser setup failed, restarting...")
                    continue
                
                # Step 8b: Check internet connection
                print(f"\n{self.BLUE}Step 8b: Internet Connection Check{self.ENDC}")
                if not self.check_internet_connection():
                    if not self.wait_for_internet_connection():
                        print("❌ No internet connection, restarting...")
                        continue
                
                # Step 8c: Open WhatsApp Web
                print(f"\n{self.BLUE}Step 8c: Opening WhatsApp Web{self.ENDC}")
                try:
                    self.driver.get("https://web.whatsapp.com/")
                    print("✓ WhatsApp Web opened")
                except Exception as e:
                    print(f"❌ Error opening WhatsApp Web: {e}")
                    continue
                
                # Step 8d: Wait for search field (Xpath001)
                print(f"\n{self.BLUE}Step 8d: Waiting for Search Field{self.ENDC}")
                search_field = self.wait_for_element("search_field", timeout=120)
                if not search_field:
                    print("❌ Search field not found within 120 seconds")
                    
                    # Step 8f: Check for loading indicator (Xpath011)
                    print(f"{self.BLUE}Step 8f: Checking Loading Indicator{self.ENDC}")
                    loading_indicator = self.check_element_present("pending_indicator")  # Using pending_indicator as Xpath011 placeholder
                    if loading_indicator:
                        print("✓ Loading indicator found, retrying...")
                        continue
                    else:
                        print("❌ No loading indicator, restarting browser...")
                        continue
                
                print("✓ Entered Mobile number search field")
                
                # Step 8e: Check report number file
                print(f"\n{self.BLUE}Step 8e: Checking Report Number File{self.ENDC}")
                report_number = self.get_report_number()
                if not report_number:
                    print("❌ Report number file not available")
                    return False
                print("✓ Report number file available")
                
                # Step 8g: Validate phone number
                print(f"\n{self.BLUE}Step 8g: Validating Phone Number{self.ENDC}")
                if not self.is_valid_phone_number(report_number):
                    print("❌ Phone number is not available or invalid")
                    return False
                print("✓ Phone number is available")
                
                # Step 8h: Enter phone number
                print(f"\n{self.BLUE}Step 8h: Entering Phone Number{self.ENDC}")
                try:
                    search_field.clear()
                    search_field.send_keys(report_number)
                    print(f"✓ Phone number entered: {report_number}")
                    time.sleep(1)
                    search_field.send_keys(Keys.ENTER)
                    print("✓ Enter key pressed")
                    time.sleep(10)  # Wait for stability
                except Exception as e:
                    print(f"❌ Error entering phone number: {e}")
                    continue
                
                # Step 8i: Check contact existence
                print(f"\n{self.BLUE}Step 8i: Checking Contact Existence{self.ENDC}")
                if self.check_element_present("contact_not_found"):
                    print("❌ Contact not found")
                    if self.check_internet_connection():
                        print("✗ Invalid Mobile Number")
                        return False
                    else:
                        print("No internet connection, restarting...")
                        continue
                else:
                    print("✓ Contact found")
                
                # Step 8j: Select contact
                print(f"\n{self.BLUE}Step 8j: Selecting Contact{self.ENDC}")
                try:
                    body = self.driver.find_element(By.TAG_NAME, 'body')
                    body.send_keys(Keys.ARROW_DOWN)
                    print("✓ Down arrow pressed")
                    time.sleep(2)  # Wait for stability
                    body.send_keys(Keys.ENTER)
                    print("✓ Enter pressed - Entered Message Field")
                except Exception as e:
                    print(f"❌ Error selecting contact: {e}")
                    continue
                
                # Step 8k: Type new bot notification message
                print(f"\n{self.BLUE}Step 8k: Composing New Bot Notification{self.ENDC}")
                if not new_bots:
                    print("No new bots to report")
                    return False
                
                # Create message for new bots
                message_lines = []
                for new_bot in new_bots:
                    local_name = self.convert_github_to_local_name(new_bot)
                    message_lines.append(f"New bot ({local_name}) is deducted!")
                
                message_lines.append("")
                message_lines.append("Need to create Google sheet configuration")
                message_lines.append("---------------------------------------------")
                message_lines.append("Step to create sheet")
                message_lines.append("-Sign in your Google account")
                message_lines.append("-Create new spread sheet named as the bot name")
                message_lines.append("-Share with your google service account")
                message_lines.append("---------------------------------------------")
                
                message = "\n".join(message_lines)
                
                try:
                    time.sleep(2)
                    message_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']"))
                    )
                    message_input.click()
                    time.sleep(1)
                    
                    # Type message with Shift+Enter for new lines
                    lines = message.split('\n')
                    for i, line in enumerate(lines):
                        message_input.send_keys(line)
                        if i < len(lines) - 1:
                            message_input.send_keys(Keys.SHIFT + Keys.ENTER)
                            time.sleep(0.5)
                    
                    print("✓ New bot notification message composed")
                except Exception as e:
                    print(f"❌ Error composing message: {e}")
                    continue
                
                # Step 8l: Send message
                print(f"\n{self.BLUE}Step 8l: Sending Message{self.ENDC}")
                try:
                    time.sleep(2)  # Wait for stability
                    message_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']"))
                    )
                    message_input.send_keys(Keys.ENTER)
                    print("✓ Message sent")
                except Exception as e:
                    print(f"❌ Error sending message: {e}")
                    continue
                
                # Step 8m: Wait for message delivery
                print(f"\n{self.BLUE}Step 8m: Waiting for Message Delivery{self.ENDC}")
                try:
                    time.sleep(2)  # Wait for stability
                    print("Monitoring message delivery...")
                    
                    start_time = time.time()
                    check_count = 0
                    pending_indicator_was_present = False
                    
                    while time.time() - start_time < 300:  # 5 minute timeout
                        check_count += 1
                        elapsed_time = int(time.time() - start_time)
                        
                        pending_indicator_present = self.check_element_present("pending_indicator")
                        
                        if pending_indicator_present:
                            if not pending_indicator_was_present:
                                print(f"  ✓ Message is pending delivery (check {check_count})")
                                pending_indicator_was_present = True
                            
                            if check_count % 10 == 0:
                                print(f"  ⏳ Still pending... {elapsed_time}s elapsed")
                        else:
                            if pending_indicator_was_present:
                                print(f"  ✓ Message delivered after {elapsed_time}s!")
                                print("✓ New bot notification sent successfully")
                                return True
                            else:
                                print(f"  ✓ Message delivered instantly after {elapsed_time}s")
                                print("✓ New bot notification sent successfully")
                                return True
                        
                        time.sleep(1)
                    
                    print(f"✗ Message delivery timeout after 300 seconds")
                    return False
                    
                except Exception as e:
                    print(f"❌ Error in delivery monitoring: {e}")
                    return False
                
            except Exception as e:
                print(f"{self.RED}❌ Unexpected error in attempt {attempt}: {e}{self.ENDC}")
                continue
            
            finally:
                if self.driver:
                    self.driver.quit()
                    self.driver = None
        
        print(f"\n{self.RED}❌ FAILED TO SEND WHATSAPP NOTIFICATION AFTER {max_attempts} ATTEMPTS{self.ENDC}")
        return False

    def run_step8(self):
        """Step 8: Detect New Bots from GitHub"""
        print("\n" + "=" * 50)
        print("STEP 8: DETECTING NEW BOTS FROM GITHUB")
        print("=" * 50)
        
        try:
            # Get completed bots from GitHub
            github_bots = self.get_completed_github_bots()
            if not github_bots:
                print(f"{self.YELLOW}⚠ No completed bots found on GitHub{self.ENDC}")
                return True, []
            
            # Get local bot folders
            local_bot_folders = self.get_bot_folders()
            local_bot_names = [folder.name for folder in local_bot_folders]
            
            print(f"\n{self.BOLD}Comparing GitHub bots with local bots...{self.ENDC}")
            print(f"GitHub bots: {len(github_bots)}")
            print(f"Local bots: {len(local_bot_names)}")
            
            # Find new bots that are on GitHub but not locally
            new_bots = []
            for github_bot in github_bots:
                local_bot_name = self.convert_github_to_local_name(github_bot)
                if local_bot_name not in local_bot_names:
                    new_bots.append(github_bot)
                    print(f"{self.YELLOW}  ⚠ New bot detected: {github_bot} -> {local_bot_name}{self.ENDC}")
                else:
                    print(f"{self.GREEN}  ✓ Bot already installed: {github_bot} -> {local_bot_name}{self.ENDC}")
            
            if new_bots:
                print(f"\n{self.BOLD}NEW BOTS FOUND:{self.ENDC}")
                for new_bot in new_bots:
                    local_name = self.convert_github_to_local_name(new_bot)
                    print(f"{self.RED}  ✗ New bot needs installation: {local_name}{self.ENDC}")
                    print(f"     GitHub name: {new_bot}")
                    print(f"     Local name: {local_name}")
                
                print(f"\n{self.YELLOW}⚠ ACTION REQUIRED:{self.ENDC}")
                print(f"{self.YELLOW}   New bots detected from GitHub that need to be installed:{self.ENDC}")
                for new_bot in new_bots:
                    local_name = self.convert_github_to_local_name(new_bot)
                    print(f"{self.YELLOW}   - {local_name}{self.ENDC}")
                
                # Install new bots
                print(f"\n{self.BOLD}Starting installation of new bots...{self.ENDC}")
                installation_success = True
                for new_bot in new_bots:
                    if not self.install_new_bot(new_bot):
                        installation_success = False
                        print(f"{self.RED}❌ Failed to install {new_bot}{self.ENDC}")
                    else:
                        print(f"{self.GREEN}✓ Successfully installed {new_bot}{self.ENDC}")
                
                if not installation_success:
                    print(f"{self.RED}❌ Some bots failed to install{self.ENDC}")
                    return True, new_bots
                
                # Send WhatsApp notification for new bots
                print(f"\n{self.BOLD}Sending WhatsApp notification for new bots...{self.ENDC}")
                if not self.run_step8_whatsapp_notification(new_bots):
                    print(f"{self.RED}❌ Failed to send WhatsApp notification{self.ENDC}")
                    return True, new_bots
                
                print(f"{self.GREEN}✓ New bots installed and notification sent successfully{self.ENDC}")
                return True, new_bots
            else:
                print(f"\n{self.GREEN}✓ All GitHub bots are already installed locally{self.ENDC}")
                return True, []
            
        except Exception as e:
            print(f"{self.RED}❌ Error in Step 8: {e}{self.ENDC}")
            return True, []

    def get_valid_bot_names(self):
        """Get valid bot names that exist in both local folders and Google Sheets (case-sensitive)"""
        local_bot_folders = self.get_bot_folders()
        local_bot_names = [folder.name for folder in local_bot_folders]
        
        if not hasattr(self, 'available_sheets') or not self.available_sheets:
            return []
        
        sheet_names = [sheet['name'] for sheet in self.available_sheets]
        
        # Filter bots that exist in both local folders and Google Sheets (case-sensitive)
        valid_bots = []
        for bot_name in local_bot_names:
            if bot_name in sheet_names and bot_name != "scheduler":
                valid_bots.append(bot_name)
        
        return valid_bots

    def get_scheduler_data(self, gc):
        """Get scheduler data from Google Sheets"""
        try:
            # Check if scheduler sheet exists
            sheet_names = [sheet['name'] for sheet in self.available_sheets]
            if "scheduler" not in sheet_names:
                return None
            
            # Open scheduler sheet
            sheet = gc.open("scheduler")
            worksheet = sheet.sheet1
            
            # Get all data including columns Q, R, S (status, last_run, remark)
            data = worksheet.get_all_records()
            return data
            
        except Exception as e:
            print(f"Error accessing scheduler sheet: {e}")
            return None

    def format_schedule_display(self, schedule_data, valid_bots):
        """Format the schedule display for terminal output including status, last_run, and remark"""
        # Get current day
        current_day = datetime.now().strftime("%A").lower()
        
        # Map day names to column names
        day_columns = {
            'sunday': ['sun_start at', 'sun_stop at'],
            'monday': ['mon_start at', 'mon_stop at'],
            'tuesday': ['tue_start at', 'tue_stop at'],
            'wednesday': ['wed_start at', 'wed_stop at'],
            'thursday': ['thu_start at', 'thu_stop at'],
            'friday': ['fri_start at ', 'fri_stop at'],
            'saturday': ['sat_start at', 'sat_stop at']
        }
        
        if current_day not in day_columns:
            return None
        
        start_col, stop_col = day_columns[current_day]
        current_date = datetime.now().strftime("%d-%m-%Y")
        
        # Filter and format data including status, last_run, remark
        display_data = []
        for row in schedule_data:
            bot_name = row.get('bots name', '').strip()
            
            # Only include valid bots that exist in both local and sheets
            if bot_name in valid_bots:
                start_time = row.get(start_col, '').strip()
                stop_time = row.get(stop_col, '').strip()
                switch = row.get('switch', '').strip().lower()
                status = row.get('status', '').strip()
                last_run = row.get('last_run', '').strip()
                remark = row.get('remark', '').strip()
                
                # Only include if we have at least one time value
                if start_time or stop_time:
                    display_data.append({
                        'bot_name': bot_name,
                        'start_at': start_time if start_time else 'N/A',
                        'stop_at': stop_time if stop_time else 'N/A',
                        'switch': switch,
                        'status': status if status else 'N/A',
                        'last_run': last_run if last_run else 'N/A',
                        'remark': remark if remark else 'N/A'
                    })
    
        return current_day.capitalize(), current_date, display_data

    def display_schedule_table(self, day, date, schedule_data, countdown=None, check_count=None):
        """Display the schedule in a formatted table with countdown timer including status, last_run, and remark"""
        # Calculate column widths based on content
        max_name_len = max(len(item['bot_name']) for item in schedule_data)
        max_name_len = max(max_name_len, len("bots name"))
        
        max_start_len = max(len(item['start_at']) for item in schedule_data)
        max_start_len = max(max_start_len, len("start_at"))
        
        max_stop_len = max(len(item['stop_at']) for item in schedule_data)
        max_stop_len = max(max_stop_len, len("stop_at"))
        
        max_switch_len = max(len(item['switch']) for item in schedule_data)
        max_switch_len = max(max_switch_len, len("switch"))
        
        max_status_len = max(len(item['status']) for item in schedule_data)
        max_status_len = max(max_status_len, len("status"))
        
        max_last_run_len = max(len(item['last_run']) for item in schedule_data)
        max_last_run_len = max(max_last_run_len, len("last_run"))
        
        max_remark_len = max(len(item['remark']) for item in schedule_data)
        max_remark_len = max(max_remark_len, len("remark"))
        
        # Add some padding
        max_name_len += 2
        max_start_len += 2
        max_stop_len += 2
        max_switch_len += 2
        max_status_len += 2
        max_last_run_len += 2
        max_remark_len += 2
        
        # Build header string to calculate total width
        header = (f"{'bots name':<{max_name_len}} "
                 f"{'start_at':<{max_start_len}} "
                 f"{'stop_at':<{max_stop_len}} "
                 f"{'switch':<{max_switch_len}} "
                 f"{'status':<{max_status_len}} "
                 f"{'last_run':<{max_last_run_len}} "
                 f"{'remark':<{max_remark_len}}")
        
        # Calculate total table width
        table_width = len(header)
        
        # Print both dash lines with the same length
        print("-" * table_width)
        print(header)
        print("-" * table_width)
        
        # Data rows
        for item in schedule_data:
            row = (f"{item['bot_name']:<{max_name_len}} "
                   f"{item['start_at']:<{max_start_len}} "
                   f"{item['stop_at']:<{max_stop_len}} "
                   f"{item['switch']:<{max_switch_len}} "
                   f"{item['status']:<{max_status_len}} "
                   f"{item['last_run']:<{max_last_run_len}} "
                   f"{item['remark']:<{max_remark_len}}")
            print(row)
        
        # Show only the bottom status line with countdown
        if countdown is not None and check_count is not None:
            print(f"{day} {date} | Check #{check_count} | Next sync: {countdown:02d}s")

    def get_bot_main_script(self, bot_folder):
        """Get the main Python script for a bot folder"""
        bot_path = self.bots_base_path / bot_folder
        
        # Look for main Python files
        python_files = list(bot_path.glob("*.py"))
        
        # Prioritize files that look like main scripts
        main_scripts = []
        for py_file in python_files:
            if py_file.name != "scheduler.py" and not py_file.name.startswith('test'):
                main_scripts.append(py_file)
        
        if main_scripts:
            # Return the first main script found
            return main_scripts[0]
        
        return None

    def is_bot_running(self, bot_name):
        """Check if a bot is currently running - FIXED to prevent false positives"""
        if bot_name not in self.bot_processes:
            return False
        
        process = self.bot_processes[bot_name]
        if process is None:
            return False
        
        # Check if process is actually running (not just defined)
        try:
            return process.poll() is None
        except:
            # If there's any error checking process status, assume it's not running
            self.bot_processes[bot_name] = None
            return False

    def start_bot(self, bot_name):
        """Start a bot process"""
        if self.is_bot_running(bot_name):
            print(f"  ⚠ {bot_name} is already running")
            return True
        
        try:
            bot_folder = self.bots_base_path / bot_name
            main_script = self.get_bot_main_script(bot_name)
            
            if not main_script:
                print(f"  ✗ No main script found for {bot_name}")
                return False
            
            # Get venv path
            venv_path = self.get_venv_path(bot_folder)
            if not venv_path:
                print(f"  ✗ No venv found for {bot_name}")
                return False
            
            # Activate venv and run the bot
            python_executable = venv_path / "bin" / "python3"
            
            if not python_executable.exists():
                print(f"  ✗ Python executable not found for {bot_name}")
                return False
            
            # Start the bot process
            process = subprocess.Popen(
                [str(python_executable), str(main_script)],
                cwd=str(bot_folder),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.bot_processes[bot_name] = process
            print(f"  ✓ Started {bot_name}")
            return True
            
        except Exception as e:
            print(f"  ✗ Error starting {bot_name}: {e}")
            return False

    def stop_bot(self, bot_name):
        """Stop a bot process"""
        if not self.is_bot_running(bot_name):
            print(f"  ⚠ {bot_name} is not running, nothing to stop")
            return True
        
        try:
            process = self.bot_processes[bot_name]
            
            # Try to terminate gracefully
            process.terminate()
            
            # Wait for process to end
            try:
                process.wait(timeout=10)
                print(f"  ✓ Stopped {bot_name} gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if not responding
                process.kill()
                process.wait()
                print(f"  ✓ Forcefully stopped {bot_name}")
            
            self.bot_processes[bot_name] = None
            return True
            
        except Exception as e:
            print(f"  ✗ Error stopping {bot_name}: {e}")
            return False

    def normalize_time_format(self, time_str):
        """Normalize time format to ensure consistent comparison - FIXED VERSION"""
        if not time_str or time_str == 'N/A':
            return None
        
        # Remove any spaces and convert to lowercase
        time_str = time_str.strip().lower()
        
        # Handle different time formats - FIXED
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) >= 2:
                hours = parts[0].zfill(2)  # Ensure 2-digit hours
                minutes = parts[1][:2].zfill(2)  # Take first 2 chars for minutes
                
                # Return in HH:MM format for consistent comparison
                return f"{hours}:{minutes}"
        
        return None

    def check_time_in_range(self, start_time, stop_time):
        """Check if current time is between start_time and stop_time - FIXED VERSION"""
        current_time = datetime.now().strftime("%H:%M")
        
        # Normalize time formats
        start_time_norm = self.normalize_time_format(start_time)
        stop_time_norm = self.normalize_time_format(stop_time)
        
        if not start_time_norm or not stop_time_norm:
            print(f"  ⚠ Invalid time format: start='{start_time}', stop='{stop_time}'")
            return False
        
        print(f"  Time Check: Current={current_time}, Start={start_time_norm}, Stop={stop_time_norm}")
        
        try:
            # Convert to time objects for proper comparison
            current_t = datetime.strptime(current_time, "%H:%M").time()
            start_t = datetime.strptime(start_time_norm, "%H:%M").time()
            stop_t = datetime.strptime(stop_time_norm, "%H:%M").time()
            
            # Handle overnight schedules (stop time < start time)
            if stop_t < start_t:
                # Overnight: current time should be >= start_time OR <= stop_time
                result = current_t >= start_t or current_t <= stop_t
                print(f"  Overnight schedule: {result}")
                return result
            else:
                # Normal: current time should be between start_time and stop_time
                result = start_t <= current_t <= stop_t
                print(f"  Normal schedule: {result}")
                return result
                
        except ValueError as e:
            print(f"  ⚠ Time parsing error: {e}")
            return False

    def check_remark_and_last_run(self, remark, last_run):
        """Check remark and last_run conditions for step 9b - FIXED VERSION"""
        current_date = datetime.now().strftime("%d-%m-%Y")
        
        print(f"  Remark Check: remark='{remark}', last_run='{last_run}', current_date='{current_date}'")
        
        # Scenario 1: Last run is from past date (not today) - continue
        if last_run and not last_run.startswith(current_date):
            print(f"  ✓ Last run is from past date, continue")
            return True
        
        # Scenario 2: Last run is today but remark doesn't contain "successfully done" - continue  
        if last_run and last_run.startswith(current_date):
            if not remark or "sucessfully done" not in remark.lower():
                print(f"  ✓ Last run is today but not successfully done, continue")
                return True
            else:
                print(f"  ✗ Already executed successfully today, nothing to do")
                return False
        
        # Scenario 3: No last run data - continue
        if not last_run:
            print(f"  ✓ No last run data, continue")
            return True
        
        # Default: don't continue
        print(f"  ✗ Conditions not met for execution")
        return False

    def sync_bots_with_schedule(self, schedule_data, valid_bots):
        """Sync bot processes with current schedule - FIXED to use same logic as step 9a-9d"""
        current_day = datetime.now().strftime("%A").lower()
        
        # Map day names to column names
        day_columns = {
            'sunday': ['sun_start at', 'sun_stop at'],
            'monday': ['mon_start at', 'mon_stop at'],
            'tuesday': ['tue_start at', 'tue_stop at'],
            'wednesday': ['wed_start at', 'wed_stop at'],
            'thursday': ['thu_start at', 'thu_stop at'],
            'friday': ['fri_start at ', 'fri_stop at'],
            'saturday': ['sat_start at', 'sat_stop at']
        }
        
        if current_day not in day_columns:
            return
        
        start_col, stop_col = day_columns[current_day]
        
        # Process each valid bot
        for bot_name in valid_bots:
            # Find bot schedule
            bot_schedule = None
            for row in schedule_data:
                if row.get('bots name', '').strip() == bot_name:
                    bot_schedule = {
                        'start_at': row.get(start_col, '').strip(),
                        'stop_at': row.get(stop_col, '').strip(),
                        'switch': row.get('switch', '').strip().lower(),
                        'remark': row.get('remark', '').strip(),
                        'last_run': row.get('last_run', '').strip()
                    }
                    break
            
            if not bot_schedule:
                continue
            
            # Use the same logic as step 9a-9d to determine if bot should run
            should_run = False
            
            # Step 9a: Check if current time is between start_at and stop_at
            if self.check_time_in_range(bot_schedule['start_at'], bot_schedule['stop_at']):
                # Step 9a: Check switch column
                if bot_schedule['switch'] == 'on':
                    # Step 9b: Check remark and last_run - FIXED LOGIC
                    should_continue = self.check_remark_and_last_run(bot_schedule['remark'], bot_schedule['last_run'])
                    should_run = should_continue
            
            is_running = self.is_bot_running(bot_name)
            
            # Only take action if there's a mismatch between desired state and actual state
            if should_run and not is_running:
                print(f"  Starting {bot_name} (scheduled to run)")
                self.start_bot(bot_name)
            elif not should_run and is_running:
                print(f"  Stopping {bot_name} (not in scheduled time or already executed)")
                self.stop_bot(bot_name)
            # If state matches desired state, no action needed

    def update_local_status(self, bot_name, status):
        """Update bot status in local schedule data"""
        if bot_name in self.local_schedule_data:
            self.local_schedule_data[bot_name]['status'] = status
            print(f"  ✓ Updated local status for {bot_name}: {status}")

    def update_local_last_run_and_remark(self, bot_name, last_run, remark):
        """Update bot last_run and remark in local schedule data"""
        if bot_name in self.local_schedule_data:
            self.local_schedule_data[bot_name]['last_run'] = last_run
            self.local_schedule_data[bot_name]['remark'] = remark
            print(f"  ✓ Updated local last_run for {bot_name}: {last_run}")
            print(f"  ✓ Updated local remark for {bot_name}: {remark}")

    def update_google_sheet_status(self, gc, bot_name, status, max_retries=3):
        """Update bot status in Google Sheet with retry logic"""
        for attempt in range(1, max_retries + 1):
            try:
                sheet = gc.open("scheduler")
                worksheet = sheet.sheet1
                
                # Find the row for this bot
                all_data = worksheet.get_all_records()
                for i, row in enumerate(all_data, start=2):  # start=2 because row 1 is header
                    if row.get('bots name', '').strip() == bot_name:
                        # Update status column (column Q, which is index 17)
                        worksheet.update_cell(i, 17, status)
                        print(f"  ✓ Updated Google Sheet status for {bot_name}: {status}")
                        return True
                
                print(f"  ✗ Bot {bot_name} not found in scheduler sheet")
                return False
                
            except Exception as e:
                print(f"  ⚠ Attempt {attempt}/{max_retries} failed to update Google Sheet for {bot_name}: {e}")
                if attempt < max_retries:
                    time.sleep(2)  # Wait before retry
                else:
                    print(f"  ✗ Failed to update Google Sheet for {bot_name} after {max_retries} attempts")
                    return False

    def prepare_run_command(self, bot_name):
        """Prepare the run command for a bot based on its name"""
        # Convert bot name to GitHub format for the folder
        github_bot_name = bot_name.replace(' ', '-')
        
        # For the filename, we need to URL encode the spaces
        github_file_name = bot_name.replace(' ', '%20') + '.py'
        
        # Get the username programmatically
        username = self.username
        
        # Construct the run command with proper quoting for paths with spaces
        run_command = f'bash -c "cd \\"/home/{username}/bots/{bot_name}\\" && source venv/bin/activate && curl -sL https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main/{github_bot_name}/{github_file_name} | python3"'
        
        print(f"  Run command prepared for {bot_name}:")
        print(f"    {run_command}")
        
        return run_command

    def run_bot_with_command(self, bot_name, run_command, start_time, stop_time, gc):
        """Run the bot using the prepared command and monitor its execution with LIVE output"""
        print(f"  Starting bot execution for {bot_name}...")
        
        try:
            # Start the bot process with proper shell execution and live output
            process = subprocess.Popen(
                run_command,
                shell=True,
                executable='/bin/bash',
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Store the process
            self.bot_processes[bot_name] = process
            
            # Monitor the process
            start_timestamp = datetime.now()
            print(f"  Bot {bot_name} started at: {start_timestamp.strftime('%d-%m-%Y %H:%M:%S')}")
            print(f"  {'='*60}")
            print(f"  LIVE OUTPUT FOR {bot_name}:")
            print(f"  {'='*60}")
            
            # Parse times with error handling
            try:
                # Normalize time formats first
                start_time_norm = self.normalize_time_format(start_time)
                stop_time_norm = self.normalize_time_format(stop_time)
                
                if not start_time_norm or not stop_time_norm:
                    print(f"  ⚠ Invalid time format: start='{start_time}', stop='{stop_time}'")
                    # Use default 1-hour window if times are invalid
                    stop_datetime = start_timestamp.replace(hour=start_timestamp.hour + 1)
                else:
                    current_date = datetime.now().strftime("%d-%m-%Y")
                    try:
                        start_datetime = datetime.strptime(f"{current_date} {start_time_norm}", "%d-%m-%Y %H:%M")
                        stop_datetime = datetime.strptime(f"{current_date} {stop_time_norm}", "%d-%m-%Y %H:%M")
                        
                        # Handle overnight schedules
                        if stop_datetime < start_datetime:
                            stop_datetime = stop_datetime.replace(day=stop_datetime.day + 1)
                    except ValueError as e:
                        print(f"  ⚠ Time parsing error: {e}, using default 1-hour window")
                        stop_datetime = start_timestamp.replace(hour=start_timestamp.hour + 1)
                        
            except Exception as e:
                print(f"  ⚠ Time parsing error: {e}, using default 1-hour window")
                stop_datetime = start_timestamp.replace(hour=start_timestamp.hour + 1)
            
            print(f"  Bot {bot_name} will run until: {stop_datetime.strftime('%d-%m-%Y %H:%M:%S')}")
            print(f"  {'='*60}")
            
            # Read output line by line in real-time
            output_lines = []
            process_output_complete = False
            
            def read_output():
                """Read output from process in real-time"""
                nonlocal process_output_complete
                try:
                    for line in process.stdout:
                        line = line.strip()
                        if line:
                            output_lines.append(line)
                            print(f"  [{bot_name}] {line}")
                    process_output_complete = True
                except Exception as e:
                    print(f"  ⚠ Error reading output: {e}")
                    process_output_complete = True
            
            # Start output reading thread
            output_thread = threading.Thread(target=read_output)
            output_thread.daemon = True
            output_thread.start()
            
            # Monitor process and check for timeout with live output
            while process.poll() is None:
                current_datetime = datetime.now()
                
                # Check if current time exceeds stop_time
                if current_datetime > stop_datetime:
                    print(f"  ⚠ Bot {bot_name} exceeded allocated time, stopping forcefully...")
                    
                    # Forcefully stop the bot
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    
                    # Update status and remark for forceful stop
                    self.update_local_status(bot_name, "idle")
                    self.update_google_sheet_status(gc, bot_name, "idle")
                    
                    # Update last_run and remark in local and Google Sheet
                    last_run_time = current_datetime.strftime("%d-%m-%Y %H:%M:%S")
                    remark_text = "forcefully stopped"
                    
                    self.update_local_last_run_and_remark(bot_name, last_run_time, remark_text)
                    self.update_google_sheet_last_run_and_remark(gc, bot_name, last_run_time, remark_text)
                    
                    print(f"  ✓ Bot {bot_name} forcefully stopped and status updated")
                    print(f"  {'='*60}")
                    return False
                
                # Wait a bit before checking again
                time.sleep(2)
            
            # Wait for output thread to complete
            output_thread.join(timeout=5)
            
            # Process completed normally
            exit_code = process.poll()
            end_timestamp = datetime.now()
            
            # Ensure all output is read
            if not process_output_complete:
                try:
                    remaining_output, _ = process.communicate(timeout=5)
                    if remaining_output:
                        lines = remaining_output.strip().split('\n')
                        for line in lines:
                            if line.strip():
                                output_lines.append(line.strip())
                                print(f"  [{bot_name}] {line.strip()}")
                except:
                    pass
            
            print(f"  {'='*60}")
            print(f"  Bot {bot_name} execution completed")
            print(f"  Exit code: {exit_code}")
            print(f"  Start time: {start_timestamp.strftime('%d-%m-%Y %H:%M:%S')}")
            print(f"  End time: {end_timestamp.strftime('%d-%m-%Y %H:%M:%S')}")
            print(f"  Duration: {end_timestamp - start_timestamp}")
            print(f"  {'='*60}")
            
            if exit_code == 0:
                print(f"  ✓ Bot {bot_name} completed successfully")
                
                # Update status, last_run and remark for successful completion
                self.update_local_status(bot_name, "idle")
                self.update_google_sheet_status(gc, bot_name, "idle")
                
                # Update last_run and remark in local and Google Sheet
                last_run_time = end_timestamp.strftime("%d-%m-%Y %H:%M:%S")
                remark_text = "sucessfully done"
                
                self.update_local_last_run_and_remark(bot_name, last_run_time, remark_text)
                self.update_google_sheet_last_run_and_remark(gc, bot_name, last_run_time, remark_text)
                
                print(f"  ✓ Bot {bot_name} status updated to 'idle' with remark 'sucessfully done'")
                return True
            else:
                print(f"  ✗ Bot {bot_name} failed with exit code: {exit_code}")
                
                # Update status and remark for failed execution
                self.update_local_status(bot_name, "idle")
                self.update_google_sheet_status(gc, bot_name, "idle")
                
                # Update last_run and remark in local and Google Sheet
                last_run_time = end_timestamp.strftime("%d-%m-%Y %H:%M:%S")
                remark_text = f"failed with exit code {exit_code}"
                
                self.update_local_last_run_and_remark(bot_name, last_run_time, remark_text)
                self.update_google_sheet_last_run_and_remark(gc, bot_name, last_run_time, remark_text)
                
                return False
                
        except Exception as e:
            print(f"  ❌ Error running bot {bot_name}: {e}")
            
            # Update status for error case
            self.update_local_status(bot_name, "idle")
            self.update_google_sheet_status(gc, bot_name, "idle")
            
            # Update last_run and remark in local and Google Sheet
            last_run_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            remark_text = f"error: {str(e)}"
            
            self.update_local_last_run_and_remark(bot_name, last_run_time, remark_text)
            self.update_google_sheet_last_run_and_remark(gc, bot_name, last_run_time, remark_text)
            
            return False

    def update_google_sheet_last_run_and_remark(self, gc, bot_name, last_run, remark, max_retries=3):
        """Update last_run and remark in Google Sheet"""
        for attempt in range(1, max_retries + 1):
            try:
                sheet = gc.open("scheduler")
                worksheet = sheet.sheet1
                
                # Find the row for this bot
                all_data = worksheet.get_all_records()
                for i, row in enumerate(all_data, start=2):  # start=2 because row 1 is header
                    if row.get('bots name', '').strip() == bot_name:
                        # Update last_run column (column R, which is index 18)
                        worksheet.update_cell(i, 18, last_run)
                        # Update remark column (column S, which is index 19)
                        worksheet.update_cell(i, 19, remark)
                        print(f"  ✓ Updated Google Sheet for {bot_name}: last_run='{last_run}', remark='{remark}'")
                        return True
                
                print(f"  ✗ Bot {bot_name} not found in scheduler sheet")
                return False
                
            except Exception as e:
                print(f"  ⚠ Attempt {attempt}/{max_retries} failed to update Google Sheet for {bot_name}: {e}")
                if attempt < max_retries:
                    time.sleep(2)  # Wait before retry
                else:
                    print(f"  ✗ Failed to update Google Sheet for {bot_name} after {max_retries} attempts")
                    return False

    def execute_steps_9a_to_9d(self, schedule_data, valid_bots, gc, check_count):
        """Execute steps 9a to 9d for bot execution management - FIXED VERSION"""
        current_day = datetime.now().strftime("%A").lower()
        
        # Map day names to column names
        day_columns = {
            'sunday': ['sun_start at', 'sun_stop at'],
            'monday': ['mon_start at', 'mon_stop at'],
            'tuesday': ['tue_start at', 'tue_stop at'],
            'wednesday': ['wed_start at', 'wed_stop at'],
            'thursday': ['thu_start at', 'thu_stop at'],
            'friday': ['fri_start at ', 'fri_stop at'],
            'saturday': ['sat_start at', 'sat_stop at']
        }
        
        if current_day not in day_columns:
            return
        
        start_col, stop_col = day_columns[current_day]
        
        # Step 9a: Check every second for time range and switch
        for row in schedule_data:
            bot_name = row.get('bots name', '').strip()
            
            if bot_name not in valid_bots:
                continue
            
            start_time = row.get(start_col, '').strip()
            stop_time = row.get(stop_col, '').strip()
            switch = row.get('switch', '').strip().lower()
            remark = row.get('remark', '').strip()
            last_run = row.get('last_run', '').strip()
            current_status = row.get('status', '').strip()
            
            # Store in local data for reference
            if bot_name not in self.local_schedule_data:
                self.local_schedule_data[bot_name] = {
                    'start_time': start_time,
                    'stop_time': stop_time,
                    'switch': switch,
                    'remark': remark,
                    'last_run': last_run,
                    'status': current_status
                }
            
            print(f"\n{self.BLUE}Checking {bot_name}:{self.ENDC}")
            print(f"  Start: {start_time}, Stop: {stop_time}, Switch: {switch}")
            print(f"  Remark: {remark}, Last Run: {last_run}, Status: {current_status}")
            
            # Step 9a: Check if current time is between start_at and stop_at
            if self.check_time_in_range(start_time, stop_time):
                print(f"{self.GREEN}  ✓ Step 9a: Time check PASSED for {bot_name}{self.ENDC}")
                
                # Step 9a: Check switch column
                if switch == 'on':
                    print(f"  ✓ Switch is ON for {bot_name}")
                    
                    # Step 9b: Check remark and last_run - FIXED LOGIC
                    print(f"{self.BLUE}  Step 9b: Checking remark and last_run for {bot_name}{self.ENDC}")
                    should_continue = self.check_remark_and_last_run(remark, last_run)
                    
                    if should_continue:
                        print(f"  ✓ Conditions met for {bot_name}, continuing to step 9c")
                        
                        # Step 9c: Pause sync and continue
                        print(f"{self.BLUE}  Step 9c: Pausing sync for {bot_name}{self.ENDC}")
                        current_day_name = datetime.now().strftime("%A")
                        current_date = datetime.now().strftime("%d-%m-%Y")
                        print(f"  {current_day_name} {current_date} | Check #{check_count} | Next sync: 21s")
                        
                        # Step 9d: Mark status as "in progress" and run the bot
                        print(f"{self.BLUE}  Step 9d: Updating status and running {bot_name}{self.ENDC}")
                        
                        # First update local status
                        self.update_local_status(bot_name, "in progress")
                        
                        # Then update Google Sheet with retry
                        if self.update_google_sheet_status(gc, bot_name, "in progress"):
                            print(f"  ✓ Successfully updated both local and Google Sheet status for {bot_name}")
                            
                            # Set other bots to "idle" ONLY if they were "in progress"
                            for other_bot in valid_bots:
                                if other_bot != bot_name and self.local_schedule_data.get(other_bot, {}).get('status') == 'in progress':
                                    self.update_local_status(other_bot, "idle")
                                    self.update_google_sheet_status(gc, other_bot, "idle")
                            
                            print(f"  ✓ Set other 'in progress' bots to 'idle'")
                            
                            # Prepare run command and run the bot
                            run_command = self.prepare_run_command(bot_name)
                            
                            # Run the bot with the prepared command
                            success = self.run_bot_with_command(bot_name, run_command, start_time, stop_time, gc)
                            
                            if success:
                                print(f"  ✓ Bot {bot_name} executed successfully")
                            else:
                                print(f"  ✗ Bot {bot_name} execution failed")
                        else:
                            print(f"  ✗ Failed to update Google Sheet status for {bot_name}")
                    
                    else:
                        print(f"  ⚠ Conditions not met for {bot_name}, nothing to do")
                else:
                    print(f"  ⚠ Switch is OFF for {bot_name}, nothing to do")
            else:
                print(f"{self.YELLOW}  ⚠ Step 9a: Time check FAILED for {bot_name}{self.ENDC}")
                # Bot not in scheduled time range - ONLY stop if it's actually running
                if self.is_bot_running(bot_name):
                    print(f"  ⚠ {bot_name} is running but not in scheduled time, stopping...")
                    if self.stop_bot(bot_name):
                        print(f"  ✓ Successfully stopped {bot_name}")
                        self.update_local_status(bot_name, "idle")
                        self.update_google_sheet_status(gc, bot_name, "idle")
                    else:
                        print(f"  ✗ Failed to stop {bot_name}")
                else:
                    # Bot is not running and not in scheduled time - this is normal, no action needed
                    print(f"  ✓ {bot_name} is idle (not running) and not in scheduled time - no action needed")

    def run_step9(self):
        """Step 9: Monitor Scheduler Sheet and Control Bots with Steps 9a-9d"""
        print("\n" + "=" * 50)
        print("STEP 9: SCHEDULER MONITORING & BOT CONTROL")
        print("=" * 50)
        
        try:
            # Get spreadsheet key
            bot_folders = self.get_bot_folders()
            key_exists, source_folder, source_key_file = self.check_spreadsheet_key_exists(bot_folders)
            
            if not key_exists:
                print(f"{self.RED}❌ Spreadsheet access key not found{self.ENDC}")
                return False
            
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
            
            # Get valid bot names (from Step 5 comparison)
            valid_bots = self.get_valid_bot_names()
            
            # Initialize bot processes dictionary
            for bot_name in valid_bots:
                if bot_name not in self.bot_processes:
                    self.bot_processes[bot_name] = None
            
            # Monitor scheduler sheet and control bots
            check_count = 0
            
            while True:
                check_count += 1
                
                # Get current day and date for display
                current_day = datetime.now().strftime("%A").lower()
                current_date = datetime.now().strftime("%d-%m-%Y")
                day = current_day.capitalize()
                date = current_date
                
                # Display "00s" while syncing with Google Sheets
                print(f"\r{day} {date} | Check #{check_count} | Next sync: 00s", end="", flush=True)
                
                # Get scheduler data with error handling
                try:
                    schedule_data = self.get_scheduler_data(gc)
                except Exception as e:
                    # Show error message
                    print(f"\n{day} {date} | Check #{check_count} | Next sync: 60s")
                    print("-" * 80)
                    print(f"{self.RED}Error accessing scheduler sheet: {e}{self.ENDC}")
                    print(f"{self.YELLOW}scheduler not available{self.ENDC}")
                    
                    # Wait 60 seconds with countdown
                    for countdown in range(60, 0, -1):
                        print(f"\r{day} {date} | Check #{check_count} | Next sync: {countdown:02d}s", end="", flush=True)
                        time.sleep(1)
                    print("\r" + " " * 80 + "\r", end="", flush=True)
                    continue
                
                if schedule_data is None:
                    # Show no data available
                    print(f"\n{day} {date} | Check #{check_count} | Next sync: 60s")
                    print("-" * 80)
                    print(f"{self.YELLOW}scheduler not available{self.ENDC}")
                    
                    # Wait 60 seconds with countdown
                    for countdown in range(60, 0, -1):
                        print(f"\r{day} {date} | Check #{check_count} | Next sync: {countdown:02d}s", end="", flush=True)
                        time.sleep(1)
                    print("\r" + " " * 80 + "\r", end="", flush=True)
                    continue
                
                # Execute steps 9a-9d for bot execution management
                self.execute_steps_9a_to_9d(schedule_data, valid_bots, gc, check_count)
                
                # Format and display schedule - ONLY ONCE per sync
                result = self.format_schedule_display(schedule_data, valid_bots)
                
                if result:
                    day, date, display_data = result
                    
                    if not display_data:
                        print(f"\n{day} {date} | Check #{check_count} | Next sync: 60s")
                        print("-" * 80)
                        print("No scheduled bots for today")
                    else:
                        # Calculate column widths for all columns including new ones
                        max_name_len = max(len(item['bot_name']) for item in display_data)
                        max_name_len = max(max_name_len, len("bots name"))
                        max_start_len = max(len(item['start_at']) for item in display_data)
                        max_start_len = max(max_start_len, len("start_at"))
                        max_stop_len = max(len(item['stop_at']) for item in display_data)
                        max_stop_len = max(max_stop_len, len("stop_at"))
                        max_switch_len = max(len(item['switch']) for item in display_data)
                        max_switch_len = max(max_switch_len, len("switch"))
                        max_status_len = max(len(item['status']) for item in display_data)
                        max_status_len = max(max_status_len, len("status"))
                        max_last_run_len = max(len(item['last_run']) for item in display_data)
                        max_last_run_len = max(max_last_run_len, len("last_run"))
                        max_remark_len = max(len(item['remark']) for item in display_data)
                        max_remark_len = max(max_remark_len, len("remark"))
                        
                        # Add padding
                        max_name_len += 2
                        max_start_len += 2
                        max_stop_len += 2
                        max_switch_len += 2
                        max_status_len += 2
                        max_last_run_len += 2
                        max_remark_len += 2
                        
                        # Build header string to calculate table width
                        header = (f"{'bots name':<{max_name_len}} "
                                 f"{'start_at':<{max_start_len}} "
                                 f"{'stop_at':<{max_stop_len}} "
                                 f"{'switch':<{max_switch_len}} "
                                 f"{'status':<{max_status_len}} "
                                 f"{'last_run':<{max_last_run_len}} "
                                 f"{'remark':<{max_remark_len}}")
                        
                        # Calculate table width for consistent dash lines
                        table_width = len(header)
                        
                        # Display table ONLY ONCE
                        print("\n" + "-" * table_width)
                        print(header)
                        print("-" * table_width)
                        
                        # Data rows
                        for item in display_data:
                            row = (f"{item['bot_name']:<{max_name_len}} "
                                   f"{item['start_at']:<{max_start_len}} "
                                   f"{item['stop_at']:<{max_stop_len}} "
                                   f"{item['switch']:<{max_switch_len}} "
                                   f"{item['status']:<{max_status_len}} "
                                   f"{item['last_run']:<{max_last_run_len}} "
                                   f"{item['remark']:<{max_remark_len}}")
                            print(row)
                    
                    # Sync bots with current schedule - FIXED VERSION
                    self.sync_bots_with_schedule(schedule_data, valid_bots)
                    
                    # Countdown timer - use carriage return to update in place
                    for countdown in range(60, 0, -1):
                        time.sleep(1)
                        print(f"\r{day} {date} | Check #{check_count} | Next sync: {countdown:02d}s", end="", flush=True)
                    print("\r" + " " * 80 + "\r", end="", flush=True)
                
                else:
                    # Show no data for today
                    print(f"\n{day} {date} | Check #{check_count} | Next sync: 60s")
                    print("-" * 80)
                    print(f"{self.YELLOW}⚠ No valid schedule data for today{self.ENDC}")
                    
                    # Wait 60 seconds with countdown
                    for countdown in range(60, 0, -1):
                        print(f"\r{day} {date} | Check #{check_count} | Next sync: {countdown:02d}s", end="", flush=True)
                        time.sleep(1)
                    print("\r" + " " * 80 + "\r", end="", flush=True)
                
                # Store current schedule data
                self.schedule_data = schedule_data
                self.last_sync_time = datetime.now()
                
        except KeyboardInterrupt:
            print(f"\n\n{self.YELLOW}Scheduler monitoring stopped by user{self.ENDC}")
            
            # Stop all running bots before exit
            for bot_name in list(self.bot_processes.keys()):
                if self.is_bot_running(bot_name):
                    self.stop_bot(bot_name)
            
            return True
        except Exception as e:
            print(f"{self.RED}❌ Error in Step 9: {e}{self.ENDC}")
            
            # Stop all running bots on error
            for bot_name in list(self.bot_processes.keys()):
                if self.is_bot_running(bot_name):
                    self.stop_bot(bot_name)
            
            return False

    def cleanup(self):
        """Cleanup method to be called before exit"""
        print("\nPerforming cleanup...")
        
        # Stop all running bots
        for bot_name in list(self.bot_processes.keys()):
            if self.is_bot_running(bot_name):
                self.stop_bot(bot_name)
        
        # Close browser
        self.close_chrome_browser()

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
                                print(f"\n{self.BLUE}All bots have matching Google Sheets, comparing CSV headers...{self.ENDC}")
                                step6_success, all_sheets_available = self.run_step6()
                                
                                if step6_success:
                                    print("\n" + "=" * 50)
                                    print("✓ Step 6 completed successfully!")
                                    print("=" * 50)
                                    
                                    # Run Step 8 - Detect new bots
                                    step8_success, new_bots = self.run_step8()
                                    
                                    # Continue to Step 9 regardless of new bots
                                    print(f"\n{self.BLUE}Starting Step 9: Scheduler Monitoring & Bot Control{self.ENDC}")
                                    step9_success = self.run_step9()
                                    if step9_success:
                                        print("\n" + "=" * 50)
                                        print("✓ ALL STEPS COMPLETED SUCCESSFULLY!")
                                        print("✓ Bots are ready to use")
                                        print("=" * 50)
                                    else:
                                        print(f"\n{self.RED}❌ Step 9 failed.{self.ENDC}")
                                        sys.exit(1)
                                else:
                                    print(f"\n{self.YELLOW}⚠ Step 6 had issues, but continuing...{self.ENDC}")
                                    # Even if Step 6 fails, continue to Step 8
                                    step8_success, new_bots = self.run_step8()
                                    
                                    # Continue to Step 9 regardless of new bots
                                    print(f"\n{self.BLUE}Starting Step 9: Scheduler Monitoring & Bot Control{self.ENDC}")
                                    step9_success = self.run_step9()
                                    if step9_success:
                                        print("\n" + "=" * 50)
                                        print("✓ Setup completed with warnings")
                                        print("=" * 50)
                                    else:
                                        print(f"\n{self.RED}❌ Step 9 failed.{self.ENDC}")
                                        sys.exit(1)
                            else:
                                # Some bots missing matching sheets - continue to Step 7
                                step7_success = self.run_step7()
                                if step7_success:
                                    print("\n" + "=" * 50)
                                    print("✓ Step 7 completed successfully!")
                                    print("✓ WhatsApp notification sent for missing sheets")
                                    print("=" * 50)
                                    
                                    # AFTER STEP 7 SUCCESS, CONTINUE WITH STEP 6
                                    print(f"\n{self.BLUE}Continuing with CSV header comparison after successful WhatsApp notification...{self.ENDC}")
                                    step6_success, all_sheets_available = self.run_step6()
                                    
                                    if step6_success:
                                        print("\n" + "=" * 50)
                                        print("✓ Step 6 completed successfully!")
                                        print("=" * 50)
                                        
                                        # Run Step 8 - Detect new bots
                                        step8_success, new_bots = self.run_step8()
                                        
                                        # Continue to Step 9 regardless of new bots
                                        print(f"\n{self.BLUE}Starting Step 9: Scheduler Monitoring & Bot Control{self.ENDC}")
                                        step9_success = self.run_step9()
                                        if step9_success:
                                            print("\n" + "=" * 50)
                                            print("✓ ALL STEPS COMPLETED SUCCESSFULLY!")
                                            print("✓ Bots are ready to use")
                                            print("=" * 50)
                                        else:
                                            print(f"\n{self.RED}❌ Step 9 failed.{self.ENDC}")
                                            sys.exit(1)
                                    else:
                                        print(f"\n{self.YELLOW}⚠ Step 6 had issues, but continuing...{self.ENDC}")
                                        # Even if Step 6 fails, continue to Step 8
                                        step8_success, new_bots = self.run_step8()
                                        
                                        # Continue to Step 9 regardless of new bots
                                        print(f"\n{self.BLUE}Starting Step 9: Scheduler Monitoring & Bot Control{self.ENDC}")
                                        step9_success = self.run_step9()
                                        if step9_success:
                                            print("\n" + "=" * 50)
                                            print("✓ Setup completed with warnings")
                                            print("=" * 50)
                                        else:
                                            print(f"\n{self.RED}❌ Step 9 failed.{self.ENDC}")
                                            sys.exit(1)
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
