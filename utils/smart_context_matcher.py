"""
Smart context matching for determining when and what project context to include.
Uses sliding window algorithm to efficiently match copied code to project files.
"""

import re
import os
from typing import Dict, List, Optional, Tuple, Set
from core.project_linker import project_linker
from .file_summarizer import project_summarizer


class CodeMatcher:
    """Efficient code matching using sliding window algorithm."""
    
    def __init__(self):
        """Initialize the code matcher."""
        self.normalized_files = {}  # Cache normalized file contents
        self.last_project = None
        self.code_indicators = {
            # Programming keywords
            'keywords': {
                'function', 'const', 'let', 'var', 'class', 'def', 'import', 'export',
                'return', 'if', 'else', 'for', 'while', 'try', 'catch', 'async', 'await',
                'useState', 'useEffect', 'useCallback', 'useMemo', 'useRef', 'useContext',
                'component', 'props', 'state', 'render', 'jsx', 'tsx'
            },
            # Code symbols that indicate programming content
            'symbols': {
                '=>', '===', '!==', '!=', '==', '&&', '||', '++', '--', 
                '+=', '-=', '*=', '/=', '=>', '??', '?.', '...', '${', 
                '</>', '</', '/>', '::', '->', '<-'
            },
            # File extensions
            'extensions': {
                '.js', '.jsx', '.ts', '.tsx', '.py', '.java', '.cpp', '.c',
                '.css', '.html', '.json', '.xml', '.yaml', '.yml', '.md'
            }
        }
    
    def normalize_code(self, text: str) -> str:
        """
        Normalize code text for comparison.
        
        Args:
            text: Raw code text
            
        Returns:
            Normalized text for comparison
        """
        if not text:
            return ""
        
        # Convert to lowercase
        normalized = text.lower()
        
        # Remove all whitespace and newlines
        normalized = re.sub(r'\s+', '', normalized)
        
        # Remove common variations that don't affect logic
        normalized = re.sub(r'["\']', '', normalized)  # Remove quotes
        normalized = re.sub(r';+', '', normalized)     # Remove semicolons
        normalized = re.sub(r',+', '', normalized)     # Remove commas in some contexts
        
        return normalized
    
    def has_code_indicators(self, text: str) -> bool:
        """
        Check if text contains programming-related content.
        
        Args:
            text: Text to check
            
        Returns:
            True if text appears to contain code
        """
        text_lower = text.lower()
        
        # Check for programming keywords
        for keyword in self.code_indicators['keywords']:
            if keyword in text_lower:
                return True
        
        # Check for code symbols
        for symbol in self.code_indicators['symbols']:
            if symbol in text:
                return True
        
        # Check for file extensions
        for ext in self.code_indicators['extensions']:
            if ext in text_lower:
                return True
        
        # Check for code patterns with regex
        code_patterns = [
            r'\w+\s*\(.*?\)',           # Function calls
            r'\w+\s*=\s*\w+',           # Variable assignments
            r'{\s*\w+.*?}',             # Object literals
            r'\[\s*\w+.*?\]',           # Array literals
            r'<\w+.*?/?>',              # HTML/JSX tags
            r'\w+\.\w+\(',              # Method calls
            r'\/\/.*|\/\*.*?\*\/',      # Comments
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, text, re.DOTALL):
                return True
        
        return False
    
    def cache_project_files(self, project_name: str) -> bool:
        """
        Cache normalized content for all project files.
        
        Args:
            project_name: Name of the project to cache
            
        Returns:
            True if successful
        """
        try:
            if project_name not in project_linker.linked_projects:
                return False
            
            project_data = project_linker.linked_projects[project_name]
            self.normalized_files = {}
            
            for file_path in project_data["files"]:
                try:
                    # Skip very large files for performance
                    file_size = os.path.getsize(file_path)
                    if file_size > 1024 * 1024:  # > 1MB
                        print(f"Skipping large file for context matching: {os.path.basename(file_path)} ({file_size:,} bytes)")
                        continue
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    normalized = self.normalize_code(content)
                    if normalized:  # Only cache non-empty files
                        self.normalized_files[file_path] = {
                            'normalized': normalized,
                            'original': content,
                            'size': len(content)
                        }
                        
                except Exception as e:
                    print(f"Error caching file {file_path}: {e}")
                    continue
            
            self.last_project = project_name
            print(f"Cached {len(self.normalized_files)} files for project '{project_name}'")
            return True
            
        except Exception as e:
            print(f"Error caching project files: {e}")
            return False
    
    def sliding_window_match(self, query_normalized: str, file_normalized: str, 
                           min_window: int = 10, max_window: int = 100) -> float:
        """
        Use sliding window to find best match between query and file.
        
        Args:
            query_normalized: Normalized query text
            file_normalized: Normalized file content
            min_window: Minimum window size
            max_window: Maximum window size
            
        Returns:
            Best similarity score (0.0 to 1.0)
        """
        if not query_normalized or not file_normalized:
            return 0.0
        
        query_len = len(query_normalized)
        if query_len < min_window:
            # For very short queries, check if it's contained
            if query_normalized in file_normalized:
                return min(0.8, query_len / 20.0)  # Score based on length
            return 0.0
        
        best_score = 0.0
        
        # Try different window sizes
        for window_size in range(min_window, min(max_window, query_len + 1), 5):
            for i in range(len(query_normalized) - window_size + 1):
                query_window = query_normalized[i:i + window_size]
                
                if query_window in file_normalized:
                    # Calculate score based on window size and position
                    score = window_size / query_len
                    if i == 0:  # Bonus for matching from start
                        score *= 1.2
                    best_score = max(best_score, score)
                    
                    # Early exit for perfect matches
                    if score > 0.9:
                        return min(1.0, score)
        
        return min(1.0, best_score)
    
    def find_matching_files(self, query_text: str, threshold: float = 0.2) -> List[Tuple[str, float]]:
        """
        Find files that match the query text using sliding window algorithm.
        
        Args:
            query_text: Text to search for
            threshold: Minimum similarity threshold
            
        Returns:
            List of (file_path, similarity_score) tuples, sorted by score
        """
        current_project = project_linker.current_project
        if not current_project:
            return []
        
        # Check if query contains code first (fast check)
        if not self.has_code_indicators(query_text):
            return []
        
        query_normalized = self.normalize_code(query_text)
        if not query_normalized or len(query_normalized) < 5:
            return []
        
        # Cache files if needed (lazy loading)
        if self.last_project != current_project or not self.normalized_files:
            print(f"Lazy loading project files for context matching: {current_project}")
            if not self.cache_project_files(current_project):
                return []
        
        matches = []
        
        for file_path, file_data in self.normalized_files.items():
            similarity = self.sliding_window_match(query_normalized, file_data['normalized'])
            
            if similarity >= threshold:
                matches.append((file_path, similarity))
        
        # Sort by similarity score (descending)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        print(f"Found {len(matches)} code matches for query (top 3 returned)")
        
        # Return top 3 matches
        return matches[:3]


