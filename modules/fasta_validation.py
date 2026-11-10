"""Deterministic FASTA syntax and alphabet screening; not biological interpretation."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from modules.workflow_contract import WorkflowContractError

MAX_FASTA_BYTES = 1_000_000
MAX_FASTA_RECORDS = 2_000
NUCLEIC_ALPHABET = set("ACGTUNRYKMSWBDHV-.")
PROTEIN_ALPHABET = set("ACDEFGHIKLMNPQRSTVWYBXZJUO*-.")
CANONICAL_NUCLEIC = set("ACGTU")


def validate_fasta(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate basic FASTA structure and report alphabet/length metadata only."""
    text = payload.get("fasta_text")
    if not isinstance(text, str) or not text.strip():
        raise WorkflowContractError("fasta_text must be non-empty FASTA text")
    try:
        encoded_length = len(text.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise WorkflowContractError("fasta_text must contain valid Unicode scalar values") from exc
    if encoded_length > MAX_FASTA_BYTES:
        raise WorkflowContractError(f"FASTA input exceeds the {MAX_FASTA_BYTES}-byte limit")

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    current_header: str | None = None
    current_header_error: str | None = None
    current_sequence: list[str] = []

    def flush_record() -> None:
        nonlocal current_header, current_header_error, current_sequence
        if current_header is None:
            return
        sequence = "".join(current_sequence).upper()
        record_errors: list[str] = []
        if current_header_error is not None:
            record_errors.append(current_header_error)
        if not sequence:
            record_errors.append("Sequence is empty.")
        header_parts = current_header.split()
        record_id = header_parts[0] if header_parts else ""
        symbols = set(sequence)
        if symbols and symbols <= NUCLEIC_ALPHABET:
            sequence_type = "nucleic_acid"
            canonical_count = sum(sequence.count(base) for base in CANONICAL_NUCLEIC)
            gc_count = sequence.count("G") + sequence.count("C")
            gc_percent = round(gc_count / canonical_count * 100, 4) if canonical_count else None
            ambiguous_count = sum(1 for base in sequence if base not in CANONICAL_NUCLEIC and base not in "-.")
        elif symbols and symbols <= PROTEIN_ALPHABET:
            sequence_type = "protein"
            gc_percent = None
            ambiguous_count = sum(1 for base in sequence if base in "BXZJUO")
        else:
            sequence_type = "invalid_or_unsupported"
            gc_percent = None
            invalid_symbols = sorted(symbols - NUCLEIC_ALPHABET - PROTEIN_ALPHABET)
            if invalid_symbols:
                record_errors.append("Unsupported symbols: " + " ".join(invalid_symbols[:30]))
            elif sequence:
                record_errors.append("Sequence alphabet could not be classified.")
            ambiguous_count = None

        records.append({
            "record_id": record_id,
            "header": current_header,
            "sequence_length": len(sequence),
            "sequence_type_screen": sequence_type,
            "gc_percent_of_canonical_nucleic_bases": gc_percent,
            "ambiguous_symbol_count": ambiguous_count,
            "valid_record": not record_errors,
            "errors": record_errors,
        })
        if record_errors:
            errors.append(f"{record_id or '(unnamed record)'}: " + "; ".join(record_errors))
        current_header = None
        current_header_error = None
        current_sequence = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            flush_record()
            current_header = line[1:].strip()
            current_header_error = (
                f"Line {line_number}: FASTA header is empty."
                if not current_header
                else None
            )
            if len(records) >= MAX_FASTA_RECORDS:
                raise WorkflowContractError(f"FASTA input exceeds {MAX_FASTA_RECORDS} records")
            continue
        if current_header is None:
            raise WorkflowContractError(
                f"Line {line_number}: sequence data appears before the first FASTA header"
            )
        if any(character.isspace() for character in raw_line.strip()):
            line = "".join(line.split())
        current_sequence.append(line)

    flush_record()
    if not records:
        raise WorkflowContractError("FASTA input contains no records")

    id_counts = Counter(record["record_id"] for record in records if record["record_id"])
    duplicates = sorted(record_id for record_id, count in id_counts.items() if count > 1)
    duplicate_ids = set(duplicates)
    for record in records:
        if record["record_id"] in duplicate_ids:
            record["valid_record"] = False
            if "Duplicate FASTA record ID." not in record["errors"]:
                record["errors"].append("Duplicate FASTA record ID.")
    if duplicates:
        errors.append("Duplicate record IDs: " + ", ".join(duplicates[:50]))

    # Recompute aggregate validity after duplicate-ID checks.
    return {
        "format": "FASTA",
        "valid": all(record["valid_record"] for record in records) and not errors,
        "record_count": len(records),
        "total_sequence_length": sum(record["sequence_length"] for record in records),
        "records": records,
        "errors": errors,
        "limitations": [
            "This is a deterministic syntax/alphabet screen, not alignment, taxonomy, gene prediction, contamination detection, or scientific validation.",
            "Nucleotide/protein classification is heuristic; short sequences may be ambiguous.",
            "GC percentage uses only canonical A/C/G/T/U symbols; ambiguity and gap symbols are excluded from the denominator.",
            "This handler processes the submitted text in memory and does not persist the sequence as an accession or sequence-log record.",
        ],
        "human_review_required": True,
    }
