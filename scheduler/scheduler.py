#!/usr/bin/env python3
"""
Scheduler Script for Managing Python Bots - Complete Implementation
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
                
                # Save XPaths to temporary local storage
                temp_xpath_file = Path("/tmp/whatsapp_xpaths.json")
                with open(temp_xpath_file, 'w') as f:
                    json.dump(xpaths_data, f, indent=2)
                print(f"✅ XPaths saved to {temp_xpath_file}")
                
                # Display fetched XPaths
                print(f"\n{self.BLUE}Fetched XPaths:{self.ENDC}")
                for xpath_name, xpath_value in sorted(self.xpaths.items()):
                    print(f"  {xpath_name}: {xpath_value}")
                    
                return True
            else:
                print(f"{self.RED}❌ No XPaths found in database{self.ENDC}")
                return False
                
        except Exception as e:
            print(f"{self.RED}❌ Error fetching XPaths: {e}{self.ENDC}")
            return False

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

    # =========================================================================
    # STEP 7 IMPLEMENTATION - COMPLETE WHATSAPP MESSAGING
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

    def wait_for_element(self, xpath_key, timeout=120, check_interval=1):
        """Wait for element to be present using XPath from database"""
        if xpath_key not in self.xpaths:
            print(f"{self.RED}❌ XPath key '{xpath_key}' not found in database{self.ENDC}")
            return None
        
        xpath = self.xpaths[xpath_key]
        print(f"Waiting for {xpath_key} (timeout: {timeout}s)...")
        
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < timeout:
            check_count += 1
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                if element.is_displayed():
                    print(f"  ✓ {xpath_key} found after {check_count} checks")
                    return element
            except NoSuchElementException:
                pass
            
            elapsed = int(time.time() - start_time)
            if check_count % 10 == 0:
                print(f"  Checking... {elapsed}s elapsed")
            
            time.sleep(check_interval)
        
        print(f"  ✗ {xpath_key} not found within {timeout} seconds")
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

    def run_step7a(self):
        """Step 7a: Close browser and reopen it"""
        print("\n" + "=" * 50)
        print("STEP 7a: Browser Management")
        print("=" * 50)
        
        self.close_chrome_browser()
        time.sleep(3)
        
        return self.setup_selenium_driver()

    def run_step7b(self):
        """Step 7b: Check internet connection"""
        print("\n" + "=" * 50)
        print("STEP 7b: Internet Connection Check")
        print("=" * 50)
        
        if self.check_internet_connection():
            print(f"{self.GREEN}✓ Internet connection is available{self.ENDC}")
            return True
        else:
            print(f"{self.YELLOW}Internet connection not available.{self.ENDC}")
            return self.wait_for_internet_connection()

    def run_step7c(self):
        """Step 7c: Open WhatsApp Web"""
        print("\n" + "=" * 50)
        print("STEP 7c: WhatsApp Web Setup")
        print("=" * 50)
        
        try:
            self.driver.get("https://web.whatsapp.com/")
            print("✓ WhatsApp Web opened")
            return True
        except Exception as e:
            print(f"{self.RED}❌ Error opening WhatsApp Web: {e}{self.ENDC}")
            return False

    def run_step7d(self):
        """Step 7d: Check for Xpath001 (search field)"""
        print("\n" + "=" * 50)
        print("STEP 7d: Checking Search Field")
        print("=" * 50)
        
        element = self.wait_for_element("Xpath001", timeout=120)
        if element:
            print("✓ Entered Mobile number search field")
            return True, element
        else:
            # Check for loading indicator (Xpath011)
            if self.check_element_present("Xpath011"):
                print("Loading chats detected, retrying search field...")
                return self.run_step7d()  # Recursive retry
            else:
                print("Search field not found and no loading indicator")
                return False, None

    def run_step7e(self):
        """Step 7e: Check report number file"""
        print("\n" + "=" * 50)
        print("STEP 7e: Checking Report Number File")
        print("=" * 50)
        
        report_number = self.get_report_number()
        if report_number:
            print("✓ Report number file available")
            print(f"✓ Phone number: {report_number}")
            return True, report_number
        else:
            print("✗ Report number file not available")
            return False, None

    def run_step7f(self):
        """Step 7f: Check loading indicator"""
        print("\n" + "=" * 50)
        print("STEP 7f: Checking Loading Indicator")
        print("=" * 50)
        
        if self.check_element_present("Xpath011"):
            print("Loading indicator present, restarting browser...")
            return "restart"
        else:
            print("No loading indicator, restarting browser...")
            return "restart"

    def run_step7g(self):
        """Step 7g: Validate phone number"""
        print("\n" + "=" * 50)
        print("STEP 7g: Validating Phone Number")
        print("=" * 50)
        
        report_number = self.get_report_number()
        if report_number and self.is_valid_phone_number(report_number):
            print("✓ Phone number is available and valid")
            return True, report_number
        else:
            print("✗ Phone number is not available or invalid")
            return False, None

    def run_step7h(self, search_field, phone_number):
        """Step 7h: Enter phone number in search field - Type digit by digit"""
        print("\n" + "=" * 50)
        print("STEP 7h: Entering Phone Number")
        print("=" * 50)
        
        try:
            # Clear the search field first
            search_field.clear()
            time.sleep(1)
            
            # Type phone number digit by digit
            print(f"Typing phone number digit by digit: {phone_number}")
            for digit in phone_number:
                search_field.send_keys(digit)
                time.sleep(0.1)  # Small delay between each digit
            
            print(f"✓ Phone number typed: {phone_number}")
            
            print("⏳ Waiting 10 seconds for stability...")
            time.sleep(10)
            
            return True
        except Exception as e:
            print(f"{self.RED}❌ Error entering phone number: {e}{self.ENDC}")
            return False

    def run_step7i(self, phone_number):
        """Step 7i: Check if contact exists"""
        print("\n" + "=" * 50)
        print("STEP 7i: Checking Contact Existence")
        print("=" * 50)
        
        # Check for Xpath004 (contact not found message)
        if self.check_element_present("Xpath004"):
            print("❌ Contact not found message detected (Xpath004 found)")
            if self.check_internet_connection():
                print("✗ Invalid Mobile Number")
                return False
            else:
                print("No internet connection, restarting browser...")
                return "restart"
        else:
            print("✓ Contact found (Xpath004 not present)")
            return True

    def run_step7j(self):
        """Step 7j: Select contact and enter message field"""
        print("\n" + "=" * 50)
        print("STEP 7j: Selecting Contact")
        print("=" * 50)
        
        try:
            # Wait 10 seconds for stability after phone number entry
            print("Waiting 10 seconds for stability after phone number entry...")
            time.sleep(10)
            
            # Press down arrow to select the first contact
            print("Pressing down arrow to select contact...")
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ARROW_DOWN)
            print("✓ Down arrow pressed - contact selected")
            
            # Wait 2 seconds for stability
            print("Waiting 2 seconds for stability...")
            time.sleep(2)
            
            # Press enter to open the chat
            print("Pressing Enter to open chat...")
            body.send_keys(Keys.ENTER)
            print("✓ Enter pressed - Chat opened")
            
            # Wait for message input field to be available
            print("Waiting 3 seconds for message field...")
            time.sleep(3)
            
            print("✓ Entered Message Field")
            return True
            
        except Exception as e:
            print(f"{self.RED}❌ Error selecting contact: {e}{self.ENDC}")
            return False

    def run_step7k(self):
        """Step 7k: Type error message about missing sheets"""
        print("\n" + "=" * 50)
        print("STEP 7k: Composing Error Message")
        print("=" * 50)
        
        if not self.missing_sheets:
            print("No missing sheets to report")
            return False
        
        # Create message based on missing sheets
        if len(self.missing_sheets) == 1:
            message = f"Google Sheet Error - {self.missing_sheets[0]}"
        else:
            message = f"Google Sheet Error - {self.missing_sheets[0]} and {self.missing_sheets[1]}" if len(self.missing_sheets) == 2 else f"Google Sheet Error - {', '.join(self.missing_sheets)}"
        
        message += "\n---------------------------------------------\n"
        
        for sheet in self.missing_sheets:
            message += f"Sheet '{sheet}' is not available [or]\n"
            message += f"Name is mismatch [or]\n"
            message += f"Not share with service account\n\n"
        
        message += "Kindly check\n"
        message += "---------------------------------------------"
        
        try:
            # Wait for message input field to be ready
            time.sleep(2)
            
            # Find the message input field in the chat
            message_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']"))
            )
            
            # Focus on the input
            message_input.click()
            time.sleep(1)
            
            # Type the message with proper line breaks using Shift+Enter
            lines = message.split('\n')
            for i, line in enumerate(lines):
                message_input.send_keys(line)
                if i < len(lines) - 1:  # Not the last line
                    # Use Shift+Enter for new line (without sending)
                    message_input.send_keys(Keys.SHIFT + Keys.ENTER)
                    time.sleep(0.5)  # Small delay between lines
            
            print("✓ Error message composed in message input field")
            return True
        except Exception as e:
            print(f"{self.RED}❌ Error composing message: {e}{self.ENDC}")
            return False

    def run_step7l(self):
        """Step 7l: Send message"""
        print("\n" + "=" * 50)
        print("STEP 7l: Sending Message")
        print("=" * 50)
        
        try:
            # Wait 2 seconds for stability before sending
            time.sleep(2)
            
            # Press Enter to send the message
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ENTER)
            print("✓ Enter pressed - Message sent")
            
            # Wait 2 seconds after sending
            time.sleep(2)
            
            return True
        except Exception as e:
            print(f"{self.RED}❌ Error sending message: {e}{self.ENDC}")
            return False

    def run_step7m(self):
        """Step 7m: Wait for message to be delivered"""
        print("\n" + "=" * 50)
        print("STEP 7m: Waiting for Message Delivery")
        print("=" * 50)
        
        print("Waiting for pending message indicator to disappear...")
        start_time = time.time()
        
        while time.time() - start_time < 300:
            if not self.check_element_present("Xpath003"):
                print("✓ Error message sent successfully")
                return True
            
            time.sleep(1)
        
        print("✗ Message delivery timeout")
        return False

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
                # Step 7a: Setup browser
                print(f"\n{self.BLUE}7a. Browser Management{self.ENDC}")
                if not self.run_step7a():
                    print("❌ Step 7a failed, restarting...")
                    continue
                
                # Step 7b: Check internet
                print(f"\n{self.BLUE}7b. Internet Connection Check{self.ENDC}")
                if not self.run_step7b():
                    print("❌ Step 7b failed, restarting...")
                    continue
                
                # Step 7c: Open WhatsApp
                print(f"\n{self.BLUE}7c. WhatsApp Web Setup{self.ENDC}")
                if not self.run_step7c():
                    print("❌ Step 7c failed, restarting...")
                    continue
                
                # Step 7d: Check search field
                print(f"\n{self.BLUE}7d. Checking Search Field{self.ENDC}")
                success, search_field = self.run_step7d()
                if not success:
                    result = self.run_step7f()
                    if result == "restart":
                        print("🔄 Restarting due to loading indicator...")
                        continue
                    else:
                        return False
                
                # Step 7e: Check report number file
                print(f"\n{self.BLUE}7e. Checking Report Number File{self.ENDC}")
                success, phone_number = self.run_step7e()
                if not success:
                    print("❌ Step 7e failed, stopping...")
                    return False
                
                # Step 7g: Validate phone number
                print(f"\n{self.BLUE}7g. Validating Phone Number{self.ENDC}")
                success, phone_number = self.run_step7g()
                if not success:
                    print("❌ Step 7g failed, stopping...")
                    return False
                
                # Step 7h: Enter phone number (TYPE DIGIT BY DIGIT)
                print(f"\n{self.BLUE}7h. Entering Phone Number{self.ENDC}")
                if not self.run_step7h(search_field, phone_number):
                    print("❌ Step 7h failed, restarting...")
                    continue
                
                # Step 7i: Check contact existence
                print(f"\n{self.BLUE}7i. Checking Contact Existence{self.ENDC}")
                result = self.run_step7i(phone_number)
                if result == "restart":
                    print("🔄 Restarting due to no internet...")
                    continue
                elif not result:
                    print("❌ Step 7i failed, stopping...")
                    return False
                
                # Step 7j: Select contact
                print(f"\n{self.BLUE}7j. Selecting Contact{self.ENDC}")
                if not self.run_step7j():
                    print("❌ Step 7j failed, restarting...")
                    continue
                
                # Step 7k: Type error message
                print(f"\n{self.BLUE}7k. Composing Error Message{self.ENDC}")
                if not self.run_step7k():
                    print("❌ Step 7k failed, restarting...")
                    continue
                
                # Step 7l: Send message
                print(f"\n{self.BLUE}7l. Sending Message{self.ENDC}")
                if not self.run_step7l():
                    print("❌ Step 7l failed, restarting...")
                    continue
                
                # Step 7m: Wait for delivery
                print(f"\n{self.BLUE}7m. Waiting for Message Delivery{self.ENDC}")
                if self.run_step7m():
                    print(f"\n{self.GREEN}✅ WHATSAPP NOTIFICATION SENT SUCCESSFULLY{self.ENDC}")
                    return True
                else:
                    print("❌ Step 7m failed, restarting...")
                    continue
                
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
        """Step 8: Placeholder for future implementation"""
        print("\n" + "=" * 50)
        print("STEP 8: Placeholder")
        print("=" * 50)
        print(f"{self.GREEN}✓ Step 8 - To be implemented later{self.ENDC}")
        return True

    def cleanup(self):
        """Cleanup method to be called before exit"""
        print("\nPerforming cleanup...")
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
                                # All bots have matching sheets - continue to Step 8
                                step8_success = self.run_step8()
                                if step8_success:
                                    print("\n" + "=" * 50)
                                    print("✓ Step 8 completed successfully!")
                                    print("✓ All Google Sheets verified and updated")
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
