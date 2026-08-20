
"""
Dependency Manager  auto-detect, auto-install, and verify all required Python packages.
Provides a one-click Streamlit UI for non-technical users to fix dependency issues.
"""
import sys
import subprocess
import importlib
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from modules.logging_utils import get_logger

logger = get_logger(__name__)

# â”€â”€â”€ Package Registry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Each package: pip_name -> (import_name, category, description, min_version)

@dataclass
class PackageInfo:
    pip_name: str
    import_name: str
    category: str
    description: str
    min_version: Optional[str] = None
    is_installed: bool = False
    installed_version: Optional[str] = None


ALL_PACKAGES: List[PackageInfo] = [
    # â”€â”€â”€ Core â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PackageInfo("streamlit", "streamlit", "Core", "Web app framework"),
    PackageInfo("pandas", "pandas", "Core", "Data manipulation"),
    PackageInfo("numpy", "numpy", "Core", "Numerical computing"),
    PackageInfo("plotly", "plotly", "Core", "Interactive visualizations"),
    PackageInfo("requests", "requests", "Core", "HTTP requests"),

    # â”€â”€â”€ File Parsing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PackageInfo("openpyxl", "openpyxl", "File Parsing", "Excel .xlsx reading/writing"),
    PackageInfo("pyreadstat", "pyreadstat", "File Parsing", "SPSS/SAS/STATA reading"),
    PackageInfo("sas7bdat", "sas7bdat", "File Parsing", "SAS file fallback reader"),
    PackageInfo("xlrd", "xlrd", "File Parsing", "Older Excel format support"),

    # â”€â”€â”€ Statistics â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PackageInfo("scipy", "scipy", "Statistics", "Scientific computing & stats", "1.11.0"),
    PackageInfo("statsmodels", "statsmodels", "Statistics", "Statistical models & tests", "0.14.0"),
    PackageInfo("pingouin", "pingouin", "Statistics", "Statistical analysis toolkit", "0.5.0"),

    # â”€â”€â”€ Factor Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PackageInfo("factor-analyzer", "factor_analyzer", "Statistics", "Factor analysis (KMO, Bartlett)", "0.4.0"),

    # â”€â”€â”€ Data Export â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PackageInfo("kaleido", "kaleido", "Export", "Plotly static image export", "0.2.1"),
    PackageInfo("fpdf2", "fpdf2", "Export", "PDF report generation", "2.7.0"),

    # â”€â”€â”€ AI/ML â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PackageInfo("scikit-learn", "sklearn", "AI/ML", "Machine learning library", "1.3.0"),
    PackageInfo("imbalanced-learn", "imblearn", "AI/ML", "Imbalanced dataset handling", "0.11.0"),
    PackageInfo("xgboost", "xgboost", "AI/ML", "Gradient boosting framework", "2.0.0"),
    PackageInfo("joblib", "joblib", "AI/ML", "Model persistence", "1.3.0"),
    PackageInfo("shap", "shap", "AI/ML", "SHAP model explanations", "0.42.0"),

    # â”€â”€â”€ Text Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PackageInfo("textblob", "textblob", "Text Analysis", "Text processing & sentiment"),
    PackageInfo("wordcloud", "wordcloud", "Text Analysis", "Word cloud generation", "1.9.0"),
    PackageInfo("nltk", "nltk", "Text Analysis", "Natural language toolkit", "3.8.0"),

    # â”€â”€â”€ Encoding â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PackageInfo("chardet", "chardet", "Utilities", "Character encoding detection", "5.0.0"),

    # â”€â”€â”€ Google Sheets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PackageInfo("gspread", "gspread", "Google Sheets", "Google Sheets API client", "5.0.0"),
    PackageInfo("oauth2client", "oauth2client", "Google Sheets", "OAuth 2.0 authentication", "4.1.3"),
    PackageInfo("google-auth", "google.auth", "Google Sheets", "Google authentication", "2.0.0"),

    # â”€â”€â”€ Bayesian â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PackageInfo("pymc", "pymc", "Advanced", "Probabilistic programming", "5.10.0"),
    PackageInfo("arviz", "arviz", "Advanced", "Bayesian visualization", "0.16.0"),

    # â”€â”€â”€ Causal Inference â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PackageInfo("causalml", "causalml", "Advanced", "Causal inference methods", "0.14.0"),

    # â”€â”€â”€ Network Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PackageInfo("networkx", "networkx", "Advanced", "Network analysis", "3.0.0"),
    PackageInfo("python-louvain", "community", "Advanced", "Community detection", "0.16"),

    # â”€â”€â”€ Utilities â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PackageInfo("python-dateutil", "dateutil", "Utilities", "Date/time parsing", "2.8.0"),
    PackageInfo("tabulate", "tabulate", "Utilities", "Markdown table export", "0.9.0"),
    PackageInfo("prophet", "prophet", "Advanced", "Time series forecasting", "1.1.0"),
]

