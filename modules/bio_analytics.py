import security_guard

import re
from collections import Counter

def analyze_sequence_variants(dna_seq: str):
    """Calculates GC content, sequence length, and codon distribution."""
    seq = re.sub(r'\s', '', dna_seq).upper()
    length = len(seq)
    if length == 0:
        return None
    
    gc_count = seq.count('G')  seq.count('C')
    gc_percentage = round((gc_count / length) * 100, 2)
    
    # Codon frequencies
    codons = [seq[i:i3] for i in range(0, length - length % 3, 3)]
    codon_counts = dict(Counter(codons))
    
    return {
        "length": length,
        "gc_content": gc_percentage,
        "at_content": round(100 - gc_percentage, 2),
        "total_codons": len(codons),
        "top_codons": dict(sorted(codon_counts.items(), key=lambda x: x[1], reverse=True)[:5])
    }
