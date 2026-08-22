
import os
import json

def build_research_knowledge_graph(entities: list, output_html: str = "graph.html"):
    """Generates an HTML interactive force-directed knowledge graph of research entities."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style type="text/css">
            #network {{
                width: 100%;
                height: 450px;
                border: 1px solid #3A4048;
                background-color: #0B0E11;
                border-radius: 8px;
            }
        </style>
    </head>
    <body>
    <div id="network"></div>
    <script type="text/javascript">
        var nodes = new vis.DataSet([
            {{id: 1, label: 'Research Workspace', color: '#3B82F6', shape: 'diamond'},
            {{id: 2, label: 'Genomic Target (NCBI)', color: '#34C787'},
            {{id: 3, label: 'Notion Database DB-1', color: '#8B5CF6'},
            {{id: 4, label: 'PubMed Citation Graph', color: '#E8A33D'},
            {{id: 5, label: 'Field Telemetry (Satellite)', color: '#EC4899'}
        ]);

        var edges = new vis.DataSet([
            {{from: 1, to: 2},
            {{from: 1, to: 3},
            {{from: 1, to: 4},
            {{from: 1, to: 5},
            {{from: 2, to: 4}
        ]);

        var container = document.getElementById('network');
        var data = {{ nodes: nodes, edges: edges };
        var options = {{
            nodes: {{ font: {{ color: '#ffffff' } },
            physics: {{ stabilization: true }
        };
        var network = new vis.Network(container, data, options);
    </script>
    </body>
    </html>
    """
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    return output_html
