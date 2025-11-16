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
            
            # Sort folders alphabetically
            folders.sort()
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
            
            # Sort folders alphabetically
            folders.sort()
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
        for norm_name, orig_name in sorted(normalized_raspberry.items()):
            print(f"  - {orig_name} -> {norm_name}")
        
        print("GitHub BOTS (normalized):")
        for norm_name, orig_name in sorted(normalized_github.items()):
            print(f"  - {orig_name} -> {norm_name}")
        
        # Find missing bot folders (in GitHub but not in Raspberry Pi)
        missing_bots = []
        for github_norm, github_orig in sorted(normalized_github.items()):
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
        
        for folder in sorted(missing_folders):
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
            
            # Execute the command with live output
            result = subprocess.run(
                ['bash', '-c', command],
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print(f"    ✅ venv.sh executed successfully for {folder_name}")
                return True
            else:
                print(f"    ❌ venv.sh failed for {folder_name} (return code: {result.returncode})")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"    ⏰ Command timed out for {folder_name}")
            return False
        except Exception as e:
            print(f"    ❌ Error running venv.sh for {folder_name}: {e}")
            return False
    
    def check_and_setup_missing_venvs(self):
        """Check each bot for missing venv and setup if needed"""
        print("Checking for missing venv folders in existing bots...")
        
        current_dir = os.getcwd()
        parent_dir = os.path.dirname(current_dir)
        raspberry_folders = self.step3_get_raspberry_folders()
        
        bots_needing_venv = []
        
        for folder in sorted(raspberry_folders):
            if not self.is_bot_folder(folder):
                continue
                
            folder_path = os.path.join(parent_dir, folder)
            venv_path = os.path.join(folder_path, 'venv')
            
            if not os.path.exists(venv_path):
                bots_needing_venv.append(folder)
                print(f"  ❌ {folder} - venv folder missing")
            else:
                print(f"  ✅ {folder} - venv folder exists")
        
        # Setup missing venvs
        if bots_needing_venv:
            print(f"\nSetting up venv for {len(bots_needing_venv)} bot(s)...")
            for bot_folder in bots_needing_venv:
                print(f"\n  Setting up venv for: {bot_folder}")
                success = self.run_bot_setup_command(bot_folder)
                if success:
                    print(f"    ✅ Successfully set up venv for {bot_folder}")
                else:
                    print(f"    ❌ Failed to set up venv for {bot_folder}")
        else:
            print("\nAll bots have venv folders - no setup needed")
        
        return len(bots_needing_venv) == 0
    
    def run_bot_setup_command(self, folder_name: str) -> bool:
        """Run the setup command for a bot that's missing venv - with LIVE output"""
        try:
            # Map folder names to their setup script names
            setup_scripts = {
                'facebook birthday wisher': 'facebook birthday wisher.sh',
                'facebook profile liker': 'facebook profile liker.sh', 
                'whatsapp birthday wisher': 'whatsapp birthday wisher.sh',
                'whatsapp messenger': 'whatsapp messenger.sh',
                'scheduler': 'scheduler.sh'
            }
            
            # Get the GitHub folder name (with hyphens)
            github_folder_name = folder_name.replace(' ', '-')
            setup_script_name = setup_scripts.get(folder_name, f"{folder_name}.sh")
            
            # URL encode spaces in the script name
            encoded_script_name = setup_script_name.replace(' ', '%20')
            
            # Create the command URL
            command_url = f"{self.raw_content_base}/{github_folder_name}/{encoded_script_name}"
            
            command = f'bash <(curl -s "{command_url}")'
            print(f"    Running command: {command}")
            print("    " + "=" * 50)
            
            # Execute the command with LIVE output (no capture)
            result = subprocess.run(
                ['bash', '-c', command],
                timeout=600  # 10 minute timeout for setup
            )
            
            print("    " + "=" * 50)
            if result.returncode == 0:
                print(f"    ✅ Setup completed successfully for {folder_name}")
                return True
            else:
                print(f"    ❌ Setup failed for {folder_name} (return code: {result.returncode})")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"    ⏰ Setup command timed out for {folder_name}")
            return False
        except Exception as e:
            print(f"    ❌ Error running setup command for {folder_name}: {e}")
            return False
    
    def step7_main_scheduler(self):
        """Step 7: Main scheduler logic"""
        print("Step 7 - Main scheduler execution")
        print("All bots are synchronized and ready!")
        
        # Final status check
        print("\nFinal Bot Status:")
        current_dir = os.getcwd()
        parent_dir = os.path.dirname(current_dir)
        raspberry_folders = self.step3_get_raspberry_folders()
        
        ready_bots = 0
        for folder in sorted(raspberry_folders):
            if not self.is_bot_folder(folder):
                continue
                
            folder_path = os.path.join(parent_dir, folder)
            venv_path = os.path.join(folder_path, 'venv')
            
            if os.path.exists(venv_path):
                print(f"  ✅ {folder} - Ready with venv")
                ready_bots += 1
            else:
                print(f"  ❌ {folder} - Missing venv")
        
        print(f"\nTotal bots ready: {ready_bots}")
    
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
        
        # Step 6: Check venv.sh and update missing bots
        if missing_folders:
            print("Missing bots found, proceeding with Step 6...")
            self.step6_check_venv_and_update(missing_folders)
        else:
            print("No missing bots found, proceeding to Step 7...")
        
        # NEW: Check and setup missing venvs for existing bots
        print("\n" + "=" * 50)
        all_venvs_ready = self.check_and_setup_missing_venvs()
        
        # Step 7: Main scheduler
        print("\n" + "=" * 50)
        self.step7_main_scheduler()
        
        print("=" * 50)
        print("Bot Manager Scheduler completed")

def main():
    """Main function"""
    bot_manager = BotManager()
    bot_manager.run_all_steps()

if __name__ == "__main__":
    main()
