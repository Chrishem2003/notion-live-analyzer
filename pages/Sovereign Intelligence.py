from __future__ import annotations

import os
import streamlit as st

from sovereign_intelligence import SovereignBrain
from sovereign_intelligence.providers.registry import ProviderRegistry


st.set_page_config(
    page_title="Sovereign Intelligence",
    page_icon="ðŸ§ ",
    layout="wide",
)


@st.cache_resource
def get_brain():

    return SovereignBrain()


st.title("ðŸ§  Sovereign Intelligence")
st.caption(
    "The problem-solving intelligence layer of the platform."
)

provider_registry = ProviderRegistry.default()
all_providers = ["openai", "openrouter", "anthropic", "google"]
configured_providers = provider_registry.configured_names()
configured_provider_priority = ["anthropic", "openai", "openrouter", "google"]
configured_default = next(
    (name for name in configured_provider_priority if name in configured_providers),
    "openai",
)
environment_default = os.getenv("SOVEREIGN_AI_PROVIDER", "").strip()
default_provider = environment_default if environment_default in all_providers else configured_default
provider_options = [default_provider] + [name for name in all_providers if name != default_provider]
provider_env_keys = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
}

with st.sidebar:

    st.subheader("Brain Configuration")

    provider = st.selectbox(
        "Provider",
        provider_options,
        index=0,
    )

    model_override = (
        os.getenv("SOVEREIGN_AI_MODEL", "").strip()
        if provider == default_provider
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

    if configured_providers:
        st.caption("Configured providers: " + ", ".join(configured_providers))
    else:
        st.warning("No provider API keys detected in the server environment.")

    verification = st.checkbox(
        "Verification",
        value=True,
    )

    st.divider()

    st.write(
        "This interface connects to the native "
        "Sovereign Intelligence Engine."
    )


if "sovereign_messages" not in st.session_state:
    st.session_state.sovereign_messages = []


for message in st.session_state.sovereign_messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


prompt = st.chat_input(
    "Describe the problem you want Sovereign Intelligence to solve..."
)


if prompt and provider not in configured_providers:
    st.error(f"{provider.title()} is not configured on the server.")
    st.info(f"Add {provider_env_keys[provider]} in the deployment environment settings. Do not paste the key into chat or source code.")

elif prompt:

    st.session_state.sovereign_messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        with st.spinner(
            "Analyzing, planning and solving..."
        ):

            try:

                brain = get_brain()

                brain.config.enable_verification = verification

                result = brain.solve(
                    prompt,
                    provider=provider,
                    model=model.strip() or None,
                )

                st.markdown(result.answer)

                if result.verification:

                    with st.expander(
                        "Verification"
                    ):

                        st.write(
                            "Passed:",
                            result.verification.passed,
                        )

                        st.write(
                            "Confidence:",
                            result.verification.confidence,
                        )

                        if result.verification.issues:
                            st.write(
                                "Issues:"
                            )
                            for issue in result.verification.issues:
                                st.write(
                                    f"- {issue}"
                                )

                if result.plan:

                    with st.expander(
                        "Execution Plan"
                    ):

                        for step in result.plan.steps:

                            st.write(
                                f"**{step.agent}** â€” "
                                f"{step.description}"
                            )

                st.session_state.sovereign_messages.append(
                    {
                        "role": "assistant",
                        "content": result.answer,
                    }
                )

            except Exception as exc:

                st.error(
                    f"Sovereign Intelligence error: {exc}"
                )

                st.info(
                    "Check your provider API key and "
                    "model configuration."
                )