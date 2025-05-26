import math
import json
import os
from typing import Dict, List, Set, Tuple, Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QComboBox
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QThread
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QTransform, QWheelEvent
import networkx as nx
from pathlib import Path
import asyncio
from api.groq_dependency_api import get_groq_dependency_api


class SummaryWorker(QThread):
    """Worker thread for getting summaries without blocking UI."""
    
    summary_ready = pyqtSignal(str)
    summary_error = pyqtSignal(str)
    
    def __init__(self, file_path: str, summaries_prepared: bool):
        super().__init__()
        self.file_path = file_path
        self.summaries_prepared = summaries_prepared
    
    def run(self):
        """Run the summary request in background thread."""
        try:
            if not self.summaries_prepared:
                self.summary_error.emit("Click 'Summarize' button first")
                return
            
            # Read file content
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            else:
                self.summary_error.emit("File not found")
                return
            
            # Create async loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Get summary from Groq
            groq_api = get_groq_dependency_api()
            if groq_api:
                summary = loop.run_until_complete(groq_api.get_hover_summary(self.file_path, content))
            else:
                summary = "Groq API not available"
            loop.close()
            
            self.summary_ready.emit(summary)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.summary_error.emit(str(e))


class FlowParticle:
    """Represents a flowing particle that travels along an edge."""
    
    def __init__(self, source_node, target_node, edge_path):
        self.source_node = source_node
        self.target_node = target_node
        self.edge_path = edge_path  # (source_file, target_file) tuple
        self.progress = 0.0  # 0.0 to 1.0 along the edge
        self.x = source_node.x
        self.y = source_node.y
        self.radius = 4
        self.color = QColor(255, 255, 100, 200)  # Bright yellow with transparency
        
    def update_position(self, speed):
        """Update particle position along the edge."""
        self.progress += speed
        
        if self.progress >= 1.0:
            # Particle reached the end, reset to beginning
            self.progress = 0.0
            return True  # Indicates cycle completed
        
        # Interpolate position between source and target nodes
        t = self.progress
        
        # Calculate positions at edge of nodes, not centers
        dx = self.target_node.x - self.source_node.x
        dy = self.target_node.y - self.source_node.y
        dist = math.sqrt(dx * dx + dy * dy)
        
        if dist > 0:
            # Normalize direction
            dx /= dist
            dy /= dist
            
            # Start from edge of source node
            start_x = self.source_node.x + dx * self.source_node.radius
            start_y = self.source_node.y + dy * self.source_node.radius
            
            # End at edge of target node
            end_x = self.target_node.x - dx * self.target_node.radius
            end_y = self.target_node.y - dy * self.target_node.radius
            
            # Interpolate along the edge
            self.x = start_x + t * (end_x - start_x)
            self.y = start_y + t * (end_y - start_y)
        
        return False


