# Implementation Plan: Top 3 Critical Gaps

## Priority 1: Meta-Analysis Engine (`modules/meta_analysis.py`)
**Files to create:**
- `modules/meta_analysis.py` — Core engine (fixed/random effects, forest plots, funnel plots, publication bias, heterogeneity)
- `pages/20_📊_Meta_Analysis.py` — Streamlit page

**Key classes:**
- `MetaAnalysisEngine` — Statistical computations
- `MetaForestPlot` — Forest plot visualization
- `MetaFunnelPlot` — Publication bias visualization

**Dependencies:** scipy, statsmodels, numpy, plotly

## Priority 2: Literature-Hypothesis Bridge
**Files to modify:**
- `modules/hypothesis_generator.py` — Add `literature_gap_analysis()` method to compare data patterns against literature effect sizes
- `modules/literature_engine.py` — Add `get_effect_size_benchmarks()` to extract effect sizes from papers

**Key additions:**
- `HypothesisGenerator.literature_gap_analysis(df, papers)` — Finds patterns in data that contradict or extend published findings
- `PaperHarvester.extract_effect_sizes(papers)` — Extracts reported effect sizes from paper metadata

## Priority 3: Data Provenance Tracker (`modules/data_provenance.py`)
**Files to create:**
- `modules/data_provenance.py` — Wraps DataFrame operations with lineage logging

**Key classes:**
- `ProvenanceTracker` — Context manager that logs every DataFrame transformation
- `ProvenanceVisualizer` — Displays lineage as a directed graph

