"""Authenticated Streamlit workspace for the platform's Ollama-first AI path.

The Ollama endpoint is configured by the deployment operator, never by a
browser user. For hosted deployments it must be a private/TLS-protected
endpoint reachable from the app service; localhost refers to the container.
"""
from __future__ import annotations

import os
import streamlit as st

from modules.llm_router import LLMRouter


def _router() -> LLMRouter:
    # Read environment configuration at call time so deployment changes are
    # honored without allowing users to override the server-side endpoint.
    return LLMRouter(
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        ollama_model=os.environ.get("OLLAMA_MODEL", "qwen2.5:3b"),
        gemini_api_key="",  # this workspace intentionally stays Ollama-first
    )


def render_ollama_workspace() -> None:
    """Render the shared Ollama-first workspace for an authenticated user."""
    identity = st.session_state.get("user_identity") or {}
    if not st.session_state.get("portal_unlocked") or not identity.get("email"):
        st.error("Sign in to use the AI workspace.")
        return

    st.title("🦙 Local & Shared AI — Ollama")
    st.caption(
        "Ollama-first inference for everyday assistance. Your account is "
        "authenticated by the platform; the model endpoint is controlled by "
        "the deployment administrator."
    )
    endpoint = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
    st.code(f"Configured model: {model}\nEndpoint: {endpoint}", language="text")
    st.warning(
        "For a hosted deployment, 127.0.0.1 points to the Render container, "
        "not your personal computer. A shared endpoint must be reachable from "
        "Render over TLS and protected by an authenticated gateway. Never "
        "expose an unauthenticated Ollama port to the public internet."
    )

    router = _router()
    if st.button("Check Ollama connection", key="ollama_check_connection"):
        if router.available_backends().get("ollama"):
            st.success(f"Ollama is reachable. Configured model: {model}")
        else:
            st.error(
                "Ollama is not reachable from this application. Check the "
                "server-side OLLAMA_BASE_URL and model installation."
            )

    prompt = st.text_area(
        "What would you like help with?",
        key="ollama_workspace_prompt",
        placeholder="Ask a question, summarize text, or plan a task…",
        max_chars=12000,
    )
    if st.button("Generate with Ollama-first routing", type="primary", key="ollama_workspace_generate"):
        if not prompt.strip():
            st.warning("Enter a prompt first.")
            return
        with st.spinner("Checking the configured Ollama model…"):
            if not router.available_backends().get("ollama"):
                st.error(
                    "Ollama is currently unavailable. No prompt was sent to "
                    "a paid provider. Restore the Ollama connection and retry."
                )
                return
            try:
                answer = router.generate(prompt.strip(), task="light", temperature=0.2)
            except Exception:
                st.error("The model request failed. Check server logs and Ollama health.")
                return
        if answer:
            st.markdown("### Response")
            st.write(answer)
        else:
            st.error("Ollama returned an empty response. Please retry.")
