

import re

def validate_fasta(sequence_str: str) -> bool:
    """Validates basic DNA/RNA FASTA input formatting."""
    cleaned = re.sub(r'\s', '', sequence_str).upper()
    if not cleaned:
        return False
    valid_bases = set("ATCGNUKMRYSWBVHD-")
    return all(base in valid_bases for base in cleaned)

def validate_doi(doi_str: str) -> bool:
    """Checks standard DOI format validity."""
    doi_pattern = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]$'
    return bool(re.match(doi_pattern, doi_str.strip(), re.IGNORECASE))
