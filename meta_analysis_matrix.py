
"""
Multi-Paper Meta-Analysis Matrix Synthesizer
Automatically constructs side-by-side comparative matrices across multiple studies.
Extracts key variables across papers into a structured, exportable matrix.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np


class MetaAnalysisMatrix:
    """
    Builds comparative matrices across multiple studies, extracting
    key variables (Sample Size, Organism/Model, Methodology, Primary Outcome,
    P-Value, Limitations) into a structured table.
    """

    # Extraction patterns for common research variables
    EXTRACTION_PATTERNS = {
        "sample_size": [
            r"[Nn]\s*=\s*(\d[\d,]*)",
            r"(?:total|overall)\s*[Nn]\s*=\s*(\d[\d,]*)",
            r"(?:enrolled|included|participants)\s*:?\s*(\d[\d,]*)",
            r"n\s*=\s*(\d[\d,]*)",
            r"(?:sample|cohort)\s*(?:size|of)?\s*(\d[\d,]*)",
        ],
        "p_value": [
            r"[pP]\s*[<>=]\s*(\d\.?\d*)",
            r"[pP]\s*=\s*(\d\.?\d*)",
            r"[pP]\s*[<]\s*0\.001",
            r"[pP]\s*[<]\s*0\.01",
            r"[pP]\s*[<]\s*0\.05",
        ],
        "effect_size": [
            r"(?:Cohen'?s?\s*[dD])\s*=\s*([-]?\d\.?\d*)",
            r"[dD]\s*=\s*([-]?\d\.?\d*)",
            r"[rR]\s*=\s*([-]?\d\.?\d*)",
            r"(?:odds\s*ratio|OR)\s*=\s*([-]?\d\.?\d*)",
            r"(?:Hedges'?[sg])\s*=\s*([-]?\d\.?\d*)",
        ],
        "model_organism": [
            r"(human|mouse|rat|zebrafish|drosophila|yeast|worm|c. elegans|primate|monkey|pig|rabbit|dog|cat)",
            r"(patients|participants|subjects|volunteers|cell line|tissue)",
            r"(in vivo|in vitro|ex vivo|in silico)",
        ],
        "methodology": [
            r"(RCT|randomized controlled trial|randomized|randomised|meta-analysis|systematic review|cohort|case-control|cross-sectional|longitudinal|observational|experimental|quasi-experimental)",
            r"(double-blind|single-blind|placebo-controlled|open-label|pilot|feasibility)",
            r"(PCR|qPCR|RNA-seq|microarray|ELISA|Western blot|immunohistochemistry|flow cytometry|mass spectrometry|MRI|fMRI|EEG)",
        ],
        "limitations": [
            r"(limitation|limitations|limitation[s]?:)",
            r"(small sample|underpowered|bias|confounding|selection bias|recall bias|attrition)",
            r"(not generalizable|generalizability|external validity|internal validity)",
        ],
    }

    # Standard column headers for the matrix
    MATRIX_COLUMNS = [
        "Paper", "Year", "Sample Size (N)", "Model/Organism",
        "Methodology", "Primary Outcome", "Effect Size",
        "P-Value", "Significant", "Limitations", "Quality Score"
    ]

    def __init__(self):
        self.matrix: pd.DataFrame = pd.DataFrame()
        self.extracted_data: List[Dict] = []

    def extract_from_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key variables from a single paper's metadata and abstract."""
        row = {
            "Paper": paper.get("title", "Unknown"),
            "Year": paper.get("year", ""),
            "Authors": paper.get("authors", "")[:100],
            "Journal": paper.get("journal", ""),
            "DOI": paper.get("doi", ""),
            "Citations": paper.get("citations", 0),
        }

        combined_text = f"{paper.get('title', '')}} {paper.get('abstract', '')}} {paper.get('user_notes', '')}} {paper.get('user_findings', '')}}"

        # Sample Size
        sample_size = self._extract_first(combined_text, "sample_size")
        row["Sample Size (N)"] = sample_size

        # P-Value
        p_value = self._extract_first(combined_text, "p_value")
        row["P-Value"] = p_value
        row["Significant"] = self._is_significant(p_value)

        # Effect Size
        effect_size = self._extract_first(combined_text, "effect_size")
        row["Effect Size"] = effect_size

        # Model/Organism
        model = self._find_first_match(combined_text, "model_organism")
        row["Model/Organism"] = model

        # Methodology
        method = self._find_first_match(combined_text, "methodology")
        row["Methodology"] = method

        # Limitations
        limitations = self._extract_context(combined_text, "limitations")
        row["Limitations"] = limitations

        # Quality Score (heuristic)
        row["Quality Score"] = self._compute_quality_score(row)

        # Primary outcome (first finding from user notes or abstract sentence)
        row["Primary Outcome"] = self._extract_outcome(combined_text)

        return row

    def _extract_first(self, text: str, pattern_key: str) -> str:
        """Extract the first match for a pattern group."""
        patterns = self.EXTRACTION_PATTERNS.get(pattern_key, [])
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return ""

    def _find_first_match(self, text: str, pattern_key: str) -> str:
        """Find the first regex match from a group of patterns."""
        patterns = self.EXTRACTION_PATTERNS.get(pattern_key, [])
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip() if match.lastindex and len(match.groups()) > 0 else match.group(0).strip()
        return ""

    def _extract_context(self, text: str, pattern_key: str, context_words: int = 20) -> str:
        """Extract context around a matched pattern."""
        patterns = self.EXTRACTION_PATTERNS.get(pattern_key, [])
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 100)
                context = text[start:end].replace("\n", " ").strip()
                return context[:200]
        return ""

    def _extract_outcome(self, text: str) -> str:
        """Extract the primary outcome/finding from text."""
        patterns = [
            r"(?:found|showed|demonstrated|revealed|indicated|observed)\sthat\s(.*?)[.;]",
            r"(?:primary|main|key)\s(?:outcome|finding|result)\s(?:was|is)\s(.*?)[.;]",
            r"(?:conclude|concluded|conclusion)\s(?:that\s)?(.*?)[.;]",
            r"(?:result|results)\s(?:show|showed|demonstrate|demonstrated|indicate|indicated)\s(?:that\s)?(.*?)[.;]",
            r"(?:significant|significantly)\s(.*?)[.;]",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = match.group(1).strip()[:200]
                if len(result) > 10:
                    return result
        return ""

    def _is_significant(self, p_value: str) -> str:
        """Determine if a p-value string indicates statistical significance."""
        if not p_value:
            return ""
        p_lower = p_value.lower()
        if "p < 0.001" in p_lower or "p<0.001" in p_lower:
            return "âœ… Yes"
        if "p < 0.01" in p_lower or "p<0.01" in p_lower or "p < 0.05" in p_lower or "p<0.05" in p_lower:
            return "âœ… Yes"
        if "p >" in p_lower or "p =" in p_lower or "p=" in p_lower:
            # Extract the actual p-value
            nums = re.findall(r"(\d\.?\d*)", p_value)
            if nums and float(nums[0]) < 0.05:
                return "âœ… Yes"
            elif nums:
                return "Ã¢ÂÅ’ No"
        return ""

    def _compute_quality_score(self, row: Dict) -> int:
        """Compute a heuristic quality score (0-100) for a paper."""
        score = 50
        if row.get("Sample Size (N)"):
            nums = re.findall(r"\d[\d,]*", row["Sample Size (N)"])
            if nums:
                n = int(nums[0].replace(",", ""))
                if n >= 1000: score = 20
                elif n >= 100: score = 10
                elif n >= 30: score = 5
        if row.get("Effect Size"): score = 10
        if row.get("Methodology"):
            if "RCT" in row["Methodology"] or "meta-analysis" in row["Methodology"]:
                score = 15
            elif "systematic" in row["Methodology"]: score = 10
        if row.get("DOI"): score = 5
        if row.get("Limitations"): score -= 5  # Self-awareness of limitations
        return max(0, min(100, score))

    def build_matrix(self, papers: List[Dict[str, Any]]) -> pd.DataFrame:
        """Build a comparative matrix from a list of papers."""
        rows = []
        for paper in papers:
            row = self.extract_from_paper(paper)
            rows.append(row)

        self.extracted_data = rows
        self.matrix = pd.DataFrame(rows)
        return self.matrix

    def add_to_session(self, paper: Dict[str, Any]) -> Dict:
        """Extract and add a single paper to the existing matrix."""
        row = self.extract_from_paper(paper)
        self.extracted_data.append(row)
        self.matrix = pd.DataFrame(self.extracted_data)
        return row

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Get summary statistics from the matrix."""
        if self.matrix.empty:
            return {"error": "No data in matrix"}
        df = self.matrix

        # Average quality score
        quality_scores = pd.to_numeric(df["Quality Score"], errors="coerce")
        avg_quality = quality_scores.mean() if not quality_scores.isna().all() else 0

        # Significant papers count
        sig_count = sum(1 for v in df["Significant"] if "âœ…" in str(v))

        return {
            "total_papers": len(df),
            "avg_quality_score": round(avg_quality, 1),
            "significant_findings": sig_count,
            "non_significant": len(df) - sig_count,
            "year_range": f"{df['Year'].min()}}Ã¢â‚¬â€œ{df['Year'].max()}}" if df["Year"].notna().any() else "N/A",
            "most_cited": df.loc[df["Citations"].idxmax(), "Paper"][:60] if "Citations" in df.columns and not df["Citations"].isna().all() else "N/A",
        }

    def export_csv(self) -> str:
        """Export matrix as CSV string."""
        if self.matrix.empty:
            return ""
        return self.matrix.to_csv(index=False)

    def export_json(self) -> str:
        """Export matrix as JSON string."""
        if self.matrix.empty:
            return "[]"
        return self.matrix.to_json(orient="records", indent=2)

    def filter_matrix(self, **kwargs) -> pd.DataFrame:
        """Filter matrix by column values."""
        if self.matrix.empty:
            return self.matrix
        df = self.matrix.copy()
        for col, val in kwargs.items():
            if col in df.columns and val:
                df = df[df[col].astype(str).str.contains(str(val), case=False, na=False)]
        return df

    def sort_matrix(self, by: str = "Year", ascending: bool = False) -> pd.DataFrame:
        """Sort the matrix by a column."""
        if self.matrix.empty or by not in self.matrix.columns:
            return self.matrix
        try:
            return self.matrix.sort_values(by=by, ascending=ascending)
        except Exception:
            return self.matrix


def render_meta_analysis_matrix_ui():
    """Render the Meta-Analysis Matrix UI."""
    import streamlit as st
    from modules.ui_components import section_header

    st.markdown("## Ã°Å¸â€œâ€˜ Multi-Paper Meta-Analysis Matrix Synthesizer")
    st.markdown("*Side-by-side comparative matrix across multiple studies*")

    if "meta_matrix" not in st.session_state:
        st.session_state["meta_matrix"] = MetaAnalysisMatrix()
    matrix_engine = st.session_state["meta_matrix"]

    tab1, tab2, tab3 = st.tabs(["ðŸ“¥ Build Matrix", " Matrix View", "ðŸ“ˆ Summary"])

    with tab1:
        st.subheader("ðŸ“¥ Build Comparative Matrix")
        st.caption("Load papers from the current literature project or paste paper data")

        papers = []
        lit_papers = st.session_state.get("lit_db_papers", [])
        if lit_papers:
            st.info(f"Ã°Å¸â€œÅ¡ Found {len(lit_papers)}} papers in current literature project")
            if st.button("Ã°Å¸â€Â¨ Build Matrix from Literature Papers", type="primary", use_container_width=True):
                with st.spinner(f"Extracting data from {len(lit_papers)}} papers..."):
                    df = matrix_engine.build_matrix(lit_papers)
                    st.session_state["meta_matrix_df"] = df
                    st.success(f"âœ… Built matrix with {len(df)}} papers")
                    st.rerun()
        else:
            st.info("No literature papers loaded. Use Literature Engine to harvest papers, or enter manually below.")

        with st.expander("Ã¢Å“ÂÃ¯Â¸Â Or enter paper details manually"):
            cols = st.columns(3)
            with cols[0]:
                title = st.text_input("Paper title", key="mm_title")
                year = st.number_input("Year", min_value=1900, max_value=2030, value=2023, step=1, key="mm_year")
                authors = st.text_input("Authors", key="mm_authors")
            with cols[1]:
                sample_size = st.text_input("Sample size", placeholder="N=150", key="mm_n")
                method = st.text_input("Methodology", placeholder="RCT, cohort...", key="mm_method")
                outcome = st.text_area("Primary outcome", height=60, key="mm_outcome")
            with cols[2]:
                effect = st.text_input("Effect size", placeholder="d=0.5", key="mm_effect")
                pval = st.text_input("P-value", placeholder="p<0.05", key="mm_pval")
                limitations = st.text_area("Limitations", height=60, key="mm_limitations")

            if st.button("Ã¢Å¾â€¢ Add Paper to Matrix", use_container_width=True) and title:
                paper_data = {
                    "title": title, "year": year, "authors": authors, "abstract": "",
                    "journal": "", "doi": "", "citations": 0,
                    "user_notes": f"Methodology: {method}}. Outcome: {outcome}}. Limitations: {limitations}}",
                    "user_findings": f"Effect: {effect}}. P-value: {pval}}",
                }
                matrix_engine.add_to_session(paper_data)
                st.session_state["meta_matrix_df"] = matrix_engine.matrix
                st.success(f"âœ… Added '{title}}'")
                st.rerun()

    with tab2:
        df = st.session_state.get("meta_matrix_df")
        if df is not None and not df.empty:
            st.subheader(f" Comparative Matrix ({len(df)}} papers)")

            col1, col2, col3 = st.columns(3)
            with col1:
                search_term = st.text_input("Ã°Å¸â€Â Search papers", placeholder="Type to filter...")
            with col2:
                sort_col = st.selectbox("Sort by", options=df.columns.tolist(), key="mm_sort")
            with col3:
                sort_asc = st.checkbox("Ascending", value=False)

            display_df = matrix_engine.filter_matrix(Paper=search_term) if search_term else df.copy()
            try:
                if sort_col in display_df.columns:
                    display_df = display_df.sort_values(by=sort_col, ascending=sort_asc)
            except Exception:
                pass

            st.dataframe(display_df, use_container_width=True, hide_index=True)

            st.subheader("ðŸ“¥ Export")
            col1, col2 = st.columns(2)
            with col1:
                csv_data = matrix_engine.export_csv()
                if csv_data:
                    import base64
                    b64 = base64.b64encode(csv_data.encode()).decode()
                    st.markdown(f'<a href="data:text/csv;base64,{b64}}" download="meta_analysis_matrix.csv">ðŸ“¥ Download CSV</a>', unsafe_allow_html=True)
            with col2:
                json_data = matrix_engine.export_json()
                if json_data:
                    import base64
                    b64 = base64.b64encode(json_data.encode()).decode()
                    st.markdown(f'<a href="data:application/json;base64,{b64}}" download="meta_analysis_matrix.json">ðŸ“¥ Download JSON</a>', unsafe_allow_html=True)
        else:
            st.info("Build the matrix first in the **Build Matrix** tab.")

    with tab3:
        df = st.session_state.get("meta_matrix_df")
        if df is not None and not df.empty:
            stats = matrix_engine.get_summary_statistics()
            if "error" not in stats:
                st.subheader("ðŸ“ˆ Matrix Summary")
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("Total Papers", stats.get("total_papers", 0))
                with col2: st.metric("Avg Quality Score", f'{stats.get("avg_quality_score", 0)}}/100')
                with col3: st.metric("âœ… Significant", stats.get("significant_findings", 0))
                with col4: st.metric("Year Range", stats.get("year_range", "N/A"))

                if "Citations" in df.columns and not df["Citations"].isna().all():
                    try:
                        top_cited = df.nlargest(5, "Citations")[["Paper", "Citations", "Year"]]
                        st.subheader("Ã°Å¸Ââ€  Most Cited Papers")
                        st.dataframe(top_cited, use_container_width=True, hide_index=True)
                    except Exception:
                        pass

                st.subheader("Quality Score Distribution")
                try:
                    scores = pd.to_numeric(df["Quality Score"], errors="coerce").dropna()
                    if not scores.empty:
                        st.bar_chart(scores.value_counts().sort_index())
                except Exception:
                    pass
        else:
            st.info("Build the matrix first.")


