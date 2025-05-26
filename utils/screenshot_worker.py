import os
import time
from PyQt5.QtCore import QThread, pyqtSignal


class ScreenshotWorker(QThread):

    screenshot_updated = pyqtSignal(str)

    def __init__(self, Anthropic_API, parent=None):
        super().__init__(parent)
        self.Anthropic_API = Anthropic_API

    def run(self):
        # Directory where screenshots are saved (assuming it's the desktop)
        desktop_path = os.path.expanduser("~/Desktop")

        # Variables to store the latest screenshots
        context = None
        main = None

        while True:
            # List all files on the desktop
            files = os.listdir(desktop_path)

            # Filter only the screenshot files
            screenshot_files = [file for file in files if file.startswith("Screenshot") or file.startswith("Screen Shot")]

            # Sort screenshot files based on timestamp
            sorted_screenshots = sorted(screenshot_files, key=lambda x: os.path.getmtime(os.path.join(desktop_path, x)), reverse=True)

            # Extract the latest 2 screenshots
            latest_two_screenshots = sorted_screenshots[:2]

            # Convert screenshot names to full image paths and encode them
            latest_screenshot_paths = [os.path.join(desktop_path, name) for name in latest_two_screenshots]

            # Check if the images have changed
            if len(latest_screenshot_paths) >= 2:
                if (context != latest_screenshot_paths[1]) or (main != latest_screenshot_paths[0]):
                    # Update context and main variables
                    if not context or not main:
                        context = latest_screenshot_paths[1]  # older screenshot
                        main = latest_screenshot_paths[0]     # newer screenshot
                        continue
                    else:
                        context = latest_screenshot_paths[1]  # older screenshot
                        main = latest_screenshot_paths[0]     # newer screenshot

                    main_response = self.Anthropic_API.send_image_to_anthropic(latest_screenshot_paths[0])

                    print("\n" * 100)
                    print(main_response)
                    
                    # Emit a signal to notify the main thread
                    self.screenshot_updated.emit(main_response)

            # Wait for 5 seconds before checking again
            time.sleep(1)