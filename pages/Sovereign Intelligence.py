from __future__ import annotations

import os
import streamlit as st

from sovereign_intelligence import SovereignBrain
from sovereign_intelligence.providers.registry import ProviderRegistry
from sovereign_intelligence.api.client import IntelligenceServiceClient, IntelligenceServiceError


st.set_page_config(
    page_title="Sovereign Intelligence",
    page_icon="🧠",
    layout="wide",
)


@st.cache_resource
def get_brain():
    return SovereignBrain()


@st.cache_resource
def get_service_client(base_url: str, api_key: str):
    return IntelligenceServiceClient(base_url, api_key)


st.title("🧠 Sovereign Intelligence")
st.caption("One governed problem-solving layer for research, automation, environmental monitoring, and engineering.")

service_url = os.getenv("INTELLIGENCE_API_URL", "").strip()
service_key = os.getenv("PLATFORM_API_KEY", "").strip()
remote_mode = bool(service_url and service_key)
partial_service_config = bool(service_url) != bool(service_key)
service_client = None
service_metadata = {}
service_error = None

if remote_mode:
    try:
        service_client = get_service_client(service_url, service_key)
        service_metadata = service_client.providers()
        configured_providers = service_metadata.get("providers", [])
    except (IntelligenceServiceError, ValueError) as exc:
        service_error = str(exc)
        configured_providers = []
else:
    provider_registry = ProviderRegistry.default()
    configured_providers = provider_registry.configured_names()

all_providers = ["openai", "openrouter", "anthropic", "google", "ollama"]
priority = ["ollama", "anthropic", "openai", "openrouter", "google"]
environment_default = os.getenv("SOVEREIGN_AI_PROVIDER", "").strip().lower()
service_default = str(service_metadata.get("default_provider") or "").strip().lower()
configured_default = next((name for name in priority if name in configured_providers), "openai")
default_provider = (
    service_default if remote_mode and service_default in all_providers
    else environment_default if environment_default in all_providers
    else configured_default
)
provider_options = [default_provider] + [name for name in all_providers if name != default_provider]

with st.sidebar:
    st.subheader("Brain Configuration")
    provider = st.selectbox("Provider", provider_options, index=0)
    default_model = {
        "ollama": "qwen2.5:3b",
        "openai": "gpt-4o-mini",
        "openrouter": "provider default",
        "anthropic": "claude-3-5-haiku-latest",
        "google": "gemini-2.0-flash",
    }.get(provider, "provider default")
    model_override = (
        os.getenv("SOVEREIGN_AI_MODEL", "").strip()
        if environment_default and provider == environment_default
        else ""
    )
    model = st.text_input(
        "Model override (optional)",
        value=model_override,
        key=f"sovereign_model_{provider}",
        placeholder=default_model,
        help=f"Leave blank to use the selected provider's default: {default_model}.",
    )
    if configured_providers:
        st.caption("Available providers: " + ", ".join(configured_providers))
    elif remote_mode:
        st.warning("The shared service reports no configured providers.")
    else:
        st.warning("No cloud credentials or reachable local Ollama provider detected.")
    verification = st.checkbox("Verification", value=True, disabled=remote_mode)
    st.divider()
    if remote_mode:
        st.caption("Execution mode: shared hosted intelligence service")
    else:
        st.caption("Execution mode: this app instance's local intelligence engine")
        st.caption("For shared hosted mode, configure INTELLIGENCE_API_URL and PLATFORM_API_KEY in the Streamlit service environment.")

if partial_service_config:
    st.warning("Shared service configuration is incomplete. Set both INTELLIGENCE_API_URL and PLATFORM_API_KEY on the server, or remove both to use local mode.")
if service_error:
    st.error(f"Shared intelligence service unavailable: {service_error}")

if "sovereign_messages" not in st.session_state:
    st.session_state.sovereign_messages = []

for message in st.session_state.sovereign_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Describe the problem you want Sovereign Intelligence to solve...")

if prompt:
    st.session_state.sovereign_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Analyzing, planning and checking the result..."):
            try:
                if partial_service_config:
                    raise IntelligenceServiceError(
                        "Set both INTELLIGENCE_API_URL and PLATFORM_API_KEY to enable shared mode."
                    )
                if service_error:
                    raise IntelligenceServiceError(service_error)
                if provider not in configured_providers:
                    raise IntelligenceServiceError(
                        f"{provider.title()} is not configured or reachable in the selected execution mode."
                    )

                if remote_mode:
                    result = service_client.solve(
                        prompt,
                        provider=provider,
                        model=model.strip() or None,
                        strategy="direct",
                    )
                    answer = result["answer"]
                    verification_result = result.get("verification")
                    governance = result.get("governance") or {}
                    with st.expander("Governance and verification"):
                        st.write("Governance accepted:", governance.get("accepted"))
                        st.write("Governance action:", governance.get("action"))
                        if verification_result:
                            st.write("Verification passed:", verification_result.get("passed"))
                            st.write("Confidence:", verification_result.get("confidence"))
                else:
                    brain = get_brain()
                    brain.config.enable_verification = verification
                    result = brain.solve(prompt, provider=provider, model=model.strip() or None)
                    answer = result.answer
                    if result.verification:
                        with st.expander("Verification"):
                            st.write("Passed:", result.verification.passed)
                            st.write("Confidence:", result.verification.confidence)
                            if result.verification.issues:
                                st.write("Issues:")
                                for issue in result.verification.issues:
                                    st.write(f"- {issue}")
                    if result.plan:
                        with st.expander("Execution Plan"):
                            for step in result.plan.steps:
                                st.write(f"**{step.agent}** — {step.description}")

                st.markdown(answer)
                st.session_state.sovereign_messages.append({"role": "assistant", "content": answer})
            except Exception as exc:
                # The shared client sanitizes transport errors. Do not display stack traces or credentials.
                safe_message = str(exc) if isinstance(exc, (IntelligenceServiceError, ValueError)) else (
                    "The intelligence engine could not complete this request. Check provider configuration and server logs."
                )
                st.error(f"Sovereign Intelligence: {safe_message}")
