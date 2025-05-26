import os
import json
from pathlib import Path

class Settings:
    """
    Manages application settings with persistence to disk.
    
    This class handles reading and writing application settings to a JSON file,
    providing default values when settings don't exist, and exposing properties
    for common settings access.
    """
    
    # Default settings values
    DEFAULT_SETTINGS = {
        "clipboard": {
            "short_timeout": 1.0,    # Short timeout in seconds (for counter=2)
            "extended_timeout": 60.0,  # Extended timeout in seconds (for counter=1)
            "check_interval": 0.5,    # Clipboard check interval in seconds
            "preserve_clipboard": True,  # Whether to preserve clipboard content when popup is dismissed
        }
    }
    
    def __init__(self):
        """Initialize the settings manager and load settings from disk."""
        self._settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_settings.json")
        self._settings = self._load_settings()
    
    def _load_settings(self):
        """Load settings from disk, or create default settings if file doesn't exist."""
        try:
            if os.path.exists(self._settings_path):
                with open(self._settings_path, 'r') as f:
                    settings = json.load(f)
                
                # Update with any missing default settings
                for category, values in self.DEFAULT_SETTINGS.items():
                    if category not in settings:
                        settings[category] = {}
                    for key, value in values.items():
                        if key not in settings[category]:
                            settings[category][key] = value
                
                return settings
            else:
                return self.DEFAULT_SETTINGS.copy()
        except Exception as e:
            print(f"Error loading settings: {e}")
            return self.DEFAULT_SETTINGS.copy()
    
    def save(self):
        """Save current settings to disk."""
        try:
            with open(self._settings_path, 'w') as f:
                json.dump(self._settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get(self, category, key, default=None):
        """
        Get a setting value.
        
        Args:
            category: The settings category (e.g., 'clipboard')
            key: The setting key name
            default: Default value if setting doesn't exist
            
        Returns:
            The setting value or default if not found
        """
        try:
            return self._settings.get(category, {}).get(key, default)
        except:
            return default
    
    def set(self, category, key, value):
        """
        Set a setting value and save to disk.
        
        Args:
            category: The settings category (e.g., 'clipboard')
            key: The setting key name
            value: The value to set
        """
        if category not in self._settings:
            self._settings[category] = {}
        
        self._settings[category][key] = value
        self.save()
    
    # Properties for common settings
    @property
    def short_timeout(self):
        """Get the short timeout for clipboard popup (seconds)."""
        return self.get('clipboard', 'short_timeout', 1.0)
    
    @short_timeout.setter
    def short_timeout(self, value):
        """Set the short timeout for clipboard popup."""
        self.set('clipboard', 'short_timeout', float(value))
    
    @property
    def extended_timeout(self):
        """Get the extended timeout for clipboard popup (seconds)."""
        return self.get('clipboard', 'extended_timeout', 60.0)
    
    @extended_timeout.setter
    def extended_timeout(self, value):
        """Set the extended timeout for clipboard popup."""
        self.set('clipboard', 'extended_timeout', float(value))
    
    @property
    def check_interval(self):
        """Get the clipboard check interval (seconds)."""
        return self.get('clipboard', 'check_interval', 0.5)
    
    @check_interval.setter
    def check_interval(self, value):
        """Set the clipboard check interval."""
        self.set('clipboard', 'check_interval', float(value))
    
    @property
    def preserve_clipboard(self):
        """Get whether to preserve clipboard content when popup is dismissed."""
        return self.get('clipboard', 'preserve_clipboard', True)
    
    @preserve_clipboard.setter
    def preserve_clipboard(self, value):
        """Set whether to preserve clipboard content when popup is dismissed."""
        self.set('clipboard', 'preserve_clipboard', bool(value))


# Create a singleton instance
settings = Settings()