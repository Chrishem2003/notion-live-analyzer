# 🚀 World-Class Research Data Analyzer & Visualizer

> **Vision**: Replace SPSS, STATA, Tableau, and Power BI with a single, intelligent, Notion-connected research platform that anyone can use.

---

## 📊 Market Gap Analysis — Why This App Wins

| Feature | SPSS | Tableau | Power BI | This App |
|---------|------|---------|----------|----------|
| Notion Native | ❌ | ❌ | ❌ | ✅ **Native** |
| AI Auto-Analysis | ❌ | ❌ | ❌ | ✅ **Built-in** |
| File Upload (CSV/Excel/SAV) | ✅ | ✅ | ✅ | ✅ |
| Statistical Tests | ✅ Full | ❌ | ❌ | ✅ **Full Suite** |
| Charts | Basic | ✅ Advanced | ✅ Advanced | ✅ **18+ Interactive** |
| Auto-Chart Recommendation | ❌ | ❌ | ❌ | ✅ **AI Rules Engine** |
| Dark Mode | ❌ | ✅ | ✅ | ✅ |
| Free & Open | ❌ | ❌ | ❌ | ✅ |
| Cross-Filtering | ❌ | ✅ | ✅ | ✅ |
| Multi-User Duplication | ❌ | ❌ | ❌ | ✅ **Auto-Detect** |
| Automated Report | ❌ | ❌ | ❌ | ✅ **PDF/HTML** |
| Predictive Modeling | ❌ | ❌ | ❌ | ✅ **scikit-learn** |

---

## 📁 Project Structure

```
notion-live-analyzer/
├── app.py                              # Entry point (thin orchestrator)
├── modules/
│   ├── __init__.py
│   ├── config.py                       # Secrets, session state, constants
│   ├── notion_client.py                # All Notion API interactions
│   ├── data_processor.py               # Data type inference, cleaning, aggregation
│   ├── statistical_engine.py           # SPSS-level statistics (NEW)
│   ├── ai_analyzer.py                  # AI auto-analysis & insights (NEW)
│   ├── file_uploader.py                # CSV/Excel/SAV/JSON parser (NEW)
│   ├── viz_engine.py                   # Auto-chart recommendation engine
│   ├── chart_builder.py                # Build all 18+ chart types with Plotly
│   ├── report_generator.py             # Automated report builder (NEW)
│   ├── ui_components.py                # Reusable UI components
│   ├── keepalive.py                    # Multi-layer keep-alive system
│   └── export.py                       # Export charts/data
├── pages/
│   ├── 1_📊_Live_Dashboard.py
│   ├── 2_📁_File_Analyzer.py           # NEW — Upload & analyze files
│   ├── 3_🔬_Statistical_Tests.py       # NEW — SPSS replacement
│   ├── 4_📈_Advanced_Visuals.py
│   ├── 5_🤖_AI_Insights.py            # NEW — AI-powered analysis
│   └── 6_⚙️_Settings.py
├── assets/
│   ├── styles.css
│   └── background.jpg
├── requirements.txt
├── Dockerfile
├── render.yaml
├── Procfile
└── README.md
```

---

## 🎯 Full Feature Matrix

### 🔌 Data Sources
- ✅ **Notion API** — Live database sync (all 20+ property types)
- ✅ **File Upload** — CSV, Excel (.xlsx/.xls), JSON, SPSS (.sav), SAS, STATA (.dta)
- ✅ **Manual Entry** — Quick data table creator
- ✅ **Google Sheets** — (Future) Live sync

