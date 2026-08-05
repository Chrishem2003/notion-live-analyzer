"""
Streamlit multipage app package.

Each numbered module in this directory is a standalone Streamlit page
discovered automatically by the multipage framework. This __init__ file
keeps the package importable and holds shared page-registry metadata.
"""

# Optional: expose a registry of page titles for central navigation/discovery.
PAGE_REGISTRY = {
    1: "File Analyzer & Ingestion",
    2: "Statistical Tests",
    3: "Advanced Visuals",
    4: "AI Insights",
    5: "Settings",
    6: "Predictive Modeling",
    7: "Variable View",
    8: "Data Transformer",
    9: "Methodology Advisor",
    10: "Clinical Analytics",
    11: "Text Analysis",
    12: "Dashboard Builder",
    13: "Data Quality",
    14: "Data Simulator",
    15: "APA Outputs",
    16: "Google Sheets",
    17: "Git Integration",
    18: "Presentation Deck",
    19: "Literature Engine",
    20: "Meta Analysis",
    21: "Global Research Radar",
    22: "Causal Analysis",
    23: "Bayesian Analysis",
    24: "Network Analysis",
    25: "Sensitivity Analysis",
    26: "Feature Engineering",
    27: "Resampling Validation",
    28: "Publication Tables",
    29: "Literature Context",
    30: "Research Quality",
    31: "NL Query",
    32: "Audit Compliance",
    33: "Research Synthesizer",
    34: "Global Localization",
    35: "Methodology Auditor",
    36: "Lab Protocol Transpiler",
    37: "Chart Data Extractor",
    38: "Research Gap Finder",
    39: "Interactive Audio",
    40: "Citation Inspector",
    41: "Meta Analysis Matrix",
    42: "Hypothesis Simulator",
    43: "Grant Formatter",
    44: "Secure Personal Vault",
    45: "Project Collaboration",
    46: "Application Pipeline",
    47: "System Diagnostics",
    48: "Advanced Chaos Engine",
}


def get_page_count() -> int:
    """Return the number of registered pages."""
    return len(PAGE_REGISTRY)
