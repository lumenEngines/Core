import os
import json
import time
import hashlib
from typing import Dict, List, Optional
from pathlib import Path


class FileTracker:
    """
    Tracks file changes and logs AI modifications to project files.
    """
    
    def __init__(self, storage_path: str = None):
        """
        Initialize the file tracker.
        
        Args:
            storage_path: Path to store tracking data
        """
        if storage_path is None:
            storage_path = os.path.join(os.path.dirname(__file__), "file_tracking")
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        self.tracked_files = {}
        self.modification_log = []
        
        self._load_tracking_data()
    
    def _load_tracking_data(self):
        """Load existing tracking data from storage."""
        tracking_file = self.storage_path / "file_tracking.json"
        if tracking_file.exists():
            try:
                with open(tracking_file, 'r') as f:
                    data = json.load(f)
                self.tracked_files = data.get('tracked_files', {})
                self.modification_log = data.get('modification_log', [])
            except Exception as e:
                print(f"Error loading tracking data: {e}")
                self.tracked_files = {}
                self.modification_log = []
    
    def _save_tracking_data(self):
        """Save tracking data to storage."""
        tracking_file = self.storage_path / "file_tracking.json"
        try:
            data = {
                'tracked_files': self.tracked_files,
                'modification_log': self.modification_log
            }
            with open(tracking_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving tracking data: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> Optional[str]:
        """Calculate MD5 hash of file content."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except Exception as e:
            print(f"Error calculating hash for {file_path}: {e}")
            return None
    
    def start_tracking_file(self, file_path: str) -> bool:
        """
        Start tracking a file for changes.
        
        Args:
            file_path: Path to the file to track
            
        Returns:
            True if tracking started successfully
        """
        try:
            file_path = str(Path(file_path).resolve())
            
            if not os.path.exists(file_path):
                print(f"File does not exist: {file_path}")
                return False
            
            # Calculate initial hash
            file_hash = self._calculate_file_hash(file_path)
            if file_hash is None:
                return False
            
            # Get file stats
            stat = os.stat(file_path)
            
            self.tracked_files[file_path] = {
                'initial_hash': file_hash,
                'current_hash': file_hash,
                'size': stat.st_size,
                'modified_time': stat.st_mtime,
                'tracked_since': time.time(),
                'ai_modifications': 0
            }
            
            self._save_tracking_data()
            print(f"Started tracking file: {os.path.basename(file_path)}")
            return True
            
        except Exception as e:
            print(f"Error starting tracking for {file_path}: {e}")
            return False
    
    def stop_tracking_file(self, file_path: str) -> bool:
        """
        Stop tracking a file.
        
        Args:
            file_path: Path to the file to stop tracking
            
        Returns:
            True if tracking stopped successfully
        """
        try:
            file_path = str(Path(file_path).resolve())
            
            if file_path in self.tracked_files:
                del self.tracked_files[file_path]
                self._save_tracking_data()
                print(f"Stopped tracking file: {os.path.basename(file_path)}")
                return True
            else:
                print(f"File not being tracked: {file_path}")
                return False
                
        except Exception as e:
            print(f"Error stopping tracking for {file_path}: {e}")
            return False
    
    def track_project_files(self, file_paths: List[str]) -> int:
        """
        Start tracking multiple project files.
        
        Args:
            file_paths: List of file paths to track
            
        Returns:
            Number of files successfully tracked
        """
        successful = 0
        for file_path in file_paths:
            if self.start_tracking_file(file_path):
                successful += 1
        
        print(f"Started tracking {successful}/{len(file_paths)} files")
        return successful
    
    def check_for_changes(self) -> List[Dict]:
        """
        Check all tracked files for changes.
        
        Returns:
            List of dictionaries containing change information
        """
        changes = []
        
        for file_path, tracking_data in self.tracked_files.items():
            try:
                if not os.path.exists(file_path):
                    # File was deleted
                    changes.append({
                        'file_path': file_path,
                        'change_type': 'deleted',
                        'timestamp': time.time()
                    })
                    continue
                
                # Check if file was modified
                stat = os.stat(file_path)
                current_hash = self._calculate_file_hash(file_path)
                
                if current_hash != tracking_data['current_hash']:
                    # File was modified
                    change_info = {
                        'file_path': file_path,
                        'change_type': 'modified',
                        'timestamp': time.time(),
                        'old_hash': tracking_data['current_hash'],
                        'new_hash': current_hash,
                        'size_change': stat.st_size - tracking_data['size']
                    }
                    changes.append(change_info)
                    
                    # Update tracking data
                    tracking_data['current_hash'] = current_hash
                    tracking_data['size'] = stat.st_size
                    tracking_data['modified_time'] = stat.st_mtime
                
            except Exception as e:
                print(f"Error checking file {file_path}: {e}")
        
        if changes:
            self._save_tracking_data()
        
        return changes
    
    def log_ai_modification(self, file_path: str, action: str, description: str = "", 
                           line_range: Optional[tuple] = None) -> bool:
        """
        Log an AI modification to a file.
        
        Args:
            file_path: Path to the modified file
            action: Type of action (e.g., 'write', 'edit', 'append')
            description: Description of what was done
            line_range: Optional tuple of (start_line, end_line) for edits
            
        Returns:
            True if logged successfully
        """
        try:
            file_path = str(Path(file_path).resolve())
            
            modification_entry = {
                'timestamp': time.time(),
                'timestamp_human': time.ctime(),
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'action': action,
                'description': description,
                'line_range': line_range
            }
            
            self.modification_log.append(modification_entry)
            
            # Update tracked file if it exists
            if file_path in self.tracked_files:
                self.tracked_files[file_path]['ai_modifications'] += 1
                
                # Update hash if file exists
                if os.path.exists(file_path):
                    new_hash = self._calculate_file_hash(file_path)
                    if new_hash:
                        self.tracked_files[file_path]['current_hash'] = new_hash
            
            self._save_tracking_data()
            print(f"Logged AI modification: {action} on {os.path.basename(file_path)}")
            return True
            
        except Exception as e:
            print(f"Error logging AI modification: {e}")
            return False
    
    def get_file_modifications(self, file_path: str = None) -> List[Dict]:
        """
        Get modification history for a file or all files.
        
        Args:
            file_path: Optional specific file path to filter by
            
        Returns:
            List of modification entries
        """
        if file_path is None:
            return self.modification_log.copy()
        
        file_path = str(Path(file_path).resolve())
        return [entry for entry in self.modification_log if entry['file_path'] == file_path]
    
    def get_tracked_files(self) -> Dict[str, Dict]:
        """Get dictionary of all tracked files and their status."""
        return self.tracked_files.copy()
    
    def get_recent_modifications(self, hours: int = 24) -> List[Dict]:
        """
        Get AI modifications from the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of recent modification entries
        """
        cutoff_time = time.time() - (hours * 3600)
        return [entry for entry in self.modification_log if entry['timestamp'] >= cutoff_time]
    
    def generate_tracking_report(self) -> str:
        """
        Generate a human-readable tracking report.
        
        Returns:
            Formatted report string
        """
        report = "File Tracking Report\n"
        report += "=" * 50 + "\n\n"
        
        # Tracked files summary
        report += f"Tracked Files: {len(self.tracked_files)}\n"
        report += f"Total AI Modifications: {len(self.modification_log)}\n\n"
        
        # Recent modifications (last 24 hours)
        recent_mods = self.get_recent_modifications(24)
        report += f"Recent Modifications (24h): {len(recent_mods)}\n\n"
        
        if recent_mods:
            report += "Recent AI Modifications:\n"
            report += "-" * 30 + "\n"
            for mod in recent_mods[-10:]:  # Last 10 modifications
                report += f"{mod['timestamp_human']}: {mod['action']} - {mod['file_name']}\n"
                if mod['description']:
                    report += f"  Description: {mod['description']}\n"
                report += "\n"
        
        # File status
        if self.tracked_files:
            report += "Tracked File Status:\n"
            report += "-" * 30 + "\n"
            for file_path, data in self.tracked_files.items():
                file_name = os.path.basename(file_path)
                report += f"{file_name}:\n"
                report += f"  AI Modifications: {data['ai_modifications']}\n"
                report += f"  Tracked since: {time.ctime(data['tracked_since'])}\n"
                report += f"  Current size: {data['size']} bytes\n\n"
        
        return report


# Create singleton instance
file_tracker = FileTracker()