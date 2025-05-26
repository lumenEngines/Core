"""Test version of main.py without API dependencies."""
import sys
import os
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt5.QtCore import Qt

# Initialize logging before importing other modules
from core.logger_config import setup_logging
setup_logging()

logger = logging.getLogger(__name__)

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lumen - Test Mode")
        self.setGeometry(100, 100, 400, 200)
        
        label = QLabel("Lumen is running!\n\nProject structure is working correctly.\n\nAPI modules require installation of dependencies.", self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 14px; padding: 20px;")
        self.setCentralWidget(label)

def main():
    logger.info("Starting Lumen in test mode...")
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    logger.info("GUI window opened successfully")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()