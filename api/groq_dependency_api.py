"""
Groq API for dependency-aware file summarization.
Uses llama-3.1-8b-instant for fast real-time hover summaries.
"""

import os
import hashlib
import json
from typing import Dict, List, Optional, Tuple
from groq import Groq
from pathlib import Path


class DependencySignature:
    """Compact representation of a file's role in the dependency graph."""
    
    def __init__(self, file_path: str, imports: List[str], imported_by: List[str], 
                 language: str = "unknown", file_type: str = "unknown"):
        self.file_path = file_path
        self.file_name = Path(file_path).name
        self.imports = imports[:5]  # Limit to top 5 for brevity
        self.imported_by = imported_by[:5]  # Limit to top 5 for brevity
        self.language = language
        self.file_type = file_type
        
    def to_compact_string(self) -> str:
        """Convert to a very compact string representation."""
        imports_str = ", ".join([Path(imp).name for imp in self.imports])
        imported_by_str = ", ".join([Path(imp).name for imp in self.imported_by])
        
        role = self._determine_role()
        
        return f"File: {self.file_name} ({self.language})\n" \
               f"Role: {role}\n" \
               f"Imports: [{imports_str}]\n" \
               f"Used by: [{imported_by_str}]"
    
    def _determine_role(self) -> str:
        """Determine the role of this file in the dependency graph."""
        imports_count = len(self.imports)
        imported_by_count = len(self.imported_by)
        
        if imports_count == 0 and imported_by_count > 0:
            return f"Core module (imported by {imported_by_count} files)"
        elif imports_count > 0 and imported_by_count == 0:
            return f"Entry point (imports {imports_count} files)"
        elif imports_count > imported_by_count:
            return f"High-level module (imports {imports_count}, used by {imported_by_count})"
        elif imported_by_count > imports_count:
            return f"Utility module (imports {imports_count}, used by {imported_by_count})"
        else:
            return f"Intermediate module (imports {imports_count}, used by {imported_by_count})"


