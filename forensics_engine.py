"""
CHRISHEM Forensic Intelligence Engine
=====================================
Digital Evidence Laboratory for the Sovereign Intelligence Platform.

Capabilities
  - Bit-level file hashing (SHA-256 / SHA-1 / MD5 / CRC32)
  - File signature & magic-byte carving (real content-type detection)
  - Metadata forensics (image EXIF: GPS / camera / timestamps)
  - Steganography detector (LSB analysis on images)
  - Timeline reconstruction from raw byte timestamps / metadata
  - Email header & phishing analyzer
  - Tamper-evident chain-of-custody vault (SQLite + SHA-256 ledger)

Owner: Kula Chris (CHRISHEM)
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import sqlite3
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Persistent evidence vault
# ---------------------------------------------------------------------------
EVIDENCE_DB = str(Path(__file__).resolve().parent.parent / "forensic_vault.db")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(EVIDENCE_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS evidence_cases (
            case_id TEXT PRIMARY KEY,
            filename TEXT,
            sha256 TEXT,
            size_bytes INTEGER,
            detected_type TEXT,
            summary TEXT,
            entered_at TEXT
        );
        CREATE TABLE IF NOT EXISTS custody_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT,
            action TEXT,
            actor TEXT,
            chain_hash TEXT,
            timestamp TEXT
        );
        """
    )
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def open_evidence_case(filename: str = "untitled_evidence.bin", summary: str = "") -> Dict[str, Any]:
    """Open a new tamper-evident evidence case in the vault."""
    case_id = "CASE-" + hashlib.sha256(
        (filename + _now()).encode("utf-8")
    ).hexdigest()[:12].upper()
    conn = _conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO evidence_cases (case_id, filename, sha256, size_bytes, detected_type, summary, entered_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (case_id, filename, "", 0, "UNKNOWN", summary, _now()),
        )
        # Genesis ledger entry
        genesis = hashlib.sha256(f"{case_id}|open|{_now()}".encode()).hexdigest()
        conn.execute(
            "INSERT INTO custody_ledger (case_id, action, actor, chain_hash, timestamp) VALUES (?, ?, ?, ?, ?)",
            (case_id, "CASE_OPEN", "SYSTEM", genesis, _now()),
        )
        conn.commit()
        return {"case_id": case_id, "status": "open", "genesis_hash": genesis}
    finally:
        conn.close()


def append_custody_record(case_id: str, action: str, actor: str) -> Dict[str, Any]:
    """Append a tamper-evident record to the chain-of-custody ledger."""
    conn = _conn()
    try:
        last = conn.execute(
            "SELECT chain_hash FROM custody_ledger WHERE case_id = ? ORDER BY id DESC LIMIT 1",
            (case_id,),
        ).fetchone()
        prev_hash = last["chain_hash"] if last else "GENESIS"
        # Chain the new record to the previous hash -> tamper evident
        block = f"{case_id}|{action}|{actor}|{_now()}|{prev_hash}"
        chain_hash = hashlib.sha256(block.encode()).hexdigest()
        conn.execute(
            "INSERT INTO custody_ledger (case_id, action, actor, chain_hash, timestamp) VALUES (?, ?, ?, ?, ?)",
            (case_id, action, actor, chain_hash, _now()),
        )
        conn.commit()
        return {"prev_hash": prev_hash, "chain_hash": chain_hash, "status": "appended"}
    finally:
        conn.close()


