from __future__ import annotations

import os
import streamlit as st

from sovereign_intelligence import SovereignBrain


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

with st.sidebar:

    st.subheader("Brain Configuration")

    provider = st.selectbox(
        "Provider",
        [
            "openai",
            "openrouter",
            "anthropic",
            "google",
        ],
    )

    model = st.text_input(
        "Model",
        value=os.getenv(
            "SOVEREIGN_AI_MODEL",
            "gpt-5",
        ),
    )

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


if prompt:

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
                    model=model,
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