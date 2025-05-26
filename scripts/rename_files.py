#!/usr/bin/env python3
"""
Script to rename files to PEP 8 snake_case convention and update imports.
"""

import os
import re
import shutil

# Mapping of old names to new names
FILE_RENAMES = {
    'ProjectDialog.py': 'project_dialog.py',
    'ProjectManagerDialog.py': 'project_manager_dialog.py',
    'ProjectManagerDialog_backup.py': 'project_manager_dialog_backup.py',
    'ScreenshotWorker.py': 'screenshot_worker.py',
    'SettingsDialog.py': 'settings_dialog.py',
    'TextWindow.py': 'text_window.py',
    'WebParser.py': 'web_parser.py',
}

# Import mappings (old import -> new import)
IMPORT_MAPPINGS = {
    'from ProjectDialog import': 'from project_dialog import',
    'from ProjectManagerDialog import': 'from project_manager_dialog import',
    'from ScreenshotWorker import': 'from screenshot_worker import',
    'from SettingsDialog import': 'from settings_dialog import',
    'from TextWindow import': 'from text_window import',
    'from WebParser import': 'from web_parser import',
    'import ProjectDialog': 'import project_dialog',
    'import ProjectManagerDialog': 'import project_manager_dialog',
    'import ScreenshotWorker': 'import screenshot_worker',
    'import SettingsDialog': 'import settings_dialog',
    'import TextWindow': 'import text_window',
    'import WebParser': 'import web_parser',
}

def update_imports_in_file(filepath):
    """Update imports in a single file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Update all imports
    for old_import, new_import in IMPORT_MAPPINGS.items():
        content = content.replace(old_import, new_import)
    
    # Only write if changed
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    """Rename files and update imports."""
    print("PEP 8 File Naming Convention Update")
    print("=" * 50)
    
    # First, update all imports in all Python files
    print("\nUpdating imports in all files...")
    updated_files = []
    
    for filename in os.listdir('.'):
        if filename.endswith('.py'):
            if update_imports_in_file(filename):
                updated_files.append(filename)
                print(f"  Updated imports in: {filename}")
    
    print(f"\nTotal files with updated imports: {len(updated_files)}")
    
    # Then rename the files
    print("\nRenaming files...")
    renamed_count = 0
    
    for old_name, new_name in FILE_RENAMES.items():
        if os.path.exists(old_name):
            shutil.move(old_name, new_name)
            print(f"  Renamed: {old_name} -> {new_name}")
            renamed_count += 1
        else:
            print(f"  Skipped: {old_name} (not found)")
    
    print(f"\nTotal files renamed: {renamed_count}")
    print("\nDone! Please test the application to ensure all imports work correctly.")

if __name__ == "__main__":
    main()