import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import networkx as nx


class FileDependencyAnalyzer:
    """
    Analyzes file dependencies across multiple programming languages without using AI.
    Uses pattern matching and static analysis to build dependency graphs.
    """
    
    def __init__(self):
        """Initialize the dependency analyzer with language patterns."""
        self.dependency_graph = nx.DiGraph()
        self.file_metadata = {}
        self.language_patterns = self._initialize_language_patterns()
        self.extension_to_language = self._initialize_extension_map()
        
    def _initialize_extension_map(self) -> Dict[str, str]:
        """Map file extensions to programming languages."""
        return {
            # JavaScript/TypeScript
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.mjs': 'javascript',
            '.cjs': 'javascript',
            
            # Python
            '.py': 'python',
            '.pyw': 'python',
            '.pyx': 'python',
            '.pyi': 'python',
            
            # Java/Kotlin/Scala
            '.java': 'java',
            '.kt': 'kotlin',
            '.kts': 'kotlin',
            '.scala': 'scala',
            
            # C/C++/Objective-C
            '.c': 'c',
            '.h': 'c',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.hpp': 'cpp',
            '.hxx': 'cpp',
            '.m': 'objc',
            '.mm': 'objc',
            
            # C#/F#/VB.NET
            '.cs': 'csharp',
            '.fs': 'fsharp',
            '.fsx': 'fsharp',
            '.vb': 'vbnet',
            
            # Go
            '.go': 'go',
            
            # Rust
            '.rs': 'rust',
            
            # Ruby
            '.rb': 'ruby',
            '.rake': 'ruby',
            
            # PHP
            '.php': 'php',
            '.phtml': 'php',
            
            # Swift
            '.swift': 'swift',
            
            # Perl
            '.pl': 'perl',
            '.pm': 'perl',
            
            # Lua
            '.lua': 'lua',
            
            # R
            '.r': 'r',
            '.R': 'r',
            
            # Shell
            '.sh': 'shell',
            '.bash': 'shell',
            '.zsh': 'shell',
            '.fish': 'shell',
            
            # Web
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            
            # Configuration/Data
            '.xml': 'xml',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.toml': 'toml',
            '.ini': 'ini',
            '.cfg': 'ini',
            
            # SQL
            '.sql': 'sql',
            
            # Assembly
            '.asm': 'assembly',
            '.s': 'assembly',
            
            # Other
            '.dart': 'dart',
            '.elm': 'elm',
            '.ex': 'elixir',
            '.exs': 'elixir',
            '.erl': 'erlang',
            '.hrl': 'erlang',
            '.hs': 'haskell',
            '.lhs': 'haskell',
            '.jl': 'julia',
            '.nim': 'nim',
            '.pas': 'pascal',
            '.pp': 'pascal',
            '.pro': 'prolog',
            '.tcl': 'tcl',
            '.v': 'verilog',
            '.vhd': 'vhdl',
            '.vhdl': 'vhdl',
        }
    
    def _initialize_language_patterns(self) -> Dict[str, Dict[str, List[re.Pattern]]]:
        """Initialize regex patterns for dependency detection in various languages."""
        patterns = {
            'javascript': {
                'imports': [
                    re.compile(r'import\s+(?:(?:\*\s+as\s+\w+)|(?:\{[^}]+\})|(?:\w+))\s+from\s+[\'"]([^\'"\n]+)[\'"]'),
                    re.compile(r'import\s*\(\s*[\'"]([^\'"\n]+)[\'"]'),
                    re.compile(r'require\s*\(\s*[\'"]([^\'"\n]+)[\'"]'),
                    re.compile(r'export\s+(?:\*|{\s*[^}]*\s*})\s+from\s+[\'"]([^\'"\n]+)[\'"]'),
                ],
                'exports': [
                    re.compile(r'export\s+(?:default\s+)?(?:class|function|const|let|var)\s+(\w+)'),
                    re.compile(r'export\s+\{\s*([^}]+)\s*\}'),
                    re.compile(r'module\.exports\s*=\s*(\w+)'),
                    re.compile(r'exports\.(\w+)\s*='),
                ],
                'variables': [
                    re.compile(r'(?:const|let|var)\s+(\w+)'),
                    re.compile(r'function\s+(\w+)'),
                    re.compile(r'class\s+(\w+)'),
                ]
            },
            'typescript': {
                'imports': [
                    re.compile(r'import\s+(?:(?:\*\s+as\s+\w+)|(?:\{[^}]+\})|(?:\w+))\s+from\s+[\'"]([^\'"\n]+)[\'"]'),
                    re.compile(r'import\s+type\s+(?:\{[^}]+\}|\w+)\s+from\s+[\'"]([^\'"\n]+)[\'"]'),
                    re.compile(r'import\s*\(\s*[\'"]([^\'"\n]+)[\'"]'),
                    re.compile(r'export\s+(?:\*|{\s*[^}]*\s*})\s+from\s+[\'"]([^\'"\n]+)[\'"]'),
                ],
                'exports': [
                    re.compile(r'export\s+(?:default\s+)?(?:class|function|const|let|var|interface|type|enum)\s+(\w+)'),
                    re.compile(r'export\s+\{\s*([^}]+)\s*\}'),
                ],
                'variables': [
                    re.compile(r'(?:const|let|var)\s+(\w+)'),
                    re.compile(r'function\s+(\w+)'),
                    re.compile(r'class\s+(\w+)'),
                    re.compile(r'interface\s+(\w+)'),
                    re.compile(r'type\s+(\w+)'),
                    re.compile(r'enum\s+(\w+)'),
                ]
            },
            'python': {
                'imports': [
                    re.compile(r'from\s+(\S+)\s+import'),
                    re.compile(r'import\s+(\S+)'),
                ],
                'exports': [
                    re.compile(r'^(?:def|class)\s+(\w+)', re.MULTILINE),
                    re.compile(r'^(\w+)\s*=', re.MULTILINE),
                ],
                'variables': [
                    re.compile(r'^(?:def|class)\s+(\w+)', re.MULTILINE),
                    re.compile(r'^(\w+)\s*=', re.MULTILINE),
                ]
            },
            'java': {
                'imports': [
                    re.compile(r'import\s+(?:static\s+)?([a-zA-Z0-9_.]+);'),
                ],
                'exports': [
                    re.compile(r'public\s+(?:class|interface|enum)\s+(\w+)'),
                ],
                'variables': [
                    re.compile(r'(?:public|private|protected|static|final)*\s*(?:class|interface|enum)\s+(\w+)'),
                    re.compile(r'(?:public|private|protected|static|final)*\s*\w+\s+(\w+)\s*[=;(]'),
                ]
            },
            'c': {
                'imports': [
                    re.compile(r'#include\s*[<"]([^>"]+)[>"]'),
                ],
                'exports': [],
                'variables': [
                    re.compile(r'(?:int|char|float|double|void|struct|enum|typedef)\s+(\w+)'),
                    re.compile(r'#define\s+(\w+)'),
                ]
            },
            'cpp': {
                'imports': [
                    re.compile(r'#include\s*[<"]([^>"]+)[>"]'),
                    re.compile(r'using\s+namespace\s+(\w+);'),
                ],
                'exports': [],
                'variables': [
                    re.compile(r'(?:class|struct|namespace)\s+(\w+)'),
                    re.compile(r'(?:int|char|float|double|void|bool|auto)\s+(\w+)'),
                    re.compile(r'#define\s+(\w+)'),
                ]
            },
            'go': {
                'imports': [
                    re.compile(r'import\s+"([^"]+)"'),
                    re.compile(r'import\s+\(\s*"([^"]+)"'),
                ],
                'exports': [
                    re.compile(r'func\s+([A-Z]\w*)'),
                    re.compile(r'type\s+([A-Z]\w*)'),
                    re.compile(r'var\s+([A-Z]\w*)'),
                    re.compile(r'const\s+([A-Z]\w*)'),
                ],
                'variables': [
                    re.compile(r'func\s+(\w+)'),
                    re.compile(r'type\s+(\w+)'),
                    re.compile(r'var\s+(\w+)'),
                    re.compile(r'const\s+(\w+)'),
                ]
            },
            'rust': {
                'imports': [
                    re.compile(r'use\s+([a-zA-Z0-9_:]+)'),
                    re.compile(r'extern\s+crate\s+(\w+)'),
                ],
                'exports': [
                    re.compile(r'pub\s+(?:fn|struct|enum|trait|type|const|static)\s+(\w+)'),
                ],
                'variables': [
                    re.compile(r'(?:fn|struct|enum|trait|type|const|static|let|mut)\s+(\w+)'),
                ]
            },
            'csharp': {
                'imports': [
                    re.compile(r'using\s+([a-zA-Z0-9_.]+);'),
                ],
                'exports': [
                    re.compile(r'public\s+(?:class|interface|struct|enum)\s+(\w+)'),
                ],
                'variables': [
                    re.compile(r'(?:public|private|protected|internal|static)*\s*(?:class|interface|struct|enum)\s+(\w+)'),
                    re.compile(r'(?:public|private|protected|internal|static)*\s*\w+\s+(\w+)\s*[=;{]'),
                ]
            },
            'ruby': {
                'imports': [
                    re.compile(r'require\s+[\'"]([^\'"\n]+)[\'"]'),
                    re.compile(r'require_relative\s+[\'"]([^\'"\n]+)[\'"]'),
                    re.compile(r'load\s+[\'"]([^\'"\n]+)[\'"]'),
                ],
                'exports': [
                    re.compile(r'class\s+(\w+)'),
                    re.compile(r'module\s+(\w+)'),
                    re.compile(r'def\s+(\w+)'),
                ],
                'variables': [
                    re.compile(r'def\s+(\w+)'),
                    re.compile(r'class\s+(\w+)'),
                    re.compile(r'module\s+(\w+)'),
                    re.compile(r'(\w+)\s*='),
                ]
            },
            'php': {
                'imports': [
                    re.compile(r'require(?:_once)?\s*\(?[\'"]([^\'"\n]+)[\'"]'),
                    re.compile(r'include(?:_once)?\s*\(?[\'"]([^\'"\n]+)[\'"]'),
                    re.compile(r'use\s+([a-zA-Z0-9_\\\\]+);'),
                ],
                'exports': [
                    re.compile(r'class\s+(\w+)'),
                    re.compile(r'function\s+(\w+)'),
                    re.compile(r'interface\s+(\w+)'),
                    re.compile(r'trait\s+(\w+)'),
                ],
                'variables': [
                    re.compile(r'function\s+(\w+)'),
                    re.compile(r'class\s+(\w+)'),
                    re.compile(r'\$(\w+)\s*='),
                ]
            }
        }
        
        # Add default pattern for unknown languages
        patterns['default'] = {
            'imports': [],
            'exports': [],
            'variables': []
        }
        
        return patterns
    
    def detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        return self.extension_to_language.get(ext, 'default')
    
    def extract_dependencies(self, file_path: str, content: str) -> Dict[str, List[str]]:
        """
        Extract dependencies from a file based on its language.
        
        Returns:
            Dict with 'imports', 'exports', and 'variables' lists
        """
        language = self.detect_language(file_path)
        patterns = self.language_patterns.get(language, self.language_patterns['default'])
        
        results = {
            'imports': [],
            'exports': [],
            'variables': []
        }
        
        # Extract imports
        for pattern in patterns.get('imports', []):
            matches = pattern.findall(content)
            results['imports'].extend(matches)
        
        # Extract exports
        for pattern in patterns.get('exports', []):
            matches = pattern.findall(content)
            results['exports'].extend(matches)
        
        # Extract variables
        for pattern in patterns.get('variables', []):
            matches = pattern.findall(content)
            results['variables'].extend(matches)
        
        # Deduplicate
        results['imports'] = list(set(results['imports']))
        results['exports'] = list(set(results['exports']))
        results['variables'] = list(set(results['variables']))
        
        return results
    
    def resolve_import_path(self, from_file: str, import_path: str, project_root: str) -> Optional[str]:
        """
        Resolve an import path to an actual file path.
        
        Args:
            from_file: Path of the file containing the import
            import_path: The import path to resolve
            project_root: Root directory of the project
            
        Returns:
            Resolved file path or None if not found
        """
        from_dir = os.path.dirname(from_file)
        
        # Handle relative imports
        if import_path.startswith('.'):
            # Relative to current file
            candidates = [
                os.path.join(from_dir, import_path),
                os.path.join(from_dir, import_path + '.js'),
                os.path.join(from_dir, import_path + '.ts'),
                os.path.join(from_dir, import_path + '.jsx'),
                os.path.join(from_dir, import_path + '.tsx'),
                os.path.join(from_dir, import_path + '.py'),
                os.path.join(from_dir, import_path, 'index.js'),
                os.path.join(from_dir, import_path, 'index.ts'),
                os.path.join(from_dir, import_path, '__init__.py'),
            ]
        else:
            # Absolute imports - check common locations
            candidates = [
                # First check same directory as importing file (most common for Python)
                os.path.join(from_dir, import_path + '.py'),
                os.path.join(from_dir, import_path, '__init__.py'),
                # Then check standard locations
                os.path.join(project_root, import_path),
                os.path.join(project_root, 'src', import_path),
                os.path.join(project_root, 'lib', import_path),
                os.path.join(project_root, 'app', import_path),
                os.path.join(project_root, import_path + '.js'),
                os.path.join(project_root, import_path + '.ts'),
                os.path.join(project_root, import_path + '.py'),
                os.path.join(project_root, 'node_modules', import_path),
            ]
            
            # Add language-specific paths
            language = self.detect_language(from_file)
            if language == 'python':
                # Replace dots with slashes for Python imports
                python_path = import_path.replace('.', os.sep)
                candidates.extend([
                    os.path.join(project_root, python_path + '.py'),
                    os.path.join(project_root, python_path, '__init__.py'),
                    os.path.join(project_root, 'src', python_path + '.py'),
                    os.path.join(project_root, 'src', python_path, '__init__.py'),
                ])
        
        # Check each candidate
        for candidate in candidates:
            if os.path.exists(candidate) and os.path.isfile(candidate):
                return os.path.abspath(candidate)
        
        return None
    
    def analyze_file(self, file_path: str, project_root: str) -> Dict:
        """
        Analyze a single file for dependencies.
        
        Args:
            file_path: Path to the file to analyze
            project_root: Root directory of the project
            
        Returns:
            Analysis results including dependencies
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract dependencies
            deps = self.extract_dependencies(file_path, content)
            
            # Resolve import paths
            resolved_imports = []
            for import_path in deps['imports']:
                resolved = self.resolve_import_path(file_path, import_path, project_root)
                if resolved:
                    resolved_imports.append(resolved)
            
            # Store metadata
            self.file_metadata[file_path] = {
                'language': self.detect_language(file_path),
                'imports': deps['imports'],
                'resolved_imports': resolved_imports,
                'exports': deps['exports'],
                'variables': deps['variables'],
                'size': len(content),
                'lines': content.count('\n')
            }
            
            # Add to dependency graph
            self.dependency_graph.add_node(file_path)
            for dep in resolved_imports:
                self.dependency_graph.add_edge(file_path, dep)
            
            return self.file_metadata[file_path]
            
        except Exception as e:
            print(f"Error analyzing file {file_path}: {e}")
            return {}
    
    def analyze_project(self, project_root: str, file_list: List[str]) -> nx.DiGraph:
        """
        Analyze all files in a project to build dependency graph.
        
        Args:
            project_root: Root directory of the project
            file_list: List of files to analyze
            
        Returns:
            NetworkX directed graph of dependencies
        """
        # Clear previous analysis
        self.dependency_graph.clear()
        self.file_metadata.clear()
        
        # Analyze each file
        for file_path in file_list:
            self.analyze_file(file_path, project_root)
        
        return self.dependency_graph
    
    def get_file_dependencies(self, file_path: str, depth: int = 2) -> Dict[str, Set[str]]:
        """
        Get dependencies for a specific file up to a certain depth.
        
        Args:
            file_path: Path to the file
            depth: How many levels of dependencies to include
            
        Returns:
            Dict with 'imports' (files this file depends on) and 'importers' (files that depend on this file)
        """
        result = {
            'imports': set(),
            'importers': set()
        }
        
        if file_path not in self.dependency_graph:
            return result
        
        # Get files this file imports (outgoing edges)
        current_level = {file_path}
        for _ in range(depth):
            next_level = set()
            for node in current_level:
                for neighbor in self.dependency_graph.successors(node):
                    if neighbor != file_path:
                        result['imports'].add(neighbor)
                        next_level.add(neighbor)
            current_level = next_level
        
        # Get files that import this file (incoming edges)
        current_level = {file_path}
        for _ in range(depth):
            next_level = set()
            for node in current_level:
                for neighbor in self.dependency_graph.predecessors(node):
                    if neighbor != file_path:
                        result['importers'].add(neighbor)
                        next_level.add(neighbor)
            current_level = next_level
        
        return result
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """Find all circular dependencies in the project."""
        try:
            cycles = list(nx.simple_cycles(self.dependency_graph))
            return cycles
        except:
            return []
    
    def get_dependency_stats(self) -> Dict:
        """Get statistics about the dependency graph."""
        stats = {
            'total_files': self.dependency_graph.number_of_nodes(),
            'total_dependencies': self.dependency_graph.number_of_edges(),
            'circular_dependencies': len(self.find_circular_dependencies()),
            'isolated_files': len(list(nx.isolates(self.dependency_graph))),
            'most_imported': [],
            'most_dependencies': []
        }
        
        # Find most imported files
        in_degrees = dict(self.dependency_graph.in_degree())
        most_imported = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
        stats['most_imported'] = [(os.path.basename(f), count) for f, count in most_imported]
        
        # Find files with most dependencies
        out_degrees = dict(self.dependency_graph.out_degree())
        most_deps = sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
        stats['most_dependencies'] = [(os.path.basename(f), count) for f, count in most_deps]
        
        return stats
    
    def export_graph_data(self) -> Dict:
        """Export graph data in a format suitable for visualization."""
        nodes = []
        edges = []
        
        # Create nodes
        for node in self.dependency_graph.nodes():
            metadata = self.file_metadata.get(node, {})
            nodes.append({
                'id': node,
                'label': os.path.basename(node),
                'language': metadata.get('language', 'unknown'),
                'size': metadata.get('size', 0),
                'lines': metadata.get('lines', 0),
                'exports': len(metadata.get('exports', [])),
                'in_degree': self.dependency_graph.in_degree(node),
                'out_degree': self.dependency_graph.out_degree(node)
            })
        
        # Create edges
        for source, target in self.dependency_graph.edges():
            edges.append({
                'source': source,
                'target': target
            })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'stats': self.get_dependency_stats()
        }
    
    def get_focused_graph_data(self, center_file: str, depth: int = 2) -> Dict:
        """
        Get graph data focused on a specific file and its dependencies.
        
        Args:
            center_file: The file to focus on
            depth: How many levels of dependencies to include
            
        Returns:
            Graph data focused on the center file
        """
        if center_file not in self.dependency_graph:
            # If center file not in graph, return empty or full graph
            return self.export_graph_data()
        
        # Get subgraph around center file
        focused_nodes = set([center_file])
        
        # Add dependencies (outgoing edges) up to depth
        current_level = {center_file}
        for _ in range(depth):
            next_level = set()
            for node in current_level:
                successors = set(self.dependency_graph.successors(node))
                next_level.update(successors)
                focused_nodes.update(successors)
            current_level = next_level
            if not current_level:
                break
        
        # Add dependents (incoming edges) up to depth  
        current_level = {center_file}
        for _ in range(depth):
            next_level = set()
            for node in current_level:
                predecessors = set(self.dependency_graph.predecessors(node))
                next_level.update(predecessors)
                focused_nodes.update(predecessors)
            current_level = next_level
            if not current_level:
                break
        
        # Create focused graph data
        nodes = []
        for node in focused_nodes:
            if node in self.file_metadata:
                metadata = self.file_metadata[node]
                nodes.append({
                    'id': node,
                    'language': metadata.get('language', 'unknown'),
                    'imports': metadata.get('imports', []),
                    'exports': metadata.get('exports', []),
                    'size': metadata.get('size', 0),
                    'lines': metadata.get('lines', 0),
                    'exports': len(metadata.get('exports', [])),
                    'in_degree': self.dependency_graph.in_degree(node),
                    'out_degree': self.dependency_graph.out_degree(node)
                })
        
        # Create edges within focused nodes
        edges = []
        for source, target in self.dependency_graph.edges():
            if source in focused_nodes and target in focused_nodes:
                edges.append({
                    'source': source,
                    'target': target
                })
        
        result = {
            'nodes': nodes,
            'edges': edges,
            'stats': self.get_dependency_stats(),
            'center_file': center_file
        }
        
        return result


# Create singleton instance
file_dependency_analyzer = FileDependencyAnalyzer()