class GraphNode:
    """Represents a node in the dependency graph."""
    
    def __init__(self, file_path: str, x: float = 0, y: float = 0):
        self.file_path = file_path
        self.label = Path(file_path).name
        self.x = x
        self.y = y
        self.vx = 0  # velocity x
        self.vy = 0  # velocity y
        self.radius = 20
        self.selected = False
        self.highlighted = False
        self.metadata = {}
        self.color = QColor(100, 150, 200)
        
    def distance_to(self, other: 'GraphNode') -> float:
        """Calculate distance to another node."""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if point is inside node."""
        dx = x - self.x
        dy = y - self.y
        return dx * dx + dy * dy <= self.radius * self.radius


class DependencyGraphWidget(QWidget):
    """Widget for visualizing file dependencies as an interactive graph."""
    
    nodeClicked = pyqtSignal(str)  # Emits file path when node is clicked
    nodeDoubleClicked = pyqtSignal(str)  # Emits file path when node is double-clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[Tuple[str, str]] = []
        self.selected_node: Optional[GraphNode] = None
        self.hover_node: Optional[GraphNode] = None
        self.center_file: Optional[str] = None
        
        # Visualization parameters
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.mouse_press_pos = None
        self.is_panning = False
        
        # Force-directed layout parameters
        self.repulsion_strength = 5000
        self.attraction_strength = 0.01
        self.damping = 0.9
        self.min_distance = 50
        
        # Animation for flowing particles
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_flow_animation)
        self.animation_timer.start(50)  # Update every 50ms for smooth animation
        
        # Flowing particles
        self.flow_particles = []  # List of particles flowing along edges
        self.particle_speed = 2.0  # Speed of particles along edges
        
        # Dependency summarization
        self.summaries_prepared = False
        self.click_summary = ""  # Current click summary
        self.current_graph_data = None  # Store graph data for summarization
        self.selected_summary_node = None  # Track which node summary is shown for
        
        # Color scheme (must be before UI setup)
        self.setup_colors()
        
        # UI Setup
        self.setup_ui()
        self.setMouseTracking(True)
        self.setMinimumSize(600, 400)
        
    def setup_colors(self):
        """Setup color scheme based on file types and states."""
        self.language_colors = {
            'python': QColor(53, 114, 165),
            'javascript': QColor(247, 223, 30),
            'typescript': QColor(49, 120, 198),
            'java': QColor(176, 114, 25),
            'cpp': QColor(0, 89, 157),
            'c': QColor(85, 85, 85),
            'go': QColor(0, 172, 215),
            'rust': QColor(222, 165, 132),
            'ruby': QColor(204, 52, 45),
            'php': QColor(119, 123, 180),
            'csharp': QColor(104, 33, 122),
            'swift': QColor(250, 175, 70),
            'kotlin': QColor(241, 142, 51),
            'default': QColor(128, 128, 128)
        }
        
        self.edge_color = QColor(150, 150, 150, 100)
        self.selected_color = QColor(255, 100, 100)
        self.highlight_color = QColor(255, 200, 100)
        self.background_color = QColor(30, 30, 30)
        
    def setup_ui(self):
        """Setup the UI controls."""
        layout = QVBoxLayout(self)
        
        # Control panel
        controls = QHBoxLayout()
        
        # Layout algorithm selector
        controls.addWidget(QLabel("Layout:"))
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["Force-Directed", "Circular", "Hierarchical", "Grid"])
        self.layout_combo.currentTextChanged.connect(self.change_layout)
        controls.addWidget(self.layout_combo)
        
        
        # Reset view button
        reset_btn = QPushButton("Reset View")
        reset_btn.clicked.connect(self.reset_view)
        controls.addWidget(reset_btn)
        
        # Summarize button for dependency-aware summaries
        self.summarize_btn = QPushButton("Summarize")
        self.summarize_btn.clicked.connect(self.prepare_summaries)
        self.summarize_btn.setToolTip("Prepare dependency-aware summaries for hover display")
        controls.addWidget(self.summarize_btn)
        
        # Zoom slider
        controls.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(lambda v: self.set_zoom(v / 100))
        controls.addWidget(self.zoom_slider)
        
        controls.addStretch()
        
        layout.addLayout(controls)
        
        
        # Graph display area
        self.graph_widget = QWidget()
        self.graph_widget.setMinimumHeight(300)
        layout.addWidget(self.graph_widget, 1)
    
        
    def load_graph_data(self, graph_data: Dict, center_file: Optional[str] = None):
        """Load graph data from the dependency analyzer."""
        self.nodes.clear()
        self.edges.clear()
        self.center_file = center_file
        self.current_graph_data = graph_data  # Store for summarization
        self.summaries_prepared = False  # Reset summarization state
        
        # Reset summarize button when new graph is loaded
        if hasattr(self, 'summarize_btn'):
            self.summarize_btn.setText("Summarize")
            self.summarize_btn.setEnabled(True)
            print("🔄 New graph loaded - summarize button reset")
        
        # Create all nodes (don't filter at data level)
        for node_data in graph_data['nodes']:
            node = GraphNode(node_data['id'])
            node.metadata = node_data
            
            # Set color based on language
            language = node_data.get('language', 'default')
            node.color = self.language_colors.get(language, self.language_colors['default'])
            
            # Set size based on importance (in_degree + out_degree)
            total_connections = node_data.get('in_degree', 0) + node_data.get('out_degree', 0)
            importance = total_connections
            node.radius = min(max(15, 15 + importance * 2), 40)
            
            # Mark isolated nodes for potential filtering in display methods
            node.is_isolated = (total_connections == 0)
            
            self.nodes[node_data['id']] = node
        
        # Create edges
        for edge_data in graph_data['edges']:
            if edge_data['source'] in self.nodes and edge_data['target'] in self.nodes:
                self.edges.append((edge_data['source'], edge_data['target']))
        
        # Apply initial layout
        self.apply_layout("Force-Directed")
        
        # Auto-center and zoom to fit all nodes
        self.fit_all_nodes()
        
        # Create flowing particles for each edge
        self.create_flow_particles()
        
        # Then center on specific file if provided (for highlighting)
        if center_file and center_file in self.nodes:
            self.center_on_node(center_file)
        
        # Force complete repaint
        self.repaint()
    
    def apply_layout(self, layout_type: str):
        """Apply a specific layout algorithm to position nodes."""
        if not self.nodes:
            return
        
        # Create NetworkX graph for layout algorithms (only include connected nodes)
        G = nx.DiGraph()
        connected_nodes = [node_id for node_id, node in self.nodes.items() if not getattr(node, 'is_isolated', False)]
        G.add_nodes_from(connected_nodes)
        G.add_edges_from(self.edges)
        
        # Calculate positions based on layout type
        if layout_type == "Force-Directed":
            # Use more iterations and reset positions for fresh layout
            pos = nx.spring_layout(G, k=3, iterations=100, pos=None)
        elif layout_type == "Circular":
            pos = nx.circular_layout(G)
        elif layout_type == "Hierarchical":
            # Try to create hierarchical layout
            try:
                pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
            except:
                # Fallback to shell layout if graphviz not available
                pos = nx.shell_layout(G)
        elif layout_type == "Grid":
            # Simple grid layout
            n = len(self.nodes)
            cols = int(math.sqrt(n))
            rows = (n + cols - 1) // cols
            pos = {}
            for i, node_id in enumerate(self.nodes.keys()):
                row = i // cols
                col = i % cols
                pos[node_id] = (col / (cols - 1) if cols > 1 else 0.5,
                               row / (rows - 1) if rows > 1 else 0.5)
        else:
            pos = nx.spring_layout(G)
        
        # Apply positions to nodes (scale to widget size)
        width = self.width() * 0.8
        height = self.height() * 0.8
        
        for node_id, (x, y) in pos.items():
            node = self.nodes[node_id]
            node.x = x * width + width * 0.1
            node.y = y * height + height * 0.1
            node.vx = 0
            node.vy = 0
    
    def change_layout(self, layout_type: str):
        """Change the graph layout."""
        self.apply_layout(layout_type)
        self.create_flow_particles()  # Recreate particles after layout change
        self.update()
    
    def create_flow_particles(self):
        """Create flowing particles for each edge."""
        self.flow_particles = []
        
        for source, target in self.edges:
            if source in self.nodes and target in self.nodes:
                source_node = self.nodes[source]
                target_node = self.nodes[target]
                
                # Skip isolated nodes
                if (getattr(source_node, 'is_isolated', False) or 
                    getattr(target_node, 'is_isolated', False)):
                    continue
                
                # Create a particle for this edge
                particle = FlowParticle(source_node, target_node, (source, target))
                # Start particles at random positions along the edge for variety
                particle.progress = hash((source, target)) % 100 / 100.0
                particle.update_position(0)  # Set initial position
                self.flow_particles.append(particle)
    
    def update_flow_animation(self):
        """Update flowing particles animation."""
        if not self.flow_particles:
            return
        
        # Update all particles
        for particle in self.flow_particles:
            particle.update_position(self.particle_speed / 100.0)  # Normalize speed
        
        # Trigger repaint
        self.update()
    
    def prepare_summaries(self):
        """Prepare dependency-aware summaries using Groq API."""
        if not self.current_graph_data:
            print("❌ No graph data available for summarization")
            return
        
        try:
            print(f"🔄 Preparing summaries for {len(self.current_graph_data.get('nodes', []))} nodes...")
            self.summarize_btn.setText("Loading...")
            self.summarize_btn.setEnabled(False)
            
            # Prepare dependency signatures
            groq_api = get_groq_dependency_api()
            if groq_api:
                groq_api.prepare_dependency_signatures(self.current_graph_data)
            self.summaries_prepared = True
            self.summarize_btn.setText("✓ Ready")
            print("✅ Dependency summaries prepared - click on nodes to see summaries")
            
        except Exception as e:
            print(f"❌ Error preparing summaries: {e}")
            import traceback
            traceback.print_exc()
            self.summarize_btn.setText("Error")
            self.summarize_btn.setEnabled(True)
    
    
    def _update_click_summary(self, file_path: str):
        """Update click summary asynchronously without blocking UI."""
        print(f"🎯 Requesting summary for: {file_path}")
        
        # Show loading message immediately
        self.click_summary = "Loading summary..."
        self.update()
        
        # Start summary worker thread
        self.summary_worker = SummaryWorker(file_path, self.summaries_prepared)
        self.summary_worker.summary_ready.connect(self._on_summary_ready)
        self.summary_worker.summary_error.connect(self._on_summary_error)
        self.summary_worker.start()
    
    def _on_summary_ready(self, summary: str):
        """Handle summary result from worker thread."""
        print(f"✅ Got summary: {summary[:100]}...")
        self.click_summary = summary
        self.update()
    
    def _on_summary_error(self, error: str):
        """Handle summary error from worker thread."""
        print(f"❌ Summary error: {error}")
        self.click_summary = f"Summary error: {error}"
        self.update()
    
    
    def update_physics(self):
        """Update node positions using force-directed physics."""
        if not self.nodes:
            return
        
        # Apply forces between nodes
        for node_id1, node1 in self.nodes.items():
            fx = 0
            fy = 0
            
            # Repulsion between all nodes
            for node_id2, node2 in self.nodes.items():
                if node_id1 != node_id2:
                    dx = node1.x - node2.x
                    dy = node1.y - node2.y
                    dist = max(math.sqrt(dx * dx + dy * dy), self.min_distance)
                    
                    force = self.repulsion_strength / (dist * dist)
                    fx += (dx / dist) * force
                    fy += (dy / dist) * force
            
            # Attraction along edges
            for source, target in self.edges:
                if source == node_id1:
                    other = self.nodes[target]
                elif target == node_id1:
                    other = self.nodes[source]
                else:
                    continue
                
                dx = other.x - node1.x
                dy = other.y - node1.y
                dist = math.sqrt(dx * dx + dy * dy)
                
                if dist > 0:
                    force = dist * self.attraction_strength
                    fx += (dx / dist) * force
                    fy += (dy / dist) * force
            
            # Update velocity and position
            node1.vx = (node1.vx + fx) * self.damping
            node1.vy = (node1.vy + fy) * self.damping
            
            node1.x += node1.vx
            node1.y += node1.vy
            
            # Keep nodes within bounds
            margin = node1.radius
            node1.x = max(margin, min(self.width() - margin, node1.x))
            node1.y = max(margin, min(self.height() - margin, node1.y))
        
        self.update()
    
    def fit_all_nodes(self):
        """Auto-center and zoom to fit all visible nodes in the viewport."""
        if not self.nodes:
            return
        
        # Filter to only consider non-isolated nodes (visible nodes)
        visible_nodes = [node for node in self.nodes.values() if not getattr(node, 'is_isolated', False)]
        
        if not visible_nodes:
            return
        
        # Calculate bounding box of all visible nodes
        min_x = min(node.x - node.radius for node in visible_nodes)
        max_x = max(node.x + node.radius for node in visible_nodes)
        min_y = min(node.y - node.radius for node in visible_nodes)
        max_y = max(node.y + node.radius for node in visible_nodes)
        
        # Calculate content dimensions
        content_width = max_x - min_x
        content_height = max_y - min_y
        
        # Calculate content center
        content_center_x = (min_x + max_x) / 2
        content_center_y = (min_y + max_y) / 2
        
        # Calculate widget center
        widget_center_x = self.width() / 2
        widget_center_y = self.height() / 2
        
        # Calculate zoom to fit all nodes with some padding
        padding = 50  # pixels of padding
        if content_width > 0 and content_height > 0:
            zoom_x = (self.width() - 2 * padding) / content_width
            zoom_y = (self.height() - 2 * padding) / content_height
            target_zoom = min(zoom_x, zoom_y, 2.0)  # Cap max zoom at 2.0
            target_zoom = max(target_zoom, 0.2)  # Set minimum zoom at 0.2
        else:
            target_zoom = 1.0
        
        # Calculate pan to center the content
        self.zoom = target_zoom
        self.pan_x = widget_center_x - content_center_x * self.zoom
        self.pan_y = widget_center_y - content_center_y * self.zoom
        
        # Update zoom slider to reflect new zoom level
        self.zoom_slider.setValue(int(self.zoom * 100))
        
        self.update()

    def center_on_node(self, file_path: str):
        """Center the view on a specific node."""
        if file_path in self.nodes:
            node = self.nodes[file_path]
            self.pan_x = self.width() / 2 - node.x * self.zoom
            self.pan_y = self.height() / 2 - node.y * self.zoom
            self.update()
    
    def reset_view(self):
        """Reset zoom and pan to default."""
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.zoom_slider.setValue(100)
        self.update()
    
    def set_zoom(self, zoom: float):
        """Set zoom level."""
        self.zoom = max(0.1, min(3.0, zoom))
        self.update()
    
    def paintEvent(self, event):
        """Paint the graph."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), self.background_color)
        
        # Apply transformations
        painter.translate(self.pan_x, self.pan_y)
        painter.scale(self.zoom, self.zoom)
        
        # Draw edges
        self.draw_edges(painter)
        
        # Draw nodes
        self.draw_nodes(painter)
        
        # Draw flowing particles
        self.draw_flow_particles(painter)
        
        # Draw labels
        self.draw_labels(painter)
        
        # Draw click summary (without transform to keep it in screen coordinates)
        painter.resetTransform()
        self.draw_click_summary(painter)
    
    
    def draw_edges(self, painter: QPainter):
        """Draw edges between nodes with arrows showing dependency direction."""
        pen = QPen(self.edge_color, 2)
        painter.setPen(pen)
        
        for source, target in self.edges:
            if source in self.nodes and target in self.nodes:
                source_node = self.nodes[source]  # The file that imports
                target_node = self.nodes[target]  # The file being imported
                
                # Skip isolated nodes in edge drawing
                if (getattr(source_node, 'is_isolated', False) or 
                    getattr(target_node, 'is_isolated', False)):
                    continue
                
                # Calculate direction vector from source to target
                dx = target_node.x - source_node.x
                dy = target_node.y - source_node.y
                dist = math.sqrt(dx * dx + dy * dy)
                
                if dist > 0:
                    # Normalize direction
                    dx /= dist
                    dy /= dist
                    
                    # Calculate start and end points (edge of circles, not centers)
                    start_x = source_node.x + dx * source_node.radius
                    start_y = source_node.y + dy * source_node.radius
                    end_x = target_node.x - dx * target_node.radius
                    end_y = target_node.y - dy * target_node.radius
                    
                    # Draw the main line from source to target
                    painter.drawLine(QPointF(start_x, start_y), QPointF(end_x, end_y))
                    
                    # Draw arrowhead pointing to target (dependency direction)
                    angle = math.atan2(dy, dx)
                    arrow_length = 12
                    arrow_angle = 0.4
                    
                    # Calculate arrowhead points
                    arrow_x1 = end_x - arrow_length * math.cos(angle - arrow_angle)
                    arrow_y1 = end_y - arrow_length * math.sin(angle - arrow_angle)
                    arrow_x2 = end_x - arrow_length * math.cos(angle + arrow_angle)
                    arrow_y2 = end_y - arrow_length * math.sin(angle + arrow_angle)
                    
                    # Draw arrowhead lines
                    painter.drawLine(QPointF(end_x, end_y), QPointF(arrow_x1, arrow_y1))
                    painter.drawLine(QPointF(end_x, end_y), QPointF(arrow_x2, arrow_y2))
    
    def draw_flow_particles(self, painter: QPainter):
        """Draw flowing particles that show dependency direction."""
        for particle in self.flow_particles:
            # Draw particle as a small glowing circle
            painter.setBrush(QBrush(particle.color))
            painter.setPen(QPen(QColor(255, 255, 255, 150), 1))
            painter.drawEllipse(QPointF(particle.x, particle.y), particle.radius, particle.radius)
            
            # Add a subtle glow effect
            glow_color = QColor(particle.color)
            glow_color.setAlpha(50)
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(particle.x, particle.y), particle.radius + 2, particle.radius + 2)
    
    def draw_click_summary(self, painter: QPainter):
        """Draw click summary tooltip."""
        if not self.click_summary or not self.selected_summary_node:
            return
        
        # Set up tooltip styling
        painter.setFont(QFont("Arial", 10))
        
        # Calculate tooltip dimensions with word wrapping for long lines
        original_lines = self.click_summary.split('\n')
        wrapped_lines = []
        max_line_width = 250  # Reduced maximum width for any line
        
        font_metrics = painter.fontMetrics()
        
        for line in original_lines:
            line = line.strip()
            if not line:
                wrapped_lines.append("")
                continue
                
            # Check if line fits within max width
            if font_metrics.horizontalAdvance(line) <= max_line_width:
                wrapped_lines.append(line)
            else:
                # Word wrap long lines
                words = line.split(' ')
                current_line = ""
                
                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    if font_metrics.horizontalAdvance(test_line) <= max_line_width:
                        current_line = test_line
                    else:
                        if current_line:
                            wrapped_lines.append(current_line)
                        current_line = word
                
                if current_line:
                    wrapped_lines.append(current_line)
        
        # Calculate actual dimensions
        max_width = 0
        line_height = font_metrics.height() + 2  # Small spacing between lines
        
        for line in wrapped_lines:
            if line:  # Skip empty lines for width calculation
                text_width = font_metrics.horizontalAdvance(line)
                max_width = max(max_width, text_width)
        
        tooltip_width = max_width + 16  # Reduced padding
        tooltip_height = len(wrapped_lines) * line_height + 12  # Top/bottom padding
        
        # Position tooltip near selected node but in screen coordinates
        node_screen_x = (self.selected_summary_node.x * self.zoom) + self.pan_x
        node_screen_y = (self.selected_summary_node.y * self.zoom) + self.pan_y
        
        # Smart positioning to keep within bounds
        margin = 10  # Margin from window edges
        
        # Try positioning to the right of the node first
        tooltip_x = node_screen_x + 30
        tooltip_y = node_screen_y - tooltip_height - 10
        
        # Check right boundary
        if tooltip_x + tooltip_width > self.width() - margin:
            # Position to the left of the node
            tooltip_x = node_screen_x - tooltip_width - 30
        
        # Check left boundary
        if tooltip_x < margin:
            # Center it if it doesn't fit on either side
            tooltip_x = max(margin, (self.width() - tooltip_width) / 2)
        
        # Check top boundary
        if tooltip_y < margin:
            # Position below the node
            tooltip_y = node_screen_y + 30
        
        # Check bottom boundary
        if tooltip_y + tooltip_height > self.height() - margin:
            # Position above the node
            tooltip_y = node_screen_y - tooltip_height - 10
            # If still doesn't fit, move it up more
            if tooltip_y < margin:
                tooltip_y = margin
        
        # Draw tooltip background
        tooltip_rect = QRectF(tooltip_x, tooltip_y, tooltip_width, tooltip_height)
        painter.setBrush(QBrush(QColor(40, 40, 40, 230)))  # Semi-transparent dark background
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRoundedRect(tooltip_rect, 5, 5)
        
        # Draw tooltip text
        painter.setPen(QPen(Qt.white))
        text_y = tooltip_y + 8  # Reduced top padding
        
        for line in wrapped_lines:
            if line:  # Only draw non-empty lines
                painter.drawText(int(tooltip_x + 8), int(text_y + font_metrics.ascent()), line)
            text_y += line_height
    
    def draw_nodes(self, painter: QPainter):
        """Draw nodes."""
        for node in self.nodes.values():
            # Skip isolated nodes (filter at display level, not data level)
            if getattr(node, 'is_isolated', False):
                continue
                
            # Determine color
            if node.selected:
                color = self.selected_color
            elif node.highlighted:
                color = self.highlight_color
            else:
                color = node.color
            
            # Draw node circle
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.white, 2))
            painter.drawEllipse(QPointF(node.x, node.y), node.radius, node.radius)
            
            # Draw selection indicator
            if node.selected:
                painter.setPen(QPen(Qt.white, 3, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(node.x, node.y), node.radius + 5, node.radius + 5)
    
    def draw_labels(self, painter: QPainter):
        """Draw node labels."""
        painter.setPen(QPen(Qt.white))
        font = QFont("Arial", 9)
        painter.setFont(font)
        
        for node in self.nodes.values():
            # Skip isolated nodes (filter at display level, not data level)
            if getattr(node, 'is_isolated', False):
                continue
                
            # Show labels for all connected nodes, selected, or highlighted nodes
            if node.selected or node.highlighted or not node.is_isolated:
                rect = QRectF(node.x - 60, node.y + node.radius + 5, 120, 20)
                painter.drawText(rect, Qt.AlignCenter, node.label)
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.LeftButton:
            # Transform mouse coordinates
            x = (event.x() - self.pan_x) / self.zoom
            y = (event.y() - self.pan_y) / self.zoom
            
            # Check if clicking on a node (skip isolated nodes)
            clicked_node = None
            for node in self.nodes.values():
                if not getattr(node, 'is_isolated', False) and node.contains_point(x, y):
                    clicked_node = node
                    break
            
            if clicked_node:
                # Select node
                if self.selected_node:
                    self.selected_node.selected = False
                clicked_node.selected = True
                self.selected_node = clicked_node
                self.nodeClicked.emit(clicked_node.file_path)
                
                # Get summary if summaries are prepared
                if self.summaries_prepared:
                    print(f"🎯 Click detected on: {clicked_node.file_path}")
                    self.selected_summary_node = clicked_node
                    self._update_click_summary(clicked_node.file_path)
                else:
                    print("⚠️  Click detected but summaries not prepared - click 'Summarize' first")
                    self.click_summary = "Click 'Summarize' button first"
                    self.selected_summary_node = None
            else:
                # Clear summary when clicking on empty space
                self.click_summary = ""
                self.selected_summary_node = None
                
                # Start panning
                self.is_panning = True
                self.mouse_press_pos = event.pos()
        
        self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        self.is_panning = False
    
    def mouseDoubleClickEvent(self, event):
        """Handle double click events."""
        # Transform mouse coordinates
        x = (event.x() - self.pan_x) / self.zoom
        y = (event.y() - self.pan_y) / self.zoom
        
        # Check if clicking on a node
        for node in self.nodes.values():
            if node.contains_point(x, y):
                self.nodeDoubleClicked.emit(node.file_path)
                break
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        if self.is_panning and self.mouse_press_pos:
            # Pan the view
            delta = event.pos() - self.mouse_press_pos
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            self.mouse_press_pos = event.pos()
            self.update()
        else:
            # Simple hover highlighting (no summaries)
            x = (event.x() - self.pan_x) / self.zoom
            y = (event.y() - self.pan_y) / self.zoom
            
            # Reset previous hover
            if self.hover_node:
                self.hover_node.highlighted = False
                self.hover_node = None
            
            # Check for new hover (just for visual highlighting)
            for node in self.nodes.values():
                if not getattr(node, 'is_isolated', False) and node.contains_point(x, y):
                    node.highlighted = True
                    self.hover_node = node
                    break
            
            self.update()
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        # Zoom in/out
        delta = event.angleDelta().y() / 120
        new_zoom = self.zoom * (1.1 ** delta)
        self.set_zoom(new_zoom)
        self.zoom_slider.setValue(int(self.zoom * 100))
    
    def highlight_dependencies(self, file_path: str, depth: int = 1):
        """Highlight dependencies of a specific file."""
        # Reset all highlights
        for node in self.nodes.values():
            node.highlighted = False
        
        if file_path not in self.nodes:
            return
        
        # Highlight the file itself
        self.nodes[file_path].highlighted = True
        
        # Highlight dependencies
        highlighted = {file_path}
        for _ in range(depth):
            new_highlighted = set()
            for source, target in self.edges:
                if source in highlighted:
                    new_highlighted.add(target)
                    if target in self.nodes:
                        self.nodes[target].highlighted = True
                if target in highlighted:
                    new_highlighted.add(source)
                    if source in self.nodes:
                        self.nodes[source].highlighted = True
            highlighted.update(new_highlighted)
        
        self.update()