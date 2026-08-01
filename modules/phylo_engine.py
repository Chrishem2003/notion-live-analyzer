# --- CHRISHEM AUTHOR PROFILE BLOCK ---
import os
import streamlit as st

st.markdown("# **Notion Live Analyzer**")
st.markdown("### **Creator: CHRISHEM**")
st.markdown("---")
# -------------------------------------

from io import StringIO
try:
    from Bio import SeqIO
    BIOPYTHON_AVAILABLE = True
except ImportError:
    BIOPYTHON_AVAILABLE = False
    SeqIO = None
import numpy as np

def parse_multi_fasta(fasta_text: str):
    """Parses raw multi-FASTA string into a dictionary of IDs and Sequences."""
    records = list(SeqIO.parse(StringIO(fasta_text), "fasta"))
    if len(records) < 2:
        raise ValueError("At least 2 FASTA sequences are required for alignment and tree generation.")
    return records

def calculate_distance_matrix(records):
    """Calculates normalized hamming distance matrix for alignable sequences."""
    n = len(records)
    matrix = np.zeros((n, n))
    names = [rec.id for rec in records]
    
    # Pad sequences to match maximum length
    max_len = max(len(rec.seq) for rec in records)
    padded_seqs = [str(rec.seq).ljust(max_len, '-') for rec in records]

    for i in range(n):
        for j in range(i  1, n):
            s1, s2 = padded_seqs[i], padded_seqs[j]
            mismatches = sum(1 for a, b in zip(s1, s2) if a != b)
            dist = round(mismatches / max_len, 4)
            matrix[i][j] = dist
            matrix[j][i] = dist

    return names, matrix

def generate_simple_newick(names, dist_matrix):
    """Builds a basic Neighbor-Joining style Newick string representation."""
    # Build a simplified star/neighbor branch structure
    branches = [f"{names[i]}:{dist_matrix[0][i]/2:.4f}" for i in range(1, len(names))]
    newick_str = f"({names[0]}:0.01,("  ",".join(branches)  "));"
    return newick_str

def render_ascii_tree(names):
    """Generates an ASCII visual phylogenetic tree structure."""
    lines = [" Phylogeny Tree Visualizer", " └─ Root"]
    for i, name in enumerate(names):
        prefix = "    ├── " if i < len(names) - 1 else "    └── "
        lines.append(f"{prefix}{name}")
    return "\n".join(lines)

