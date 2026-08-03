import security_guard

import requests

def translate_dna_to_protein(dna_seq: str) -> dict:
    """Translates a DNA sequence into amino acids using the standard genetic code."""
    codon_table = {
        'ATA':'I', 'ATC':'I', 'ATT':'I', 'ATG':'M',
        'ACA':'T', 'ACC':'T', 'ACG':'T', 'ACT':'T',
        'AAC':'N', 'AAT':'N', 'AAA':'K', 'AAG':'K',
        'AGC':'S', 'AGT':'S', 'AGA':'R', 'AGG':'R',
        'CTA':'L', 'CTC':'L', 'CTG':'L', 'CTT':'L',
        'CCA':'P', 'CCC':'P', 'CCG':'P', 'CCT':'P',
        'CAC':'H', 'CAT':'H', 'CAA':'Q', 'CAG':'Q',
        'CGA':'R', 'CGC':'R', 'CGG':'R', 'CGT':'R',
        'GTA':'V', 'GTC':'V', 'GTG':'V', 'GTT':'V',
        'GCA':'A', 'GCC':'A', 'GCG':'A', 'GCT':'A',
        'GAC':'D', 'GAT':'D', 'GAA':'E', 'GAG':'E',
        'GGA':'G', 'GGC':'G', 'GGG':'G', 'GGT':'G',
        'TCA':'S', 'TCC':'S', 'TCG':'S', 'TCT':'S',
        'TTC':'F', 'TTT':'F', 'TTA':'L', 'TTG':'L',
        'TAC':'Y', 'TAT':'Y', 'TAA':'_', 'TAG':'_', 'TGA':'_'
    }
    
    seq = dna_seq.upper().replace(" ", "").replace("\n", "")
    protein = []
    for i in range(0, len(seq) - len(seq) % 3, 3):
        codon = seq[i:i3]
        protein.append(codon_table.get(codon, '?'))
        
    protein_seq = "".join(protein)
    
    # Rough molecular weight estimation (avg amino acid ~ 110 Da)
    mol_weight_kDa = round((len(protein_seq) * 110) / 1000.0, 2)
    
    return {
        "protein_sequence": protein_seq,
        "aa_count": len(protein_seq),
        "est_mol_weight_kDa": mol_weight_kDa,
        "stop_codons": protein_seq.count('_')
    }

def fetch_pdb_metadata(pdb_id: str) -> dict:
    """Fetches structure metadata from RCSB Protein Data Bank."""
    url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id.lower()}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            title = data.get("struct", {}).get("title", "N/A")
            method = data.get("exptl", [{}])[0].get("method", "N/A")
            resolution = data.get("rcsb_entry_info", {}).get("resolution_combined", ["N/A"])[0]
            return {
                "pdb_id": pdb_id.upper(),
                "title": title,
                "method": method,
                "resolution": f"{resolution} Ã…" if resolution != "N/A" else "N/A",
                "valid": True
            }
    except Exception:
        pass
    return {"pdb_id": pdb_id.upper(), "valid": False, "error": "PDB ID not found or API unavailable"}