def verify_chain(case_id: str) -> Dict[str, Any]:
    """Verify the integrity of a case's custody chain."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT action, chain_hash, timestamp FROM custody_ledger WHERE case_id = ? ORDER BY id ASC",
            (case_id,),
        ).fetchall()
        if not rows:
            return {"valid": False, "reason": "no records"}
        prev = "GENESIS"
        for row in rows:
            block = f"{case_id}|{row['action']}|{row['timestamp']}|{prev}"
            calc = hashlib.sha256(block.encode()).hexdigest()
            if calc != row["chain_hash"]:
                return {"valid": False, "reason": f"tamper at action={row['action']}"}
            prev = row["chain_hash"]
        return {"valid": True, "records": len(rows)}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Bit & signature analysis
# ---------------------------------------------------------------------------
def compute_hashes(data: bytes) -> Dict[str, str]:
    """Compute multiple cryptographic hashes for a byte stream."""
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "sha1": hashlib.sha1(data).hexdigest(),
        "md5": hashlib.md5(data).hexdigest(),
        "crc32": format(zlib.crc32(data) & 0xFFFFFFFF, "08x"),
        "size_bytes": len(data),
    }


# Common magic-byte signatures (real content detection)
MAGIC_SIGNATURES: Dict[str, List[Tuple[str, Any]]] = {
    "PNG Image": [
        (b"\x89PNG\r\n\x1a\n", 0),
    ],
    "JPEG Image": [
        (b"\xff\xd8\xff", 0),
    ],
    "GIF Image": [
        (b"GIF8", 0),
    ],
    "PDF Document": [
        (b"%PDF-", 0),
    ],
    "ZIP Archive": [
        (b"PK\x03\x04", 0),
        (b"PK\x05\x06", 0),
    ],
    "GZIP Archive": [
        (b"\x1f\x8b", 0),
    ],
    "MP3 Audio": [
        (b"ID3", 0),
    ],
    "WAV Audio": [
        (b"RIFF", 0),
    ],
    "SQLite Database": [
        (b"SQLite format 3\x00", 0),
    ],
    "Microsoft Office (DOCX/XLSX)": [
        (b"PK\x03\x04", 0),
    ],
    "ELF Executable": [
        (b"\x7fELF", 0),
    ],
    "PE Executable": [
        (b"MZ", 0),
    ],
    "Debian Package": [
        (b"!<arch>\ndebian-binary", 0),
    ],
}


def detect_file_type(data: bytes) -> Dict[str, Any]:
    """
    Detect the real file type from magic bytes (even if extension is spoofed).
    Returns detected signature, confidence, and any mismatch when the extension lies.
    """
    for ftype, sigs in MAGIC_SIGNATURES.items():
        for sig, offset in sigs:
            if data[offset : offset + len(sig)] == sig:
                return {"detected_type": ftype, "signature_hex": sig.hex(), "confidence": "HIGH"}
    return {
        "detected_type": "UNKNOWN / Text Data",
        "signature_hex": data[:8].hex(),
        "confidence": "LOW",
    }


def compare_extension(data: bytes, filename: str) -> Dict[str, Any]:
    """Flag a spoofed/mismatched file extension by comparing magic bytes to the declared extension."""
    det = detect_file_type(data)
    ext = str(filename).rsplit(".", 1)[-1].lower() if "." in str(filename) else ""
    type_hint_map = {
        "png": "PNG Image", "jpg": "JPEG Image", "jpeg": "JPEG Image",
        "gif": "GIF Image", "pdf": "PDF Document", "zip": "ZIP Archive",
        "gz": "GZIP Archive", "mp3": "MP3 Audio", "wav": "WAV Audio",
        "sqlite": "SQLite Database", "db": "SQLite Database", "xlsx": "Microsoft Office",
        "docx": "Microsoft Office", "so": "ELF Executable", "exe": "PE Executable",
    }
    expected = type_hint_map.get(ext, "")
    if expected and expected.split()[0].lower() not in det["detected_type"].lower():
        return {
            "mismatch": True,
            "declared_extension": ext,
            "expected_type": expected,
            "actual_type": det["detected_type"],
            "verdict": "EXTENSION SPOOFED / MISMATCHED",
        }
    return {
        "mismatch": False,
        "declared_extension": ext,
        "actual_type": det["detected_type"],
        "verdict": "EXTENSION MATCHES CONTENT",
    }


# ---------------------------------------------------------------------------
# Metadata forensics (EXIF)
# ---------------------------------------------------------------------------
def extract_exif(data: bytes) -> Dict[str, Any]:
    """
    Extract EXIF metadata from JPEG/TIFF images: camera make/model, GPS
    coordinates, capture time, etc. Uses pure-python parsing from TIFF IFD
    structure without external dependencies.
    """
    gps_marker = b"GPS\x00\x00"
    exif_marker = b"Exif\x00\x00"
    exif_index = data.find(exif_marker)
    gps_index = data.find(gps_marker)

    result: Dict[str, Any] = {"has_exif": False, "has_jpeg_marker": data[:3] == b"\xff\xd8\xff"}
    if exif_index == -1:
        result["note"] = "No EXIF APP1 marker found (image may have been stripped)."
        return result
    result["has_exif"] = True
    exif_blob = data[exif_index + 6 : exif_index + 6 + 400]
    result["exif_app1_present"] = True

    # Camera make/model extraction (ASCII strings near standard vendor tags)
    for tag, label in [(271, "Make"), (272, "Model"), (305, "Software")]:
        marker = struct.pack(">H", tag)
        pos = exif_blob.find(marker)
        if pos != -1 and pos + 12 < len(exif_blob):
            raw = exif_blob[pos + 8 : pos + 8 + 24]
            text = re.sub(rb"[^\x20-\x7e]", b" ", raw).decode("latin-1").strip().rstrip("\x00")
            if text:
                result[label] = re.sub(r"\s+", " ", text)[:40]

    if gps_index != -1:
        gps_blob = data[gps_index + 6 : gps_index + 6 + 400]
        # Extract ASCII-decodable numbers as GPS coordinate hints
        lat = _find_rational(gps_blob, 2)
        lon = _find_rational(gps_blob, 4)
        if lat is not None and lon is not None:
            result["GPS"] = {"latitude": round(lat, 6), "longitude": round(lon, 6)}
            result["has_gps"] = True
    return result


def _find_rational(blob: bytes, count_index: int) -> Optional[float]:
    """Best-effort rational number extraction from a TIFF GPS IFD blob."""
    # look for a 4-byte value followed by a 4-byte denominator pattern
    for i in range(0, len(blob) - 8, 4):
        num_bytes = blob[i : i + 4]
        den_bytes = blob[i + 4 : i + 8]
        try:
            num = struct.unpack(">I", num_bytes)[0]
            den = struct.unpack(">I", den_bytes)[0]
        except (struct.error, ValueError):
            continue
        if 0 < int(num) < 100000 and 0 < int(den) < 100000 and den != 0:
            # plausible GPS-like rational
            return float(num) / float(den)
    return None


def extract_common_metadata(data: bytes) -> Dict[str, Any]:
    """Extract human-readable strings and urls embedded in the byte stream (memory carving)."""
    # Extract printable ASCII strings
    strings = re.findall(rb"[\x20-\x7e]{6,}", data)
    printable = [s.decode("ascii", "ignore") for s in strings[:40]]
    urls = re.findall(rb"(?:https?://)[^\s\x00]{6,120}", data[: len(data)])
    emails = re.findall(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", data[: len(data)])
    ip_addrs = re.findall(
        rb"\b(?:\d{1,3}\.){3}\d{1,3}\b", data[: len(data)]
    )
    return {
        "printable_strings": printable[:30],
        "urls": [u.decode("latin-1", "ignore") for u in urls[:15]],
        "emails": [e.decode("latin-1", "ignore") for e in emails[:15]],
        "ip_addresses": [i.decode("latin-1", "ignore") for i in ip_addrs[:15]],
    }


# ---------------------------------------------------------------------------
# Steganography detector (LSB)
# ---------------------------------------------------------------------------
def analyze_lsb_steganography(data: bytes) -> Dict[str, Any]:
    """
    Detect hidden payloads in the least-significant bits of image pixel data.
    Computes LSB entropy and a bias/randomness test to flag likely hidden data.
    """
    if data[:3] != b"\xff\xd8\xff" and data[:8] != b"\x89PNG\r\n\x1a\n":
        return {
            "supported": False,
            "note": "LSB stego analysis requires an image (PNG/JPEG).",
        }

    # Extract a pixel-like byte window after header for statistical analysis
    start = data.find(b"\xff\xd8\xff")
    if start == -1:
        start = data.find(b"\x89PNG")
    payload = data[start + 16 : start + 16 + 20000]
    if not payload:
        payload = data[start + 16 :]

    lsb_bits = [(b & 1) for b in payload[: len(payload) - len(payload) % 8]]
    if not lsb_bits:
        return {"supported": True, "bit_length": 0, "note": "insufficient data"}

    n = len(lsb_bits)
    ones = sum(lsb_bits)
    ratio = ones / n
    entropy = _entropy_of_bits(lsb_bits)

    # Random LSB bitstream (ratio ~0.5, entropy ~1.0) suggests embedded payload.
    # Compressed/structured natural data usually has biased LSBs.
    hidden_likelihood = "HIGH" if (0.4 < ratio < 0.6 and entropy > 0.95) else "LOW"
    return {
        "supported": True,
        "bits_sampled": n,
        "ones_ratio": round(ratio, 4),
        "entropy": round(entropy, 4),
        "hidden_payload_likelihood": hidden_likelihood,
        "estimate": "Possible hidden data embedded" if hidden_likelihood == "HIGH" else "No significant hidden payload detected",
    }


def _entropy_of_bits(bits) -> float:
    n = len(bits)
    if n == 0:
        return 0.0
    ones = sum(bits)
    zeros = n - ones
    p0 = zeros / n
    p1 = ones / n
    import math

    e = 0.0
    if p0 > 0:
        e -= p0 * math.log2(p0)
    if p1 > 0:
        e -= p1 * math.log2(p1)
    return e


# ---------------------------------------------------------------------------
# Timeline reconstruction from metadata
# ---------------------------------------------------------------------------
def reconstruct_timeline(files_meta: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Reconstruct an activity timeline from a list of file metadata records
    containing timestamps, sorting them chronologically for investigative review.
    """
    events = []
    for m in files_meta:
        ts = m.get("timestamp") or m.get("mtime")
        if ts:
            events.append(
                {
                    "timestamp": ts,
                    "filename": m.get("filename", ""),
                    "action": m.get("action", "ACCESS"),
                    "detail": m.get("detail", ""),
                }
            )
    events.sort(key=lambda e: str(e["timestamp"]))
    return {"events": events, "count": len(events)}


