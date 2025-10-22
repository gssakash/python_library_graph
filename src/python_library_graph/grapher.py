import networkx as nx
# Replaced pyvis with plotly for 3D visualization
import plotly.graph_objects as go
import plotly.colors as pcolors # Import colors for clustering
import importlib.util # For dynamic import of community module
import numpy as np 
import os
import sys
import argparse
# Removed Selenium dependencies. We now rely on the 'kaleido' engine for static image export.

# Python built-in modules for running external commands
import subprocess
import json

# NOTE: The project now requires 'pipreqs', 'plotly', 'networkx', 'kaleido' (for static image export), 
# and optionally 'python-louvain' (for community detection).
# Please ensure 'pip install pipreqs plotly networkx kaleido python-louvain' is included in the installation steps.

# --- MOCK DATA FOR FALLBACK/TESTING ONLY ---
MOCK_DEPENDENCY_DATA = {
    "python-library-graph": ["pytest", "networkx", "plotly", "kaleido"],
    "pytest": ["iniconfig", "packaging"],
    "networkx": ["decorator"],
    "plotly": ["numpy", "tenacity"],
    "kaleido": ["svgwrite"],
    "iniconfig": [],
    "packaging": [],
    "decorator": [],
    "numpy": [],
    "tenacity": [],
    "svgwrite": [],
}

# --- MOCK DEPENDENCY SIZES (Used for Edge Labels) ---
# NOTE: Real dependency size must be calculated by a separate tool or included in your data source.
MOCK_DEPENDENCY_SIZES = {
    "pytest": "250 KB", "networkx": "4.1 MB", "plotly": "10 MB", "kaleido": "2.2 MB",
    "iniconfig": "50 KB", "packaging": "300 KB", "decorator": "80 KB", "numpy": "25 MB",
    "tenacity": "120 KB", "svgwrite": "60 KB"
}
# ------------------------------------------

