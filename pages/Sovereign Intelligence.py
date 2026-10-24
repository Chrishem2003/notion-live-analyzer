from __future__ import annotations

import os
import streamlit as st

from sovereign_intelligence import SovereignBrain
from sovereign_intelligence.providers.registry import ProviderRegistry

st.set_page_config(
    page_title="Sovereign Intelligence",
    page_icon="🧠",
    layout="wide",
)

SHARED_GATEWAY_CONFIGURED = bool(os.getenv("SHARED_AI_API_URL", "").strip())


@st.cache_resource
def get_brain():
    return SovereignBrain()


st.title("🧠 Sovereign Intelligence")
st.caption("The problem-solving intelligence layer of the platform.")

provider_registry = ProviderRegistry.default()
all_providers = ["ollama", "openai", "openrouter", "anthropic", "google"]
configured_providers = provider_registry.configured_names()
configured_provider_priority = ["ollama", "anthropic", "openai", "openrouter", "google"]
configured_default = next(
    (name for name in configured_provider_priority if name in configured_providers),
    "ollama" if "ollama" in all_providers else "openai",
)
environment_default = os.getenv("SOVEREIGN_AI_PROVIDER", "").strip().lower()
default_provider = environment_default if environment_default in all_providers else configured_default
provider_options = [default_provider] + [name for name in all_providers if name != default_provider]
provider_env_keys = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "ollama": "local Ollama service (OLLAMA_BASE_URL and OLLAMA_MODEL)",
}

with st.sidebar:
    st.subheader("Brain Configuration")
    if SHARED_GATEWAY_CONFIGURED:
        st.success("Shared AI gateway configured")
        st.caption("The server controls the provider and model. Your platform API key remains server-side.")
        provider = "shared gateway"
        model = ""
        verification = False
    else:
        st.warning("Local development mode. For multi-user use, configure SHARED_AI_API_URL and PLATFORM_API_KEY on the Streamlit server.")
        provider = st.selectbox("Provider", provider_options, index=0)
        model_override = (
            os.getenv("SOVEREIGN_AI_MODEL", "").strip()
            if environment_default and provider == environment_default
            else ""
        )
        default_model = provider_registry.get(provider).default_model
        model = st.text_input(
            "Model override (optional)",
            value=model_override,
            key=f"sovereign_model_{provider}",
            placeholder=default_model,
            help=f"Leave blank to use this provider's default model: {default_model}.",
        )
        verification = st.checkbox("Verification", value=True)
        if configured_providers:
            st.caption("Configured local providers: " + ", ".join(configured_providers))
        else:
            st.warning("No provider credentials detected and local Ollama is not reachable.")
    st.divider()
    st.write("This interface connects to the shared AI service when configured; otherwise it uses the local development brain.")

if SHARED_GATEWAY_CONFIGURED:
    identity = st.session_state.get("user_identity", {})
    user_email = str(identity.get("email", "")).strip().lower() if isinstance(identity, dict) else ""
    if not st.session_state.get("portal_unlocked") or not user_email:
        st.error("Sign in through the main platform before using shared AI.")
        st.stop()

if "sovereign_messages" not in st.session_state:
    st.session_state.sovereign_messages = []

for message in st.session_state.sovereign_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Describe the problem you want Sovereign Intelligence to solve...")

if prompt and not SHARED_GATEWAY_CONFIGURED and provider not in configured_providers:
    st.error(f"{provider.title()} is not configured on this server.")
    st.info(f"Configure {provider_env_keys[provider]} or start local Ollama. Never paste API keys into chat or source code.")
elif prompt:
    st.session_state.sovereign_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Analyzing, planning and solving..."):
            try:
                if SHARED_GATEWAY_CONFIGURED:
                    from modules.shared_ai_client import request_shared_ai
                    response = request_shared_ai(
                        product="sovereign_intelligence",
                        task="solve_problem",
                        input_text=prompt,
                        user_email=user_email,
                    )
                    answer = response["output"]
                    st.markdown(answer)
                    st.caption(f"Shared provider: {response.get('provider', 'configured server provider')} · model: {response.get('model', 'server default')}")
                else:
                    brain = get_brain()
                    brain.config.enable_verification = verification
                    result = brain.solve(prompt, provider=provider, model=model.strip() or None)
                    answer = result.answer
                    st.markdown(answer)
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
                st.session_state.sovereign_messages.append({"role": "assistant", "content": answer})
            except Exception as exc:
                # SharedAIError messages are intentionally sanitized; do not echo raw provider exceptions.
                from modules.shared_ai_client import SharedAIError
                if isinstance(exc, SharedAIError):
                    st.error(str(exc))
                else:
                    st.error("Sovereign Intelligence could not complete this request.")
                    st.info("Check the configured provider, model, and service health. No external action was executed.")
