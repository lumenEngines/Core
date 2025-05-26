import os
import json
import time
import asyncio
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading

# Import isolated API for Project Manager
from api.isolated_api import isolated_api_manager


class FileSummarizer:
    """
    Handles parallel file summarization using selected LLM APIs.
    """
    
    def __init__(self, max_workers: int = 3):
        """
        Initialize the file summarizer.
        
        Args:
            max_workers: Maximum number of concurrent API calls
        """
        self.max_workers = max_workers
        
        # Rate limiting
        self.last_call_time = {}
        self.min_delay = 0.5  # Minimum delay between calls (seconds)
        self.call_lock = threading.Lock()
        
    def _get_file_content(self, file_path: str) -> Optional[str]:
        """
        Read file content safely.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File content or None if unable to read
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Skip if file is too large (> 100KB)
            if len(content) > 100 * 1024:
                return None
                
            # Skip if file is empty or only whitespace
            if not content.strip():
                return None
                
            return content
            
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    def _rate_limit_api_call(self, api_name: str):
        """
        Apply rate limiting to API calls.
        
        Args:
            api_name: Name of the API being called
        """
        with self.call_lock:
            current_time = time.time()
            last_call = self.last_call_time.get(api_name, 0)
            
            time_since_last = current_time - last_call
            if time_since_last < self.min_delay:
                sleep_time = self.min_delay - time_since_last
                time.sleep(sleep_time)
            
            self.last_call_time[api_name] = time.time()
    
    def _create_summary_prompt(self, file_path: str, content: str, file_size: int) -> str:
        """
        Create a prompt for file summarization.
        
        Args:
            file_path: Path to the file
            content: File content
            file_size: Size category (small, medium, large)
            
        Returns:
            Formatted prompt for the LLM
        """
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_path)[1]
        
        prompt = f"""Please analyze this code file and provide a concise summary.

File: {file_name}
Type: {file_extension}
Path: {file_path}

Content:
{content}

Please provide:
1. A brief description of what this file does (1-2 sentences)
2. Key functions/classes/components (list main ones)
3. Dependencies and imports used
4. File's role in the larger project context

Keep the summary concise and focus on the most important aspects."""
        
        return prompt
    
    def _call_selected_api(self, prompt: str, api_preference: str = 'anthropic') -> Optional[str]:
        """
        Call the selected API with rate limiting - completely isolated from main UI.
        
        Args:
            prompt: The prompt to send
            api_preference: Preferred API to use
            
        Returns:
            API response or None if failed
        """
        try:
            # Apply rate limiting
            self._rate_limit_api_call(api_preference)
            
            # Check if API is available
            if not isolated_api_manager.is_api_available(api_preference):
                print(f"API {api_preference} not available in isolated manager")
                return None
            
            # Make completely isolated API call
            print(f"Making isolated {api_preference} API call for file summarization...")
            response = isolated_api_manager.call_api(prompt, api_preference, max_tokens=1000)
            
            if response:
                print(f"✓ Received response from isolated {api_preference} API")
                return response
            else:
                print(f"✗ No response from isolated {api_preference} API")
                return None
            
        except Exception as e:
            print(f"Error in isolated {api_preference} API call: {e}")
            return None
    
    def summarize_file(self, file_path: str, api_preference: str = 'anthropic') -> Optional[Dict]:
        """
        Summarize a single file.
        
        Args:
            file_path: Path to the file to summarize
            api_preference: Preferred API to use
            
        Returns:
            Dictionary containing summary data or None if failed
        """
        try:
            # Read file content
            content = self._get_file_content(file_path)
            if content is None:
                return None
            
            # Create prompt
            file_size = len(content)
            size_category = 'small' if file_size < 5*1024 else 'medium' if file_size < 50*1024 else 'large'
            
            prompt = self._create_summary_prompt(file_path, content, size_category)
            
            # Get summary from API
            summary = self._call_selected_api(prompt, api_preference)
            if summary is None:
                return None
            
            # Create summary data
            summary_data = {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'file_size': file_size,
                'size_category': size_category,
                'summary': summary,
                'timestamp': time.time(),
                'api_used': api_preference
            }
            
            return summary_data
            
        except Exception as e:
            print(f"Error summarizing file {file_path}: {e}")
            return None
    
    def summarize_files_batch(self, file_paths: List[str], api_preference: str = 'anthropic', 
                             progress_callback=None) -> Dict[str, Dict]:
        """
        Summarize multiple files in parallel batches.
        
        Args:
            file_paths: List of file paths to summarize
            api_preference: Preferred API to use
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary mapping file paths to summary data
        """
        summaries = {}
        total_files = len(file_paths)
        completed = 0
        
        print(f"Starting summarization of {total_files} files using {api_preference}")
        
        # Process files in batches to avoid overwhelming the API
        batch_size = min(self.max_workers, 5)  # Limit batch size
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_path = {}
            
            for i in range(0, len(file_paths), batch_size):
                batch = file_paths[i:i + batch_size]
                
                for file_path in batch:
                    future = executor.submit(self.summarize_file, file_path, api_preference)
                    future_to_path[future] = file_path
                
                # Process batch results
                for future in as_completed(future_to_path):
                    file_path = future_to_path[future]
                    completed += 1
                    
                    try:
                        result = future.get(timeout=60)  # 60 second timeout per file
                        
                        if result:
                            summaries[file_path] = result
                            print(f"✓ Summarized: {os.path.basename(file_path)}")
                        else:
                            print(f"✗ Failed to summarize: {os.path.basename(file_path)}")
                        
                        # Call progress callback if provided
                        if progress_callback:
                            progress_percentage = int((completed / total_files) * 100)
                            progress_callback(progress_percentage, f"Processed {completed}/{total_files} files")
                        
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
                
                # Clear completed futures to free memory
                for future in list(future_to_path.keys()):
                    if future.done():
                        del future_to_path[future]
                
                # Small delay between batches to avoid rate limiting
                if i + batch_size < len(file_paths):
                    time.sleep(1)
        
        print(f"Completed summarization: {len(summaries)}/{total_files} files successful")
        return summaries
    
    def categorize_files_for_batching(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        Categorize files by size for optimal batching.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Dictionary with size categories as keys
        """
        categories = {
            'small': [],    # < 5KB - can batch more aggressively
            'medium': [],   # 5KB - 50KB - moderate batching
            'large': []     # > 50KB - process individually
        }
        
        for file_path in file_paths:
            try:
                file_size = os.path.getsize(file_path)
                if file_size < 5 * 1024:
                    categories['small'].append(file_path)
                elif file_size < 50 * 1024:
                    categories['medium'].append(file_path)
                else:
                    categories['large'].append(file_path)
            except:
                # If we can't get size, treat as medium
                categories['medium'].append(file_path)
        
        return categories
    
    def save_summaries(self, summaries: Dict[str, Dict], output_path: str):
        """
        Save summaries to a JSON file.
        
        Args:
            summaries: Dictionary of file summaries
            output_path: Path to save the summaries
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Add metadata
            output_data = {
                'metadata': {
                    'total_files': len(summaries),
                    'generated_at': time.time(),
                    'generated_at_human': time.ctime()
                },
                'summaries': summaries
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"Summaries saved to: {output_path}")
            
        except Exception as e:
            print(f"Error saving summaries: {e}")
    
    def load_summaries(self, input_path: str) -> Dict[str, Dict]:
        """
        Load summaries from a JSON file.
        
        Args:
            input_path: Path to load summaries from
            
        Returns:
            Dictionary of file summaries
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data.get('summaries', {})
            
        except Exception as e:
            print(f"Error loading summaries: {e}")
            return {}


