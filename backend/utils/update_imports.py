"""
Import Update Script for Reorganized Project Structure
This script updates all imports to work with the new directory structure
"""
import os
import re
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent

# Import mappings: old import -> new import
IMPORT_MAPPINGS = {
    # Core module imports
    r'^from process_video import': 'from core.process_video import',
    r'^from database import': 'from core.database import',
    r'^from auth import': 'from core.auth import',
    r'^from notifications import': 'from core.notifications import',
    r'^import config': 'from core import config',
    r'^from config import': 'from core.config import',
    r'^from credentials import': 'from core.credentials import',
    r'^from paths import': 'from core.paths import',
    r'^from india_utils import': 'from core.india_utils import',
    
    # Standalone imports
    r'^import process_video': 'from core import process_video',
    r'^import database': 'from core import database',
    r'^import auth': 'from core import auth',
    r'^import notifications': 'from core import notifications',
    r'^import credentials': 'from core import credentials',
    r'^import paths': 'from core import paths',
    r'^import india_utils': 'from core import india_utils',
}

# File path mappings for string literals
PATH_MAPPINGS = {
    r'"client/': '"frontend/',
    r"'client/": "'frontend/",
    r'directory="client"': 'directory="frontend"',
    r"directory='client'": "directory='frontend'",
    r'"schema.sql"': '"database/schema.sql"',
    r"'schema.sql'": "'database/schema.sql'",
}

def update_imports_in_file(file_path):
    """Update imports in a single file"""
    print(f"Updating: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    lines = content.split('\n')
    updated_lines = []
    
    for line in lines:
        updated_line = line
        
        # Update imports
        for old_pattern, new_import in IMPORT_MAPPINGS.items():
            if re.match(old_pattern, line.strip()):
                # Replace the matched part
                updated_line = re.sub(old_pattern, new_import, updated_line)
                break
        
        # Update path strings
        for old_path, new_path in PATH_MAPPINGS.items():
            updated_line = re.sub(old_path, new_path, updated_line)
        
        updated_lines.append(updated_line)
    
    new_content = '\n'.join(updated_lines)
    
    if new_content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  ✅ Updated {file_path.name}")
        return True
    else:
        print(f"  ⏭️  No changes needed for {file_path.name}")
        return False

def main():
    print("=" * 70)
    print("  UPDATING IMPORTS FOR REORGANIZED PROJECT STRUCTURE")
    print("=" * 70)
    print()
    
    # Files to update in core/
    core_files = [
        PROJECT_ROOT / 'core' / 'app.py',
        PROJECT_ROOT / 'core' / 'process_video.py',
        PROJECT_ROOT / 'core' / 'auth.py',
        PROJECT_ROOT / 'core' / 'database.py',
        PROJECT_ROOT / 'core' / 'notifications.py',
        PROJECT_ROOT / 'core' / 'config.py',
        PROJECT_ROOT / 'core' / 'credentials.py',
        PROJECT_ROOT / 'core' / 'paths.py',
    ]
    
    # Files to update in database/
    database_files = [
        PROJECT_ROOT / 'database' / 'init_database.py',
        PROJECT_ROOT / 'database' / 'create_user.py',
        PROJECT_ROOT / 'database' / 'update_schema.py',
    ]
    
    # Files to update in tests/
    test_files = [
        PROJECT_ROOT / 'tests' / 'test_analysis.py',
        PROJECT_ROOT / 'tests' / 'test_email.py',
        PROJECT_ROOT / 'tests' / 'test_login.py',
        PROJECT_ROOT / 'tests' / 'test_welcome_email.py',
    ]
    
    all_files = core_files + database_files + test_files
    updated_count = 0
    
    for file_path in all_files:
        if file_path.exists():
            if update_imports_in_file(file_path):
                updated_count += 1
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print()
    print("=" * 70)
    print(f"  SUMMARY: Updated {updated_count} files")
    print("=" * 70)

if __name__ == "__main__":
    main()
