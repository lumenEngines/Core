#!/usr/bin/env python3
"""
Script to update print statements to logging calls in Python files.
This is a helper script for refactoring the codebase.
"""

import os
import re
import logging

# Mapping of print patterns to appropriate log levels
REPLACEMENTS = [
    # Error patterns
    (r'print\(f?"Error', 'logger.error('),
    (r'print\(f?"Failed', 'logger.error('),
    (r'print\(f?"Exception', 'logger.error('),
    
    # Warning patterns
    (r'print\(f?"Warning', 'logger.warning('),
    (r'print\(f?"Skipping', 'logger.warning('),
    
    # Info patterns
    (r'print\(f?"Success', 'logger.info('),
    (r'print\(f?"Completed', 'logger.info('),
    (r'print\(f?"Starting', 'logger.info('),
    (r'print\(f?"Loading', 'logger.info('),
    (r'print\(f?"Saving', 'logger.info('),
    
    # Debug patterns (default for most prints)
    (r'print\(', 'logger.debug('),
]

def update_file(filepath):
    """Update print statements in a single file."""
    logger_import = "logger = logging.getLogger(__name__)\n"
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Check if logging is already imported
    if 'import logging' not in content:
        # Add logging import after other imports
        import_match = re.search(r'(import .*\n)+', content)
        if import_match:
            pos = import_match.end()
            content = content[:pos] + "import logging\n" + content[pos:]
    
    # Check if logger is already defined
    if 'logger = logging.getLogger' not in content:
        # Add logger definition after imports
        class_match = re.search(r'\n\nclass ', content)
        func_match = re.search(r'\n\ndef ', content)
        
        if class_match and (not func_match or class_match.start() < func_match.start()):
            pos = class_match.start()
        elif func_match:
            pos = func_match.start()
        else:
            # Add at the end of imports
            import_match = re.search(r'(import .*\n)+', content)
            if import_match:
                pos = import_match.end()
            else:
                pos = 0
        
        content = content[:pos] + "\n" + logger_import + content[pos:]
    
    # Replace print statements
    for pattern, replacement in REPLACEMENTS:
        content = re.sub(pattern, replacement, content)
    
    # Only write if changed
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    """Update all Python files in the current directory."""
    updated_files = []
    
    for filename in os.listdir('.'):
        if filename.endswith('.py') and filename != 'update_logging.py':
            if update_file(filename):
                updated_files.append(filename)
                print(f"Updated: {filename}")
    
    print(f"\nTotal files updated: {len(updated_files)}")
    
if __name__ == "__main__":
    main()