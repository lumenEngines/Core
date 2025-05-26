import os
import json
import hashlib
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

class FileAnalyzer:
    """
    Analyzes project files to create summaries and build project context.
    """
    
    IGNORED_EXTENSIONS = {
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib',
        '.class', '.jar', '.war', '.ear',
        '.o', '.obj', '.lib', '.a',
        '.tmp', '.temp', '.log', '.cache',
        '.git', '.svn', '.hg',
        '.DS_Store', 'Thumbs.db',
        '.egg-info', '.dist-info',
        '__pycache__',
        # Media files - never include these
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv',
        '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg', '.webp',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
        '.exe', '.msi', '.dmg', '.deb', '.rpm',
        '.iso', '.img', '.bin', '.cue'
    }
    
    IGNORED_DIRECTORIES = {
        'node_modules', '.git', '.svn', '.hg', '__pycache__',
        '.pytest_cache', '.mypy_cache', '.coverage',
        'dist', 'build', 'target', 'out', 'bin',
        '.venv', 'venv', 'env', '.env',
        '.idea', '.vscode', '.vs',
        'logs', 'temp', 'tmp'
    }
    
    LIBRARY_INDICATORS = {
        'node_modules', 'site-packages', 'dist-packages',
        'vendor', 'third_party', 'external',
        '.cargo', '.gem', '.npm'
    }
    
    def __init__(self, max_workers: int = 4):
        """Initialize the file analyzer with thread pool."""
        self.max_workers = max_workers
        self.max_file_size = 10 * 1024 * 1024  # 10MB max file size
        
    def is_user_file(self, file_path: str) -> bool:
        """
        Determine if a file is user-built (not a library/dependency).
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if it's a user-built file
        """
        try:
            path = Path(file_path)
            
            # Check file size first (fastest check)
            if os.path.getsize(file_path) > self.max_file_size:
                print(f"Skipping large file: {os.path.basename(file_path)} ({os.path.getsize(file_path):,} bytes)")
                return False
            
            # Check if any parent directory indicates a library
            for part in path.parts:
                if part.lower() in self.LIBRARY_INDICATORS:
                    return False
                if part.startswith('.') and part in self.IGNORED_DIRECTORIES:
                    return False
                    
            # Check file extension
            if path.suffix.lower() in self.IGNORED_EXTENSIONS:
                return False
                
            # Check directory name
            if path.parent.name.lower() in self.IGNORED_DIRECTORIES:
                return False
                
            return True
            
        except (OSError, IOError):
            # Skip files that can't be accessed
            return False
    
    def discover_user_files(self, project_path: str) -> List[str]:
        """
        Discover all user-built files in a project directory.
        
        Args:
            project_path: Root path of the project
            
        Returns:
            List of file paths for user-built files
        """
        user_files = []
        project_path = Path(project_path)
        
        try:
            for root, dirs, files in os.walk(project_path):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRECTORIES]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    if self.is_user_file(file_path):
                        user_files.append(file_path)
                        
        except Exception as e:
            print(f"Error discovering files: {e}")
            
        return sorted(user_files)
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except:
            return 0
    
    def categorize_files_by_size(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        Categorize files by size for batching API calls.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Dictionary with size categories as keys
        """
        categories = {
            'small': [],    # < 5KB
            'medium': [],   # 5KB - 50KB  
            'large': []     # > 50KB
        }
        
        for file_path in file_paths:
            size = self.get_file_size(file_path)
            if size < 5 * 1024:  # 5KB
                categories['small'].append(file_path)
            elif size < 50 * 1024:  # 50KB
                categories['medium'].append(file_path)
            else:
                categories['large'].append(file_path)
                
        return categories


class TextComparator:
    """
    Efficient text comparison algorithm for matching copied content to project files.
    """
    
    def __init__(self):
        """Initialize the text comparator."""
        self.file_hashes = {}
        self.normalized_content = {}
        
    def normalize_text(self, text: str) -> str:
        """
        Normalize text by removing whitespace and newlines for comparison.
        
        Args:
            text: Raw text content
            
        Returns:
            Normalized text
        """
        # Remove all whitespace and newlines, convert to lowercase
        normalized = re.sub(r'\s+', '', text.lower())
        return normalized
    
    def create_content_hash(self, content: str) -> str:
        """
        Create a hash of normalized content for fast lookup.
        
        Args:
            content: Text content
            
        Returns:
            Hash string
        """
        normalized = self.normalize_text(content)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def index_file_content(self, file_path: str, content: str):
        """
        Index file content for fast comparison.
        
        Args:
            file_path: Path to the file
            content: File content
        """
        normalized = self.normalize_text(content)
        content_hash = self.create_content_hash(content)
        
        self.file_hashes[content_hash] = file_path
        self.normalized_content[file_path] = normalized
    
    def find_matching_files(self, copied_text: str, threshold: float = 0.8) -> List[Tuple[str, float]]:
        """
        Find files that match the copied text.
        
        Args:
            copied_text: Text that was copied
            threshold: Minimum similarity threshold (0.0 to 1.0)
            
        Returns:
            List of (file_path, similarity_score) tuples
        """
        if not copied_text.strip():
            return []
            
        normalized_query = self.normalize_text(copied_text)
        
        # First try exact hash match
        query_hash = self.create_content_hash(copied_text)
        if query_hash in self.file_hashes:
            return [(self.file_hashes[query_hash], 1.0)]
        
        # Then try substring matching
        matches = []
        for file_path, normalized_content in self.normalized_content.items():
            if normalized_query in normalized_content:
                # Calculate similarity score based on length ratio
                similarity = len(normalized_query) / len(normalized_content)
                if similarity >= threshold:
                    matches.append((file_path, similarity))
        
        # Sort by similarity score (descending)
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:5]  # Return top 5 matches


class ProjectLinker:
    """
    Main class for managing project linking functionality.
    """
    
    def __init__(self, storage_path: str = None):
        """
        Initialize the project linker.
        
        Args:
            storage_path: Path to store project data
        """
        if storage_path is None:
            storage_path = os.path.join(os.path.dirname(__file__), "linked_projects")
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        self.file_analyzer = FileAnalyzer()
        self.text_comparator = TextComparator()
        self.linked_projects = {}
        self.current_project = None  # Don't auto-load any project
        
        self._load_linked_projects()
        self._validate_and_clean_projects()
    
    def _load_linked_projects(self):
        """Load existing linked projects from storage."""
        projects_file = self.storage_path / "projects.json"
        if projects_file.exists():
            try:
                with open(projects_file, 'r') as f:
                    self.linked_projects = json.load(f)
            except Exception as e:
                print(f"Error loading linked projects: {e}")
                self.linked_projects = {}
    
    def _save_linked_projects(self):
        """Save linked projects to storage."""
        projects_file = self.storage_path / "projects.json"
        try:
            with open(projects_file, 'w') as f:
                json.dump(self.linked_projects, f, indent=2)
        except Exception as e:
            print(f"Error saving linked projects: {e}")
    
    def _validate_and_clean_projects(self):
        """Validate and clean corrupted or problematic projects."""
        projects_to_remove = []
        
        for project_name, project_data in self.linked_projects.items():
            try:
                # Check if project path still exists
                project_path = project_data.get("path", "")
                if not os.path.exists(project_path):
                    print(f"Removing project '{project_name}' - path no longer exists: {project_path}")
                    projects_to_remove.append(project_name)
                    continue
                
                # Check if files list is reasonable (not too many huge files)
                files = project_data.get("files", [])
                if len(files) > 10000:  # Suspiciously large number of files
                    print(f"Removing project '{project_name}' - too many files ({len(files)})")
                    projects_to_remove.append(project_name)
                    continue
                
                # Check for corrupted file data
                valid_files = []
                for file_path in files:
                    try:
                        if os.path.exists(file_path) and self.file_analyzer.is_user_file(file_path):
                            valid_files.append(file_path)
                    except:
                        continue  # Skip problematic files
                
                # Update with cleaned file list
                project_data["files"] = valid_files
                
                # Reset indexed status to force re-indexing with new file filter
                project_data["indexed"] = False
                
                print(f"Cleaned project '{project_name}': {len(files)} -> {len(valid_files)} files")
                
            except Exception as e:
                print(f"Error validating project '{project_name}': {e}")
                projects_to_remove.append(project_name)
        
        # Remove problematic projects
        for project_name in projects_to_remove:
            del self.linked_projects[project_name]
        
        if projects_to_remove:
            self._save_linked_projects()
            print(f"Removed {len(projects_to_remove)} problematic projects")
    
    def link_project(self, project_name: str, project_path: str) -> bool:
        """
        Link a project directory to Lumen.
        
        Args:
            project_name: Name for the project
            project_path: Path to the project directory
            
        Returns:
            bool: True if successful
        """
        try:
            project_path = str(Path(project_path).resolve())
            
            if not os.path.exists(project_path):
                raise ValueError(f"Project path does not exist: {project_path}")
            
            if not os.path.isdir(project_path):
                raise ValueError(f"Project path is not a directory: {project_path}")
            
            # Discover user files
            print(f"Discovering files in {project_path}...")
            user_files = self.file_analyzer.discover_user_files(project_path)
            
            # Create project data structure
            project_data = {
                "name": project_name,
                "path": project_path,
                "linked_at": time.time(),
                "files": user_files,
                "summaries": {},
                "indexed": False
            }
            
            # Store project data
            self.linked_projects[project_name] = project_data
            self._save_linked_projects()
            
            # Auto-select this project as current
            self.current_project = project_name
            
            print(f"Successfully linked project '{project_name}' with {len(user_files)} files")
            return True
            
        except Exception as e:
            print(f"Error linking project: {e}")
            return False
    
    def remove_project(self, project_name: str) -> bool:
        """
        Remove a linked project.
        
        Args:
            project_name: Name of the project to remove
            
        Returns:
            bool: True if successful
        """
        try:
            if project_name not in self.linked_projects:
                return False
            
            # Remove project data
            del self.linked_projects[project_name]
            self._save_linked_projects()
            
            # Clear current project if it was removed
            if self.current_project == project_name:
                self.current_project = None
            
            print(f"Successfully removed project '{project_name}'")
            return True
            
        except Exception as e:
            print(f"Error removing project: {e}")
            return False
    
    def get_linked_projects(self) -> List[str]:
        """Get list of linked project names."""
        return list(self.linked_projects.keys())
    
    def select_project(self, project_name: str) -> bool:
        """
        Select a project as the current active project.
        
        Args:
            project_name: Name of the project to select
            
        Returns:
            bool: True if successful
        """
        if project_name not in self.linked_projects:
            return False
        
        self.current_project = project_name
        print(f"Selected project '{project_name}' - indexing disabled for performance")
        
        # DON'T auto-index - let it be lazy loaded only when needed
        # This prevents infinite loading on large projects
        # if not self.linked_projects[project_name].get("indexed", False):
        #     self._index_project_files(project_name)
            
        return True
    
    def _index_project_files(self, project_name: str):
        """
        Index project files for text comparison.
        
        Args:
            project_name: Name of the project to index
        """
        try:
            project_data = self.linked_projects[project_name]
            
            print(f"Indexing files for project '{project_name}'...")
            
            for file_path in project_data["files"]:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    self.text_comparator.index_file_content(file_path, content)
                except Exception as e:
                    print(f"Error indexing file {file_path}: {e}")
            
            # Mark as indexed
            project_data["indexed"] = True
            self._save_linked_projects()
            
            print(f"Successfully indexed {len(project_data['files'])} files")
            
        except Exception as e:
            print(f"Error indexing project files: {e}")
    
    def find_source_files(self, copied_text: str) -> List[Tuple[str, float]]:
        """
        Find source files that match copied text.
        
        Args:
            copied_text: Text that was copied
            
        Returns:
            List of (file_path, similarity_score) tuples
        """
        if not self.current_project:
            return []
        
        return self.text_comparator.find_matching_files(copied_text)
    
    def get_project_summary(self, project_name: str = None) -> str:
        """
        Get a summary of the project structure and files.
        
        Args:
            project_name: Name of the project (uses current if None)
            
        Returns:
            Project summary string
        """
        if project_name is None:
            project_name = self.current_project
        
        if not project_name or project_name not in self.linked_projects:
            return "No project selected or project not found."
        
        project_data = self.linked_projects[project_name]
        
        summary = f"Project: {project_data['name']}\n"
        summary += f"Path: {project_data['path']}\n"
        summary += f"Files: {len(project_data['files'])}\n"
        summary += f"Linked: {time.ctime(project_data['linked_at'])}\n\n"
        
        # Group files by directory
        file_tree = {}
        for file_path in project_data["files"]:
            rel_path = os.path.relpath(file_path, project_data['path'])
            dir_path = os.path.dirname(rel_path)
            if dir_path not in file_tree:
                file_tree[dir_path] = []
            file_tree[dir_path].append(os.path.basename(rel_path))
        
        summary += "File Structure:\n"
        for dir_path, files in sorted(file_tree.items()):
            if dir_path == '.':
                summary += "Root:\n"
            else:
                summary += f"{dir_path}/:\n"
            for file in sorted(files):
                summary += f"  - {file}\n"
            summary += "\n"
        
        return summary


# Create singleton instance
project_linker = ProjectLinker()