def resolve_dependencies():
    """
    Executes 'pipdeptree --json' to get the real, current dependency tree 
    of the active Python environment.
    
    Returns:
        A dict mapping {package_name: [list_of_dependencies]}
    """
    requirements_file = 'requirements.txt'

    # 0. Check for requirements.txt and generate if missing using pipreqs
    if not os.path.exists(requirements_file):
        print(f"INFO: '{requirements_file}' not found. Generating using pipreqs...", file=sys.stderr)
        try:
            # Run pipreqs on the current working directory to generate requirements.txt
            subprocess.run(
                [sys.executable, '-m', 'pipreqs', os.getcwd(), '--force'], 
                capture_output=True, 
                text=True, 
                check=True
            )
            print(f"INFO: Successfully generated '{requirements_file}'.", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"WARNING: Failed to run pipreqs. Please ensure 'pip install pipreqs' is run. Details: {e.stderr}", file=sys.stderr)
        except FileNotFoundError:
            print(f"WARNING: 'pipreqs' command not found. Please install it with 'pip install pipreqs'.", file=sys.stderr)


    try:
        # Use subprocess to run pipdeptree command
        # The `--json` flag provides structured, easy-to-parse output.
        result = subprocess.run(
            [sys.executable, '-m', 'pipdeptree', '--json'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # 1. Parse the JSON output
        tree_list = json.loads(result.stdout)
        
        # 2. Transform the list structure into the required dictionary format
        dependency_map = {}
        
        # First pass: map all packages to their direct dependencies
        for package_info in tree_list:
            package_name = package_info.get('package', {}).get('key')
            if package_name:
                # Extract keys of direct dependencies
                dependencies = [dep.get('key') for dep in package_info.get('dependencies', []) if dep.get('key')]
                dependency_map[package_name] = dependencies

        # 3. Use the current project name as the graph root.
        try:
            current_project_name = os.path.basename(os.getcwd()).lower().replace('-', '_')
        except:
            current_project_name = "local_environment_root"
        
        return dependency_map

    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to run pipdeptree. Make sure 'pip install pipdeptree' is run. Details: {e.stderr}", file=sys.stderr)
        print("--- FALLING BACK TO MOCK DATA ---", file=sys.stderr)
        return MOCK_DEPENDENCY_DATA
    except Exception as e:
        print(f"ERROR during dependency resolution: {e}", file=sys.stderr)
        print("--- FALLING BACK TO MOCK DATA ---", file=sys.stderr)
        return MOCK_DEPENDENCY_DATA


def generate_dependency_graph(project_name, dep_data, html_filename, screenshot_filename):
    """
    Generates an interactive 3D graph using Plotly/NetworkX and captures a screenshot.
    Colors nodes based on community detection (modularity) if available, 
    otherwise falls back to dependency depth (Direct/Transitive).
    """
    G = nx.DiGraph()

    # 1. Add Project Root Node and Dependencies
    top_level_deps = set()
    
    # First pass: Build the graph and identify top-level nodes
    for parent, children in dep_data.items():
        is_transitive_dependency = any(parent in sub_deps for sub_deps in dep_data.values())
        if not is_transitive_dependency:
            top_level_deps.add(parent)
        
        G.add_node(parent)
        for child in children:
            G.add_node(child)
            G.add_edge(parent, child, title="depends on")

    # Connect Top-Level Dependencies to the Project Root Node
    G.add_node(project_name)
    for dep in top_level_deps:
        if dep != project_name:
             G.add_edge(project_name, dep, title="direct requirement")

    # 2. Compute 3D Spring Layout
    # Use NetworkX's spring layout algorithm to place nodes in 3D space
    pos = nx.spring_layout(G, dim=3, seed=42)
    
    # 3. Prepare Edge Traces (Lines) & Edge Label Traces
    edge_x = []
    edge_y = []
    edge_z = []
    
    edge_label_x = []
    edge_label_y = []
    edge_label_z = []
    edge_labels = []

    for edge in G.edges():
        x0, y0, z0 = pos[edge[0]]
        x1, y1, z1 = pos[edge[1]]
        
        # Line trace coordinates
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_z.extend([z0, z1, None])
        
        # Label midpoint coordinates
        xm = (x0 + x1) / 2
        ym = (y0 + y1) / 2
        zm = (z0 + z1) / 2
        
        edge_label_x.append(xm)
        edge_label_y.append(ym)
        edge_label_z.append(zm)
        
        # Get mock size for the destination dependency node and format for bold text
        dep_name = edge[1]
        size_label = MOCK_DEPENDENCY_SIZES.get(dep_name, "Unknown Size")
        # Use HTML <b> tag for bolding the label text
        edge_labels.append(f"<b>{size_label}</b>")


    edge_trace = go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z,
        line=dict(width=0.8, color='#8A2BE2'), # Edges in a purple shade
        hoverinfo='none',
        mode='lines')
    
    # Trace for bold edge labels (dependency sizes)
    edge_label_trace = go.Scatter3d(
        x=edge_label_x, y=edge_label_y, z=edge_label_z,
        mode='text',
        hoverinfo='none',
        text=edge_labels,
        textfont=dict(
            color='white',
            size=10, # Smaller font for edge labels
        )
    )

    # 4. Prepare Node Traces (Points)
    node_x = []
    node_y = []
    node_z = []
    node_info = []
    node_text = []
    node_size = []
    node_color = []

    # --- COMMUNITY DETECTION LOGIC (Clustering by Connectivity) ---
    community = None
    partition = {}
    coloring_method = "Depth" # Default method
    
    # Check if 'python-louvain' is installed to enable structural clustering
    if importlib.util.find_spec('community'):
        try:
            # Dynamically import the community module (python-louvain)
            community = importlib.import_module('community')
            # Calculate communities using the Louvain method
            partition = community.best_partition(G.to_undirected()) # Louvain works on undirected graphs
            
            num_communities = max(partition.values()) + 1
            # Use a large discrete color set for community IDs
            colors = pcolors.qualitative.Alphabet
            
            print(f"INFO: Detected {num_communities} communities. Coloring nodes by community.", file=sys.stderr)
            
        except ImportError:
            community = None 
            print("WARNING: 'python-louvain' module failed to import. Falling back to Depth-based coloring.", file=sys.stderr)
        except Exception as e:
             community = None
             print(f"WARNING: Community detection failed ({e}). Falling back to Depth-based coloring.", file=sys.stderr)

    # --- Assign Colors based on Community or Depth ---
    for node in G.nodes():
        x, y, z = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_z.append(z)
        
        # Determine size, title, and coloring method
        size = 3 if node == project_name else (2 if node in top_level_deps else 1)
        title = ""
        
        current_coloring_method = "Depth (Fallback)"
        
        # 1. Project Root: Always Gold (Highest priority)
        if node == project_name:
            color = '#FFD700'  # Project Root: Gold (High Contrast)
            title = f"Root: {node}"
            current_coloring_method = "Project Root"
        
        # 2. Community Detection Coloring (Next priority)
        elif community is not None and node in partition:
            community_id = partition[node]
            # Use modulo to cycle through the available colors
            color_index = community_id % len(colors)
            color = colors[color_index]
            title = f"Community {community_id}: {node}"
            current_coloring_method = "Community"

        # 3. Fallback: Depth-based Coloring
        elif node in top_level_deps:
            color = '#8A2BE2'  # Direct: Blue Violet (Purple)
            title = f"Direct Dep: {node}"
        else:
            color = '#4169E1'  # Transitive: Royal Blue
            title = f"Transitive Dep: {node}"

        # Text for permanent label (bold, 15px is set in layout)
        node_text.append(f"<b>{node}</b>")
        # Text for hover info
        node_info.append(f"{node}<br>{title}<br>Coloring Method: {current_coloring_method}") 
        node_size.append(size * 10)
        node_color.append(color)


    node_trace = go.Scatter3d(
        x=node_x, y=node_y, z=node_z,
        mode='markers+text', # SHOW LABELS BY DEFAULT
        hoverinfo='text',
        text=node_text, # Use the bolded text for the persistent label
        textposition="middle center",
        marker=dict(
            symbol='circle',
            size=node_size,
            color=node_color,
            line=dict(color='rgba(0,0,0,0)', width=0.5)
        ),
        textfont=dict(
            color='white', 
            size=15 # Requested 15px font size
        ),
        customdata=node_info # Store hover info
    )

    # 5. Create 3D Figure
    fig = go.Figure(data=[edge_trace, node_trace, edge_label_trace], # Added edge_label_trace
                 layout=go.Layout(
                    title=f'<span style="color:white; font-size:18px;"><b>Interactive 3D Dependency Graph: {project_name}</b></span>',
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    paper_bgcolor='#1A202C', # Dark background
                    plot_bgcolor='#1A202C', # Dark plot area
                    font=dict(
                        color="white", # White text
                        size=15, # Default font size for other elements
                    ),
                    scene=dict(
                        # Define dark background for the 3D scene itself
                        xaxis=dict(showbackground=False, showline=False, zeroline=False, showgrid=False, title='', backgroundcolor='#1A202C'),
                        yaxis=dict(showbackground=False, showline=False, zeroline=False, showgrid=False, title='', backgroundcolor='#1A202C'),
                        zaxis=dict(showbackground=False, showline=False, zeroline=False, showgrid=False, title='', backgroundcolor='#1A202C'),
                        aspectmode='cube'
                    ),
                    height=750, # Set plot height
                    )
                )

    # 6. Save HTML File (self-contained)
    # include_plotlyjs='cdn' ensures the file is self-contained but loads the library from a CDN
    fig.write_html(html_filename, auto_open=False, include_plotlyjs='cdn')
    print(f"Interactive 3D graph saved to: {html_filename}")

    # 7. Capture Screenshot using Plotly's native export (requires kaleido)
    print("Capturing static preview using kaleido...")
    try:
        # Export the figure directly as a high-resolution PNG using kaleido
        fig.write_image(
            screenshot_filename, 
            format='png', 
            width=2000, 
            height=2000,
            engine='kaleido'
        )
        print(f"Static preview saved to: {screenshot_filename}")

    except Exception as e:
        print(f"WARNING: Could not generate screenshot using kaleido. Please ensure 'pip install kaleido' is run. Error: {e}", file=sys.stderr)
