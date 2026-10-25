"""Optional Streamlit surface for the shared AI gateway.

This UI only requests answers/draft workflows. It does not execute automations,
write external records, or expose the bearer token. Call it only after the
application has obtained a verified user access token server-side.
"""
from __future__ import annotations

import streamlit as st

from modules.shared_ai_client import SharedAIError, request_shared_ai

PRODUCT_OPTIONS = {
    "General platform assistant": "platform_general",
    "Automation Studio": "auto_studio",
    "Bio-Research": "bio_research",
    "NEMA-AGORA": "nema_agora",
    "Sovereign Intelligence": "sovereign_intelligence",
    "Sales": "sales",
    "Marketing": "marketing",
    "Finance": "finance",
    "IT operations": "it_operations",
    "Supply chain": "supply_chain",
}


def render_shared_ai_assistant(access_token: str) -> None:
    """Render a server-token-backed assistant; token is never shown or logged."""
    st.subheader("Shared AI Assistant")
    st.caption("Creates guidance and proposals only. No workflow or external action is executed.")
    label = st.selectbox("Workspace", list(PRODUCT_OPTIONS), key="shared_ai_product")
    task = st.text_input("What should the AI help with?", key="shared_ai_task")
    prompt = st.text_area(
        "Describe the problem or work",
        key="shared_ai_prompt",
        max_chars=12000,
        placeholder="Describe the goal, relevant context, constraints, and expected result…",
    )
    if st.button("Ask Shared AI", key="shared_ai_submit"):
        if not task.strip() or not prompt.strip():
            st.warning("Enter both a task and a description.")
            return
        try:
            result = request_shared_ai(
                product=PRODUCT_OPTIONS[label],
                task=task.strip(),
                input_text=prompt.strip(),
                access_token=access_token,
            )
        except SharedAIError as exc:
            st.error(str(exc))
            return
        st.markdown("#### AI response")
        st.write(result["output"])
        st.caption(
            f"Provider: {result.get('provider', 'not reported')} · "
            f"Model: {result.get('model', 'not reported')}"
        )
