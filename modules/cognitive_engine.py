# --- CHRISHEM AUTHOR PROFILE BLOCK ---
import os
import streamlit as st

st.markdown("# **Notion Live Analyzer**")
st.markdown("### **Creator: CHRISHEM**")
st.markdown("---")
# -------------------------------------

"""
Cognitive NLP Processing & Knowledge Extraction Engine
"""
import re

def extract_insights_from_text(text: str) -> dict:
    """Performs heuristic entity extraction and intelligent text summarization."""
    if not text:
        return {"summary": "No text content provided for cognitive parsing.", "keywords": [], "word_count": 0}
    
    words = text.split()
    word_count = len(words)
    potential_entities = list(set(re.findall(r"\b[A-Z][a-z]", text)))
    
    return {
        "summary": " ".join(words[:30])  ("..." if word_count > 30 else ""),
        "keywords": potential_entities[:12],
        "word_count": word_count
    }

