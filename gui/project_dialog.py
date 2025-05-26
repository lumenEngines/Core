from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, 
                             QLabel, QPushButton, QLineEdit, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from core.project_manager import project_manager

class ProjectDialog(QDialog):
    """
    Dialog for selecting and creating projects.
    
    This dialog allows users to select existing projects or create new ones.
    """
    
    # Signal emitted when a project is selected or created
    project_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """Initialize the project dialog."""
        super().__init__(parent)
        self.setWindowTitle("Select Project")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setFixedWidth(300)
        self.init_ui()
        
    def init_ui(self):
        """Set up the dialog UI components."""
        layout = QVBoxLayout()
        
        # Current project label
        current_project = project_manager.get_current_project()
        self.current_label = QLabel(f"Current Project: {current_project}")
        layout.addWidget(self.current_label)
        
        # Project selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Select:"))
        
        self.project_combo = QComboBox()
        self.update_project_list()
        self.project_combo.setCurrentText(current_project)
        selector_layout.addWidget(self.project_combo, 1)
        
        # Select button
        select_button = QPushButton("Select")
        select_button.clicked.connect(self.select_project)
        selector_layout.addWidget(select_button)
        
        layout.addLayout(selector_layout)
        
        # New project section
        new_layout = QHBoxLayout()
        new_layout.addWidget(QLabel("New:"))
        
        self.new_project_input = QLineEdit()
        self.new_project_input.setPlaceholderText("Enter new project name")
        new_layout.addWidget(self.new_project_input, 1)
        
        # Create button
        create_button = QPushButton("Create")
        create_button.clicked.connect(self.create_project)
        new_layout.addWidget(create_button)
        
        layout.addLayout(new_layout)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
    
    def update_project_list(self):
        """Update the project dropdown with current projects."""
        self.project_combo.clear()
        projects = project_manager.get_project_list(sort_by_recent=True)
        for project in projects:
            self.project_combo.addItem(project)
    
    def select_project(self):
        """Select the chosen project."""
        project_name = self.project_combo.currentText()
        if project_name:
            success = project_manager.select_project(project_name)
            if success:
                self.current_label.setText(f"Current Project: {project_name}")
                self.project_selected.emit(project_name)
                self.close()
    
    def create_project(self):
        """Create a new project."""
        project_name = self.new_project_input.text().strip()
        if not project_name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid project name.")
            return
        
        # Validate project name (alphanumeric with underscores and dashes)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', project_name):
            QMessageBox.warning(self, "Invalid Name", 
                               "Project name can only contain letters, numbers, underscores, and dashes.")
            return
        
        success = project_manager.create_project(project_name)
        if success:
            self.update_project_list()
            self.project_combo.setCurrentText(project_name)
            self.select_project()
        else:
            QMessageBox.warning(self, "Project Exists", 
                               f"A project named '{project_name}' already exists.")