import argparse
from grapher import generate_dependency_graph, MOCK_DEPENDENCY_DATA
import sys
import os

def resolve_dependencies():
    """Placeholder for real dependency resolution (e.g., using pipdeptree)."""
    print("--- WARNING: Using MOCK Dependency Data ---", file=sys.stderr)
    return MOCK_DEPENDENCY_DATA

def main():
    """
    The main entry function for the 'python-graph' command.
    """
    parser = argparse.ArgumentParser(
        description="Visualize Python dependencies as an interactive knowledge graph and generate a static preview."
    )
    parser.add_argument(
        "-p", "--project-name", 
        default=os.path.basename(os.getcwd()),
        help="The root name of the project being analyzed."
    )
    parser.add_argument(
        "-o", "--output-prefix", 
        default="dependency_graph",
        help="The base filename for the output files (e.g., 'report' creates report.html and report_preview.png)."
    )
    args = parser.parse_args()

    # Define output files based on the prefix
    html_file = f"{args.output_prefix}.html"
    screenshot_file = f"{args.output_prefix}_preview.png"

    # 1. Resolve Dependencies
    dependency_data = resolve_dependencies()
    
    # 2. Generate Graph, HTML, and Screenshot
    generate_dependency_graph(
        project_name=args.project_name,
        dep_data=dependency_data,
        html_filename=html_file,
        screenshot_filename=screenshot_file
    )
    
    print("\n----------------------------------------------------")
    print(f"Results are ready:")
    print(f"  - Interactive Graph: {html_file}")
    print(f"  - Static Preview:    {screenshot_file}")
    print("----------------------------------------------------")

if __name__ == '__main__':
    main()
