#!/usr/bin/env python3
"""
Scheduler Script for Managing Python Bots
Handles folder structure, report numbers, and virtual environment setup
"""

import os
import sys
import subprocess
import time
import select
import threading
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
        try:
            result = subprocess.run([
                'curl', '-sL', 
                'https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main/all-in-one-venv/all%20in%20one%20venv.py'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                exec(result.stdout)
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
    
    def get_venv_path(self, bot_folder):
        """Get the venv path for a bot folder"""
        # Check for venv folder inside the bot folder
        venv_path = bot_folder / "venv"
        if venv_path.exists() and venv_path.is_dir():
            return venv_path
        
        # If no venv folder, check for other common virtual environment names
        for venv_name in ["venv", "virtualenv", ".venv", "env"]:
            potential_venv = bot_folder / venv_name
            if potential_venv.exists() and potential_venv.is_dir():
                return potential_venv
        
        return None
    
    def check_report_numbers_exist(self, bot_folders):
        """Check if report number files exist in all bot folders' venv"""
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if not venv_path:
                return False  # No venv folder found
            
            report_file = venv_path / "report number"
            if not report_file.exists():
                return False
        return True
    
    def delete_all_report_numbers(self, bot_folders):
        """Delete all report number files from venv folders"""
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                report_file = venv_path / "report number"
                if report_file.exists():
                    report_file.unlink()
                    print(f"Deleted report number from {folder.name}/venv/")
    
    def create_report_numbers(self, bot_folders, report_number):
        """Create report number files in all bot folders' venv"""
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
            else:
                print(f"Warning: No venv folder found in {folder.name}")
    
    def input_with_timeout(self, prompt, timeout=10):
        """Get user input with timeout"""
        print(prompt, end='', flush=True)
        
        # For piped input (curl | python3), we need to handle differently
        if not sys.stdin.isatty():
            try:
                # Try to read from /dev/tty for direct terminal access
                import termios
                import tty
                
                fd = os.open('/dev/tty', os.O_RDWR)
                try:
                    old_settings = termios.tcgetattr(fd)
                    try:
                        tty.setraw(fd)
                        
                        # Start timer
                        start_time = time.time()
                        input_chars = []
                        
                        while time.time() - start_time < timeout:
                            # Check if input is available
                            if select.select([fd], [], [], 0.1)[0]:
                                char = os.read(fd, 1).decode('utf-8')
                                if char == '\r' or char == '\n':  # Enter pressed
                                    break
                                elif char == '\x03':  # Ctrl+C
                                    raise KeyboardInterrupt
                                else:
                                    input_chars.append(char)
                                    print(char, end='', flush=True)
                        
                        result = ''.join(input_chars).strip()
                        print()  # New line after input
                        return result
                        
                    finally:
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                finally:
                    os.close(fd)
            except:
                # Fallback for systems without /dev/tty access
                pass
        
        # Standard timeout input for terminal
        try:
            if sys.platform != "win32":
                # Unix-like systems
                import select
                print(prompt, end='', flush=True)
                rlist, _, _ = select.select([sys.stdin], [], [], timeout)
                if rlist:
                    return sys.stdin.readline().strip()
                else:
                    print("\nTimeout reached. Continuing...")
                    return ""
            else:
                # Windows
                import msvcrt
                import time
                
                print(prompt, end='', flush=True)
                start_time = time.time()
                input_chars = []
                
                while time.time() - start_time < timeout:
                    if msvcrt.kbhit():
                        char = msvcrt.getwch()
                        if char == '\r':  # Enter key
                            break
                        elif char == '\x03':  # Ctrl+C
                            raise KeyboardInterrupt
                        else:
                            input_chars.append(char)
                            print(char, end='', flush=True)
                    time.sleep(0.1)
                
                if input_chars:
                    return ''.join(input_chars)
                else:
                    print("\nTimeout reached. Continuing...")
                    return ""
        except:
            # Ultimate fallback - simple input without timeout
            try:
                return input(prompt).strip()
            except:
                return ""
    
    def handle_report_numbers(self, bot_folders):
        """Handle report number creation/modification with timeout"""
        all_have_report_numbers = self.check_report_numbers_exist(bot_folders)
        
        if not all_have_report_numbers:
            # Some folders don't have report numbers
            print("Some bots are missing report numbers in their venv folders.")
            report_number = self.input_with_timeout("Enter the report number: ", timeout=30)
            if report_number:
                self.create_report_numbers(bot_folders, report_number)
                print(f"Report number '{report_number}' set for all bots in their venv folders.")
            else:
                print("No report number provided. Using existing values where available.")
            return
        
        # All folders have report numbers
        print("Report number already available in all bots folder's venv folders.")
        
        # Ask if user wants to modify with 10-second timeout
        response = self.input_with_timeout("Do you want to modify? y/n: ", timeout=10)
        
        if response.lower() == 'y':
            self.delete_all_report_numbers(bot_folders)
            new_report_number = self.input_with_timeout("Enter the report number: ", timeout=30)
            if new_report_number:
                self.create_report_numbers(bot_folders, new_report_number)
                print(f"Report number updated to '{new_report_number}' in all venv folders")
        elif response.lower() == 'n':
            print("Continuing with existing report numbers...")
        else:
            print("No valid response received within 10 seconds. Continuing with existing report numbers...")
    
    def list_bot_folders(self, bot_folders):
        """List all available bot folders with venv status"""
        if bot_folders:
            print("\nAvailable bot folders:")
            for folder in bot_folders:
                venv_path = self.get_venv_path(folder)
                if venv_path:
                    report_file = venv_path / "report number"
                    status = "✓" if report_file.exists() else "✗"
                    venv_status = "✓"
                else:
                    status = "✗"
                    venv_status = "✗"
                
                print(f"  - {folder.name} [venv: {venv_status}] [report number: {status}]")
        else:
            print("No bot folders found.")
    
    def verify_report_numbers(self, bot_folders):
        """Verify that report numbers are properly set in venv folders"""
        print("\nVerifying report numbers in venv folders...")
        all_set = True
        
        for folder in bot_folders:
            venv_path = self.get_venv_path(folder)
            if venv_path:
                report_file = venv_path / "report number"
                if report_file.exists():
                    try:
                        with open(report_file, 'r') as f:
                            content = f.read().strip()
                        if content:
                            print(f"  ✓ {folder.name}/venv/: {content}")
                        else:
                            print(f"  ✗ {folder.name}/venv/: Empty report number")
                            all_set = False
                    except Exception as e:
                        print(f"  ✗ {folder.name}/venv/: Error reading - {e}")
                        all_set = False
                else:
                    print(f"  ✗ {folder.name}/venv/: No report number file")
                    all_set = False
            else:
                print(f"  ✗ {folder.name}: No venv folder found")
                all_set = False
        
        return all_set
    
    def run_step2(self):
        """Placeholder for Step 2 implementation"""
        print("\n" + "=" * 50)
        print("STEP 2: Bot Scheduling and Management")
        print("=" * 50)
        print("Step 2 functionality will be implemented here...")
        # Add your Step 2 logic here
    
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
        
        # Verify report numbers are set
        report_numbers_ok = self.verify_report_numbers(bot_folders)
        
        print("\n" + "=" * 50)
        if report_numbers_ok:
            print("✓ Step 1 completed successfully!")
            print("✓ All report numbers are properly set in venv folders")
        else:
            print("⚠ Step 1 completed with warnings")
            print("⚠ Some report numbers may not be set correctly in venv folders")
        
        # Proceed to Step 2
        self.run_step2()

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