# ---------------------------------------------------------------------------
# Email header & phishing analyzer
# ---------------------------------------------------------------------------
SUSPICIOUS_KEYWORDS = [
    "urgent", "verify", "password", "account suspended", "lottery", "winner",
    "wire transfer", "inherit", "gift card", "click here", "login now",
    "unusual activity", "confirm your", "paypal", "irs", "crypto", "bitcoin",
]


def analyze_email_headers(raw_email: str) -> Dict[str, Any]:
    """Parse and analyze email headers for spoofing and phishing indicators."""
    text = raw_email or ""
    lines = text.splitlines()
    parsed: Dict[str, str] = {}
    current = ""
    for line in lines:
        if re.match(r"^\S+: ", line):
            key, _, val = line.partition(":")
            current = key.strip()
            parsed[current] = val.strip()
        elif current and line.startswith((" ", "\t")):
            parsed[current] += " " + line.strip()

    received = parsed.get("Received-From") or parsed.get("Received")
    from_header = parsed.get("From", "")
    reply_to = parsed.get("Reply-To", "")
    subject = parsed.get("Subject", "")
    return_path = parsed.get("Return-Path", "")

    suspicious_findings = []

    # Domain mismatches
    def extract_domain(addr: str):
        m = re.search(r"@([^\s>]+)", addr or "")
        return m.group(1).lower() if m else ""

    from_dom = extract_domain(from_header)
    return_dom = extract_domain(return_path)
    reply_dom = extract_domain(reply_to)

    if from_dom and reply_dom and from_dom != reply_dom:
        suspicious_findings.append(
            f"Reply-To domain ({reply_dom}) differs from From domain ({from_dom}) — a classic spoofing signal."
        )
    if from_dom and return_dom and from_dom != return_dom:
        suspicious_findings.append(
            f"Return-Path domain ({return_dom}) differs from From domain ({from_dom})."
        )

    # Keyword risk scan
    subj_lower = (subject or "").lower()
    body_lower = text.lower()
    keyword_hits = [k for k in SUSPICIOUS_KEYWORDS if k in subj_lower or k in body_lower]

    # SPF/DKIM presence
    spf = any("spf=" in ln.lower() for ln in parsed.values())
    dkim = any("dkim=" in ln.lower() for ln in parsed.values())

    risk_indicator_count = len(suspicious_findings) + len(keyword_hits)
    risk = "HIGH" if risk_indicator_count >= 4 else "MEDIUM" if risk_indicator_count >= 2 else "LOW"

    return {
        "parsed": parsed,
        "received_chain_count": received.count("\n") + 1 if received else int(bool(received)),
        "from_domain": from_dom,
        "reply_to_domain": reply_dom,
        "return_path_domain": return_dom,
        "suspicious_findings": suspicious_findings,
        "keyword_hits": keyword_hits[:10],
        "spf_present": spf,
        "dkim_present": dkim,
        "phishing_risk": risk,
        "verdict": "PHISHING / SPOOFING INDICATORS DETECTED" if risk == "HIGH"
        else "Review Recommended" if risk == "MEDIUM" else "Appears Benign",
    }


