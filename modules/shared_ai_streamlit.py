"""Optional Streamlit surface for shared AI and approval-gated automation drafts.

Call only after the app has obtained a verified Supabase access token server-side.
Tokens are never rendered or logged. No workflow or external action is executed.
"""
from __future__ import annotations

import streamlit as st

from modules.shared_ai_client import (
    SharedAIError,
    request_automation_draft,
    request_shared_ai,
)

PRODUCT_OPTIONS = {
    "General platform assistant": "platform_general",
    "Bio-Research": "bio_research",
    "NEMA-AGORA": "nema_agora",
    "Sovereign Intelligence": "sovereign_intelligence",
    "Sales": "sales",
    "Marketing": "marketing",
    "Finance": "finance",
    "IT operations": "it_operations",
    "Supply chain": "supply_chain",
}


def _render_automation_draft(draft: dict) -> None:
    st.markdown("#### Proposed automation")
    st.write(draft["title"])
    st.caption(f"Risk level: {draft['risk_level']} · Approval required: yes")
    if draft.get("trigger"):
        st.markdown("**Trigger**")
        st.write(draft["trigger"])
    st.markdown("**Proposed steps**")
    for index, step in enumerate(draft["steps"], start=1):
        with st.expander(f"{index}. {step.get('type', 'step').replace('_', ' ').title()}: {step.get('description', 'Step details')}"):
            if step.get("connector"):
                st.write(f"Connector: {step['connector']}")
            if step.get("inputs"):
                st.json(step["inputs"])
            st.warning("Approval required before this step can ever execute.")
    for heading, key in (
        ("Required permissions", "permissions_required"),
        ("Error handling", "error_handling"),
        ("Test plan", "test_plan"),
        ("Assumptions", "assumptions"),
    ):
        values = draft.get(key, [])
        if values:
            st.markdown(f"**{heading}**")
            for value in values:
                st.write(f"• {value}")
    st.info("Draft only. Nothing was saved, connected to external services, or executed.")


def render_shared_ai_assistant(access_token: str) -> None:
    """Render server-token-backed assistant and draft-only automation builder."""
    st.subheader("Shared AI Assistant")
    st.caption("AI guidance and automation proposals across the platform. Actions remain approval-gated.")
    mode = st.radio(
        "What do you want to build?",
        ["Ask the platform assistant", "Design an automation"],
        horizontal=True,
        key="shared_ai_mode",
    )

    if mode == "Design an automation":
        description = st.text_area(
            "Describe the automation you want",
            key="shared_ai_automation_description",
            max_chars=12000,
            placeholder="When should it start? What data should it use? What result do you expect? Which actions need human approval?",
        )
        if st.button("Generate safe draft", key="shared_ai_automation_submit"):
            if not description.strip():
                st.warning("Describe the automation first.")
                return
            try:
                result = request_automation_draft(
                    description=description.strip(),
                    access_token=access_token,
                )
            except SharedAIError as exc:
                st.error(str(exc))
                return
            _render_automation_draft(result["draft"])
        return

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
