"""Optional Streamlit surface for shared AI and approval-gated automation drafts.

Call only after the app has obtained a verified Supabase access token server-side.
Tokens are never rendered or logged. No workflow or external action is executed.
"""
from __future__ import annotations

import streamlit as st

from modules.shared_ai_client import (
    SharedAIError,
    cancel_user_job,
    get_user_job,
    request_automation_draft,
    request_shared_ai,
    request_user_job,
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
        ["Ask the platform assistant", "Design an automation", "Run a durable intelligence job"],
        horizontal=True,
        key="shared_ai_mode",
    )

    if mode == "Run a durable intelligence job":
        st.caption("Authenticated, user-owned background jobs. This endpoint remains disabled until the API, database migrations, and worker are approved in staging.")
        prompt = st.text_area(
            "Describe the intelligence job",
            key="shared_ai_durable_job_prompt",
            max_chars=12000,
            placeholder="Describe the analysis or reasoning task to run in the background…",
        )
        if st.button("Queue my job", key="shared_ai_durable_job_submit"):
            if not prompt.strip():
                st.warning("Describe the job first.")
            else:
                try:
                    result = request_user_job(prompt=prompt.strip(), access_token=access_token)
                except SharedAIError as exc:
                    st.error(str(exc))
                else:
                    st.session_state["shared_ai_last_job_id"] = result["job_id"]
                    st.success(f"Job {result['job_id']} — status: {result['status']}")
                    if result["status"] == "queued":
                        st.caption("The server confirmed queue acceptance. Processing requires the separately managed worker.")
        last_job_id = st.session_state.get("shared_ai_last_job_id", "")
        if last_job_id:
            st.markdown("**Most recent job from this session**")
            st.code(last_job_id)
        lookup_id = st.text_input(
            "Job ID to inspect or cancel",
            key="shared_ai_job_lookup",
            placeholder="Paste a job ID",
        ).strip() or last_job_id
        col_status, col_cancel = st.columns(2)
        with col_status:
            if st.button("Check status", key="shared_ai_job_check"):
                if not lookup_id:
                    st.warning("Queue a job or enter a job ID first.")
                else:
                    try:
                        result = get_user_job(job_id=lookup_id, access_token=access_token)
                    except SharedAIError as exc:
                        st.error(str(exc))
                    else:
                        for key in ("job_id", "status", "job_type", "attempt_count", "max_attempts", "error_code", "created_at", "updated_at", "completed_at"):
                            if key in result:
                                st.write(f"**{key.replace('_', ' ').title()}:** {result[key]}")
                        if result.get("result_json"):
                            st.markdown("**Result**")
                            st.json(result["result_json"])
        with col_cancel:
            if st.button("Cancel my job", key="shared_ai_job_cancel"):
                if not lookup_id:
                    st.warning("Queue a job or enter a job ID first.")
                else:
                    try:
                        result = cancel_user_job(job_id=lookup_id, access_token=access_token)
                    except SharedAIError as exc:
                        st.error(str(exc))
                    else:
                        st.success(f"Job {result['job_id']} cancelled.")
        return

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