### 🧪 Statistical Analysis (SPSS Replacement)
| Test | Description |
|------|-------------|
| Descriptive Statistics | Mean, median, mode, std, variance, skewness, kurtosis, quartiles, IQR, range |
| Frequency Analysis | Frequency tables, cross-tabulations, contingency tables |
| T-Tests | Independent, paired, one-sample (with Cohen's d effect size) |
| ANOVA | One-way, two-way, repeated measures, post-hoc (Tukey, Bonferroni) |
| Chi-Square | Independence, goodness-of-fit, Cramer's V |
| Correlation | Pearson, Spearman, Kendall-Tau, partial correlation |
| Regression | Linear, multiple, logistic, polynomial, stepwise |
| Non-Parametric | Mann-Whitney U, Wilcoxon, Kruskal-Wallis, Friedman |
| Factor Analysis | PCA, EFA, Kaiser-Meyer-Olkin (KMO), Bartlett's test |
| Reliability | Cronbach's alpha, split-half, test-retest |
| Power Analysis | Sample size estimation, effect size, post-hoc power |
| Time Series | ACF, PACF, decomposition, stationarity tests, ARIMA |

### 📈 18+ Interactive Chart Types
Bar (grouped/stacked/horizontal), Line (with confidence bands), Pie/Donut, Histogram (KDE overlay), Scatter (with trendline), Bubble, Area (stacked), Box Plot, Violin Plot, Heatmap, Treemap, Sunburst, Radar/Spider, Parallel Coordinates, 3D Scatter, Waterfall, Funnel, Gauge/Speedometer, Correlation Matrix

### 🤖 AI Auto-Analysis Engine
- **Data Profiling** — Automatic column type detection, missing values, outliers
- **Smart Test Recommendation** — "Your data has 2 groups + numeric → try independent t-test"
- **Natural Language Insights** — "Sales increased 23% QoQ, driven by Region A"
- **Auto-Visualization Selection** — Best chart picked for your data
- **Outlier Detection** — IQR, Z-score, DBSCAN
- **Trend Analysis** — Automatic trend lines, seasonality detection
- **Narrative Report Generator** — Full PDF report with charts + stats

---

## 🎯 Implementation Phases

### PHASE 1: Architecture & 24/7 Keep-Alive (START NOW)
**Goal**: Restructure into modules, implement enterprise-grade keep-alive

1. **Modular split** → `config.py`, `notion_client.py`, `data_processor.py`, `keepalive.py`, `ui_components.py`, `export.py`, `viz_engine.py`, `chart_builder.py`
2. **5-Layer Keep-Alive**:
   - L1: Client-side JS heartbeat
   - L2: Server-side background thread self-ping
   - L3: Streamlit `[server]` heartbeat config
   - L4: Render cron job (existing)
   - L5: Auto-restart watchdog process
3. **Health endpoint** at `/health`
4. **Session persistence** with file-based cache

### PHASE 2: Full Notion Data Engine
1. **Universal property extractor** — ALL 20+ types parsed
2. **Auto-type inference** → map to pandas/numpy
3. **Smart database fingerprinting** — SHA-256 schema hash
4. **Auto-connect on duplicate** — detect matching DB by schema fingerprint

### PHASE 3: File Upload & Data Processing
1. **File uploader** — CSV, Excel, JSON, SPSS .sav, SAS, STATA
2. **Data validation & cleaning** — missing values, duplicates, type coercion
3. **User data merging** — merge uploaded data with Notion data
4. **Manual data editor** — quick table input

### PHASE 4: SPSS-Level Statistical Engine
1. **Descriptive statistics** module
2. **T-Tests & ANOVA** module
3. **Correlation & Regression** module
4. **Non-parametric & Categorical** module
5. **Factor Analysis & Reliability** module
6. **Power Analysis** module
7. **Beautiful results formatting** — publication-ready tables

### PHASE 5: Advanced Visualization Engine
1. **Auto-chart recommendation** (rules-based AI)
2. **18+ chart types** built with Plotly
3. **Cross-filtering** — interactive linked views
4. **Chart customization** — colors, labels, annotations
5. **Dashboard builder** — drag-and-drop grid

### PHASE 6: AI Insights & Automation
1. **AI data profiling** — smart summaries
2. **Test recommendation** — "based on your data, try..."
3. **Natural language insights** — generated findings
4. **Outlier & trend detection**
5. **Narrative report generator** — PDF with all findings

### PHASE 7: Professional UI/UX
1. **Dark mode + Light mode**
2. **Custom themes & accent colors**
3. **Responsive design**
4. **Keyboard shortcuts**
5. **Onboarding tour**

### PHASE 8: Deployment & Monitoring
1. **Structured logging**
2. **Performance dashboards**
3. **Auto-recovery**
4. **Usage analytics (opt-in)**

---

## 🛠️ Technical Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit + Custom CSS |
| Charts | Plotly (interactive, WebGL) |
| Statistics | SciPy, StatsModels, Pingouin |
| AI/ML | scikit-learn, NumPy, Pandas |
| Data Parsing | Pandas, pyreadstat (.sav), openpyxl (.xlsx) |
| Export | Kaleido (PNG/SVG), ReportLab (PDF), Fpdf2 |
| State | Streamlit Session + Pickle cache |
| Deployment | Docker, Render, Streamlit Cloud |

---

## 📐 Key Technical Details

### Universal Notion Property Extractor
```python
NOTION_PROPERTY_PARSERS = {
    'title': lambda p: extract_rich_text(p.get('title', [])),
    'rich_text': lambda p: extract_rich_text(p.get('rich_text', [])),
    'number': lambda p: p.get('number'),
    'select': lambda p: p.get('select', {}).get('name') if p.get('select') else None,
    'multi_select': lambda p: [s['name'] for s in p.get('multi_select', [])],
    'status': lambda p: p.get('status', {}).get('name') if p.get('status') else None,
    'date': lambda p: p.get('date', {}).get('start') if p.get('date') else None,
    'checkbox': lambda p: p.get('checkbox', False),
    'email': lambda p: p.get('email'),
    'phone': lambda p: p.get('phone'),
    'url': lambda p: p.get('url'),
    'formula': lambda p: parse_formula(p.get('formula', {})),
    'relation': lambda p: [r['id'] for r in p.get('relation', [])],
    'rollup': lambda p: parse_rollup(p.get('rollup', {})),
    'people': lambda p: [person['name'] for person in p.get('people', []) if person.get('name')],
    'files': lambda p: [f['name'] for f in p.get('files', [])],
    'created_by': lambda p: p.get('created_by', {}).get('name'),
    'created_time': lambda p: p.get('created_time'),
    'last_edited_by': lambda p: p.get('last_edited_by', {}).get('name'),
    'last_edited_time': lambda p: p.get('last_edited_time'),
    'unique_id': lambda p: f"{p.get('unique_id', {}).get('prefix', '')}-{p.get('unique_id', {}).get('number', '')}",
}
```

### AI Auto-Analysis Pipeline
```python
def auto_analyze(df):
    """Fully automated data analysis pipeline."""
    results = {
        'profile': profile_dataset(df),
        'missing': analyze_missing_values(df),
        'outliers': detect_outliers(df),
        'distributions': test_normality(df),
        'correlations': compute_correlations(df),
        'recommendations': recommend_tests(df),
        'insights': generate_insights(df),
        'visualizations': recommend_charts(df),
    }
    return results
```

### Statistical Engine (SPSS Replacement)
```python
class StatisticalEngine:
    def descriptive_stats(self, df, columns): ...
    def independent_ttest(self, df, group_col, value_col): ...
    def paired_ttest(self, df, before_col, after_col): ...
    def anova_one_way(self, df, group_col, value_col): ...
    def anova_two_way(self, df, factor1, factor2, value_col): ...
    def chi_square(self, df, col1, col2): ...
    def pearson_correlation(self, df, col1, col2): ...
    def spearman_correlation(self, df, col1, col2): ...
    def linear_regression(self, df, target, features): ...
    def logistic_regression(self, df, target, features): ...
    def pca(self, df, columns): ...
    def cronbach_alpha(self, df, items): ...
    def power_analysis(self, test_type, effect_size, alpha, power): ...
```

---

## 🚦 Build Order (Step-by-Step)

```
STEP 1  → Phase 1: Modular architecture + Keep-Alive
STEP 2  → Phase 2: Notion data engine (all types)
STEP 3  → Phase 3: File upload & data processing
STEP 4  → Phase 4: Statistical engine (SPSS replacement)
STEP 5  → Phase 5: Visualization engine (18+ charts)
STEP 6  → Phase 6: AI insights & automation
STEP 7  → Phase 7: UI/UX overhaul (dark mode, etc.)
STEP 8  → Phase 8: Deployment & monitoring
```

**Status**: ✅ Ready to start STEP 1 now.