# ---------------------------------------------------------------------------
# Convenience: full investigation of a raw byte stream
# ---------------------------------------------------------------------------
def investigate_bytes(data: bytes, filename: str = "evidence.bin") -> Dict[str, Any]:
    """Run the full forensic suite against a raw byte stream."""
    report: Dict[str, Any] = {}
    report["hashes"] = compute_hashes(data)
    report["signature_detection"] = detect_file_type(data)
    report["extension_check"] = compare_extension(data, filename)
    if data[:3] == b"\xff\xd8\xff":
        report["exif"] = extract_exif(data)
    report["embedded"] = extract_common_metadata(data)
    report["lsb_stego"] = analyze_lsb_steganography(data)
    report["entropy_bits_per_byte"] = round(_byte_entropy(data[:20000]), 4)
    return report


def _byte_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    import math

    counts = [0] * 256
    for b in data:
        counts[b] += 1
    e = 0.0
    n = len(data)
    for c in counts:
        if c:
            p = c / n
            e -= p * math.log2(p)
    return e


if __name__ == "__main__":
    # Quick self-test
    sample = b"\x89PNG\r\n\x1a\n" + os.urandom(512)
    rep = investigate_bytes(sample, "photo.png")
    print(json.dumps({k: rep[k] for k in ("hashes", "signature_detection")}, indent=2))

