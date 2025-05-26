import os
import sys
import json
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTreeWidget, QTreeWidgetItem, QLabel, QFileDialog,
                             QMessageBox, QLineEdit, QTextEdit, QComboBox,
                             QWidget, QSplitter, QProgressBar, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QSyntaxHighlighter, QTextCharFormat, QColor
from core.project_linker import project_linker
from utils.file_summarizer import project_summarizer
from utils.file_dependency_analyzer import file_dependency_analyzer
from .dependency_graph_widget import DependencyGraphWidget
import time
import re

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_for_filename, TextLexer
    from pygments.formatters import HtmlFormatter
    from pygments.styles import get_style_by_name
    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False


class BasicSyntaxHighlighter(QSyntaxHighlighter):
    """Basic syntax highlighter for when Pygments is not available."""
    
    def __init__(self, document, file_extension):
        super().__init__(document)
        self.file_extension = file_extension
        
        # Define color scheme
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor(86, 156, 214))  # Blue
        self.keyword_format.setFontWeight(QFont.Bold)
        
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor(206, 145, 120))  # Orange
        
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor(106, 153, 85))  # Green
        self.comment_format.setFontItalic(True)
        
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor(220, 220, 170))  # Yellow
        
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor(181, 206, 168))  # Light green
        
        # Define patterns based on file type
        self.highlighting_rules = []
        
        if file_extension in ['.py', '.pyw']:
            self.setup_python_rules()
        elif file_extension in ['.js', '.jsx', '.ts', '.tsx']:
            self.setup_javascript_rules()
        elif file_extension in ['.java']:
            self.setup_java_rules()
        elif file_extension in ['.cpp', '.cc', '.cxx', '.c', '.h', '.hpp']:
            self.setup_cpp_rules()
        elif file_extension in ['.css', '.scss', '.sass']:
            self.setup_css_rules()
        elif file_extension in ['.html', '.htm', '.xml']:
            self.setup_html_rules()
        elif file_extension in ['.json']:
            self.setup_json_rules()
        else:
            self.setup_generic_rules()
    
    def setup_python_rules(self):
        """Setup highlighting rules for Python."""
        # Python keywords
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
            'from', 'global', 'if', 'import', 'in', 'is', 'lambda',
            'None', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
            'True', 'try', 'while', 'with', 'yield', 'async', 'await'
        ]
        
        for keyword in keywords:
            pattern = r'\b' + keyword + r'\b'
            self.highlighting_rules.append((re.compile(pattern), self.keyword_format))
        
        # Python strings
        self.highlighting_rules.extend([
            (re.compile(r'\"\"\".*?\"\"\"', re.DOTALL), self.string_format),
            (re.compile(r"'''.*?'''", re.DOTALL), self.string_format),
            (re.compile(r'"[^"\\\\]*(\\\\.[^"\\\\]*)*"'), self.string_format),
            (re.compile(r"'[^'\\\\]*(\\\\.[^'\\\\]*)*'"), self.string_format),
        ])
        
        # Python comments
        self.highlighting_rules.append((re.compile(r'#[^\n]*'), self.comment_format))
        
        # Python functions
        self.highlighting_rules.append((re.compile(r'\bdef\s+(\w+)'), self.function_format))
        self.highlighting_rules.append((re.compile(r'\bclass\s+(\w+)'), self.function_format))
        
        # Numbers
        self.highlighting_rules.append((re.compile(r'\b\d+\.?\d*\b'), self.number_format))
    
    def setup_javascript_rules(self):
        """Setup highlighting rules for JavaScript/TypeScript."""
        # JavaScript keywords
        keywords = [
            'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger',
            'default', 'delete', 'do', 'else', 'export', 'extends', 'finally',
            'for', 'function', 'if', 'import', 'in', 'instanceof', 'let', 'new',
            'return', 'super', 'switch', 'this', 'throw', 'try', 'typeof', 'var',
            'void', 'while', 'with', 'yield', 'async', 'await', 'of'
        ]
        
        for keyword in keywords:
            pattern = r'\b' + keyword + r'\b'
            self.highlighting_rules.append((re.compile(pattern), self.keyword_format))
        
        # JavaScript strings
        self.highlighting_rules.extend([
            (re.compile(r'"[^"\\\\]*(\\\\.[^"\\\\]*)*"'), self.string_format),
            (re.compile(r"'[^'\\\\]*(\\\\.[^'\\\\]*)*'"), self.string_format),
            (re.compile(r'`[^`]*`'), self.string_format),  # Template literals
        ])
        
        # JavaScript comments
        self.highlighting_rules.extend([
            (re.compile(r'//[^\n]*'), self.comment_format),
            (re.compile(r'/\\*.*?\\*/', re.DOTALL), self.comment_format),
        ])
        
        # Numbers
        self.highlighting_rules.append((re.compile(r'\b\d+\.?\d*\b'), self.number_format))
    
    def setup_java_rules(self):
        """Setup highlighting rules for Java."""
        # Java keywords
        keywords = [
            'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch',
            'char', 'class', 'const', 'continue', 'default', 'do', 'double',
            'else', 'enum', 'extends', 'final', 'finally', 'float', 'for',
            'goto', 'if', 'implements', 'import', 'instanceof', 'int', 'interface',
            'long', 'native', 'new', 'package', 'private', 'protected', 'public',
            'return', 'short', 'static', 'strictfp', 'super', 'switch', 'synchronized',
            'this', 'throw', 'throws', 'transient', 'try', 'void', 'volatile', 'while'
        ]
        
        for keyword in keywords:
            pattern = r'\b' + keyword + r'\b'
            self.highlighting_rules.append((re.compile(pattern), self.keyword_format))
        
        # Java strings
        self.highlighting_rules.extend([
            (re.compile(r'"[^"\\\\]*(\\\\.[^"\\\\]*)*"'), self.string_format),
            (re.compile(r"'[^'\\\\]*(\\\\.[^'\\\\]*)*'"), self.string_format),
        ])
        
        # Java comments
        self.highlighting_rules.extend([
            (re.compile(r'//[^\n]*'), self.comment_format),
            (re.compile(r'/\\*.*?\\*/', re.DOTALL), self.comment_format),
        ])
        
        # Numbers
        self.highlighting_rules.append((re.compile(r'\b\d+\.?\d*[fFlL]?\b'), self.number_format))
    
    def setup_cpp_rules(self):
        """Setup highlighting rules for C/C++."""
        # C++ keywords
        keywords = [
            'auto', 'break', 'case', 'char', 'const', 'continue', 'default',
            'do', 'double', 'else', 'enum', 'extern', 'float', 'for', 'goto',
            'if', 'int', 'long', 'register', 'return', 'short', 'signed',
            'sizeof', 'static', 'struct', 'switch', 'typedef', 'union',
            'unsigned', 'void', 'volatile', 'while', 'class', 'namespace',
            'template', 'this', 'using', 'virtual', 'private', 'public',
            'protected', 'friend', 'inline', 'delete', 'new', 'try', 'catch',
            'throw', 'const_cast', 'static_cast', 'dynamic_cast', 'reinterpret_cast'
        ]
        
        for keyword in keywords:
            pattern = r'\b' + keyword + r'\b'
            self.highlighting_rules.append((re.compile(pattern), self.keyword_format))
        
        # C++ strings
        self.highlighting_rules.extend([
            (re.compile(r'"[^"\\\\]*(\\\\.[^"\\\\]*)*"'), self.string_format),
            (re.compile(r"'[^'\\\\]*(\\\\.[^'\\\\]*)*'"), self.string_format),
        ])
        
        # C++ comments
        self.highlighting_rules.extend([
            (re.compile(r'//[^\n]*'), self.comment_format),
            (re.compile(r'/\\*.*?\\*/', re.DOTALL), self.comment_format),
        ])
        
        # Preprocessor directives
        preprocessor_format = QTextCharFormat()
        preprocessor_format.setForeground(QColor(155, 155, 155))
        self.highlighting_rules.append((re.compile(r'#\w+'), preprocessor_format))
        
        # Numbers
        self.highlighting_rules.append((re.compile(r'\b\d+\.?\d*[fFlL]?\b'), self.number_format))
    
    def setup_css_rules(self):
        """Setup highlighting rules for CSS."""
        # CSS selectors
        selector_format = QTextCharFormat()
        selector_format.setForeground(QColor(215, 186, 125))  # Gold
        self.highlighting_rules.append((re.compile(r'[.#]?\w+(?=[\\s{])'), selector_format))
        
        # CSS properties
        property_format = QTextCharFormat()
        property_format.setForeground(QColor(86, 156, 214))  # Blue
        self.highlighting_rules.append((re.compile(r'\w+(?=\s*:)'), property_format))
        
        # CSS values
        self.highlighting_rules.extend([
            (re.compile(r'"[^"]*"'), self.string_format),
            (re.compile(r"'[^']*'"), self.string_format),
        ])
        
        # CSS comments
        self.highlighting_rules.append((re.compile(r'/\\*.*?\\*/', re.DOTALL), self.comment_format))
        
        # Numbers and units
        self.highlighting_rules.append((re.compile(r'\b\d+\.?\d*(px|em|rem|%|vh|vw)?\b'), self.number_format))
    
    def setup_html_rules(self):
        """Setup highlighting rules for HTML/XML."""
        # HTML tags
        tag_format = QTextCharFormat()
        tag_format.setForeground(QColor(86, 156, 214))  # Blue
        self.highlighting_rules.append((re.compile(r'</?\\b[^>]+>'), tag_format))
        
        # HTML attributes
        attr_format = QTextCharFormat()
        attr_format.setForeground(QColor(156, 220, 254))  # Light blue
        self.highlighting_rules.append((re.compile(r'\w+(?==)'), attr_format))
        
        # Strings
        self.highlighting_rules.extend([
            (re.compile(r'"[^"]*"'), self.string_format),
            (re.compile(r"'[^']*'"), self.string_format),
        ])
        
        # HTML comments
        self.highlighting_rules.append((re.compile(r'<!--.*?-->', re.DOTALL), self.comment_format))
    
    def setup_json_rules(self):
        """Setup highlighting rules for JSON."""
        # JSON keys
        key_format = QTextCharFormat()
        key_format.setForeground(QColor(156, 220, 254))  # Light blue
        self.highlighting_rules.append((re.compile(r'"[^"]+"\s*(?=:)'), key_format))
        
        # JSON strings
        self.highlighting_rules.append((re.compile(r'"[^"]*"'), self.string_format))
        
        # JSON numbers
        self.highlighting_rules.append((re.compile(r'\b-?\d+\.?\d*([eE][+-]?\d+)?\b'), self.number_format))
        
        # JSON booleans and null
        self.highlighting_rules.extend([
            (re.compile(r'\btrue\b'), self.keyword_format),
            (re.compile(r'\bfalse\b'), self.keyword_format),
            (re.compile(r'\bnull\b'), self.keyword_format),
        ])
    
    def setup_generic_rules(self):
        """Setup generic highlighting rules."""
        # Generic strings
        self.highlighting_rules.extend([
            (re.compile(r'"[^"\\\\]*(\\\\.[^"\\\\]*)*"'), self.string_format),
            (re.compile(r"'[^'\\\\]*(\\\\.[^'\\\\]*)*'"), self.string_format),
        ])
        
        # Generic comments
        self.highlighting_rules.extend([
            (re.compile(r'#[^\n]*'), self.comment_format),  # Shell/Python style
            (re.compile(r'//[^\n]*'), self.comment_format),  # C++ style
            (re.compile(r'/\\*.*?\\*/', re.DOTALL), self.comment_format),  # C style
        ])
        
        # Numbers
        self.highlighting_rules.append((re.compile(r'\b\d+\.?\d*\b'), self.number_format))
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text."""
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), format)


class SingleFileSummarizationThread(QThread):
    """Thread for summarizing a single file."""
    
    file_summarized = pyqtSignal(str, dict)  # file_path, summary_data
    summarization_failed = pyqtSignal(str, str)  # file_path, error_message
    
    def __init__(self, file_path, api_preference='anthropic'):
        super().__init__()
        self.file_path = file_path
        self.api_preference = api_preference
    
    def run(self):
        try:
            summary_data = project_summarizer.file_summarizer.summarize_file(
                self.file_path, self.api_preference
            )
            
            if summary_data:
                self.file_summarized.emit(self.file_path, summary_data)
            else:
                self.summarization_failed.emit(self.file_path, "Failed to generate summary")
                
        except Exception as e:
            self.summarization_failed.emit(self.file_path, str(e))


class ProjectSummarizationThread(QThread):
    """Thread for summarizing project files without blocking UI."""
    
    progress_updated = pyqtSignal(int, str)  # progress percentage, status message
    file_summarized = pyqtSignal(str, dict)  # file_path, summary_data
    summarization_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, project_name, file_paths, api_preference='anthropic'):
        super().__init__()
        self.project_name = project_name
        self.file_paths = file_paths
        self.api_preference = api_preference
    
    def run(self):
        try:
            self.progress_updated.emit(5, "Starting file summarization...")
            
            
            self.progress_updated.emit(10, "Categorizing files...")
            
            # Categorize files for optimal processing
            categories = project_summarizer.file_summarizer.categorize_files_for_batching(self.file_paths)
            
            total_files = len(self.file_paths)
            processed_files = 0
            
            # Process each category with appropriate settings
            for category, files in categories.items():
                if not files:
                    continue
                
                self.progress_updated.emit(
                    int(20 + (processed_files / total_files) * 70), 
                    f"Processing {category} files: {len(files)} files"
                )
                
                # Process files individually to provide real-time updates
                for file_path in files:
                    try:
                        summary_data = project_summarizer.file_summarizer.summarize_file(
                            file_path, self.api_preference
                        )
                        
                        if summary_data:
                            self.file_summarized.emit(file_path, summary_data)
                        
                        processed_files += 1
                        progress = int(20 + (processed_files / total_files) * 70)
                        self.progress_updated.emit(
                            progress, 
                            f"Summarized {os.path.basename(file_path)} ({processed_files}/{total_files})"
                        )
                        
                    except Exception as e:
                        print(f"Error summarizing {file_path}: {e}")
                        processed_files += 1
            
            self.progress_updated.emit(95, "Saving summaries...")
            
            # Note: Individual summaries are already saved via file_summarized signal
            # This is just for final cleanup
            
            self.progress_updated.emit(100, "Summarization completed!")
            self.summarization_completed.emit(True, f"Successfully summarized {processed_files} files")
            
        except Exception as e:
            self.summarization_completed.emit(False, f"Error during summarization: {str(e)}")


class ProjectManagerDialog(QDialog):
    """Simplified Project Manager focused on file structure and summaries."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project Manager")
        self.setGeometry(200, 200, 1200, 800)
        self.summarization_thread = None
        self.file_summaries = {}
        self.current_selected_file = None
        self.syntax_highlighter = None  # Store reference to prevent garbage collection
        
        self.initUI()
        
        # Don't auto-load any project - start fresh
        project_linker.current_project = None
        self.load_existing_project()
        
    
    def initUI(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header with project selection
        self.setup_header(layout)
        
        # Main content area
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # Left side - File tree
        self.setup_file_tree(main_splitter)
        
        # Right side - File details and summary
        self.setup_details_panel(main_splitter)
        
        # Set splitter proportions - give more space to file tree
        main_splitter.setStretchFactor(0, 4)  # File tree gets more space
        main_splitter.setStretchFactor(1, 3)  # Details panel gets less space
        
        # Progress bar for summarization
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        refresh_button = QPushButton("Refresh Files")
        refresh_button.clicked.connect(self.refresh_project)
        button_layout.addWidget(refresh_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
    
    def setup_header(self, layout):
        """Setup the compact header with project selection."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_frame.setMaximumHeight(40)  # Limit header height
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins
        
        # Compact label
        project_label = QLabel("Project:")
        project_label.setMinimumWidth(50)
        project_label.setMaximumWidth(50)
        header_layout.addWidget(project_label)
        
        # Compact project dropdown
        self.project_combo = QComboBox()
        self.project_combo.addItem("No Project Selected")
        self.project_combo.currentTextChanged.connect(self.on_project_changed)
        self.project_combo.setMinimumWidth(120)
        self.project_combo.setMaximumWidth(200)
        header_layout.addWidget(self.project_combo)
        
        # Compact buttons
        link_button = QPushButton("Link")
        link_button.clicked.connect(self.link_new_project)
        link_button.setMinimumWidth(50)
        link_button.setMaximumWidth(60)
        header_layout.addWidget(link_button)
        
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_current_project)
        self.remove_button.setEnabled(False)
        self.remove_button.setMinimumWidth(60)
        self.remove_button.setMaximumWidth(70)
        header_layout.addWidget(self.remove_button)
        
        # Add stretch to push everything left
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
    
    def setup_file_tree(self, parent):
        """Setup the file tree widget."""
        tree_widget = QWidget()
        tree_layout = QVBoxLayout(tree_widget)
        
        # Tree header
        tree_header = QLabel("Project File Structure")
        tree_header.setFont(QFont("Arial", 12, QFont.Bold))
        tree_layout.addWidget(tree_header)
        
        # File tree
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["File", "Status", "Size"])
        self.file_tree.itemClicked.connect(self.on_file_selected)
        tree_layout.addWidget(self.file_tree)
        
        parent.addWidget(tree_widget)
    
    def setup_details_panel(self, parent):
        """Setup the details panel for file information."""
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        
        # Details header with action buttons
        header_layout = QHBoxLayout()
        self.details_header = QLabel("Select a file to view details")
        self.details_header.setFont(QFont("Arial", 10, QFont.Bold))
        header_layout.addWidget(self.details_header)
        
        header_layout.addStretch()
        
        # Summarize button
        self.summarize_button = QPushButton("Summarize")
        self.summarize_button.clicked.connect(self.summarize_selected_file)
        self.summarize_button.setEnabled(False)
        self.summarize_button.setMaximumWidth(80)
        header_layout.addWidget(self.summarize_button)
        
        details_layout.addLayout(header_layout)
        
        # Create vertical splitter for content, summary, and dependency graph
        content_splitter = QSplitter(Qt.Vertical)
        
        # File content area (top)
        content_frame = QWidget()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(5, 5, 5, 5)
        
        content_header = QLabel("File Content")
        content_header.setFont(QFont("Arial", 9, QFont.Bold))
        content_layout.addWidget(content_header)
        
        self.file_content = QTextEdit()
        self.file_content.setReadOnly(True)
        self.file_content.setPlainText("No file selected")
        self.file_content.setFont(QFont("Courier", 10))  # Monospace font for code
        self.file_content.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                padding: 5px;
            }
        """)
        content_layout.addWidget(self.file_content)
        
        content_splitter.addWidget(content_frame)
        
        # File summary area (bottom)
        summary_frame = QWidget()
        summary_layout = QVBoxLayout(summary_frame)
        summary_layout.setContentsMargins(5, 5, 5, 5)
        
        summary_header = QLabel("AI Summary")
        summary_header.setFont(QFont("Arial", 9, QFont.Bold))
        summary_layout.addWidget(summary_header)
        
        self.file_summary = QTextEdit()
        self.file_summary.setReadOnly(True)
        self.file_summary.setPlainText("No summary available")
        summary_layout.addWidget(self.file_summary)
        
        content_splitter.addWidget(summary_frame)
        
        
        # Dependency graph area (bottom)
        graph_frame = QWidget()
        graph_layout = QVBoxLayout(graph_frame)
        graph_layout.setContentsMargins(5, 5, 5, 5)
        
        graph_header_layout = QHBoxLayout()
        graph_header = QLabel("File Dependencies")
        graph_header.setFont(QFont("Arial", 9, QFont.Bold))
        graph_header_layout.addWidget(graph_header)
        
        # Analyze dependencies button
        self.analyze_deps_button = QPushButton("Analyze Dependencies")
        self.analyze_deps_button.clicked.connect(self.analyze_dependencies)
        self.analyze_deps_button.setMaximumWidth(150)
        graph_header_layout.addWidget(self.analyze_deps_button)
        
        graph_header_layout.addStretch()
        graph_layout.addLayout(graph_header_layout)
        
        # Dependency graph widget
        self.dependency_graph = DependencyGraphWidget()
        self.dependency_graph.nodeClicked.connect(self.on_graph_node_clicked)
        self.dependency_graph.nodeDoubleClicked.connect(self.on_graph_node_double_clicked)
        self.dependency_graph.setMinimumHeight(200)  # Ensure minimum height
        graph_layout.addWidget(self.dependency_graph)
        
        content_splitter.addWidget(graph_frame)
        
        # Set vertical splitter proportions
        content_splitter.setStretchFactor(0, 3)  # File content
        content_splitter.setStretchFactor(1, 2)  # Summary
        content_splitter.setStretchFactor(2, 3)  # Dependency graph
        
        details_layout.addWidget(content_splitter)
        
        parent.addWidget(details_widget)
    
    def load_existing_project(self):
        """Load existing linked projects into the combo box."""
        self.project_combo.clear()
        
        linked_projects = project_linker.get_linked_projects()
        
        if not linked_projects:
            self.project_combo.addItem("No Project Selected")
            return
        
        # Add all linked projects
        for project in linked_projects:
            self.project_combo.addItem(project)
        
        # Set current project as selected
        if project_linker.current_project:
            index = self.project_combo.findText(project_linker.current_project)
            if index >= 0:
                self.project_combo.setCurrentIndex(index)
                self.load_project_files()
    
    def on_project_changed(self, project_name):
        """Handle project selection change."""
        if project_name == "No Project Selected" or not project_name:
            project_linker.current_project = None  # Explicitly clear
            self.clear_file_tree()
            self.remove_button.setEnabled(False)
            return
        
        # Select the project
        success = project_linker.select_project(project_name)
        if success:
            self.remove_button.setEnabled(True)
            self.load_project_files()
            print(f"Selected project: {project_name}")
            
        else:
            QMessageBox.warning(self, "Error", f"Failed to select project '{project_name}'")
    
    def link_new_project(self):
        """Link a new project."""
        # Get project directory
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Select Project Directory",
            os.path.expanduser("~")
        )
        
        if not directory:
            return
        
        # Get project name
        project_name = os.path.basename(directory)
        from PyQt5.QtWidgets import QInputDialog
        project_name, ok = QInputDialog.getText(
            self, 
            "Project Name", 
            f"Enter name for this project:",
            text=project_name
        )
        
        if not ok or not project_name.strip():
            return
        
        project_name = project_name.strip()
        
        # Check if project already exists
        if project_name in project_linker.get_linked_projects():
            QMessageBox.warning(self, "Warning", f"Project '{project_name}' already exists.")
            return
        
        # Link the project
        self.start_project_linking(project_name, directory)
    
    def start_project_linking(self, project_name, project_path):
        """Start linking and summarizing a project."""
        try:
            # Link the project first
            success = project_linker.link_project(project_name, project_path)
            if not success:
                QMessageBox.critical(self, "Error", "Failed to link project")
                return
            
            # Select the project
            project_linker.select_project(project_name)
            
            # Update UI
            self.load_existing_project()
            self.load_project_files()
            
            # Don't auto-summarize - let user select files to summarize
            project_data = project_linker.linked_projects[project_name]
            file_count = len(project_data["files"])
            self.status_label.setText(f"Project '{project_name}' linked successfully with {file_count} files. Select files to summarize.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to link project: {str(e)}")
    
    def start_file_summarization(self, project_name, file_paths):
        """Start file summarization in background."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting file summarization...")
        
        # Create and start summarization thread
        self.summarization_thread = ProjectSummarizationThread(project_name, file_paths)
        self.summarization_thread.progress_updated.connect(self.on_summarization_progress)
        self.summarization_thread.file_summarized.connect(self.on_file_summarized)
        self.summarization_thread.summarization_completed.connect(self.on_summarization_completed)
        self.summarization_thread.start()
    
    def on_summarization_progress(self, progress, message):
        """Handle summarization progress updates."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
    
    def on_file_summarized(self, file_path, summary_data):
        """Handle individual file summarization completion."""
        self.file_summaries[file_path] = summary_data
        
        # Update the tree item status
        self.update_file_tree_status(file_path, "Summarized")
        
        # If this file is currently selected, update the details
        current_item = self.file_tree.currentItem()
        if current_item and current_item.data(0, Qt.UserRole) == file_path:
            self.display_file_details(file_path)
    
    def on_summarization_completed(self, success, message):
        """Handle summarization completion."""
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_label.setText(message)
        else:
            self.status_label.setText(f"Error: {message}")
            QMessageBox.warning(self, "Summarization Error", message)
    
    
    def load_project_files(self):
        """Load the current project's file structure into the tree."""
        self.clear_file_tree()
        
        if not project_linker.current_project:
            return
        
        project_data = project_linker.linked_projects[project_linker.current_project]
        project_path = project_data["path"]
        file_paths = project_data["files"]
        
        # Load existing summaries
        self.file_summaries = project_summarizer.get_project_summaries(project_linker.current_project)
        
        # Build file tree structure
        self.build_file_tree(project_path, file_paths)
    
    def build_file_tree(self, project_path, file_paths):
        """Build the file tree structure."""
        # Create directory structure
        dir_items = {}
        
        for file_path in sorted(file_paths):
            rel_path = os.path.relpath(file_path, project_path)
            
            # Split path into components
            path_parts = rel_path.split(os.sep)
            file_name = path_parts[-1]
            
            # Create directory structure
            current_parent = self.file_tree.invisibleRootItem()
            current_path = ""
            
            for i, part in enumerate(path_parts[:-1]):  # Exclude file name
                current_path = os.path.join(current_path, part) if current_path else part
                
                if current_path not in dir_items:
                    dir_item = QTreeWidgetItem(current_parent)
                    dir_item.setText(0, part + "/")
                    dir_item.setText(1, "Directory")
                    dir_item.setData(0, Qt.UserRole, None)  # Mark as directory
                    dir_items[current_path] = dir_item
                
                current_parent = dir_items[current_path]
            
            # Add file item
            file_item = QTreeWidgetItem(current_parent)
            file_item.setText(0, file_name)
            file_item.setData(0, Qt.UserRole, file_path)  # Store full path
            
            # Set status and size
            try:
                file_size = os.path.getsize(file_path)
                file_item.setText(2, f"{file_size:,} bytes")
                
                if file_path in self.file_summaries:
                    file_item.setText(1, "Summarized")
                else:
                    file_item.setText(1, "Pending")
            except:
                file_item.setText(1, "Error")
                file_item.setText(2, "Unknown")
        
        # Expand all directories
        self.file_tree.expandAll()
    
    def update_file_tree_status(self, file_path, status):
        """Update the status of a specific file in the tree."""
        for i in range(self.file_tree.topLevelItemCount()):
            self._update_item_status(self.file_tree.topLevelItem(i), file_path, status)
    
    def _update_item_status(self, item, file_path, status):
        """Recursively update item status."""
        if item.data(0, Qt.UserRole) == file_path:
            item.setText(1, status)
            return True
        
        for i in range(item.childCount()):
            if self._update_item_status(item.child(i), file_path, status):
                return True
        
        return False
    
    def clear_file_tree(self):
        """Clear the file tree."""
        self.file_tree.clear()
        self.file_content.setPlainText("No file selected")
        self.file_summary.setPlainText("No summary available")
        self.details_header.setText("Select a file to view details")
    
    def on_file_selected(self, item, column):
        """Handle file selection in the tree."""
        file_path = item.data(0, Qt.UserRole)
        
        if file_path is None:  # Directory selected
            self.current_selected_file = None
            self.details_header.setText("Directory: " + item.text(0))
            self.file_content.setPlainText("Directory selected. Select a file to view its content.")
            self.file_summary.setPlainText("No summary available for directories.")
            self.summarize_button.setEnabled(False)
            return
        
        self.current_selected_file = file_path
        self.summarize_button.setEnabled(True)
        self.display_file_details(file_path)
        
        # Update dependency graph if loaded
        if hasattr(self, 'dependency_graph') and self.dependency_graph.nodes:
            self.dependency_graph.highlight_dependencies(file_path, depth=1)
            self.dependency_graph.center_on_node(file_path)
    
    def display_file_details(self, file_path):
        """Display details for the selected file."""
        file_name = os.path.basename(file_path)
        self.details_header.setText(f"File: {file_name}")
        
        # Load file content immediately
        self.load_file_content(file_path)
        
        # Display summary if available
        if file_path in self.file_summaries:
            summary_data = self.file_summaries[file_path]
            
            details = f"File: {summary_data['file_name']}\n"
            details += f"Size: {summary_data['file_size']:,} bytes ({summary_data['size_category']})\n"
            details += f"Summarized: {time.ctime(summary_data['timestamp'])}\n"
            details += f"API Used: {summary_data['api_used']}\n\n"
            details += "Summary:\n"
            details += "=" * 50 + "\n"
            details += summary_data['summary']
            
            self.file_summary.setPlainText(details)
        else:
            try:
                file_size = os.path.getsize(file_path)
                self.file_summary.setPlainText(
                    f"File: {file_name}\n"
                    f"Path: {file_path}\n"
                    f"Size: {file_size:,} bytes\n\n"
                    "Summary not yet available. Click 'Summarize' to generate summary."
                )
            except:
                self.file_summary.setPlainText(
                    f"File: {file_name}\n"
                    f"Path: {file_path}\n\n"
                    "Summary not yet available. Click 'Summarize' to generate summary."
                )
    
    def load_file_content(self, file_path):
        """Load and display file content with syntax highlighting."""
        try:
            # Try to read the file with different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                # If all encodings fail, try binary read and show info
                with open(file_path, 'rb') as f:
                    binary_content = f.read()
                
                if len(binary_content) > 1024 * 1024:  # > 1MB
                    self.file_content.setPlainText(
                        f"File is too large to display ({len(binary_content):,} bytes)\n"
                        "Large binary or text file - content not shown for performance."
                    )
                else:
                    # Try to show as text anyway, replacing bad characters
                    try:
                        content = binary_content.decode('utf-8', errors='replace')
                        self.display_with_highlighting(content, file_path)
                    except:
                        self.file_content.setPlainText(
                            f"Binary file ({len(binary_content):,} bytes)\n"
                            "Cannot display binary content as text."
                        )
            else:
                # Check if content is too large
                if len(content) > 500000:  # > 500KB of text
                    # Show first 500KB with warning
                    truncated_content = content[:500000]
                    self.display_with_highlighting(truncated_content, file_path)
                    # Add truncation notice
                    cursor = self.file_content.textCursor()
                    cursor.movePosition(cursor.End)
                    cursor.insertText(f"\n\n... [File truncated - showing first 500KB of {len(content):,} characters total]")
                else:
                    self.display_with_highlighting(content, file_path)
                    
        except Exception as e:
            self.file_content.setPlainText(f"Error reading file: {str(e)}")
    
    def display_with_highlighting(self, content, file_path):
        """Display content with syntax highlighting based on file type."""
        print(f"Displaying file with highlighting: {file_path}")
        print(f"Pygments available: {HAS_PYGMENTS}")
        
        if HAS_PYGMENTS:
            try:
                # Get appropriate lexer for the file
                lexer = get_lexer_for_filename(file_path, content)
                print(f"Using lexer: {lexer.__class__.__name__}")
                
                # Use a dark theme formatter
                formatter = HtmlFormatter(
                    style='monokai',
                    noclasses=True,
                    nobackground=True,
                    linenos=False
                )
                
                # Generate highlighted HTML
                highlighted_html = highlight(content, lexer, formatter)
                
                # Apply custom CSS for dark theme
                css = """
                <style>
                body { 
                    background-color: #1e1e1e; 
                    color: #d4d4d4;
                    font-family: 'Courier New', Courier, monospace;
                    font-size: 10pt;
                    margin: 5px;
                }
                pre { 
                    margin: 0; 
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
                </style>
                """
                
                # Set HTML content
                self.file_content.setHtml(css + highlighted_html)
                print("Successfully applied Pygments highlighting")
                
            except Exception as e:
                # Fallback to plain text if highlighting fails
                print(f"Pygments highlighting failed: {e}")
                self.apply_basic_highlighting(content, file_path)
        else:
            # Fallback: basic syntax highlighting without Pygments
            print("Using basic syntax highlighting (Pygments not available)")
            self.apply_basic_highlighting(content, file_path)
    
    def apply_basic_highlighting(self, content, file_path):
        """Apply basic syntax highlighting without Pygments."""
        self.file_content.setPlainText(content)
        
        # Determine file type from extension
        ext = os.path.splitext(file_path)[1].lower()
        
        # Create and apply a basic highlighter
        # The highlighter will automatically highlight when attached to the document
        self.syntax_highlighter = BasicSyntaxHighlighter(self.file_content.document(), ext)
    
    def summarize_selected_file(self):
        """Summarize the currently selected file."""
        if not self.current_selected_file:
            return
        
        file_path = self.current_selected_file
        file_name = os.path.basename(file_path)
        
        # Update UI to show summarization in progress
        self.summarize_button.setEnabled(False)
        self.summarize_button.setText("Summarizing...")
        self.update_file_tree_status(file_path, "Summarizing...")
        self.status_label.setText(f"Summarizing {file_name}...")
        
        # Start summarization in a separate thread
        self.start_single_file_summarization(file_path)
    
    def start_single_file_summarization(self, file_path):
        """Start summarization for a single file."""
        # Create a simple single-file thread
        self.summarization_thread = SingleFileSummarizationThread(file_path)
        self.summarization_thread.file_summarized.connect(self.on_single_file_summarized)
        self.summarization_thread.summarization_failed.connect(self.on_single_file_failed)
        self.summarization_thread.start()
    
    def on_single_file_summarized(self, file_path, summary_data):
        """Handle single file summarization completion."""
        self.file_summaries[file_path] = summary_data
        
        # Save the summary to project storage
        if project_linker.current_project:
            project_summaries_file = os.path.join(
                project_summarizer.storage_path, 
                f"{project_linker.current_project}_summaries.json"
            )
            
            # Load existing summaries and add this one
            try:
                if os.path.exists(project_summaries_file):
                    with open(project_summaries_file, 'r') as f:
                        data = json.load(f)
                    all_summaries = data.get('summaries', {})
                else:
                    all_summaries = {}
                
                all_summaries[file_path] = summary_data
                
                # Save updated summaries
                output_data = {
                    'metadata': {
                        'total_files': len(all_summaries),
                        'generated_at': time.time(),
                        'generated_at_human': time.ctime()
                    },
                    'summaries': all_summaries
                }
                
                os.makedirs(os.path.dirname(project_summaries_file), exist_ok=True)
                with open(project_summaries_file, 'w') as f:
                    json.dump(output_data, f, indent=2)
                    
            except Exception as e:
                print(f"Error saving summary: {e}")
        
        # Update UI
        self.update_file_tree_status(file_path, "Summarized")
        self.summarize_button.setEnabled(True)
        self.summarize_button.setText("Summarize File")
        
        # Update display if this file is still selected
        if self.current_selected_file == file_path:
            self.display_file_details(file_path)
        
        file_name = os.path.basename(file_path)
        self.status_label.setText(f"Successfully summarized {file_name}")
    
    def on_single_file_failed(self, file_path, error_message):
        """Handle single file summarization failure."""
        self.update_file_tree_status(file_path, "Error")
        self.summarize_button.setEnabled(True)
        self.summarize_button.setText("Summarize File")
        
        file_name = os.path.basename(file_path)
        self.status_label.setText(f"Failed to summarize {file_name}: {error_message}")
        QMessageBox.warning(self, "Summarization Error", f"Failed to summarize {file_name}:\n{error_message}")
    
    def remove_current_project(self):
        """Remove the current project."""
        current_project = project_linker.current_project
        if not current_project:
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove project '{current_project}'?\n"
            "This will only remove it from Lumen, not delete the actual files.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = project_linker.remove_project(current_project)
            if success:
                self.load_existing_project()
                self.clear_file_tree()
                QMessageBox.information(self, "Success", f"Project '{current_project}' removed.")
            else:
                QMessageBox.warning(self, "Error", f"Failed to remove project '{current_project}'.")
    
    def refresh_project(self):
        """Refresh the current project file list."""
        if not project_linker.current_project:
            QMessageBox.information(self, "Info", "No project selected to refresh.")
            return
        
        project_data = project_linker.linked_projects[project_linker.current_project]
        
        # Re-discover files
        old_file_count = len(project_data["files"])
        new_files = project_linker.file_analyzer.discover_user_files(project_data["path"])
        project_data["files"] = new_files
        project_linker._save_linked_projects()
        
        # Reload file tree
        self.load_project_files()
        
        new_file_count = len(new_files)
        if new_file_count != old_file_count:
            self.status_label.setText(f"Refreshed: {new_file_count} files found ({new_file_count - old_file_count:+d} change)")
        else:
            self.status_label.setText(f"Refreshed: {new_file_count} files found (no change)")
    
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # Stop summarization thread if running
        if self.summarization_thread and self.summarization_thread.isRunning():
            self.summarization_thread.quit()
            self.summarization_thread.wait()
        
        
        event.accept()
    
    def analyze_dependencies(self):
        """Analyze dependencies for the current project."""
        if not project_linker.current_project:
            QMessageBox.information(self, "Info", "No project selected.")
            return
        
        project_data = project_linker.linked_projects[project_linker.current_project]
        project_path = project_data["path"]
        file_paths = project_data["files"]
        
        self.status_label.setText("Analyzing file dependencies...")
        self.analyze_deps_button.setEnabled(False)
        
        try:
            # Analyze the project
            dependency_graph = file_dependency_analyzer.analyze_project(project_path, file_paths)
            
            # Get graph data for visualization
            if self.current_selected_file:
                # Use focused graph data when a file is selected
                graph_data = file_dependency_analyzer.get_focused_graph_data(self.current_selected_file, depth=2)
                self.dependency_graph.load_graph_data(graph_data, self.current_selected_file)
            else:
                # Use full graph data when no file is selected
                graph_data = file_dependency_analyzer.export_graph_data()
                self.dependency_graph.load_graph_data(graph_data)
            
            # Show statistics
            stats = graph_data['stats']
            self.status_label.setText(
                f"Analyzed {stats['total_files']} files with {stats['total_dependencies']} dependencies. "
                f"Found {stats['circular_dependencies']} circular dependencies."
            )
            
            # Highlight current file if selected
            if self.current_selected_file:
                self.dependency_graph.highlight_dependencies(self.current_selected_file, depth=2)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to analyze dependencies: {str(e)}")
            self.status_label.setText("Dependency analysis failed")
        finally:
            self.analyze_deps_button.setEnabled(True)
    
    def on_graph_node_clicked(self, file_path):
        """Handle node click in dependency graph."""
        # Find and select the file in the tree
        self.select_file_in_tree(file_path)
        
        # Highlight dependencies
        self.dependency_graph.highlight_dependencies(file_path, depth=1)
    
    def on_graph_node_double_clicked(self, file_path):
        """Handle node double-click in dependency graph."""
        # Open the file in the main editor if possible
        if hasattr(self.parent(), 'open_file'):
            self.parent().open_file(file_path)
        else:
            # At least select it
            self.select_file_in_tree(file_path)
    
    def select_file_in_tree(self, file_path):
        """Select a file in the file tree."""
        # Search through all items to find the one with matching file path
        for i in range(self.file_tree.topLevelItemCount()):
            if self._select_item_by_path(self.file_tree.topLevelItem(i), file_path):
                break
    
    def _select_item_by_path(self, item, file_path):
        """Recursively search and select item by file path."""
        if item.data(0, Qt.UserRole) == file_path:
            self.file_tree.setCurrentItem(item)
            self.on_file_selected(item, 0)
            return True
        
        for i in range(item.childCount()):
            if self._select_item_by_path(item.child(i), file_path):
                return True
        
        return False