class GroqDependencyAPI:
    """Fast dependency-aware summarization using Groq API."""
    
    def __init__(self):
        self.client = None
        self.model = "llama-3.1-8b-instant"  # 128K context, fast for real-time
        self.summary_cache = {}  # Cache summaries to avoid repeat API calls
        self.dependency_signatures = {}  # Store dependency signatures
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Groq client with API key."""
        import logging
        from core.config import config
        from .api_exceptions import APIKeyError, APIConnectionError
        
        logger = logging.getLogger(__name__)
        
        try:
            # Get API key from config
            api_key = config.groq_api_key
            if not api_key:
                logger.error("Groq API key not found in configuration")
                raise APIKeyError("Groq API key not configured. Please set GROQ_API_KEY in .env file")
            
            self.client = Groq(api_key=api_key)
            logger.info("✓ Groq API initialized for dependency summarization")
                
        except APIKeyError:
            raise
        except Exception as e:
            logger.error(f"✗ Error initializing Groq API: {e}")
            raise APIConnectionError(f"Failed to initialize Groq client: {e}")
    
    def prepare_dependency_signatures(self, graph_data: Dict) -> None:
        """Prepare compact dependency signatures for all nodes."""
        self.dependency_signatures = {}
        
        # Build import/imported_by relationships
        imports_map = {}
        imported_by_map = {}
        
        # Initialize maps
        for node in graph_data['nodes']:
            file_path = node['id']
            imports_map[file_path] = []
            imported_by_map[file_path] = []
        
        # Populate relationships from edges
        for edge in graph_data['edges']:
            source = edge['source']  # File that imports
            target = edge['target']  # File being imported
            
            if source in imports_map and target in imported_by_map:
                imports_map[source].append(target)
                imported_by_map[target].append(source)
        
        # Create dependency signatures
        for node in graph_data['nodes']:
            file_path = node['id']
            language = node.get('language', 'unknown')
            file_type = node.get('type', 'unknown')
            
            signature = DependencySignature(
                file_path=file_path,
                imports=imports_map.get(file_path, []),
                imported_by=imported_by_map.get(file_path, []),
                language=language,
                file_type=file_type
            )
            
            self.dependency_signatures[file_path] = signature
        
        print(f"✓ Prepared {len(self.dependency_signatures)} dependency signatures")
    
    def get_cache_key(self, file_path: str, file_content: str) -> str:
        """Generate cache key for summary."""
        content_hash = hashlib.md5(file_content.encode()).hexdigest()[:8]
        return f"{file_path}_{content_hash}"
    
    def truncate_file_content(self, content: str, max_lines: int = 100) -> str:
        """Intelligently truncate file content to focus on important parts."""
        lines = content.split('\n')
        
        if len(lines) <= max_lines:
            return content
        
        # Priority: imports, exports, class/function definitions, main logic
        important_lines = []
        regular_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            
            # High priority lines
            if (stripped.startswith(('import ', 'from ', 'export ', 'class ', 'def ', 'function ', 'async def')) or
                'main' in stripped or '__name__' in stripped or 'if __main__' in stripped):
                important_lines.append((i, line))
            else:
                regular_lines.append((i, line))
        
        # Take all important lines + some regular lines to fill max_lines
        selected_lines = important_lines[:max_lines//2]
        remaining_space = max_lines - len(selected_lines)
        selected_lines.extend(regular_lines[:remaining_space])
        
        # Sort by original line number and reconstruct
        selected_lines.sort(key=lambda x: x[0])
        
        result = '\n'.join([line for _, line in selected_lines])
        if len(lines) > max_lines:
            result += f"\n\n... (truncated {len(lines) - max_lines} lines)"
        
        return result
    
    async def get_hover_summary(self, file_path: str, file_content: str) -> str:
        """Get a 2-line dependency-aware summary for hover display."""
        print(f"🚀 Groq API called for: {file_path}")
        
        if not self.client:
            print("❌ Groq API client not available")
            return "Groq API not available"
        
        # Check cache first
        cache_key = self.get_cache_key(file_path, file_content)
        if cache_key in self.summary_cache:
            print(f"💾 Using cached summary for: {file_path}")
            return self.summary_cache[cache_key]
        
        try:
            # Get dependency signature
            signature = self.dependency_signatures.get(file_path)
            if not signature:
                return "No dependency analysis available"
            
            # Truncate content to stay within context limits
            truncated_content = self.truncate_file_content(file_content)
            
            # Build compact prompt
            dependency_context = signature.to_compact_string()
            
            prompt = f"""Analyze this file and provide a 2-line summary considering its role in the dependency graph.

DEPENDENCY CONTEXT:
{dependency_context}

FILE CONTENT:
{truncated_content}

Provide exactly 2 lines:
Line 1: What this file does (focus on its main purpose/functionality)
Line 2: How it fits in the dependency structure (its role/relationships)

Be concise and specific. No explanations, just the 2-line summary."""
            
            # Make API call
            print(f"📡 Making Groq API call with {len(prompt)} character prompt...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,  # Keep response short
                temperature=0.3,  # Consistent summaries
                stream=False
            )
            
            summary = response.choices[0].message.content.strip()
            print(f"✅ Groq API response: {summary}")
            
            # Cache the result
            self.summary_cache[cache_key] = summary
            
            return summary
            
        except Exception as e:
            print(f"Error getting Groq summary for {file_path}: {e}")
            return "Summary generation failed"
    
    def clear_cache(self):
        """Clear the summary cache."""
        self.summary_cache = {}
        print("✓ Groq summary cache cleared")


# Global instance for dependency summarization
groq_dependency_api = None

def get_groq_dependency_api():
    """Get or create the global Groq dependency API instance."""
    global groq_dependency_api
    if groq_dependency_api is None:
        try:
            groq_dependency_api = GroqDependencyAPI()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to initialize Groq dependency API: {e}")
            return None
    return groq_dependency_api