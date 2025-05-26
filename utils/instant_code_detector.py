"""
Instant code detection system for fast popup feedback.
Uses hash tables and content fingerprints for sub-millisecond detection.
"""

import hashlib
import re
import os
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from core.project_linker import project_linker


class InstantCodeDetector:
    """Ultra-fast code detection using multiple lookup strategies."""
    
    def __init__(self):
        """Initialize the instant detector."""
        self.current_project = None
        
        # Fast lookup tables
        self.line_hashes = {}           # hash -> (file_path, line_number)
        self.word_sequences = {}        # sequence_hash -> (file_path, start_pos)
        self.identifier_files = defaultdict(set)  # identifier -> set of files
        self.file_fingerprints = {}     # file_path -> set of content hashes
        
        # Performance tracking
        self.last_build_time = 0
        self.total_files = 0
    
    def build_fast_lookup(self, project_name: str) -> bool:
        """
        Build fast lookup tables for instant detection.
        
        Args:
            project_name: Name of the project to index
            
        Returns:
            True if successful
        """
        try:
            import time
            start_time = time.time()
            
            if project_name not in project_linker.linked_projects:
                return False
            
            print(f"Building fast lookup tables for project: {project_name}")
            
            # Clear existing data
            self.line_hashes.clear()
            self.word_sequences.clear()
            self.identifier_files.clear()
            self.file_fingerprints.clear()
            
            project_data = project_linker.linked_projects[project_name]
            file_paths = project_data.get("files", [])
            
            processed_files = 0
            
            for file_path in file_paths:
                try:
                    # Skip very large files for instant lookup
                    if os.path.getsize(file_path) > 500 * 1024:  # 500KB limit for instant lookup
                        continue
                    
                    self._index_file_for_instant_lookup(file_path)
                    processed_files += 1
                    
                except Exception as e:
                    print(f"Error indexing {file_path} for instant lookup: {e}")
                    continue
            
            self.current_project = project_name
            self.total_files = processed_files
            self.last_build_time = time.time() - start_time
            
            print(f"Fast lookup built: {processed_files} files in {self.last_build_time:.3f}s")
            print(f"- {len(self.line_hashes)} line hashes")
            print(f"- {len(self.word_sequences)} word sequences") 
            print(f"- {len(self.identifier_files)} unique identifiers")
            
            return True
            
        except Exception as e:
            print(f"Error building fast lookup: {e}")
            return False
    
    def _index_file_for_instant_lookup(self, file_path: str):
        """Index a single file for instant lookup."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if not content.strip():
                return
            
            lines = content.split('\n')
            file_hashes = set()
            
            # Index individual lines
            for line_num, line in enumerate(lines, 1):
                line_clean = line.strip()
                if len(line_clean) > 10:  # Only index substantial lines
                    line_hash = hashlib.md5(line_clean.encode()).hexdigest()[:12]
                    self.line_hashes[line_hash] = (file_path, line_num)
                    file_hashes.add(line_hash)
            
            # Index word sequences (3-5 word sliding windows)
            words = re.findall(r'\b\w+\b', content.lower())
            for i in range(len(words) - 2):
                # 3-word sequences
                if i + 2 < len(words):
                    seq = ' '.join(words[i:i+3])
                    if len(seq) > 8:  # Only meaningful sequences
                        seq_hash = hashlib.md5(seq.encode()).hexdigest()[:10]
                        self.word_sequences[seq_hash] = (file_path, i)
                
                # 4-word sequences for better precision
                if i + 3 < len(words):
                    seq = ' '.join(words[i:i+4])
                    seq_hash = hashlib.md5(seq.encode()).hexdigest()[:10]
                    self.word_sequences[seq_hash] = (file_path, i)
            
            # Index identifiers (function names, variable names, etc.)
            identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', content)
            for identifier in set(identifiers):  # Unique identifiers only
                if len(identifier) > 3 and not identifier.lower() in {'true', 'false', 'null', 'undefined'}:
                    self.identifier_files[identifier.lower()].add(file_path)
            
            # Store file fingerprint
            self.file_fingerprints[file_path] = file_hashes
            
        except Exception as e:
            print(f"Error indexing file {file_path}: {e}")
    
    def instant_detect_multiple(self, copied_text: str) -> List[Tuple[str, str, float]]:
        """
        Instantly detect multiple possible matches for copied text.
        
        Args:
            copied_text: Text that was copied
            
        Returns:
            List of (file_path, file_name, confidence) tuples, sorted by confidence
        """
        if not self.current_project or not copied_text.strip():
            return []
        
        # Quick project check
        current_project_linker = project_linker.current_project
        if current_project_linker != self.current_project:
            return []
        
        copied_clean = copied_text.strip()
        if len(copied_clean) < 5:
            return []
        
        matches = []
        file_match_scores = defaultdict(float)  # Track best score per file
        
        # Strategy 1: Direct line matching (fastest, highest confidence)
        lines = copied_clean.split('\n')
        for line in lines:
            line_clean = line.strip()
            if len(line_clean) > 10:
                line_hash = hashlib.md5(line_clean.encode()).hexdigest()[:12]
                if line_hash in self.line_hashes:
                    file_path, line_num = self.line_hashes[line_hash]
                    file_name = os.path.basename(file_path)
                    confidence = 0.95
                    file_match_scores[file_path] = max(file_match_scores[file_path], confidence)
        
        # Strategy 2: Word sequence matching (fast, good confidence)
        words = re.findall(r'\b\w+\b', copied_clean.lower())
        if len(words) >= 3:
            for i in range(len(words) - 2):
                seq = ' '.join(words[i:i+3])
                if len(seq) > 8:
                    seq_hash = hashlib.md5(seq.encode()).hexdigest()[:10]
                    if seq_hash in self.word_sequences:
                        file_path, pos = self.word_sequences[seq_hash]
                        confidence = 0.8
                        file_match_scores[file_path] = max(file_match_scores[file_path], confidence)
        
        # Strategy 3: Identifier matching (very fast, lower confidence)
        identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{3,}\b', copied_clean)
        identifier_scores = defaultdict(int)
        
        for identifier in identifiers:
            if identifier.lower() in self.identifier_files:
                for file_path in self.identifier_files[identifier.lower()]:
                    identifier_scores[file_path] += 1
        
        # Convert identifier scores to matches
        for file_path, score in identifier_scores.items():
            if score >= 2:  # At least 2 identifier matches
                confidence = min(0.7, 0.3 + (score * 0.1))
                file_match_scores[file_path] = max(file_match_scores[file_path], confidence)
        
        # Convert to list format
        for file_path, confidence in file_match_scores.items():
            file_name = os.path.basename(file_path)
            matches.append((file_path, file_name, confidence))
        
        # Sort by confidence (descending) and return top 5
        matches.sort(key=lambda x: x[2], reverse=True)
        return matches[:5]
    
    def instant_detect(self, copied_text: str) -> Optional[Tuple[str, str, float]]:
        """
        Instantly detect best match for copied text (backwards compatibility).
        
        Args:
            copied_text: Text that was copied
            
        Returns:
            Tuple of (file_path, file_name, confidence) or None if no match
        """
        matches = self.instant_detect_multiple(copied_text)
        return matches[0] if matches else None
    
    def is_ready(self) -> bool:
        """Check if the detector is ready for instant detection."""
        return (
            self.current_project is not None and 
            len(self.line_hashes) > 0 and
            self.current_project == project_linker.current_project
        )
    
    def get_stats(self) -> Dict[str, any]:
        """Get detector statistics."""
        return {
            'project': self.current_project,
            'files_indexed': self.total_files,
            'line_hashes': len(self.line_hashes),
            'word_sequences': len(self.word_sequences),
            'identifiers': len(self.identifier_files),
            'build_time_ms': round(self.last_build_time * 1000, 2),
            'ready': self.is_ready()
        }
    
    def refresh_if_needed(self):
        """Refresh lookup tables if current project changed."""
        current_project_linker = project_linker.current_project
        
        if current_project_linker != self.current_project:
            if current_project_linker:
                print(f"Project changed to {current_project_linker}, rebuilding fast lookup...")
                self.build_fast_lookup(current_project_linker)
            else:
                print("No project selected, clearing fast lookup")
                self.current_project = None
                self.line_hashes.clear()
                self.word_sequences.clear()
                self.identifier_files.clear()
                self.file_fingerprints.clear()


# Create singleton instance
instant_detector = InstantCodeDetector()