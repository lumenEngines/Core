import os
import sys
import threading
import time
import json
from PyQt5.QtGui import QKeyEvent, QCursor, QPalette
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDialog, QPushButton,
                             QVBoxLayout, QWidget, QTextEdit, QLineEdit, QSizePolicy, QLabel,
                             QHBoxLayout, QComboBox, QListWidget, QListWidgetItem)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebEngineWidgets import QWebEnginePage
from PyQt5.QtCore import QTimer, pyqtSignal, QThread
from matplotlib.backends.backend_template import FigureCanvas
import core.prompting as prompting
import subprocess
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtGui import QPixmap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from core.settings import settings
from .settings_dialog import SettingsDialog
from utils.plot import PlotThread, PlotWindow, CustomEvent
from .project_manager_dialog import ProjectManagerDialog
from core.project_manager import project_manager
from utils.instant_code_detector import instant_detector



class TextWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.vision_timer = None
        self.initUI()
        self.initVariables()
        self.initTimers()
        background_color = QColor(0, 0, 0, 30)  # Black with < 30% opacity
        self.setStyleSheet(f"background-color: rgba({background_color.red()}, {background_color.green()}, {background_color.blue()}, {background_color.alpha()});")
        
        # Install event filter for application-wide key events
        QApplication.instance().installEventFilter(self)


    def initUI(self):
        self.setWindowTitle("Lumen")
        self.setGeometry(100, 100, 1000, 1000)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.web_view = self.createWebView()
        layout.addWidget(self.web_view)

        self.sourcesBox = self.createSourcesBox()
        layout.addWidget(self.sourcesBox)

        self.createButtons(layout)

    def initVariables(self):
        self.clipboardHandler = None
        self.clipboard = QApplication.clipboard()
        self.searchText = self.clipboard.text()
        self.clipboard_lock = threading.Lock()
        self.pages = []
        self.pageIndex = -1
        self.popup_permanent = False  # Flag to indicate if popup should stay open
        self.popup_active = False
        self.popup_timer = None
        self.context_buffer = ""
        self.context_lock = threading.Lock()
        self.project_button = None
        self.pages_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")
        os.makedirs(self.pages_path, exist_ok=True)
        self.output_file_path = "./src/output.txt"
        self.html_file_path = "./src/html.txt"
        self.last_file_size = 0
        self.last_modified_time = 0
        self.formatting_done = False
        self.streaming_started = False
        self.copy_key_pressed = False
        self.mode_active = True
        self.format_enabled = False

    def initTimers(self):
        self.clipboard_timer = QTimer(self)
        self.clipboard_timer.timeout.connect(self.check_clipboard)
        self.clipboard_timer.start(int(settings.check_interval * 1000))

        self.file_check_timer = QTimer(self)
        self.file_check_timer.timeout.connect(self.check_file_changes)
        self.file_check_timer.start(2000)

    def createWebView(self):
        web_view = QWebEngineView()
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        html_file_path = os.path.join(base_path, 'resources', 'intropage.html')
        with open(html_file_path) as file:
            web_view.setHtml(file.read())
        return web_view

    def event(self, event):
        if event.type() == CustomEvent.EVENT_TYPE:
            self.create_plot_window(event.plot_path)
            return True
        return super().event(event)
        
    def eventFilter(self, watched, event):
        """Application-wide event filter to catch key events."""
        if event.type() == QEvent.KeyPress:
            key_event = QKeyEvent(event)
            
            # Always print detected key events
            key_code = key_event.key()
            modifiers = key_event.modifiers()
            mod_text = []
            if modifiers & Qt.ControlModifier:
                mod_text.append("Ctrl")
            if modifiers & Qt.MetaModifier:
                mod_text.append("Cmd")
            if modifiers & Qt.ShiftModifier:
                mod_text.append("Shift")
            if modifiers & Qt.AltModifier:
                mod_text.append("Alt")
            mods = "+".join(mod_text) if mod_text else "None"
            print(f"GLOBAL KEY PRESS: Key code: {key_code} - Modifiers: {mods}")
            
            # Specifically look for Cmd+C or Ctrl+C combination
            if key_event.key() == Qt.Key_C and (modifiers & Qt.ControlModifier or modifiers & Qt.MetaModifier):
                print("Copy key combination detected in global filter")
                print(f"Popup active: {self.popup_active}")
                print(f"PromptWindow exists: {hasattr(self, 'promptWindow') and self.promptWindow}")
                print(f"PromptWindow visible: {hasattr(self, 'promptWindow') and self.promptWindow and self.promptWindow.isVisible()}")
                print(f"Project Manager open: {hasattr(self, 'project_manager_dialog') and self.project_manager_dialog and self.project_manager_dialog.isVisible()}")
                
                # If popup is active, this is a second Cmd+C - make it stay
                if self.popup_active and hasattr(self, 'promptWindow') and self.promptWindow and self.promptWindow.isVisible():
                    print("Second Cmd+C detected - making popup stay")
                    
                    # Use the existing update_popup_timeout method with extended timeout from settings
                    self.update_popup_timeout(int(settings.extended_timeout * 1000))
                    
                    # Stop any countdown in the prompt window
                    if hasattr(self.promptWindow, 'stop_countdown'):
                        self.promptWindow.stop_countdown()
                    
                    # Update UI to indicate popup will stay
                    self.promptWindow.setWindowTitle("Press Enter to process or Escape to cancel")
                    
                    # Find and update the instruction label
                    if hasattr(self.promptWindow, 'layout'):
                        for i in range(self.promptWindow.layout().count()):
                            widget = self.promptWindow.layout().itemAt(i).widget()
                            if isinstance(widget, QLabel) and "TIP" in widget.text():
                                widget.setText("<b>TIP:</b> Press Enter to process or Escape to cancel")
                                widget.setStyleSheet("color: green; margin-bottom: 5px;")
                                break
                    
                    # Mark as permanent
                    self.popup_permanent = True
                    return True  # Event handled
        
        # Let the event continue to be processed
        return super().eventFilter(watched, event)

    def create_plot_window(self, plot_path):
        self.plot_window = PlotWindow(plot_path)
        self.plot_window.show()

    def createSourcesBox(self):
        sources_box = QTextEdit(self)
        sources_box.setPlainText("")
        sources_box.setFixedHeight(100)
        sources_box.setVisible(False)
        # Force white text color for the text editor
        sources_box.setStyleSheet("""
            QTextEdit {
                color: white;
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.3);
                padding: 5px;
            }
        """)
        return sources_box

    def createButtons(self, layout):
        buttons = [
            ("Reset Memory", None, False),  # Non-toggle button
            ("Open Prompt Constructor", "Hide Prompt Constructor", True),
            ("Anthropic", "Deep", True),
            ("Turn Intelligence Off", "Turn Intelligence On", True),
            ("Project Manager", None, False),  # Project management button
            ("Settings", None, False)   # Settings button
        ]

        for text_on, text_off, is_toggle in buttons:
            if is_toggle:
                button = ToggleButton(text_on, text_off)
            else:
                button = QPushButton(text_on)
                # Apply the same styling to regular buttons
                button.setStyleSheet("""
                    QPushButton {
                        color: white;
                    }
                    QPushButton:hover {
                        background-color: #333333;
                        color: white;
                    }
                """)
            layout.addWidget(button)
            button_name = text_on.replace(' ', '_').lower()
            setattr(self, f"button_{button_name}", button)

        self.connectButtonSignals()

    def connectButtonSignals(self):
        self.button_reset_memory.clicked.connect(self.resetMemory)
        self.button_open_prompt_constructor.clicked.connect(self.toggleTerminalClicked)
        self.button_turn_intelligence_off.clicked.connect(self.toggle_mode)
        self.button_project_manager.clicked.connect(self.openProjectManager)
        self.button_settings.clicked.connect(self.openSettings)

    def launchVision(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(current_dir, 'program/multiple_objects.py')
        subprocess.Popen(['python', script_path])

    def resetMemory(self):
        prompting.chat = ["empty", "empty", "empty", "empty"]
        prompting.messages = ["empty", "empty", "empty", "empty"]
        
        # Also clear project history
        current_project = project_manager.get_current_project()
        history_path = os.path.join(project_manager.base_path, current_project, "history.json")
        
        try:
            # Reset the project history file
            initial_history = {
                "conversations": [],
                "metadata": {
                    "created": time.time(),
                    "last_accessed": time.time()
                }
            }
            with open(history_path, 'w') as f:
                json.dump(initial_history, f, indent=2)
            print(f"Memory reset: Chat, messages, and project history cleared for project '{current_project}'.")
        except Exception as e:
            print(f"Memory reset: Chat and messages cleared. Warning: Could not clear project history: {e}")

    def check_file_changes(self):
        current_file_size = len(prompting.output)

        if current_file_size != self.last_file_size:
            self.last_file_size = current_file_size

            if current_file_size > 0:
                self.update_text_display()

        elif (current_file_size > 0) and (prompting.shouldUpdate == "t"):
            self.formatting_done = True
            # Skip the Groq formatting - streaming display is already good
            self.addPage(prompting.output)
            prompting.shouldUpdate = "f"
            print("Output is:")
            print(prompting.output)
            n = (-1)
            while n > (-4):
                prompting.chat[n - 1] = prompting.chat[n]
                n -= 1
            prompting.chat[-1] = prompting.output


    def update_text_display(self):
        # Save current scroll position
        current_scroll = self.web_view.page().scrollPosition()

        full_text = prompting.output
        formatted_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                }}
            </style>
            <script>
                function setScrollPosition(x, y) {{
                    window.scrollTo(x, y);
                }}
            </script>
        </head>
        <body>
            {full_text}
        </body>
        </html>
        """

        # Create a new QWebEnginePage
        new_page = QWebEnginePage(self.web_view)

        # Load the content into the new page
        new_page.setHtml(formatted_html)

        # Wait for the page to finish loading
        def on_load_finished(ok):
            if ok:
                # Set the new page to the web view
                self.web_view.setPage(new_page)

                # Restore scroll position
                self.web_view.page().runJavaScript(f"setScrollPosition({current_scroll.x()}, {current_scroll.y()});")

        new_page.loadFinished.connect(on_load_finished)

    def create_graph(self):
        full_text = prompting.output
        formatted_html = f"""
        <html>
        <head>
        </head>
        <body>
        {full_text}
        </body>
        </html>
        """
        self.web_view.setHtml(formatted_html)

    def addClipboardHandler(self, handler):
        self.clipboardHandler = handler

    def resetSources(self):
        self.sourcesBox.setPlainText("Type your prompt here: \n\n")

    def addURLSource(self, str):
        self.sourcesBox.append(str)

    def is_not_live(self) -> bool:
        return True  # Always fast mode (not live mode) since we removed the button

    def printGraph(self):
        pass

    def writeToFile(self):
        # Default to smart model since we removed the button
        prompting.model = "claude-3-5-sonnet-20240620"

    def toggleTerminalClicked(self):
        if self.button_open_prompt_constructor.is_toggled:
            self.sourcesBox.setVisible(False)
        else:
            self.sourcesBox.setVisible(True)

    def isDeepEnabled(self) -> bool:
        return not self.button_anthropic.is_toggled

    def isRegularModeEnabled(self) -> bool:
        return True  # Always regular mode since we removed the button

    def shouldWaitForPrompting(self) -> bool:
        return False  # Always show popup (don't wait) since we removed the button

    def showPage(self, html):
        self.web_view.setHtml(html)

    def addPage(self, html):
        self.pages.append(html)
        self.pageIndex = len(self.pages) - 1
        self.showPage(html)

    def previousPage(self):
        if self.pageIndex > 0:
            self.pageIndex -= 1
            self.showPage(self.pages[self.pageIndex])
        print(f"Page {self.pageIndex+1}/{len(self.pages)}")

    def nextPage(self):
        if self.pageIndex < len(self.pages) - 1:
            self.pageIndex += 1
            self.showPage(self.pages[self.pageIndex])
        print(f"Page {self.pageIndex+1}/{len(self.pages)}")

    def keyPressEvent(self, event: QKeyEvent):
        # Always print key events for debugging
        key_code = event.key()
        modifiers = event.modifiers()
        mod_text = []
        if modifiers & Qt.ControlModifier:
            mod_text.append("Ctrl")
        if modifiers & Qt.MetaModifier:
            mod_text.append("Cmd")
        if modifiers & Qt.ShiftModifier:
            mod_text.append("Shift")
        if modifiers & Qt.AltModifier:
            mod_text.append("Alt")
        mods = "+".join(mod_text) if mod_text else "None"
        print(f"KEY PRESSED: Key code: {key_code} - Modifiers: {mods}")
        
        if event.key() == Qt.Key_Left:
            print("Key left")
            self.previousPage()
        elif event.key() == Qt.Key_Right:
            print("Key right")
            self.nextPage()
        elif event.key() == Qt.Key_Escape:
            # Allow Escape key to forcefully dismiss popup
            if self.popup_active and self.promptWindow:
                print("ESCAPE KEY: Performing emergency popup dismissal")
                
                # Mark as not permanent anymore since we're dismissing
                self.popup_permanent = False
                
                # IMPORTANT: Stop all timers immediately to prevent race conditions
                if hasattr(self, 'popup_timer') and self.popup_timer and self.popup_timer.isActive():
                    print("Stopping popup timer")
                    self.popup_timer.stop()
                
                if hasattr(self, 'clipboard_timer') and self.clipboard_timer and self.clipboard_timer.isActive():
                    print("Stopping clipboard timer temporarily")
                    self.clipboard_timer.stop()
                
                # Only attempt window operations if a valid window exists
                if self.promptWindow:
                    print("Hiding popup window")
                    try:
                        # First hide the window to give visual feedback
                        self.promptWindow.hide()
                    except Exception as e:
                        print(f"Warning: Error hiding window: {e}")
                    
                    print("Deleting window from memory")
                    try:
                        # Delete the window completely
                        self.promptWindow.deleteLater()
                    except Exception as e:
                        print(f"Warning: Error destroying window: {e}")
                
                # Clear references and reset state variables
                self.promptWindow = None
                self.popup_active = False
                self.popup_permanent = False
                
                # Schedule clipboard operations after a delay to avoid further events
                def delayed_cleanup():
                    if not settings.preserve_clipboard:
                        print("Clearing clipboard content")
                        self.clipboard.clear()
                    else:
                        print("Preserving clipboard content as configured in settings")
                        
                    # Finally restart clipboard timer with a longer delay
                    if self.mode_active:
                        print("Restarting clipboard timer")
                        self.clipboard_timer.start(int(settings.check_interval * 1000))
                
                # Use a longer delay (500ms) to ensure all pending events are processed
                QTimer.singleShot(500, delayed_cleanup)
                return True
                
        # Note: Cmd+C/Ctrl+C handling is now exclusively in the eventFilter method
        # to avoid duplicate handling and ensure consistent behavior
                
        # Always let the event propagate to parent
        return super().keyPressEvent(event)

    def toggle_mode(self):
        self.mode_active = not self.mode_active
        if self.mode_active:
            self.clipboard_timer.start(int(settings.check_interval * 1000))
        else:
            self.clipboard_timer.stop()

    def check_clipboard(self):
        if not self.mode_active:
            return

        with self.clipboard_lock:
            current_text = self.clipboard.text()
            # Skip empty clipboard or if content hasn't changed
            if not current_text or current_text == self.searchText:
                return
                
            print(f"New clipboard content detected: '{current_text[:30]}...' (length: {len(current_text)})")
            print(f"Popup active: {self.popup_active}")
                
            # SAFETY: Force cleanup any existing popup before creating new one
            if self.popup_active or (hasattr(self, 'promptWindow') and self.promptWindow):
                print("SAFETY: Cleaning up existing popup before creating new one")
                self.force_cleanup_popup()
                return  # Skip this clipboard event to avoid race conditions
                
            # Set clipboard content as searchText - NOT clearing the clipboard
            self.searchText = current_text
            self.popup_active = True
            self.popup_permanent = False  # New popups are initially temporary
            
            # Stop the clipboard timer while showing popup
            self.clipboard_timer.stop()
            
            # Show popup with appropriate timeout based on state
            if not self.shouldWaitForPrompting():
                # Normal timeout for first detection (from settings)
                timeout_value = settings.short_timeout * 1000
                print(f"DEBUG: Using timeout from settings: {settings.short_timeout}s = {timeout_value}ms")
                self.show_popup_with_timeout(int(timeout_value))
            else:
                # Direct processing mode
                if self.clipboardHandler:
                    result = self.clipboardHandler(self.searchText)
                    if result is not None:
                        self.addPage(result)
                # Reset state
                self.popup_active = False
                # Do NOT clear clipboard as requested - only new text will replace it
                # Restart the timer
                self.clipboard_timer.start(int(settings.check_interval * 1000))
    
    def show_popup_with_timeout(self, timeout_ms):
        # Initialize instant matches for project code detection
        instant_matches = []
        
        try:
            # Refresh detector if project changed
            instant_detector.refresh_if_needed()
            
            # Try instant detection on clipboard content
            if hasattr(self, 'searchText') and self.searchText:
                all_matches = instant_detector.instant_detect_multiple(self.searchText)
                
                # Filter out matches below 95% confidence
                instant_matches = [(path, name, conf) for path, name, conf in all_matches if conf >= 0.95]
                
                if instant_matches:
                    print(f"Found {len(instant_matches)} high-confidence file matches (≥95%):")
                    for file_path, file_name, confidence in instant_matches:
                        print(f"  - {file_name} ({confidence:.0%} confidence)")
                elif all_matches:
                    print(f"Found {len(all_matches)} matches, but all below 95% confidence threshold")
                else:
                    print("No instant code matches found")
            
        except Exception as e:
            print(f"Error in instant detection: {e}")
        
        # Create and show the prompt window with explicit no parent to avoid focus issues
        self.promptWindow = PromptWindow(parent=None, instant_matches=instant_matches)
        print(f"Creating popup window with timeout {timeout_ms}ms")
        
        # Set up a timer to close the popup automatically - create a new timer each time
        self.popup_timer = QTimer(self)
        self.popup_timer.setSingleShot(True)
        self.popup_timer.timeout.connect(self.handle_popup_timeout)
        
        # Connect accept/reject signals
        self.promptWindow.accepted.connect(self.on_popup_accepted)
        self.promptWindow.rejected.connect(self.on_popup_rejected)
        
        # Connect the Add to Context button
        self.promptWindow.add_context_button.clicked.connect(self.add_to_context)
        
        # Pass context buffer reference to the popup (if available)
        if hasattr(self, 'context_buffer') and self.context_buffer:
            self.promptWindow.update_context_preview(self.context_buffer)
        
        # Display instructions for popup
        self.promptWindow.setWindowTitle("Press Cmd+C/Ctrl+C to keep popup open")
        instruction_label = QLabel("<b>TIP:</b> Press Cmd+C to keep open, then Enter to process")
        instruction_label.setStyleSheet("color: blue; margin-bottom: 5px;")
        self.promptWindow.layout().insertWidget(2, instruction_label)
        
        # Start countdown timer in the popup
        self.promptWindow.start_countdown(timeout_ms)
        
        # Show the popup - ensure it's visible and on top
        self.promptWindow.show()
        self.promptWindow.raise_()
        self.promptWindow.activateWindow()
        
        # Send main window to back after popup appears
        QTimer.singleShot(10, self.minimizeMainWindow)
        
        # Start the timer directly - don't defer with singleShot
        print(f"Starting popup timer with {timeout_ms}ms timeout")
        print(f"Timer object: {self.popup_timer}")
        print(f"Timer interval set to: {int(timeout_ms)}")
        self.popup_timer.start(int(timeout_ms))
        print(f"Timer started. Is active: {self.popup_timer.isActive()}")
        print(f"Timer remaining time: {self.popup_timer.remainingTime()}")
    
    def update_popup_timeout(self, timeout_ms):
        """Update the popup timeout duration."""
        print(f"update_popup_timeout called with {timeout_ms}ms")
        
        # Stop the original timer completely
        if self.popup_timer and self.popup_timer.isActive():
            self.popup_timer.stop()
            print("Stopped original timer")
        
        # Reuse the same timer object to avoid confusion
        self.popup_timer.setSingleShot(True)
        self.popup_timer.timeout.connect(self.handle_popup_timeout)
        print(f"Starting extended timer with {timeout_ms}ms")
        self.popup_timer.start(int(timeout_ms))
            
        # Update the countdown in the prompt window
        if self.promptWindow and hasattr(self.promptWindow, 'update_timeout'):
            print("Updating countdown in prompt window")
            self.promptWindow.update_timeout(timeout_ms)
    
    def handle_popup_timeout(self):
        """Handle popup timeout - dismiss it and reset state."""
        print("TIMEOUT HANDLER - Auto-dismissing popup")
        print(f"popup_permanent = {self.popup_permanent}")
        print(f"popup_active = {self.popup_active}")
        print(f"promptWindow exists = {hasattr(self, 'promptWindow') and self.promptWindow}")
        print(f"promptWindow visible = {hasattr(self, 'promptWindow') and self.promptWindow and self.promptWindow.isVisible()}")
        
        # Check if popup is marked as permanent
        if self.popup_permanent:
            print("Popup is permanent - ignoring timeout")
            return
        
        # Process the timeout - auto-dismiss the popup
        with self.clipboard_lock:
            if self.promptWindow and self.promptWindow.isVisible():
                # Auto-dismiss when timer reaches zero
                print("Timeout expired - auto-dismissing popup")
                
                # Do NOT clear clipboard as requested - preserving clipboard content
                
                # Now trigger UI rejection (close the popup)
                # Use hide() and close() instead of reject() for better reliability
                self.promptWindow.hide()
                QTimer.singleShot(10, lambda: self.promptWindow.close())
                QTimer.singleShot(20, self.on_popup_rejected)  # Manually call the rejected handler
                
                # Send main window to background after timeout dismissal
                self.lower()
                self.clearFocus()
                
                # Make sure clipboard timer will restart
                if not self.clipboard_timer.isActive():
                    print("Restarting clipboard timer directly")
                    self.clipboard_timer.start(int(settings.check_interval * 1000))
    
    def on_popup_accepted(self):
        """Handle popup acceptance - process the input."""
        with self.clipboard_lock:
            print("Popup ACCEPTED - Processing input")
            
            # Stop any timers
            if hasattr(self, 'popup_timer') and self.popup_timer:
                if self.popup_timer.isActive():
                    self.popup_timer.stop()
                
            # Stop the countdown in the prompt window
            if self.promptWindow and hasattr(self.promptWindow, 'stop_countdown'):
                self.promptWindow.stop_countdown()
                
            # Get user input and process it
            user_prompt = self.promptWindow.getPromptText()
            project_context_requested = self.promptWindow.getProjectContextEnabled()
            chat_history_requested = self.promptWindow.getChatHistoryEnabled()
            edit_mode_requested = self.promptWindow.getEditModeEnabled()
            selected_file_path = getattr(self.promptWindow, 'selected_file_path', None)
            full_prompt = user_prompt + ': ' + self.searchText if user_prompt else self.searchText
            
            # Store context info on textWindow for textHandler to access
            self.current_project_context_requested = project_context_requested
            self.current_chat_history_requested = chat_history_requested
            self.current_selected_file_path = selected_file_path
            
            # Handle edit mode - route to diff viewer instead of regular chat
            if edit_mode_requested and selected_file_path:
                print(f"🔧 Edit mode requested for: {selected_file_path}")
                print(f"📝 Modification request: {user_prompt}")
                
                # Open project manager if not already open
                if not hasattr(self, 'project_manager_dialog') or not self.project_manager_dialog.isVisible():
                    self.openProjectManager()
                
                # Send request to diff viewer
                if hasattr(self, 'project_manager_dialog') and self.project_manager_dialog.isVisible():
                    self.project_manager_dialog.diff_viewer.generate_diff(selected_file_path, user_prompt)
                    self.addPage(f"📝 Generating file modifications for {os.path.basename(selected_file_path)}...")
                else:
                    self.addPage("⚠️ Could not open project manager for diff view")
            elif self.clipboardHandler:
                print(f"Calling clipboardHandler with: {full_prompt[:50]}...")
                result = self.clipboardHandler(full_prompt)
                if result is not None:
                    self.addPage(result)
                else:
                    print("clipboardHandler returned None")
            else:
                print("ERROR: clipboardHandler is None - cannot process request")
                self.addPage("⚠️ Error: Request handler not available")
            
            # Reset state variables
            self.popup_active = False
            self.popup_permanent = False
            
            # When query is submitted, bring main window to front to show response
            # (Don't send to background like other dismissals)
            self.show()
            self.raise_()
            self.activateWindow()
            
            # DO NOT clear clipboard as requested - preserve clipboard content
            
            # ENSURE clipboard timer is restarted
            if hasattr(self, 'clipboard_timer'):
                if not self.clipboard_timer.isActive() and self.mode_active:
                    print("Restarting clipboard timer after acceptance")
                    self.clipboard_timer.start(int(settings.check_interval * 1000))
    
    def on_popup_rejected(self):
        """Handle popup rejection - clean up and reset."""
        with self.clipboard_lock:
            print("Popup REJECTED - Cleaning up")
            
            # Stop any timers
            if hasattr(self, 'popup_timer') and self.popup_timer:
                if self.popup_timer.isActive():
                    self.popup_timer.stop()
                
            # Stop the countdown in the prompt window
            if self.promptWindow and hasattr(self.promptWindow, 'stop_countdown'):
                self.promptWindow.stop_countdown()
                
            # Reset state variables
            self.popup_active = False
            self.popup_permanent = False
            
            # Send main window to background after popup is dismissed
            self.lower()
            self.clearFocus()
            
            # DO NOT clear clipboard as requested - preserve clipboard content
            
            # ENSURE clipboard timer is restarted
            if hasattr(self, 'clipboard_timer'):
                if not self.clipboard_timer.isActive() and self.mode_active:
                    print("Restarting clipboard timer after rejection")
                    self.clipboard_timer.start(int(settings.check_interval * 1000))
    
    def add_to_context(self):
        """Add current clipboard content to context buffer."""
        with self.context_lock:
            print("Adding to context buffer")
            
            # Stop any timers
            if hasattr(self, 'popup_timer') and self.popup_timer:
                if self.popup_timer.isActive():
                    self.popup_timer.stop()
            
            # Stop the countdown in the prompt window
            if self.promptWindow and hasattr(self.promptWindow, 'stop_countdown'):
                self.promptWindow.stop_countdown()
                
            # Format and add content to context buffer
            user_prompt = self.promptWindow.getPromptText()
            formatted_content = f"--- Context Segment ---\n"
            formatted_content += f"{self.searchText}\n"
            if user_prompt:
                formatted_content += f"Note: {user_prompt}\n"
            formatted_content += f"---------------------\n\n"
            self.context_buffer += formatted_content
            
            # Reset state variables
            self.popup_active = False
            self.popup_permanent = False
            
            # DO NOT clear clipboard as requested - preserve clipboard content
            
            # Close the popup
            if self.promptWindow and self.promptWindow.isVisible():
                self.promptWindow.close()
            
            # ENSURE clipboard timer is restarted
            if hasattr(self, 'clipboard_timer'):
                if not self.clipboard_timer.isActive() and self.mode_active:
                    print("Restarting clipboard timer after adding to context")
                    self.clipboard_timer.start(int(settings.check_interval * 1000))
    
    def minimizeMainWindow(self):
        """Send the main window to back instead of minimizing to avoid clipboard monitoring issues."""
        self.lower()
        self.clearFocus()
        # Don't minimize as it might interfere with clipboard monitoring on macOS
    
    def openSettings(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Update the timer interval if it has changed
            self.clipboard_timer.setInterval(int(settings.check_interval * 1000))
    
    def openProjectManager(self):
        """Open the project manager dialog."""
        print("Opening Project Manager...")
        
        # CRITICAL: Preserve clipboard handler state before ANY operations
        handler_backup = self.clipboardHandler
        popup_state_backup = {
            'popup_active': self.popup_active,
            'popup_permanent': self.popup_permanent,
            'timer_active': hasattr(self, 'popup_timer') and self.popup_timer and self.popup_timer.isActive()
        }
        
        print(f"Backing up state - clipboardHandler: {handler_backup}")
        print(f"Backing up state - clipboardHandler type: {type(handler_backup)}")
        print(f"Backing up state - popup_active: {popup_state_backup['popup_active']}")
        
        # Check if project manager is already open
        if hasattr(self, 'project_manager_dialog') and self.project_manager_dialog.isVisible():
            # Bring existing dialog to front
            self.project_manager_dialog.raise_()
            self.project_manager_dialog.activateWindow()
            print("Project Manager already open - brought to front")
            return
        
        print(f"Before PM creation - clipboardHandler: {self.clipboardHandler}")
        
        # Create new non-modal project manager
        self.project_manager_dialog = ProjectManagerDialog(self)
        
        print(f"After PM creation - clipboardHandler: {self.clipboardHandler}")
        
        self.project_manager_dialog.show()  # Non-modal - allows interaction with main window
        
        print(f"After PM show - clipboardHandler: {self.clipboardHandler}")
        print("Project Manager created and shown")
        
        # CRITICAL: Always restore if handler is lost
        if not self.clipboardHandler and handler_backup:
            print("RESTORING lost clipboardHandler")
            self.clipboardHandler = handler_backup
        elif self.clipboardHandler != handler_backup:
            print(f"WARNING: clipboardHandler changed from {handler_backup} to {self.clipboardHandler}")
            print("FORCING restore of original handler")
            self.clipboardHandler = handler_backup
        
        # Only reset popup_permanent if no popup is currently active
        if not popup_state_backup['popup_active']:
            self.popup_permanent = False
            print("Reset popup_permanent to False (no active popup)")
        else:
            print("Preserving popup_permanent state (popup active)")
        
        print(f"Final state - clipboardHandler: {self.clipboardHandler}")
        print(f"Final state - clipboardHandler type: {type(self.clipboardHandler)}")
        print(f"Final state - popup_active: {self.popup_active}")
    
    def force_cleanup_popup(self):
        """Force cleanup of any existing popup to prevent threading issues."""
        print("FORCE CLEANUP: Cleaning up existing popup state")
        
        # Stop all timers immediately
        if hasattr(self, 'popup_timer') and self.popup_timer and self.popup_timer.isActive():
            print("FORCE CLEANUP: Stopping popup timer")
            self.popup_timer.stop()
        
        # Clean up popup window
        if hasattr(self, 'promptWindow') and self.promptWindow:
            print("FORCE CLEANUP: Cleaning up prompt window")
            try:
                if self.promptWindow.isVisible():
                    self.promptWindow.hide()
                if hasattr(self.promptWindow, 'stop_countdown'):
                    self.promptWindow.stop_countdown()
                self.promptWindow.deleteLater()
            except Exception as e:
                print(f"FORCE CLEANUP: Error cleaning popup: {e}")
        
        # Reset state variables
        self.promptWindow = None
        self.popup_active = False
        self.popup_permanent = False
        
        # Ensure clipboard timer is running if mode is active
        if self.mode_active and not self.clipboard_timer.isActive():
            print("FORCE CLEANUP: Restarting clipboard timer")
            self.clipboard_timer.start(int(settings.check_interval * 1000))
        
        print("FORCE CLEANUP: Popup state reset complete")
            


class ToggleButton(QPushButton):
    def __init__(self, text_on, text_off, parent=None):
        super().__init__(parent)
        self.text_on = text_on
        self.text_off = text_off
        self.is_toggled = True
        self.setText(self.text_on)
        self.clicked.connect(self.toggle)
        self.setStyleSheet("""
              QPushButton {
                color: white;
              }
              QPushButton:hover {
                background-color: #333333;
                color: white;
              }
              QToggleButton:hover {
                background-color: #333333;
              }
            """)

    def toggle(self):
        self.is_toggled = not self.is_toggled
        self.setText(self.text_on if self.is_toggled else self.text_off)


from PyQt5.QtWidgets import QDesktopWidget


class PromptWindow(QDialog):
    def __init__(self, parent=None, detection_text="", instant_matches=None):
        super().__init__(parent)
        self.history_visible = False
        self.context_visible = False
        self.context_text = ""
        self.detection_text = detection_text
        self.instant_matches = instant_matches or []
        self.selected_file_path = None
        self.timeout_remaining = 0
        self.countdown_timer = None
        self.is_dark_mode = self.detect_dark_mode()
        self.initUI()
    
    def detect_dark_mode(self):
        """Detect if the system is in dark mode."""
        palette = QApplication.instance().palette()
        window_color = palette.color(QPalette.Window)
        # Check if the window background is dark (low lightness)
        return window_color.lightness() < 128
    
    def get_button_style(self):
        """Get appropriate button style based on dark/light mode."""
        if self.is_dark_mode:
            # Dark mode - white text
            return """
                QPushButton {
                    color: white;
                }
            """
        else:
            # Light mode - use system default colors
            return ""
    
    def get_line_edit_style(self):
        """Get appropriate line edit style based on dark/light mode."""
        if self.is_dark_mode:
            # Dark mode - white text with semi-transparent background
            return """
                QLineEdit {
                    color: white;
                    background-color: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    padding: 5px;
                    border-radius: 3px;
                }
                QLineEdit:focus {
                    border: 1px solid rgba(255, 255, 255, 0.5);
                }
            """
        else:
            # Light mode - use system defaults
            return """
                QLineEdit {
                    padding: 5px;
                    border-radius: 3px;
                }
            """
    
    def get_combo_box_style(self):
        """Get appropriate combo box style based on dark/light mode."""
        if self.is_dark_mode:
            # Dark mode - white text
            return """
                QComboBox {
                    color: white;
                    background-color: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    padding: 5px;
                    border-radius: 3px;
                    min-width: 300px;
                }
                QComboBox:focus {
                    border: 1px solid rgba(255, 255, 255, 0.5);
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox::down-arrow {
                    width: 12px;
                    height: 12px;
                }
                QComboBox QAbstractItemView {
                    color: white;
                    background-color: #333333;
                    selection-background-color: #555555;
                }
            """
        else:
            # Light mode - dark text
            return """
                QComboBox {
                    padding: 5px;
                    border-radius: 3px;
                    min-width: 300px;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox::down-arrow {
                    width: 12px;
                    height: 12px;
                }
            """

    def getPromptText(self) -> str:
        """Get the text from the prompt input field."""
        return self.line_edit.text()
    
    def getProjectContextEnabled(self) -> bool:
        """Get the state of the project context checkbox."""
        return self.project_context_checkbox.isChecked()
    
    def getChatHistoryEnabled(self) -> bool:
        """Get the state of the chat history checkbox."""
        return self.chat_history_checkbox.isChecked()
    
    def getEditModeEnabled(self) -> bool:
        """Get the state of the edit mode checkbox."""
        # Edit mode disabled - always return False
        return False
        # return self.edit_mode_checkbox is not None and self.edit_mode_checkbox.isChecked()
    
    def update_context_preview(self, context_text):
        """Update the context preview with the current context buffer."""
        self.context_text = context_text
        if hasattr(self, 'context_preview') and self.context_preview:
            self.context_preview.setPlainText(context_text)
            # If context exists, make the toggle button visible
            if hasattr(self, 'context_toggle_button'):
                self.context_toggle_button.setVisible(bool(context_text))
    
    def on_edit_mode_changed(self, state):
        """Handle edit mode checkbox state change."""
        self.update_submit_button_text()
        
        # Update placeholder text
        if self.getEditModeEnabled():
            self.line_edit.setPlaceholderText("Describe the modifications you want to make to the file...")
        else:
            self.line_edit.setPlaceholderText("Enter a prompt...")
    
    def update_submit_button_text(self):
        """Update submit button text based on edit mode."""
        if hasattr(self, 'submit_button') and self.submit_button:
            if self.getEditModeEnabled():
                self.submit_button.setText("🔧 Generate Diff")
                self.submit_button.setStyleSheet("QPushButton { background-color: #ff6b35; color: white; font-weight: bold; }")
            else:
                self.submit_button.setText("Submit")
                self.submit_button.setStyleSheet(self.get_button_style())
        
    def initUI(self):
        self.setWindowTitle("Enter a prompt")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        main_layout = QVBoxLayout()
        
        # Timeout countdown
        self.timeout_label = QLabel("")
        self.timeout_label.setStyleSheet("color: #666; font-size: 12px;")
        main_layout.addWidget(self.timeout_label)

        # Project code detection display with file selection
        if self.instant_matches:
            if len(self.instant_matches) == 1:
                # Single match - show simple label
                file_path, file_name, confidence = self.instant_matches[0]
                self.selected_file_path = file_path
                detection_text = f"📄 Project file detected: {file_name} ({confidence:.0%} match)"
                self.detection_label = QLabel(detection_text)
                self.detection_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px; padding: 5px;")
                self.detection_label.setAlignment(Qt.AlignCenter)
                main_layout.addWidget(self.detection_label)
            else:
                # Multiple matches - show dropdown selection
                detection_label = QLabel(f"📄 {len(self.instant_matches)} project files detected - select one:")
                detection_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px; padding: 5px;")
                detection_label.setAlignment(Qt.AlignCenter)
                main_layout.addWidget(detection_label)
                
                # File selection dropdown
                self.file_selector = QComboBox()
                self.file_selector.setStyleSheet(self.get_combo_box_style())
                
                # Add "No file" option first
                self.file_selector.addItem("No file", None)
                
                # Populate dropdown with file options
                for file_path, file_name, confidence in self.instant_matches:
                    display_text = f"{file_name} ({confidence:.0%} match)"
                    self.file_selector.addItem(display_text, file_path)
                
                # Set default selection to highest confidence match if it exists
                if self.instant_matches:
                    # Select the first file (index 1, since "No file" is at index 0)
                    self.file_selector.setCurrentIndex(1)
                    self.selected_file_path = self.instant_matches[0][0]
                else:
                    # Default to "No file" 
                    self.selected_file_path = None
                
                # Connect selection change
                self.file_selector.currentIndexChanged.connect(self.on_file_selected)
                main_layout.addWidget(self.file_selector)
        elif self.detection_text:
            # Fallback for legacy detection_text parameter
            self.detection_label = QLabel(self.detection_text)
            self.detection_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px; padding: 5px;")
            self.detection_label.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(self.detection_label)

        # Prompt input
        self.line_edit = QLineEdit()
        self.line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.line_edit.setFocus()
        self.line_edit.setPlaceholderText("Enter a prompt...")
        self.line_edit.setMinimumWidth(220)
        self.line_edit.setStyleSheet(self.get_line_edit_style())
        main_layout.addWidget(self.line_edit)
        
        # Toggle buttons layout
        toggle_layout = QHBoxLayout()
        
        # History toggle button
        history_button = QPushButton("Show History")
        history_button.clicked.connect(self.toggle_history)
        history_button.setStyleSheet(self.get_button_style())
        toggle_layout.addWidget(history_button)
        
        # Context toggle button (only visible when context exists)
        self.context_toggle_button = QPushButton("Show Context")
        self.context_toggle_button.clicked.connect(self.toggle_context)
        self.context_toggle_button.setVisible(bool(self.context_text))  # Only visible if there's context
        self.context_toggle_button.setStyleSheet(self.get_button_style())
        toggle_layout.addWidget(self.context_toggle_button)
        
        main_layout.addLayout(toggle_layout)
        
        # History list (hidden by default)
        self.history_list = QListWidget()
        self.history_list.setVisible(False)
        self.history_list.setMaximumHeight(150)
        self.history_list.itemClicked.connect(self.select_history_item)
        self.update_history_list()
        main_layout.addWidget(self.history_list)
        
        # Context preview (hidden by default)
        self.context_preview = QTextEdit()
        self.context_preview.setReadOnly(True)
        self.context_preview.setVisible(False)
        self.context_preview.setMaximumHeight(150)
        if self.context_text:
            self.context_preview.setPlainText(self.context_text)
        main_layout.addWidget(self.context_preview)
        
        # Checkboxes row
        checkboxes_layout = QVBoxLayout()
        
        # Project context checkbox
        project_layout = QHBoxLayout()
        from PyQt5.QtWidgets import QCheckBox
        self.project_context_checkbox = QCheckBox("Include Project Context")
        self.project_context_checkbox.setToolTip("Include full project structure and summaries with your query")
        project_layout.addWidget(self.project_context_checkbox)
        project_layout.addStretch()
        checkboxes_layout.addLayout(project_layout)
        
        # Chat history checkbox
        history_layout = QHBoxLayout()
        self.chat_history_checkbox = QCheckBox("Include Chat History")
        self.chat_history_checkbox.setToolTip("Include previous conversation messages in the context")
        self.chat_history_checkbox.setChecked(True)  # Default to enabled (current behavior)
        history_layout.addWidget(self.chat_history_checkbox)
        history_layout.addStretch()
        checkboxes_layout.addLayout(history_layout)
        
        # Edit mode checkbox (only show when file is detected)
        # Commented out to remove edit mode button
        # if self.instant_matches:
        #     edit_layout = QHBoxLayout()
        #     self.edit_mode_checkbox = QCheckBox("📝 Edit Mode - Modify File")
        #     self.edit_mode_checkbox.setToolTip("Generate file modifications instead of chat response")
        #     self.edit_mode_checkbox.setStyleSheet("QCheckBox { color: #ff6b35; font-weight: bold; }")
        #     self.edit_mode_checkbox.stateChanged.connect(self.on_edit_mode_changed)
        #     edit_layout.addWidget(self.edit_mode_checkbox)
        #     edit_layout.addStretch()
        #     checkboxes_layout.addLayout(edit_layout)
        # else:
        #     self.edit_mode_checkbox = None
        self.edit_mode_checkbox = None
        
        main_layout.addLayout(checkboxes_layout)
        
        # Buttons row
        button_layout = QHBoxLayout()
        
        # Add to Context button
        self.add_context_button = QPushButton("Add to Context")
        self.add_context_button.setStyleSheet(self.get_button_style())
        button_layout.addWidget(self.add_context_button)
        
        # Submit button
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.accept)
        self.submit_button.setStyleSheet(self.get_button_style())
        button_layout.addWidget(self.submit_button)
        
        # Update submit button text based on edit mode
        self.update_submit_button_text()

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setStyleSheet(self.get_button_style())
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        # Dynamic size based on content
        self.setMinimumWidth(350)
        self.adjustSize()

        # Center the window on the screen
        self.center()

        # Initialize countdown timer
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.setInterval(100)  # Update every 100ms for smooth countdown
        
    
    def update_history_list(self):
        """Update the history list."""
        self.history_list.clear()
        
        # Get recent conversations from the current project
        try:
            conversations = project_manager.get_project_history(max_items=10)
            
            for conv in conversations:
                # Create a list item for each conversation
                user_msg = conv.get('user', '')
                if user_msg:
                    # Truncate long messages for display
                    display_text = user_msg[:50] + '...' if len(user_msg) > 50 else user_msg
                    
                    # Create list item
                    item = QListWidgetItem(display_text)
                    # Store full text in UserRole for retrieval
                    item.setData(Qt.UserRole, user_msg)
                    
                    # Add timestamp if available
                    timestamp = conv.get('timestamp')
                    if timestamp:
                        from datetime import datetime
                        dt = datetime.fromtimestamp(timestamp)
                        item.setToolTip(f"Sent at: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    self.history_list.addItem(item)
                    
        except Exception as e:
            print(f"Error loading history: {e}")
    
    def toggle_history(self):
        """Toggle the visibility of the history list."""
        self.history_visible = not self.history_visible
        self.history_list.setVisible(self.history_visible)
        
        # Hide context if showing history
        if self.history_visible and self.context_visible:
            self.toggle_context()
            
        # Adjust dialog size
        sender = self.sender()
        if sender:
            sender.setText("Hide History" if self.history_visible else "Show History")
        self.adjustSize()
    
    def toggle_context(self):
        """Toggle the visibility of the context preview."""
        self.context_visible = not self.context_visible
        self.context_preview.setVisible(self.context_visible)
        
        # Hide history if showing context
        if self.context_visible and self.history_visible:
            self.toggle_history()
            
        # Adjust dialog size
        sender = self.sender()
        if sender:
            sender.setText("Hide Context" if self.context_visible else "Show Context")
        self.adjustSize()

    def select_history_item(self, item):
        """Copy a history item to the prompt input."""
        if item:
            full_text = item.data(Qt.UserRole)
            self.line_edit.setText(full_text)

    def on_file_selected(self, index):
        """Handle file selection from dropdown."""
        if hasattr(self, 'file_selector') and index >= 0:
            self.selected_file_path = self.file_selector.itemData(index)
            print(f"Selected file: {self.selected_file_path}")

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def keyPressEvent(self, event: QKeyEvent):
        # Print all key events for debugging
        key_code = event.key()
        modifiers = event.modifiers()
        mod_text = []
        if modifiers & Qt.ControlModifier:
            mod_text.append("Ctrl")
        if modifiers & Qt.MetaModifier:
            mod_text.append("Cmd")
        if modifiers & Qt.ShiftModifier:
            mod_text.append("Shift")
        if modifiers & Qt.AltModifier:
            mod_text.append("Alt")
        mods = "+".join(mod_text) if mod_text else "None"
        print(f"POPUP KEY PRESS: Key code: {key_code} - Modifiers: {mods}")
        
        # Important: For Cmd+C, just let it propagate to the parent window's event filter
        if event.key() == Qt.Key_C and (modifiers & Qt.ControlModifier or modifiers & Qt.MetaModifier):
            print("Copy key combination detected in popup - letting event filter handle it")
            # Let standard event handling continue to ensure it reaches the global filter
            super().keyPressEvent(event)
            return
        
        # Process special keys    
        elif event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            print("Enter key - accepting dialog")
            self.accept()
            return
        
        # For Escape, use a very simple approach that prevents loops
        elif event.key() == Qt.Key_Escape:
            print("Escape key - closing dialog directly")
            # Just close the window directly to avoid any circular event handling
            self.hide()
            QTimer.singleShot(10, self.reject)
            return
        
        # Let standard event handling continue for other keys
        super().keyPressEvent(event)

    def activate_and_raise(self):
        self.activateWindow()
        self.raise_()
        
    def start_countdown(self, timeout_ms):
        """Start the countdown timer with the given timeout."""
        print(f"Starting countdown in PromptWindow with {timeout_ms}ms")
        self.timeout_remaining = timeout_ms / 1000  # Convert to seconds
        self.update_countdown()  # Initial update
        if self.countdown_timer:
            self.countdown_timer.start()
            print("Countdown timer started successfully")
        
    def update_timeout(self, timeout_ms):
        """Update the countdown timer with a new timeout."""
        print(f"PromptWindow.update_timeout called with {timeout_ms}ms")
        print(f"Old timeout_remaining: {self.timeout_remaining}")
        
        # Stop the current countdown timer
        if self.countdown_timer and self.countdown_timer.isActive():
            self.countdown_timer.stop()
            print("Stopped countdown timer for update")
        
        # Update timeout
        self.timeout_remaining = timeout_ms / 1000  # Convert to seconds
        print(f"New timeout_remaining: {self.timeout_remaining}")
        
        # Restart the countdown timer
        if self.countdown_timer:
            self.countdown_timer.start()
            print("Restarted countdown timer with new timeout")
        
        # Update display immediately
        self.update_countdown()
        
    def update_countdown(self):
        """Update the countdown display."""
        if self.timeout_remaining > 0:
            self.timeout_remaining -= 0.1  # Subtract 100ms
            if self.timeout_remaining < 0:
                self.timeout_remaining = 0
                
            # Format countdown with 1 decimal place
            seconds = max(0, round(self.timeout_remaining, 1))
            
            # Print countdown every second for debugging
            if seconds % 1.0 < 0.11:  # Print approximately once per second
                print(f"Countdown: {seconds:.1f}s remaining")
            
            # Change color based on remaining time
            if seconds < 1.0:
                color = "red"
            elif seconds < 2.0:
                color = "orange"
            else:
                color = "#666"
            
            # Get parent window to check counter state
            parent = QApplication.activeWindow()
            while parent and not isinstance(parent, TextWindow):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'popup_permanent'):
                if parent.popup_permanent:
                    # Popup is permanent - no countdown needed
                    self.timeout_label.setText(f"<span style='color:{color};'>Popup will stay open</span>")
                else:
                    self.timeout_label.setText(f"<span style='color:{color};'>Auto-close: {seconds}s</span>")
            else:
                self.timeout_label.setText(f"<span style='color:{color};'>Auto-close: {seconds}s</span>")
            
            # If countdown reaches zero, close the dialog, but only in normal states
            # Check parent window to ensure we're not in dismissing state (-1)
            parent = QApplication.activeWindow()
            while parent and not isinstance(parent, TextWindow):
                parent = parent.parent()
            
            # Only auto-close if popup is not permanent
            should_auto_close = True
            if parent and hasattr(parent, 'popup_permanent'):
                if parent.popup_permanent:  # Popup is permanent
                    should_auto_close = False
                    print("Not auto-closing since popup is permanent")
                    
            if seconds <= 0 and should_auto_close:
                print("Countdown reached zero - safely closing dialog")
                self.countdown_timer.stop()
                self.timeout_label.setText("")
                # Hide window first for visual feedback
                self.hide()
                # Force dialog to close via reject() after a tiny delay
                QTimer.singleShot(100, self.reject)
        else:
            # Same logic as above, only auto-close if in normal state
            parent = QApplication.activeWindow()
            while parent and not isinstance(parent, TextWindow):
                parent = parent.parent()
                
            should_auto_close = True
            if parent and hasattr(parent, 'popup_permanent'):
                if parent.popup_permanent:  # Popup is permanent
                    should_auto_close = False
                    
            if should_auto_close:
                print("Countdown reached zero")
                self.countdown_timer.stop()
                self.timeout_label.setText("")
                # Hide window first for visual feedback
                self.hide()
                # Force dialog to close with a safe delay
                QTimer.singleShot(100, self.reject)
        
    def stop_countdown(self):
        """Stop the countdown timer."""
        self.countdown_timer.stop()
        self.timeout_label.setText("")