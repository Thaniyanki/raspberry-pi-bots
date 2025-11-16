# scheduler Python Script
import os
import subprocess
import requests
import json
from typing import List, Set

class BotManager:
    def __init__(self):
        self.github_owner = "Thaniyanki"
        self.github_repo = "raspberry-pi-bots"
        self.github_api_base = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}"
        self.raw_content_base = f"https://raw.githubusercontent.com/{self.github_owner}/{self.github_repo}/main"
        
    def step3_get_raspberry_folders(self) -> List[str]:
        """Step 3: Get folder list from Raspberry Pi local directory"""
        try:
            current_dir = os.getcwd()
            folders = []
            
            for item in os.listdir(current_dir):
                if os.path.isdir(item):
                    folders.append(item)
            
            print("Step 3 - Raspberry Pi folders:")
            for folder in folders:
                print(f"  - {folder}")
            
            return folders
        except Exception as e:
            print(f"Error reading Raspberry Pi folders: {e}")
            return []
    
    def step4_get_github_folders(self) -> List[str]:
        """Step 4: Get folder list from GitHub repository"""
        try:
            url = f"{self.github_api_base}/contents"
            response = requests.get(url)
            response.raise_for_status()
            
            contents = response.json()
            folders = []
            
            for item in contents:
                if item['type'] == 'dir':
                    folders.append(item['name'])
            
            print("Step 4 - GitHub folders:")
            for folder in folders:
                print(f"  - {folder}")
            
            return folders
        except Exception as e:
            print(f"Error fetching GitHub folders: {e}")
            return []
    
    def normalize_folder_name(self, folder_name: str) -> str:
        """Normalize folder names by removing hyphens and spaces for comparison"""
        return folder_name.replace('-', ' ').replace('_', ' ').lower().strip()
    
    def step5_compare_folders(self, raspberry_folders: List[str], github_folders: List[str]) -> List[str]:
        """Step 5: Compare folders and find missing ones"""
        # Normalize all folder names for comparison
        normalized_raspberry = {self.normalize_folder_name(folder): folder for folder in raspberry_folders}
        normalized_github = {self.normalize_folder_name(folder): folder for folder in github_folders}
        
        print("Step 5 - Comparing folders:")
        print("Raspberry Pi (normalized):")
        for norm_name, orig_name in normalized_raspberry.items():
            print(f"  - {orig_name} -> {norm_name}")
        
        print("GitHub (normalized):")
        for norm_name, orig_name in normalized_github.items():
            print(f"  - {orig_name} -> {norm_name}")
        
        # Find missing folders (in GitHub but not in Raspberry Pi)
        missing_folders = []
        for github_norm, github_orig in normalized_github.items():
            if github_norm not in normalized_raspberry:
                missing_folders.append(github_orig)
                print(f"  Missing: {github_orig} (normalized: {github_norm})")
        
        if not missing_folders:
            print("  No missing folders found - both contain same bots")
        
        return missing_folders
    
    def step6_check_venv_and_update(self, missing_folders: List[str]) -> bool:
        """Step 6: Check for venv and update missing bots"""
        if not missing_folders:
            print("Step 6 - No missing folders, continuing to Step 7")
            return True
        
        print("Step 6 - Processing missing folders:")
        
        for folder in missing_folders:
            print(f"  Checking folder: {folder}")
            
            # Check if venv exists in the GitHub folder
            venv_exists = self.check_venv_in_github_folder(folder)
            
            if not venv_exists:
                print(f"    No venv found in {folder}, continuing to Step 7")
                continue
            
            print(f"    Venv found in {folder}, preparing to update...")
            
            # Prepare and run the update command
            success = self.run_update_command(folder)
            if success:
                print(f"    Successfully updated {folder}")
            else:
                print(f"    Failed to update {folder}")
        
        return True
    
    def check_venv_in_github_folder(self, folder_name: str) -> bool:
        """Check if venv directory exists in GitHub folder"""
        try:
            url = f"{self.github_api_base}/contents/{folder_name}"
            response = requests.get(url)
            response.raise_for_status()
            
            contents = response.json()
            
            for item in contents:
                if item['type'] == 'dir' and 'venv' in item['name'].lower():
                    return True
            
            return False
        except Exception as e:
            print(f"    Error checking venv for {folder_name}: {e}")
            return False
    
    def run_update_command(self, folder_name: str) -> bool:
        """Run the update command for a specific folder"""
        try:
            # Create the script URL - handle spaces in folder names
            script_folder = folder_name.replace(' ', '%20')
            script_url = f"{self.raw_content_base}/{script_folder}/{script_folder}.sh"
            
            # Alternative URL pattern if above doesn't work
            if ' ' in folder_name:
                # Try with hyphens instead of spaces
                hyphenated_name = folder_name.replace(' ', '-')
                script_url = f"{self.raw_content_base}/{folder_name}/{hyphenated_name}.sh"
            
            command = f'bash <(curl -s "{script_url}")'
            print(f"    Running command: {command}")
            
            # Execute the command
            result = subprocess.run(
                ['bash', '-c', command],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print(f"    Command executed successfully for {folder_name}")
                print(f"    Output: {result.stdout}")
                return True
            else:
                print(f"    Command failed for {folder_name}")
                print(f"    Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"    Command timed out for {folder_name}")
            return False
        except Exception as e:
            print(f"    Error running command for {folder_name}: {e}")
            return False
    
    def step7_main_scheduler(self):
        """Step 7: Main scheduler logic"""
        print("Step 7 - Main scheduler execution")
        print("All steps completed successfully!")
        
        # Add your main scheduler logic here
        # This is where you would implement the core functionality
        # of your scheduler after ensuring all bots are updated
        
        # Example: Run each bot's main script
        self.run_all_bots()
    
    def run_all_bots(self):
        """Run all available bots"""
        print("Running all available bots...")
        
        raspberry_folders = self.step3_get_raspberry_folders()
        
        for folder in raspberry_folders:
            print(f"Checking bot: {folder}")
            
            # Look for main Python files in the folder
            main_scripts = self.find_main_scripts(folder)
            
            for script in main_scripts:
                print(f"  Running script: {script}")
                self.run_python_script(folder, script)
    
    def find_main_scripts(self, folder_name: str) -> List[str]:
        """Find main Python scripts in a folder"""
        try:
            scripts = []
            folder_path = os.path.join(os.getcwd(), folder_name)
            
            if not os.path.exists(folder_path):
                return []
            
            for file in os.listdir(folder_path):
                if file.endswith('.py') and not file.startswith('__'):
                    # Check for common main script patterns
                    if any(pattern in file.lower() for pattern in ['main', 'bot', 'scheduler', 'run']):
                        scripts.append(file)
            
            # If no obvious main scripts found, return all Python files
            if not scripts:
                scripts = [f for f in os.listdir(folder_path) if f.endswith('.py') and not f.startswith('__')]
            
            return scripts
        except Exception as e:
            print(f"Error finding scripts in {folder_name}: {e}")
            return []
    
    def run_python_script(self, folder_name: str, script_name: str):
        """Run a Python script from a specific folder"""
        try:
            script_path = os.path.join(folder_name, script_name)
            
            if not os.path.exists(script_path):
                print(f"    Script not found: {script_path}")
                return
            
            # Run the Python script
            result = subprocess.run(
                ['python3', script_path],
                capture_output=True,
                text=True,
                cwd=folder_name,
                timeout=600  # 10 minute timeout per script
            )
            
            if result.returncode == 0:
                print(f"    Script {script_name} executed successfully")
                if result.stdout:
                    print(f"    Output: {result.stdout[:200]}...")  # First 200 chars
            else:
                print(f"    Script {script_name} failed")
                if result.stderr:
                    print(f"    Error: {result.stderr[:200]}...")  # First 200 chars
                    
        except subprocess.TimeoutExpired:
            print(f"    Script {script_name} timed out")
        except Exception as e:
            print(f"    Error running script {script_name}: {e}")
    
    def run_all_steps(self):
        """Execute all steps in sequence"""
        print("Starting Bot Manager Scheduler")
        print("=" * 50)
        
        # Step 3: Get Raspberry Pi folders
        raspberry_folders = self.step3_get_raspberry_folders()
        
        # Step 4: Get GitHub folders
        github_folders = self.step4_get_github_folders()
        
        if not github_folders:
            print("Error: Could not fetch GitHub folders. Check internet connection.")
            return
        
        # Step 5: Compare folders
        missing_folders = self.step5_compare_folders(raspberry_folders, github_folders)
        
        # Step 6: Check venv and update
        if missing_folders:
            print("Missing folders found, proceeding with Step 6...")
            self.step6_check_venv_and_update(missing_folders)
        else:
            print("No missing folders found, proceeding to Step 7...")
        
        # Step 7: Main scheduler
        self.step7_main_scheduler()
        
        print("=" * 50)
        print("Bot Manager Scheduler completed")

def main():
    """Main function"""
    bot_manager = BotManager()
    bot_manager.run_all_steps()

if __name__ == "__main__":
    main()
