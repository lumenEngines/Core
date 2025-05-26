"""
Git-style diff viewer widget for reviewing and applying AI-proposed file changes.
"""

import os
import difflib
from typing import List, Tuple, Optional, Dict
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QTextEdit, QLabel, QSplitter, QFrame, QScrollArea,
                           QCheckBox, QComboBox, QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt5.QtGui import QFont, QColor, QPalette, QTextCharFormat, QTextCursor, QSyntaxHighlighter, QTextDocument


class DiffLine:
    """Represents a single line in a diff."""
    
    def __init__(self, line_type: str, content: str, old_line_num: Optional[int] = None, 
                 new_line_num: Optional[int] = None):
        self.line_type = line_type  # 'added', 'removed', 'unchanged', 'context'
        self.content = content
        self.old_line_num = old_line_num
        self.new_line_num = new_line_num
        self.selected = True  # Whether this change should be applied


class DiffHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for diff content."""
    
    def __init__(self, parent: QTextDocument):
        super().__init__(parent)
        
        # Define diff colors for dark theme
        self.added_format = QTextCharFormat()
        self.added_format.setBackground(QColor(40, 80, 40))   # Dark green background
        self.added_format.setForeground(QColor(150, 255, 150))  # Light green text
        
        self.removed_format = QTextCharFormat()
        self.removed_format.setBackground(QColor(80, 40, 40))   # Dark red background
        self.removed_format.setForeground(QColor(255, 150, 150))  # Light red text
        
        self.context_format = QTextCharFormat()
        self.context_format.setForeground(QColor(180, 180, 180))  # Light gray
        
        self.line_number_format = QTextCharFormat()
        self.line_number_format.setForeground(QColor(100, 150, 255))  # Light blue
        
    def highlightBlock(self, text: str):
        """Highlight a block of diff text."""
        if not text:
            return
            
        # Line numbers at start
        if text.startswith('@@'):
            self.setFormat(0, len(text), self.line_number_format)
        elif text.startswith('+') and not text.startswith('+++'):
            self.setFormat(0, len(text), self.added_format)
        elif text.startswith('-') and not text.startswith('---'):
            self.setFormat(0, len(text), self.removed_format)
        elif text.startswith(' '):
            self.setFormat(0, len(text), self.context_format)


class DiffGeneratorWorker(QThread):
    """Worker thread for generating AI-proposed diffs."""
    
    diff_ready = pyqtSignal(str, str, str)  # original_content, modified_content, diff_text
    diff_error = pyqtSignal(str)
    
    def __init__(self, file_path: str, original_content: str, modification_request: str):
        super().__init__()
        self.file_path = file_path
        self.original_content = original_content
        self.modification_request = modification_request
    
    def run(self):
        """Generate diff using AI API."""
        try:
            # Import the dedicated diff API (thread-safe)
            from diff_anthropic_api import diff_anthropic_api
            
            if not diff_anthropic_api.client:
                self.diff_error.emit("Anthropic API not available")
                return
            
            # Create prompt for file modification
            prompt = f"""I need you to modify this file according to the request. Return ONLY the complete modified file content, no explanations.

File: {self.file_path}

Original content:
```
{self.original_content}
```

Modification request: {self.modification_request}

