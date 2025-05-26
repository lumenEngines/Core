#!/usr/bin/env python3
# debug.py - A simple debugging script for PyQt

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Debug Window")
        self.setGeometry(100, 100, 400, 300)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add a label
        label = QLabel("If you can see this window, PyQt is working correctly!")
        layout.addWidget(label)
        
        # Add a button
        button = QPushButton("Click Me")
        button.clicked.connect(self.on_button_click)
        layout.addWidget(button)
    
    def on_button_click(self):
        print("Button clicked!")

def main():
    print("Starting debug app...")
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    print("Window shown, entering app.exec_...")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()