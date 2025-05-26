from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLabel, QDoubleSpinBox, QPushButton, QGroupBox, QCheckBox)
from PyQt5.QtCore import Qt
from core.settings import settings

class SettingsDialog(QDialog):
    """
    Dialog for configuring application settings.
    
    This dialog allows users to configure timeout durations and other settings
    for the clipboard functionality.
    """
    
    def __init__(self, parent=None):
        """Initialize the settings dialog."""
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Set up the dialog UI components."""
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        
        # Main layout
        layout = QVBoxLayout()
        
        # Clipboard Settings group
        clipboard_group = QGroupBox("Clipboard Behavior")
        clipboard_layout = QFormLayout()
        
        # Short timeout spinner
        self.short_timeout_spinner = QDoubleSpinBox()
        self.short_timeout_spinner.setRange(0.2, 3.0)
        self.short_timeout_spinner.setSingleStep(0.1)
        self.short_timeout_spinner.setDecimals(1)
        self.short_timeout_spinner.setSuffix(" seconds")
        self.short_timeout_spinner.setValue(settings.short_timeout)
        clipboard_layout.addRow("Initial popup timeout:", self.short_timeout_spinner)
        
        # Extended timeout spinner
        self.extended_timeout_spinner = QDoubleSpinBox()
        self.extended_timeout_spinner.setRange(1.0, 3600.0)  # Allow up to 1 hour
        self.extended_timeout_spinner.setSingleStep(1.0)
        self.extended_timeout_spinner.setDecimals(0)
        self.extended_timeout_spinner.setSuffix(" seconds")
        self.extended_timeout_spinner.setValue(settings.extended_timeout)
        clipboard_layout.addRow("Extended popup timeout:", self.extended_timeout_spinner)
        
        # Check interval spinner
        self.check_interval_spinner = QDoubleSpinBox()
        self.check_interval_spinner.setRange(0.1, 2.0)
        self.check_interval_spinner.setSingleStep(0.1)
        self.check_interval_spinner.setDecimals(1)
        self.check_interval_spinner.setSuffix(" seconds")
        self.check_interval_spinner.setValue(settings.check_interval)
        clipboard_layout.addRow("Clipboard check interval:", self.check_interval_spinner)
        
        # Preserve clipboard checkbox
        self.preserve_clipboard_checkbox = QCheckBox("Preserve clipboard content when popup is dismissed")
        self.preserve_clipboard_checkbox.setChecked(settings.preserve_clipboard)
        clipboard_layout.addRow("", self.preserve_clipboard_checkbox)
        
        # Add help text
        help_text = QLabel(
            "Initial timeout: How long the popup appears after first clipboard copy\n"
            "Extended timeout: How long the popup remains after pressing copy again\n"
            "Check interval: How frequently the application checks for clipboard changes\n"
            "Preserve clipboard: Keep clipboard content after popup is closed (prevents auto-clearing)"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #666; font-size: 11px;")
        
        clipboard_group.setLayout(clipboard_layout)
        layout.addWidget(clipboard_group)
        layout.addWidget(help_text)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Save button
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def save_settings(self):
        """Save the settings and close the dialog."""
        # Save settings
        settings.short_timeout = self.short_timeout_spinner.value()
        settings.extended_timeout = self.extended_timeout_spinner.value()
        settings.check_interval = self.check_interval_spinner.value()
        settings.preserve_clipboard = self.preserve_clipboard_checkbox.isChecked()
        
        # Accept the dialog (closes it)
        self.accept()