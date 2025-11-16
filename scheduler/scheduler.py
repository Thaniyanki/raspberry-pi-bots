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
            parent_dir = os.path.dirname(current_dir)  # Go up one level to bots folder
            
            folders = []
            
            for item in os.listdir(parent_dir):
                item_path = os.path.join(parent_dir, item)
                if os.path.isdir(item_path):
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
    
    def is_bot_folder(self, folder_name: str) -> bool:
        """Check if a folder is actually a bot (exclude utility folders)"""
        non_bot_folders = [
            'all-in-one-venv',
            'venv',
            'env',
            'virtualenv',
            'tmp',
            'temp',
            'backup',
            'archive',
            'test',
            'tests',
            'docs',
            'documentation'
        ]
        
        normalized_name = self.normalize_folder_name(folder_name)
        return normalized_name not in [self.normalize_folder_name(nb) for nb in non_bot_folders]
    
    def step5_compare_folders(self, raspberry_folders: List[str], github_folders: List[str]) -> List[str]:
        """Step 5: Compare folders and find missing ones"""
        # Filter out non-bot folders
        raspberry_bots = [f for f in raspberry_folders if self.is_bot_folder(f)]
        github_bots = [f for f in github_folders if self.is_bot_folder(f)]
        
        # Normalize all folder names for comparison
        normalized_raspberry = {self.normalize_folder_name(folder): folder for folder in raspberry_bots}
        normalized_github = {self.normalize_folder_name(folder): folder for folder in github_bots}
        
        print("Step 5 - Comparing BOT folders:")
        print("Raspberry Pi BOTS (normalized):")
        for norm_name, orig_name in normalized_raspberry.items():
            print(f"  - {orig_name} -> {norm_name}")
        
        print("GitHub BOTS (normalized):")
        for norm_name, orig_name in normalized_github.items():
            print(f"  - {orig_name} -> {norm_name}")
        
        # Find missing bot folders (in GitHub but not in Raspberry Pi)
        missing_bots = []
        for github_norm, github_orig in normalized_github.items():
            if github_norm not in normalized_raspberry:
                missing_bots.append(github_orig)
                print(f"  Missing BOT: {github_orig} (normalized: {github_norm})")
        
        if not missing_bots:
            print("  No missing bots found - both contain same bots")
        
        return missing_bots
    
    def step6_check_venv_and_update(self, missing_folders: List[str]) -> bool:
        """Step 6: Check for venv.sh and update missing bots"""
        if not missing_folders:
            print("Step 6 - No missing bots, continuing to Step 7")
            return True
        
        print("Step 6 - Processing missing bots:")
        
        for folder in missing_folders:
            print(f"  Checking bot: {folder}")
            
            # Check if venv.sh exists in the GitHub folder
            venv_sh_exists = self.check_venv_sh_in_github_folder(folder)
            
            if not venv_sh_exists:
                print(f"    No venv.sh found in {folder}, continuing to Step 7")
                continue
            
            print(f"    venv.sh found in {folder}, preparing to update...")
            
            # Prepare and run the update command
            success = self.run_venv_sh_command(folder)
            if success:
                print(f"    Successfully created venv for {folder}")
            else:
                print(f"    Failed to create venv for {folder}")
        
        return True
    
    def check_venv_sh_in_github_folder(self, folder_name: str) -> bool:
        """Check if venv.sh file exists in GitHub folder"""
        try:
            url = f"{self.github_api_base}/contents/{folder_name}"
            response = requests.get(url)
            response.raise_for_status()
            
            contents = response.json()
            
            for item in contents:
                if item['type'] == 'file' and item['name'].lower() == 'venv.sh':
                    return True
            
            return False
        except Exception as e:
            print(f"    Error checking venv.sh for {folder_name}: {e}")
            return False
    
    def run_venv_sh_command(self, folder_name: str) -> bool:
        """Run the venv.sh command for a specific folder"""
        try:
            # Create the venv.sh URL
            venv_sh_url = f"{self.raw_content_base}/{folder_name}/venv.sh"
            
            command = f'bash <(curl -s "{venv_sh_url}")'
            print(f"    Running command: {command}")
            
            # Execute the command
            result = subprocess.run(
                ['bash', '-c', command],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print(f"    venv.sh executed successfully for {folder_name}")
                print(f"    Output: {result.stdout}")
                return True
            else:
                print(f"    venv.sh failed for {folder_name}")
                print(f"    Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"    Command timed out for {folder_name}")
            return False
        except Exception as e:
            print(f"    Error running venv.sh for {folder_name}: {e}")
            return False
    
    def step7_main_scheduler(self):
        """Step 7: Main scheduler logic"""
        print("Step 7 - Main scheduler execution")
        print("All steps completed successfully!")
        
        # Run all available bots
        self.run_all_bots()
    
    def find_main_scripts(self, folder_name: str) -> List[str]:
        """Find main Python scripts in a folder with improved detection"""
        try:
            current_dir = os.getcwd()
            parent_dir = os.path.dirname(current_dir)
            folder_path = os.path.join(parent_dir, folder_name)
            
            if not os.path.exists(folder_path):
                return []
            
            all_python_files = [f for f in os.listdir(folder_path) if f.endswith('.py') and not f.startswith('__')]
            
            if not all_python_files:
                return []
            
            # Priority 1: Look for obvious main files
            main_files = []
            for file in all_python_files:
                lower_file = file.lower()
                if any(pattern in lower_file for pattern in ['main', 'bot', 'scheduler', 'run', 'app', 'start']):
                    main_files.append(file)
            
            if main_files:
                return main_files
            
            # Priority 2: If no obvious main files, check file content for main function
            for file in all_python_files:
                try:
                    file_path = os.path.join(folder_path, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'if __name__ == "__main__"' in content or 'def main()' in content:
                            main_files.append(file)
                except:
                    continue
            
            if main_files:
                return main_files
            
            # Priority 3: Return all Python files if no main detected
            return all_python_files[:1]  # Return first Python file only
            
        except Exception as e:
            print(f"Error finding scripts in {folder_name}: {e}")
            return []
    
    def run_all_bots(self):
        """Run all available bots with improved detection"""
        print("Running all available bots...")
        
        raspberry_folders = self.step3_get_raspberry_folders()
        
        for folder in raspberry_folders:
            # Skip non-bot folders
            if not self.is_bot_folder(folder):
                print(f"\nSkipping non-bot folder: {folder}")
                continue
                
            print(f"\nChecking bot: {folder}")
            
            # Look for main Python files in the folder
            main_scripts = self.find_main_scripts(folder)
            
            if not main_scripts:
                print(f"  No Python scripts found in {folder}")
                continue
                
            for script in main_scripts:
                print(f"  Running script: {script}")
                self.run_python_script(folder, script)
    
    def run_python_script(self, folder_name: str, script_name: str):
        """Run a Python script from a specific folder"""
        try:
            current_dir = os.getcwd()
            parent_dir = os.path.dirname(current_dir)
            folder_path = os.path.join(parent_dir, folder_name)
            script_path = os.path.join(folder_path, script_name)
            
            if not os.path.exists(script_path):
                print(f"    Script not found: {script_path}")
                return
            
            # Check if venv exists in the folder
            venv_path = os.path.join(folder_path, 'venv')
            python_cmd = 'python3'
            
            if os.path.exists(venv_path):
                python_cmd = os.path.join(venv_path, 'bin', 'python3')
                print(f"    Using venv Python: {python_cmd}")
            else:
                print(f"    Using system Python")
            
            # Run the Python script
            result = subprocess.run(
                [python_cmd, script_name],
                capture_output=True,
                text=True,
                cwd=folder_path,
                timeout=600  # 10 minute timeout per script
            )
            
            if result.returncode == 0:
                print(f"    ✅ Script {script_name} executed successfully")
                if result.stdout.strip():
                    print(f"    Output: {result.stdout.strip()}")
            else:
                print(f"    ❌ Script {script_name} failed")
                if result.stderr.strip():
                    print(f"    Error: {result.stderr.strip()}")
                    
        except subprocess.TimeoutExpired:
            print(f"    ⏰ Script {script_name} timed out")
        except Exception as e:
            print(f"    ❌ Error running script {script_name}: {e}")
    
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
        
        # Step 6: Check venv.sh and update
        if missing_folders:
            print("Missing bots found, proceeding with Step 6...")
            self.step6_check_venv_and_update(missing_folders)
        else:
            print("No missing bots found, proceeding to Step 7...")
        
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