# â”€â”€â”€ Category groupings for UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

CATEGORY_ORDER = ["Core", "File Parsing", "Statistics", "Export", "AI/ML",
                  "Text Analysis", "Google Sheets", "Advanced", "Utilities"]

CATEGORY_ICONS = {
    "Core": "📦",
    "File Parsing": "ðŸ“",
    "Statistics": "",
    "Export": "📥",
    "AI/ML": "ðŸ§ ",
    "Text Analysis": "ðŸ’¬",
    "Google Sheets": "ðŸ”—",
    "Advanced": "ðŸ”¬",
    "Utilities": "ðŸ”§",
}


# â”€â”€â”€ Dependency Checking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def check_single_package(pkg: PackageInfo) -> bool:
    """Check if a single package is installed."""
    try:
        mod = importlib.import_module(pkg.import_name)
        # Try to get version
        if hasattr(mod, "__version__"):
            pkg.installed_version = mod.__version__
        pkg.is_installed = True
        return True
    except ImportError:
        pkg.is_installed = False
        pkg.installed_version = None
        return False
    except Exception:
        # The module exists but fails to import cleanly (broken install, bad
        # native extension, ...). Treat it as present, but make it visible.
        logger.warning("Package %r is installed but failed to import", pkg.pip_name, exc_info=True)
        pkg.is_installed = True
        return True


def check_all_packages() -> Tuple[List[PackageInfo], List[str], List[str]]:
    """Check all packages and return categorized results."""
    for pkg in ALL_PACKAGES:
        check_single_package(pkg)

    installed_pkgs = [p for p in ALL_PACKAGES if p.is_installed]
    missing_pkgs = [p for p in ALL_PACKAGES if not p.is_installed]
    categories = sorted(set(p.category for p in ALL_PACKAGES),
                        key=lambda c: CATEGORY_ORDER.index(c) if c in CATEGORY_ORDER else 99)

    return ALL_PACKAGES, missing_pkgs, categories


