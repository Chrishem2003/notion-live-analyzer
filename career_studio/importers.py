def parse_imported_resume(raw_text: str) -> dict:
    return {
        "raw_length": len(raw_text),
        "status": "parsed_successfully",
        "extracted_snippet": raw_text[:150] + "..." if len(raw_text) > 150 else raw_text
    }
