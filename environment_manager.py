"""
Environment & Dependency Manager
===================================
Honest about what's actually possible: Streamlit Cloud (and most managed
hosts) don't give end users a terminal, so a Settings page can't "make pip
install permanent" — the durable fix is requirements.txt, checked at
deploy time. What this DOES do for real:

1. Checks which optional packages are actually importable right now.
2. Offers a real "Install Now" button that runs an actual subprocess pip
   install into the current running process — this genuinely works on
   most Streamlit Cloud deployments (the container's Python environment
   is writable at runtime), but it is EPHEMERAL: it lasts until the app
   restarts/redeploys, at which point it's gone unless the package is
   also in requirements.txt. The UI says this plainly rather than
   implying it's a permanent fix.
"""

import importlib
import subprocess
import sys
import streamlit as st

OPTIONAL_PACKAGES = {
    "kaleido": "kaleido",
    "python-pptx": "pptx",
    "vaderSentiment": "vaderSentiment",
    "streamlit-webrtc": "streamlit_webrtc",
    "folium": "folium",
    "streamlit-folium": "streamlit_folium",
    "duckdb": "duckdb",
    "psutil": "psutil",
    "cryptography": "cryptography",
    "statsmodels": "statsmodels",
    "scikit-learn": "sklearn",
}


def check_package(import_name: str) -> bool:
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def render_environment_manager():
    st.markdown("#### 📦 Dependency Status")
    st.caption(
        "The durable fix for a missing package is adding it to `requirements.txt` so it installs "
        "automatically on every deploy. The button below is a real, working best-effort fallback for "
        "*this running session only* — it will not survive a restart unless requirements.txt is also "
        "updated. This page cannot silently make the fix permanent; nothing here pretends otherwise."
    )

    missing = []
    for pip_name, import_name in OPTIONAL_PACKAGES.items():
        available = check_package(import_name)
        col1, col2 = st.columns([4, 1])
        col1.write(f"{'✅' if available else '❌'} `{pip_name}`")
        if not available:
            missing.append(pip_name)

    if not missing:
        st.success("Every optional package checked is already available.")
        return

    st.warning(f"{len(missing)} package(s) missing: {', '.join(missing)}")
    if st.button(f"⚡ Install {len(missing)} missing package(s) now (this session only)", type="primary"):
        results = []
        progress = st.progress(0)
        for i, pkg in enumerate(missing):
            with st.spinner(f"Installing {pkg}..."):
                try:
                    proc = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "--quiet", pkg],
                        capture_output=True, text=True, timeout=180,
                    )
                    ok = proc.returncode == 0
                    results.append((pkg, ok, proc.stderr[-300:] if not ok else ""))
                except Exception as e:
                    results.append((pkg, False, str(e)))
            progress.progress((i + 1) / len(missing))

        for pkg, ok, err in results:
            if ok:
                st.success(f"✅ {pkg} installed for this session.")
            else:
                st.error(f"❌ {pkg} failed: {err}")

        st.info(
            "Add the successfully installed packages to `requirements.txt` and redeploy to make this "
            "permanent — otherwise this reverts the next time the app restarts."
        )
        if st.button("Reload app to use newly installed packages"):
            st.rerun()