class SmartContextManager:
    """Manages intelligent context inclusion based on user intent and code matching."""
    
    def __init__(self):
        """Initialize the context manager."""
        self.code_matcher = CodeMatcher()
    
    def should_include_context(self, message: str, user_requested_context: bool = False) -> Tuple[bool, str, str]:
        """
        Determine what context to include based on message content and user choice.
        
        Args:
            message: User's message
            user_requested_context: Whether user explicitly requested project context
            
        Returns:
            Tuple of (include_context, context_type, context_content)
            - include_context: Whether to include any context
            - context_type: "full_project" | "specific_file" | "none"
            - context_content: The actual context string to include
        """
        current_project = project_linker.current_project
        
        print(f"Smart context check - Project: {current_project}, User requested: {user_requested_context}")
        print(f"Message length: {len(message)}, Preview: {message[:50]}...")
        
        if not current_project:
            print("No current project - skipping context")
            return False, "none", ""
        
        # Case 1: User explicitly requested full project context
        if user_requested_context:
            print("User requested full project context")
            context_content = self._build_full_project_context(current_project)
            return True, "full_project", context_content
        
        # Case 2: Check for code matches
        print("Checking for code matches...")
        matching_files = self.code_matcher.find_matching_files(message)
        if matching_files:
            # Found code match - include specific file context
            best_match = matching_files[0]  # Highest scoring match
            file_path, similarity = best_match
            print(f"Found code match: {os.path.basename(file_path)} (similarity: {similarity:.2f})")
            context_content = self._build_file_context(file_path, similarity)
            return True, "specific_file", context_content
        
        # Case 3: No match and no user request - no context
        print("No code matches found - no context added")
        return False, "none", ""
    
    def _build_full_project_context(self, project_name: str) -> str:
        """
        Build full project context including structure and all summaries.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Full project context string
        """
        context = "Full Project Context:\n"
        context += "=" * 50 + "\n\n"
        
        # Add project structure
        project_summary = project_linker.get_project_summary(project_name)
        context += project_summary + "\n\n"
        
        # Add all available file summaries
        summaries = project_summarizer.get_project_summaries(project_name)
        if summaries:
            context += "File Summaries:\n"
            context += "-" * 30 + "\n"
            
            for file_path, summary_data in summaries.items():
                file_name = os.path.basename(file_path)
                context += f"\n{file_name}:\n{summary_data.get('summary', 'No summary available')}\n"
        
        return context
    
    def _build_file_context(self, file_path: str, similarity: float) -> str:
        """
        Build context for a specific matched file.
        
        Args:
            file_path: Path to the matched file
            similarity: Similarity score of the match
            
        Returns:
            File-specific context string
        """
        file_name = os.path.basename(file_path)
        context = f"Matched File Context (similarity: {similarity:.2f}):\n"
        context += "=" * 50 + "\n\n"
        
        # Check if we have a summary for this file
        current_project = project_linker.current_project
        summaries = project_summarizer.get_project_summaries(current_project)
        
        if file_path in summaries:
            # Use AI summary if available
            summary_data = summaries[file_path]
            context += f"File: {file_name}\n"
            context += f"Path: {file_path}\n"
            context += f"Summary:\n{summary_data.get('summary', 'No summary available')}\n\n"
        else:
            # Include truncated file content if no summary
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                if len(content) > 2000:  # Truncate large files
                    content = content[:2000] + f"\n\n... [File truncated - showing first 2000 characters of {len(content):,} total]"
                
                context += f"File: {file_name}\n"
                context += f"Path: {file_path}\n"
                context += f"Content:\n{content}\n\n"
                
            except Exception as e:
                context += f"File: {file_name}\n"
                context += f"Path: {file_path}\n"
                context += f"Error reading file: {str(e)}\n\n"
        
        return context


# Create singleton instance
smart_context_manager = SmartContextManager()