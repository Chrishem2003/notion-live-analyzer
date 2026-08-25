﻿
import pandas as pd
from collections import Counter
from modules.database import log_backend_event

def parse_fasta(file_contents: str) -> dict:
    """
    Parses a raw FASTA string into a dictionary mapping sequence IDs to their genetic sequences.
    """
    sequences = {}
    current_id = None
    current_seq = []

    for line in file_contents.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current_id:
                sequences[current_id] = "".join(current_seq)
            current_id = line[1:]
            current_seq = []
        else:
            current_seq.append(line.upper())
            
    if current_id:
        sequences[current_id] = "".join(current_seq)
        
    return sequences

def calculate_gc_content(sequence: str) -> float:
    """
    Calculates the GC (Guanine-Cytosine) percentage of a given DNA/RNA sequence.
    """
    if not sequence:
        return 0.0
    
    gc_count = sequence.count('G') + sequence.count('C')
    total_bases = len(sequence)
    return round((gc_count / total_bases) * 100, 2)

def analyze_sequence_batch(fasta_data: str) -> pd.DataFrame:
    """
    Processes a batch of sequences, calculating base frequencies, length, and GC content,
    returning an enterprise-ready pandas DataFrame for visualization.
    """
    try:
        parsed_data = parse_fasta(fasta_data)
        results = []
        
        for seq_id, sequence in parsed_data.items():
            base_counts = Counter(sequence)
            gc_content = calculate_gc_content(sequence)
            length = len(sequence)
            
            results.append({
                "Sequence_ID": seq_id,
                "Length": length,
                "GC_Content_%": gc_content,
                "A_Count": base_counts.get('A', 0),
                "T_Count": base_counts.get('T', 0),
                "G_Count": base_counts.get('G', 0),
                "C_Count": base_counts.get('C', 0)
            })
            
        log_backend_event("INFO", f"Successfully analyzed {len(results)} genomic sequences.")
        return pd.DataFrame(results)
        
    except Exception as e:
        log_backend_event("ERROR", f"Bioinformatics pipeline failure: {str(e)}")
        return pd.DataFrame()