class ProjectSummarizer:
    """
    High-level interface for project summarization.
    """
    
    def __init__(self, storage_path: str = None):
        """
        Initialize project summarizer.
        
        Args:
            storage_path: Path to store project summaries
        """
        if storage_path is None:
            storage_path = os.path.join(os.path.dirname(__file__), "project_summaries")
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        self.file_summarizer = FileSummarizer()
    
    def summarize_project(self, project_name: str, file_paths: List[str], 
                         api_preference: str = 'anthropic', progress_callback=None) -> bool:
        """
        Summarize all files in a project.
        
        Args:
            project_name: Name of the project
            file_paths: List of file paths to summarize
            api_preference: Preferred API to use
            progress_callback: Optional progress callback
            
        Returns:
            True if successful
        """
        try:
            print(f"Starting project summarization for: {project_name}")
            
            # Categorize files by size for optimal processing
            categories = self.file_summarizer.categorize_files_for_batching(file_paths)
            
            all_summaries = {}
            total_categories = len([cat for cat in categories.values() if cat])
            completed_categories = 0
            
            # Process each category
            for category, files in categories.items():
                if not files:
                    continue
                
                print(f"Processing {category} files: {len(files)} files")
                
                # Adjust batch processing based on category
                if category == 'small':
                    self.file_summarizer.max_workers = 5
                elif category == 'medium':
                    self.file_summarizer.max_workers = 3
                else:  # large
                    self.file_summarizer.max_workers = 2
                
                category_summaries = self.file_summarizer.summarize_files_batch(
                    files, api_preference, progress_callback
                )
                
                all_summaries.update(category_summaries)
                completed_categories += 1
                
                if progress_callback:
                    overall_progress = int((completed_categories / total_categories) * 100)
                    progress_callback(overall_progress, f"Completed {category} files")
            
            # Save summaries
            output_path = self.storage_path / f"{project_name}_summaries.json"
            self.file_summarizer.save_summaries(all_summaries, str(output_path))
            
            print(f"Project summarization completed: {len(all_summaries)} files summarized")
            return True
            
        except Exception as e:
            print(f"Error summarizing project: {e}")
            return False
    
    def get_project_summaries(self, project_name: str) -> Dict[str, Dict]:
        """
        Get existing summaries for a project.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Dictionary of file summaries
        """
        summaries_path = self.storage_path / f"{project_name}_summaries.json"
        
        if summaries_path.exists():
            return self.file_summarizer.load_summaries(str(summaries_path))
        else:
            return {}
    
    def has_summaries(self, project_name: str) -> bool:
        """
        Check if summaries exist for a project.
        
        Args:
            project_name: Name of the project
            
        Returns:
            True if summaries exist
        """
        summaries_path = self.storage_path / f"{project_name}_summaries.json"
        return summaries_path.exists()


# Create singleton instance
project_summarizer = ProjectSummarizer()