Return the complete modified file content:"""

            # Get AI response
            modified_content = diff_anthropic_api.send_message(prompt)
            
            # Debug: Print response info
            print(f"AI Response length: {len(modified_content) if modified_content else 0}")
            print(f"AI Response preview: {modified_content[:200] if modified_content else 'None'}...")
            
            if not modified_content or not modified_content.strip():
                self.diff_error.emit("AI did not return modified content")
                return
            
            # Clean up the response (remove any remaining markdown if present)
            modified_content = modified_content.strip()
            if modified_content.startswith('```'):
                # Remove markdown code blocks if somehow still present
                lines = modified_content.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                modified_content = '\n'.join(lines)
            
            # Generate unified diff
            diff_lines = list(difflib.unified_diff(
                self.original_content.splitlines(keepends=True),
                modified_content.splitlines(keepends=True),
                fromfile=f"a/{os.path.basename(self.file_path)}",
                tofile=f"b/{os.path.basename(self.file_path)}",
                lineterm=''
            ))
            
            diff_text = ''.join(diff_lines)
            
            self.diff_ready.emit(self.original_content, modified_content, diff_text)
            
        except Exception as e:
            self.diff_error.emit(f"Error generating diff: {str(e)}")


class DiffViewerWidget(QWidget):
    """Git-style diff viewer with accept/deny functionality."""
    
    file_modified = pyqtSignal(str, str)  # file_path, new_content
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = ""
        self.original_content = ""
        self.modified_content = ""
        self.diff_lines = []
        self.is_expanded = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the diff viewer UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with controls
        self.header = self.create_header()
        layout.addWidget(self.header)
        
        # Diff content (initially hidden)
        self.content_frame = QFrame()
        self.content_frame.setVisible(False)
        self.content_frame.setStyleSheet("""
            QFrame { 
                background-color: #1e1e1e; 
                border: 1px solid #3c3c3c; 
            }
        """)
        
        content_layout = QVBoxLayout(self.content_frame)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        self.accept_btn = QPushButton("Accept")
        self.accept_btn.setStyleSheet("""
            QPushButton { 
                background-color: #3c3c3c; 
                color: #d4d4d4; 
                font-size: 11px;
                padding: 4px 8px; 
                border: 1px solid #555555;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #484848;
                border-color: #666666;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        self.accept_btn.clicked.connect(self.accept_changes)
        
        self.deny_btn = QPushButton("Deny")
        self.deny_btn.setStyleSheet("""
            QPushButton { 
                background-color: #3c3c3c; 
                color: #d4d4d4; 
                font-size: 11px;
                padding: 4px 8px; 
                border: 1px solid #555555;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #484848;
                border-color: #666666;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        self.deny_btn.clicked.connect(self.deny_changes)
        
        self.feedback_btn = QPushButton("Request Changes")
        self.feedback_btn.setStyleSheet("""
            QPushButton { 
                background-color: #3c3c3c; 
                color: #d4d4d4; 
                font-size: 11px;
                padding: 4px 8px; 
                border: 1px solid #555555;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #484848;
                border-color: #666666;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        self.feedback_btn.clicked.connect(self.request_changes)
        
        actions_layout.addWidget(self.accept_btn)
        actions_layout.addWidget(self.deny_btn)
        actions_layout.addWidget(self.feedback_btn)
        actions_layout.addStretch()
        
        content_layout.addLayout(actions_layout)
        
        # Progress bar for AI processing
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2d2d2d;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                text-align: center;
                color: #d4d4d4;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
        content_layout.addWidget(self.progress_bar)
        
        # Diff display
        self.diff_display = QTextEdit()
        self.diff_display.setFont(QFont("Consolas", 10))
        self.diff_display.setReadOnly(True)
        self.diff_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                padding: 8px;
                selection-background-color: #264f78;
            }
        """)
        
        # Add syntax highlighting
        self.highlighter = DiffHighlighter(self.diff_display.document())
        
        content_layout.addWidget(self.diff_display)
        
        layout.addWidget(self.content_frame)
        
    def create_header(self):
        """Create the header with toggle and status."""
        header = QFrame()
        header.setStyleSheet("""
            QFrame { 
                background-color: #2d2d2d; 
                border: 1px solid #3c3c3c; 
                padding: 8px; 
            }
        """)
        header.setMaximumHeight(50)
        
        layout = QHBoxLayout(header)
        
        # Toggle button
        self.toggle_btn = QPushButton("▶ Diff Editor")
        self.toggle_btn.setFlat(True)
        self.toggle_btn.setStyleSheet("""
            QPushButton { 
                font-weight: bold; 
                text-align: left; 
                color: #d4d4d4;
                border: none;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #3c3c3c;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_expansion)
        
        # Status label
        self.status_label = QLabel("Ready for file modifications")
        self.status_label.setStyleSheet("QLabel { color: #888888; font-style: italic; }")
        
        layout.addWidget(self.toggle_btn)
        layout.addWidget(self.status_label)
        layout.addStretch()
        
        return header
        
    def toggle_expansion(self):
        """Toggle the diff viewer expansion."""
        self.is_expanded = not self.is_expanded
        self.content_frame.setVisible(self.is_expanded)
        
        if self.is_expanded:
            self.toggle_btn.setText("▼ Diff Editor")
            self.status_label.setText("Diff viewer expanded")
        else:
            self.toggle_btn.setText("▶ Diff Editor")
            self.status_label.setText("Ready for file modifications")
            
    def generate_diff(self, file_path: str, modification_request: str):
        """Generate a diff for the specified file modification."""
        self.file_path = file_path
        
        # Read original file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.original_content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not read file: {str(e)}")
            return
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_label.setText("Generating AI modifications...")
        
        # Disable buttons during processing
        self.accept_btn.setEnabled(False)
        self.deny_btn.setEnabled(False)
        self.feedback_btn.setEnabled(False)
        
        # Expand if not already
        if not self.is_expanded:
            self.toggle_expansion()
        
        # Start AI diff generation
        self.diff_worker = DiffGeneratorWorker(file_path, self.original_content, modification_request)
        self.diff_worker.diff_ready.connect(self.on_diff_ready)
        self.diff_worker.diff_error.connect(self.on_diff_error)
        self.diff_worker.start()
        
    def on_diff_ready(self, original_content: str, modified_content: str, diff_text: str):
        """Handle successful diff generation."""
        self.original_content = original_content
        self.modified_content = modified_content
        
        # Hide progress
        self.progress_bar.setVisible(False)
        
        # Enable buttons
        self.accept_btn.setEnabled(True)
        self.deny_btn.setEnabled(True)
        self.feedback_btn.setEnabled(True)
        
        # Display diff
        if diff_text.strip():
            self.diff_display.setPlainText(diff_text)
            self.status_label.setText(f"Diff ready for {os.path.basename(self.file_path)}")
        else:
            self.diff_display.setPlainText("No changes detected in the AI response.")
            self.status_label.setText("No modifications needed")
            
    def on_diff_error(self, error_message: str):
        """Handle diff generation error."""
        self.progress_bar.setVisible(False)
        self.accept_btn.setEnabled(True)
        self.deny_btn.setEnabled(True)
        self.feedback_btn.setEnabled(True)
        
        self.status_label.setText("Error generating diff")
        self.diff_display.setPlainText(f"Error: {error_message}")
        
    def accept_changes(self):
        """Accept and apply the changes to the file."""
        if not self.modified_content or not self.file_path:
            QMessageBox.warning(self, "Error", "No changes to apply")
            return
            
        reply = QMessageBox.question(
            self, 
            "Apply Changes",
            f"Are you sure you want to apply these changes to {os.path.basename(self.file_path)}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Write modified content to file
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    f.write(self.modified_content)
                
                self.status_label.setText("✓ Changes applied successfully")
                self.file_modified.emit(self.file_path, self.modified_content)
                
                # Clear the diff after a delay
                QTimer.singleShot(2000, self.clear_diff)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to apply changes: {str(e)}")
                
    def deny_changes(self):
        """Deny the changes and clear the diff."""
        self.status_label.setText("Changes denied")
        QTimer.singleShot(1000, self.clear_diff)
        
    def request_changes(self):
        """Request modifications to the proposed changes."""
        # For now, just clear and allow new request
        # In future, could open a dialog for feedback
        self.status_label.setText("Request new modifications")
        QTimer.singleShot(1000, self.clear_diff)
        
    def clear_diff(self):
        """Clear the current diff display."""
        self.diff_display.clear()
        self.file_path = ""
        self.original_content = ""
        self.modified_content = ""
        self.status_label.setText("Ready for file modifications")
        
        # Collapse the viewer
        if self.is_expanded:
            self.toggle_expansion()