def install_package(pip_name: str, timeout: int = 120) -> Tuple[bool, str]:
    """Install a single package using pip. Returns (success, message)."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pip_name],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            return True, f"✅ {pip_name} installed successfully"
        else:
            error_msg = result.stderr[:300] if result.stderr else "Unknown error"
            return False, f"âŒ Failed to install {pip_name}: {error_msg}"
    except subprocess.TimeoutExpired:
        return False, f"âŒ Installation of {pip_name} timed out after {timeout}s"
    except Exception as e:
        return False, f"âŒ Installation error for {pip_name}: {str(e)}"


def install_missing_packages(
    package_names: List[str],
    progress_callback=None,
    timeout: int = 120,
) -> Dict[str, Tuple[bool, str]]:
    """Install multiple missing packages. Returns dict of results."""
    results = {}
    total = len(package_names)

    for i, name in enumerate(package_names):
        if progress_callback:
            progress_callback(i, total, f"Installing {name}...")

        success, message = install_package(name, timeout=timeout)
        results[name] = (success, message)

        if progress_callback:
            progress_callback(i + 1, total, message)

    return results


def get_package_summary() -> Dict[str, Dict]:
    """Get a summary of installed vs missing packages per category."""
    _, missing_pkgs, categories = check_all_packages()
    summary = {}

    for cat in categories:
        cat_pkgs = [p for p in ALL_PACKAGES if p.category == cat]
        cat_installed = [p for p in cat_pkgs if p.is_installed]
        cat_missing = [p for p in cat_pkgs if not p.is_installed]
        summary[cat] = {
            "total": len(cat_pkgs),
            "installed": len(cat_installed),
            "missing": len(cat_missing),
            "missing_names": [p.pip_name for p in cat_missing],
            "installed_names": [p.pip_name for p in cat_installed],
        }

    return summary


# â”€â”€â”€ Streamlit UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€----

def render_dependency_ui():
    """Render a Streamlit UI for checking and fixing dependencies."""
    import streamlit as st

    st.markdown("## ðŸ”§ Dependency Manager")
    st.markdown("*Check, verify, and install all required Python packages with one click.*")

    # Check current status
    all_pkgs, missing_pkgs, categories = check_all_packages()

    total = len(all_pkgs)
    installed_count = len(all_pkgs) - len(missing_pkgs)
    pct = int(installed_count / total * 100) if total > 0 else 0

    # Overall progress
    st.markdown(f"###  Overall Status: {installed_count}/{total} packages installed ({pct}%)")

    if pct == 100:
        st.success("✅ **All packages are installed!** The application is ready to use.")
    else:
        st.warning(f"âš ï¸ **{len(missing_pkgs)} packages** need to be installed for full functionality.")

    # Progress bar
    st.progress(pct)

    # â”€â”€â”€ Per-category breakdown â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    st.markdown("### 📋 Package Breakdown by Category")

    summary = get_package_summary()

    for cat in categories:
        cat_data = summary[cat]
        icon = CATEGORY_ICONS.get(cat, "📦")

        with st.expander(
            f"{icon} **{cat}**  {cat_data['installed']}/{cat_data['total']} installed",
            expanded=cat_data["missing"] > 0,
        ):
            cols = st.columns(2)
            with cols[0]:
                st.markdown("**✅ Installed:**")
                for name in cat_data["installed_names"]:
                    pkg = next((p for p in all_pkgs if p.pip_name == name), None)
                    version = f" v{pkg.installed_version}" if pkg and pkg.installed_version else ""
                    st.markdown(f"- ✅ {name}{version}")

            with cols[1]:
                if cat_data["missing_names"]:
                    st.markdown("**âŒ Missing:**")
                    for name in cat_data["missing_names"]:
                        pkg = next((p for p in all_pkgs if p.pip_name == name), None)
                        desc = f"  {pkg.description}" if pkg else ""
                        st.markdown(f"- âŒ {name}{desc}")
                else:
                    st.markdown("**✅ All installed!**")

    # â”€â”€â”€ Install missing packages â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if missing_pkgs:
        st.markdown("---")
        st.markdown("### ðŸš€ One-Click Install Missing Packages")

        col1, col2 = st.columns([2, 1])
        with col1:
            missing_names = [p.pip_name for p in missing_pkgs]
            st.markdown(f"Will install: **{', '.join(missing_names)}**")
            st.caption("This may take a few minutes. The app will update after installation.")

        with col2:
            install_clicked = st.button(
                "ðŸ”§ Install All Missing Packages",
                type="primary",
                use_container_width=True,
            )

        if install_clicked:
            progress_bar = st.progress(0)
            status_text = st.empty()

            def progress_callback(current, total, message):
                progress_bar.progress(int(current / total * 100))
                status_text.text(f"[{current}/{total}] {message}")

            with st.spinner("Installing packages... This may take several minutes."):
                results = install_missing_packages(missing_names, progress_callback)

            # Show results
            st.markdown("### 📋 Installation Results")
            success_count = sum(1 for s, _ in results.values() if s)
            fail_count = sum(1 for s, _ in results.values() if not s)
            st.markdown(f"**{success_count} succeeded**, **{fail_count} failed**")

            for name, (success, message) in results.items():
                if success:
                    st.success(message)
                else:
                    st.error(message)

            if fail_count == 0:
                st.success("ðŸŽ‰ **All packages installed!** Please refresh the app to apply changes.")
                if st.button("ðŸ”„ Refresh App Now", type="primary"):
                    st.rerun()
            else:
                st.warning("âš ï¸ Some packages failed to install. Try installing them individually via terminal.")

    # â”€â”€â”€ Advanced: Manual install â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    with st.expander("ðŸ› ï¸ Advanced: Install Individual Package"):
        pkg_names = sorted([p.pip_name for p in ALL_PACKAGES])
        selected_pkg = st.selectbox("Select a package to install", options=pkg_names)

        if st.button(f"📥 Install {selected_pkg}"):
            with st.spinner(f"Installing {selected_pkg}..."):
                success, message = install_package(selected_pkg)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)


def auto_fix_missing_critical(quiet: bool = False) -> int:
    """
    Auto-install all missing critical packages without UI interaction.
    Used at app startup. Returns number of packages installed.
    """
    _, missing_pkgs, _ = check_all_packages()

    if not missing_pkgs:
        return 0

    installed_count = 0
    for pkg in missing_pkgs:
        try:
            success, msg = install_package(pkg.pip_name, timeout=120)
            if success:
                installed_count = 1
                if not quiet:
                    print(f"✅ Auto-installed: {pkg.pip_name}")
            else:
                logger.error("Auto-install of %s failed: %s", pkg.pip_name, msg)
                if not quiet:
                    print(f"âš ï¸ Failed: {pkg.pip_name}  {msg}")
        except Exception as e:
            logger.exception("Auto-install of %s raised an error", pkg.pip_name)
            if not quiet:
                print(f"âš ï¸ Error installing {pkg.pip_name}: {e}")

    return installed_count


# â”€â”€â”€ Safe Import Helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def safe_import(import_name: str, pip_name: str, category: str = "Custom", description: str = ""):
    """
    Attempt to import a module. If missing, show a clear message with install instructions.
    Returns (module, is_available) tuple.
    """
    try:
        mod = importlib.import_module(import_name)
        return mod, True
    except ImportError:
        logger.info("Optional dependency %r is not installed (pip install %s)", import_name, pip_name)
        return None, False
    except Exception:
        logger.warning("Optional dependency %r failed to import", import_name, exc_info=True)
        return None, False

