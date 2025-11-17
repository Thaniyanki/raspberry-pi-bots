#!/usr/bin/env python3
"""
Scheduler Script for Managing Python Bots
Handles folder structure, report numbers, and virtual environment setup
"""

import os
import sys
import subprocess
import time
from pathlib import Path

class BotScheduler:
    def __init__(self):
        self.username = os.getenv('USER') or os.getenv('USERNAME')
        if not self.username:
            print("Error: Could not determine username")
            sys.exit(1)
            
        self.bots_base_path = Path(f"/home/{self.username}/bots")
        self.scheduler_folder = "scheduler"
        
    def run_curl_command(self):
        """Run the curl command to setup bots"""
        print("Setting up bots using curl command...")
        curl_command = [
            'curl', '-sL', 
            'https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main/all-in-one-venv/all%20in%20one%20venv.py'
        ]
        
        try:
            result = subprocess.run(
                ['python3', '-c', f"import urllib.request; exec(urllib.request.urlopen('{curl_command[2]}').read())"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("Bots setup completed successfully")
            else:
                print(f"Error running setup: {result.stderr}")
        except Exception as e:
            print(f"Error executing setup: {e}")
            
        sys.exit(0)
    
    def check_bots_folder(self):
        """Check if bots folder exists and has valid content"""
        if not self.bots_base_path.exists():
            print("Bots folder not found. Running setup...")
            self.run_curl_command()
            return False
            
        # Get all items in bots folder
        items = list(self.bots_base_path.iterdir())
        folders = [item for item in items if item.is_dir() and item.name != self.scheduler_folder]
        
        if not folders:
            print("Bots folder is empty or only contains scheduler folder. Running setup...")
            self.run_curl_command()
            return False
            
        return True
    
    def get_bot_folders(self):
        """Get all bot folders excluding scheduler folder"""
        if not self.bots_base_path.exists():
            return []
            
        items = list(self.bots_base_path.iterdir())
        bot_folders = [item for item in items if item.is_dir() and item.name != self.scheduler_folder]
        return bot_folders
    
    def check_report_numbers_exist(self, bot_folders):
        """Check if report number files exist in all bot folders"""
        for folder in bot_folders:
            report_file = folder / "report number"
            if not report_file.exists():
                return False
        return True
    
    def delete_all_report_numbers(self, bot_folders):
        """Delete all report number files"""
        for folder in bot_folders:
            report_file = folder / "report number"
            if report_file.exists():
                report_file.unlink()
                print(f"Deleted report number from {folder.name}")
    
    def create_report_numbers(self, bot_folders, report_number):
        """Create report number files in all bot folders"""
        for folder in bot_folders:
            report_file = folder / "report number"
            try:
                with open(report_file, 'w') as f:
                    f.write(report_number)
                print(f"Created report number in {folder.name}")
            except Exception as e:
                print(f"Error creating report number in {folder.name}: {e}")
    
    def get_user_input(self, prompt, timeout=10):
        """Get user input with optional timeout"""
        print(prompt, end='', flush=True)
        
        if timeout > 0:
            # Simple input without timeout for now
            # In a more advanced version, you could use threading for timeout
            try:
                user_input = input().strip()
                return user_input
            except EOFError:
                return ""
        else:
            try:
                user_input = input().strip()
                return user_input
            except EOFError:
                return ""
    
    def handle_report_numbers(self, bot_folders):
        """Handle report number creation/modification"""
        all_have_report_numbers = self.check_report_numbers_exist(bot_folders)
        
        if not all_have_report_numbers:
            # Some folders don't have report numbers
            report_number = self.get_user_input("Enter the report number: ")
            if report_number:
                self.create_report_numbers(bot_folders, report_number)
            return
        
        # All folders have report numbers
        while True:
            response = self.get_user_input(
                "Report number already available in all bots folder. Do you want to modify? y/n: "
            ).lower()
            
            if response == 'y':
                self.delete_all_report_numbers(bot_folders)
                report_number = self.get_user_input("Enter the report number: ")
                if report_number:
                    self.create_report_numbers(bot_folders, report_number)
                break
            elif response == 'n':
                print("Continuing with existing report numbers...")
                break
            else:
                print("Please press either 'y' or 'n'")
                # Wait 10 seconds and continue if no valid input
                print("Waiting 10 seconds for response...")
                time.sleep(10)
                # Try one more time
                response = self.get_user_input("Do you want to modify? y/n: ").lower()
                if response == 'y':
                    self.delete_all_report_numbers(bot_folders)
                    report_number = self.get_user_input("Enter the report number: ")
                    if report_number:
                        self.create_report_numbers(bot_folders, report_number)
                    break
                elif response == 'n':
                    print("Continuing with existing report numbers...")
                    break
                else:
                    print("No valid response. Continuing with existing report numbers...")
                    break
    
    def list_bot_folders(self, bot_folders):
        """List all available bot folders"""
        if bot_folders:
            print("\nAvailable bot folders:")
            for folder in bot_folders:
                print(f"  - {folder.name}")
        else:
            print("No bot folders found.")
    
    def run(self):
        """Main execution function"""
        print("=" * 50)
        print("Bot Scheduler Starting...")
        print(f"Username: {self.username}")
        print(f"Bots path: {self.bots_base_path}")
        print("=" * 50)
        
        # Step 1: Check bots folder structure
        if not self.check_bots_folder():
            return
            
        # Get bot folders
        bot_folders = self.get_bot_folders()
        
        if not bot_folders:
            print("No bot folders found. Running setup...")
            self.run_curl_command()
            return
        
        # List available bot folders
        self.list_bot_folders(bot_folders)
        
        # Handle report numbers
        self.handle_report_numbers(bot_folders)
        
        # Step 2 will be implemented here later
        print("\n" + "=" * 50)
        print("Step 1 completed successfully!")
        print("Ready for Step 2 implementation...")
        print("=" * 50)

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
