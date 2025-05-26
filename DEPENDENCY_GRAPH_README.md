# File Dependency Graph Feature

## Overview
The File Dependency Graph is a new feature in the Project Manager that algorithmically analyzes and visualizes file dependencies across your entire project. It works with a vast variety of programming languages without using AI.

## Features

### Multi-Language Support
The dependency analyzer supports over 40 programming languages including:
- **Modern Languages**: Python, JavaScript, TypeScript, Go, Rust, Swift, Kotlin
- **Classic Languages**: C, C++, Java, C#, Ruby, PHP, Perl
- **Web Technologies**: HTML, CSS, SCSS, JSX, TSX
- **Functional Languages**: Haskell, Elm, Elixir, Erlang, F#
- **Other**: Assembly, VHDL, Verilog, SQL, and more

### Dependency Detection
The analyzer uses pattern matching to detect:
- Import statements (e.g., `import`, `require`, `include`, `use`)
- Export statements (e.g., `export`, `module.exports`, `pub`)
- Module definitions and declarations
- Variable and function references across files

### Graph Visualization
The 2D graph visualization includes:
- **Force-Directed Layout**: Nodes naturally organize based on connections
- **Interactive Controls**: Pan, zoom, and click on nodes
- **Multiple Layouts**: Force-directed, circular, hierarchical, and grid
- **Color Coding**: Files are colored by programming language
- **Node Sizing**: Important files (many dependencies) appear larger
- **Dependency Highlighting**: Click a node to highlight its dependencies

### Analysis Statistics
The system provides detailed statistics including:
- Total files and dependencies count
- Circular dependency detection
- Most imported files (hub detection)
- Files with most dependencies
- Isolated files (no connections)

## Usage

### In Project Manager
1. Open the Project Manager dialog
2. Select or link a project
3. Click the "Analyze Dependencies" button at the bottom
4. The dependency graph will appear in the bottom panel

### Graph Interactions
- **Click a node**: Select the file and highlight its direct dependencies
- **Double-click a node**: Open the file in the editor (if supported)
- **Mouse wheel**: Zoom in/out
- **Drag**: Pan the view
- **Select file in tree**: Automatically centers and highlights in graph

### Layout Options
- **Force-Directed**: Natural clustering based on connections
- **Circular**: All nodes arranged in a circle
- **Hierarchical**: Tree-like structure showing dependency flow
- **Grid**: Organized grid layout

## Implementation Details

### File: `file_dependency_analyzer.py`
Core analyzer that:
- Detects programming language from file extensions
- Extracts dependencies using regex patterns
- Resolves import paths to actual files
- Builds a directed graph using NetworkX
- Detects circular dependencies
- Exports data for visualization

### File: `dependency_graph_widget.py`
PyQt5 widget that:
- Renders nodes and edges using QPainter
- Implements force-directed physics simulation
- Handles user interactions (clicks, drags, zoom)
- Provides multiple layout algorithms
- Animates node positions

### Integration: `ProjectManagerDialog.py`
Modified to:
- Include dependency graph widget at bottom
- Add "Analyze Dependencies" button
- Connect file selection to graph highlighting
- Handle node clicks to select files

## Performance Considerations
- Only analyzes user-created files (ignores libraries/dependencies)
- Skips binary files and large files
- Caches analysis results
- Uses efficient pattern matching
- Limits graph animation frame rate

## Future Enhancements
Potential improvements include:
- Cross-project dependency analysis
- Dependency change tracking over time
- Export graph as image/PDF
- Filter by file type or directory
- Search within the graph
- Dependency metrics and code smell detection