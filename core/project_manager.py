import os
import json
import time
from pathlib import Path

class ProjectManager:
    """
    Manages project-specific chat histories and context.
    
    This class handles project creation, selection, and history management.
    Each project maintains its own chat history and context buffer.
    """
    
    def __init__(self):
        """Initialize the project manager."""
        self.base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "projects")
        self._ensure_directory_exists(self.base_path)
        self.current_project = "default"
        self.projects = self._load_projects()
        self._ensure_project_exists(self.current_project)
    
    def _ensure_directory_exists(self, directory):
        """Create directory if it doesn't exist."""
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    def _load_projects(self):
        """Load existing projects from disk."""
        projects = []
        try:
            for item in os.listdir(self.base_path):
                if os.path.isdir(os.path.join(self.base_path, item)):
                    projects.append(item)
            
            if not projects:
                # Create default project if none exist
                self._create_project_directory("default")
                projects = ["default"]
            
            return projects
        except Exception as e:
            print(f"Error loading projects: {e}")
            # Ensure at least default project exists
            self._create_project_directory("default")
            return ["default"]
    
    def _create_project_directory(self, project_name):
        """Create a new project directory and initialize files."""
        project_path = os.path.join(self.base_path, project_name)
        self._ensure_directory_exists(project_path)
        
        # Create initial history file
        history_path = os.path.join(project_path, "history.json")
        if not os.path.exists(history_path):
            initial_history = {
                "conversations": [],
                "metadata": {
                    "created": time.time(),
                    "last_accessed": time.time()
                }
            }
            with open(history_path, 'w') as f:
                json.dump(initial_history, f, indent=2)
    
    def _ensure_project_exists(self, project_name):
        """Ensure the specified project exists, create if it doesn't."""
        if project_name not in self.projects:
            self._create_project_directory(project_name)
            self.projects.append(project_name)
    
    def create_project(self, project_name):
        """
        Create a new project.
        
        Args:
            project_name: Name of the new project
            
        Returns:
            bool: True if created successfully, False if already exists
        """
        if project_name in self.projects:
            return False
        
        self._create_project_directory(project_name)
        self.projects.append(project_name)
        return True
    
    def select_project(self, project_name):
        """
        Select a project as the current active project.
        
        Args:
            project_name: Name of the project to select
            
        Returns:
            bool: True if selection successful, False if project doesn't exist
        """
        self._ensure_project_exists(project_name)
        self.current_project = project_name
        
        # Update last accessed time
        history_path = os.path.join(self.base_path, project_name, "history.json")
        try:
            with open(history_path, 'r') as f:
                history = json.load(f)
            
            history["metadata"]["last_accessed"] = time.time()
            
            with open(history_path, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"Error updating project access time: {e}")
        
        return True
    
    def get_project_history(self, project_name=None, max_items=5):
        """
        Get recent conversation history for a project.
        
        Args:
            project_name: Name of the project (uses current if None)
            max_items: Maximum number of conversation pairs to retrieve
            
        Returns:
            list: Recent conversations as list of user/assistant message pairs
        """
        if project_name is None:
            project_name = self.current_project
        
        self._ensure_project_exists(project_name)
        history_path = os.path.join(self.base_path, project_name, "history.json")
        
        try:
            with open(history_path, 'r') as f:
                history = json.load(f)
            
            # Return the most recent conversations (up to max_items)
            return history["conversations"][-max_items:] if history["conversations"] else []
        except Exception as e:
            print(f"Error retrieving project history: {e}")
            return []
    
    def add_conversation(self, user_message, assistant_response, project_name=None):
        """
        Add a conversation pair to project history.
        
        Args:
            user_message: The user's message
            assistant_response: The assistant's response
            project_name: Name of the project (uses current if None)
            
        Returns:
            bool: True if added successfully
        """
        if project_name is None:
            project_name = self.current_project
        
        self._ensure_project_exists(project_name)
        history_path = os.path.join(self.base_path, project_name, "history.json")
        
        try:
            with open(history_path, 'r') as f:
                history = json.load(f)
            
            # Add the new conversation
            history["conversations"].append({
                "user": user_message,
                "assistant": assistant_response,
                "timestamp": time.time()
            })
            
            # Update last accessed time
            history["metadata"]["last_accessed"] = time.time()
            
            with open(history_path, 'w') as f:
                json.dump(history, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error adding conversation to project: {e}")
            return False
    
    def get_project_list(self, sort_by_recent=True):
        """
        Get list of available projects.
        
        Args:
            sort_by_recent: If True, sorts projects by last accessed time
            
        Returns:
            list: Project names
        """
        if not sort_by_recent:
            return self.projects
        
        # Sort projects by last accessed time
        project_times = []
        for project in self.projects:
            history_path = os.path.join(self.base_path, project, "history.json")
            try:
                with open(history_path, 'r') as f:
                    history = json.load(f)
                last_accessed = history["metadata"].get("last_accessed", 0)
                project_times.append((project, last_accessed))
            except:
                project_times.append((project, 0))
        
        # Sort by last accessed time (descending)
        project_times.sort(key=lambda x: x[1], reverse=True)
        return [project for project, _ in project_times]
    
    def delete_project(self, project_name):
        """
        Delete a project and all its history.
        
        Args:
            project_name: Name of the project to delete
            
        Returns:
            bool: True if deleted successfully
        """
        if project_name == "default":
            # Don't allow deleting the default project
            return False
        
        if project_name not in self.projects:
            return False
        
        try:
            import shutil
            project_path = os.path.join(self.base_path, project_name)
            shutil.rmtree(project_path)
            self.projects.remove(project_name)
            
            # Select default project if we deleted the current one
            if project_name == self.current_project:
                self.current_project = "default"
            
            return True
        except Exception as e:
            print(f"Error deleting project: {e}")
            return False
    
    def get_current_project(self):
        """Get the name of the current project."""
        return self.current_project

# Create a singleton instance
project_manager = ProjectManager()