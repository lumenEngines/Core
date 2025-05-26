#!/usr/bin/env python3
"""Test script to run ProjectManagerDialog independently"""

import sys
from PyQt5.QtWidgets import QApplication
from project_manager_dialog import ProjectManagerDialog

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create and show the dialog
    dialog = ProjectManagerDialog()
    dialog.show()
    
    # Run the application
    sys.exit(app.exec_())