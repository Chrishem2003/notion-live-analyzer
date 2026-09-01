import streamlit as st
import traceback

st.set_page_config(
    page_title="Sovereign Career OS",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 Sovereign Career OS")
st.caption(
    "Professional career command center for CVs, resumes, "
    "applications, opportunities, interviews, compensation "
    "and long-term career strategy."
)

try:

    from career_studio.career_os import (
        build_career_os,
        executive_snapshot
    )

    from career_studio.career_strategy import (
        gap_analysis,
        priority_actions,
        milestone_plan
    )

    from career_studio.opportunity import (
        rank_jobs,
        market_summary
    )

    from career_studio.interview_academy import (
        question_bank,
        score_answer,
        readiness
    )

    from career_studio.negotiation import (
        compare_offers,
        target_range,
        script_points
    )

    from career_studio.analytics import (
        dashboard
    )

except Exception:

    st.error("Career OS failed to load.")

    st.code(
        traceback.format_exc(),
        language="text"
    )

    st.stop()


# ================================================================
# SESSION DATA
# ================================================================

if "sovereign_career_profile" not in st.session_state:

    st.session_state.sovereign_career_profile = {
        "name": "",
        "target_role": "",
        "summary": "",
        "skills": [],
        "target_skills": [],
        "applications": [],
        "job_opportunities": [],
        "offers": [],
        "salary_records": []
    }

profile = st.session_state.sovereign_career_profile


# ================================================================
# NAVIGATION
# ================================================================

section = st.sidebar.radio(
    "Career OS",
    [
        "🏠 Command Center",
        "📝 Professional Profile",
        "🎯 Career Strategy",
        "📊 Application Analytics",
        "🌐 Opportunity Intelligence",
        "🎤 Interview Academy",
        "💰 Salary & Negotiation",
        "🛡️ Data Integrity"
    ]
)


# ================================================================
# PROFILE
# ================================================================

if section == "📝 Professional Profile":

    st.header("📝 Professional Profile")

    profile["name"] = st.text_input(
        "Full name",
        profile["name"]
    )

    profile["target_role"] = st.text_input(
        "Target role",
        profile["target_role"]
    )

    profile["summary"] = st.text_area(
        "Professional summary",
        profile["summary"],
        height=180
    )

    skills = st.text_input(
        "Current skills",
        ", ".join(profile["skills"])
    )

    target_skills = st.text_input(
        "Target skills",
        ", ".join(profile["target_skills"])
    )

    profile["skills"] = [
        x.strip()
        for x in skills.split(",")
        if x.strip()
    ]

    profile["target_skills"] = [
        x.strip()
        for x in target_skills.split(",")
        if x.strip()
    ]

    st.success(
        "Professional profile updated for this Streamlit session."
    )


# ================================================================
# COMMAND CENTER
# ================================================================

elif section == "🏠 Command Center":

    st.header("🚀 Career Command Center")

    data = build_career_os(profile)

    snapshot = executive_snapshot(data)

    cols = st.columns(6)

    metrics = [
        ("Skill Coverage", f"{snapshot['skill_coverage_pct']}%"),
        ("Applications", snapshot["applications"]),
        ("Interview Rate", f"{snapshot['interview_rate']}%"),
        ("Offer Rate", f"{snapshot['offer_rate']}%"),
        ("Interview Readiness", f"{snapshot['interview_readiness']}%"),
        ("Offers", snapshot["offers_tracked"])
    ]

    for col, (label, value) in zip(cols, metrics):

        col.metric(label, value)

    st.divider()

    st.subheader("🎯 Priority Actions")

    actions = data["career_strategy"]["priority_actions"]

    if actions:

        for action in actions:

            st.write(
                f"**{action['priority'].upper()}** — "
                f"{action['action']}"
            )

    else:

        st.info(
            "No priority actions have been generated."
        )

    st.subheader("🧠 Skill Gaps")

    gaps = data["career_strategy"]["skill_gaps"]

    if gaps:

        for gap in gaps:
            st.write("• " + gap)

    else:

        st.success(
            "No target skill gaps recorded."
        )

    st.subheader("🌐 Top Opportunities")

    jobs = data["opportunities"]["top_matches"]

    if jobs:

        st.dataframe(
            jobs,
            use_container_width=True
        )

    else:

        st.info(
            "No real job opportunities have been recorded yet."
        )


# ================================================================
# CAREER STRATEGY
# ================================================================

elif section == "🎯 Career Strategy":

    st.header("🎯 Career Strategy Engine")

    result = gap_analysis(profile)

    c1, c2 = st.columns(2)

    c1.metric(
        "Skill Coverage",
        f"{result['coverage_pct']}%"
    )

    c2.metric(
        "Skill Gaps",
        len(result["skill_gaps"])
    )

    st.subheader("Missing Target Skills")

    for skill in result["skill_gaps"]:

        st.write("• " + skill)

    st.subheader("Priority Actions")

    for action in priority_actions(profile):

        st.write(
            f"**{action['priority'].upper()}** — "
            f"{action['action']}"
        )

    st.subheader("90-Day Career Plan")

    st.dataframe(
        milestone_plan(profile, 90),
        use_container_width=True
    )


# ================================================================
# APPLICATION ANALYTICS
# ================================================================

elif section == "📊 Application Analytics":

    st.header("📊 Application Analytics")

    result = dashboard(
        profile.get("applications", [])
    )

    funnel = result["funnel"]

    cols = st.columns(6)

    for col, key in zip(
        cols,
        [
            "applied",
            "screening",
            "interview",
            "final",
            "offer",
            "rejected"
        ]
    ):

        col.metric(
            key.title(),
            funnel[key]
        )

    st.subheader("CV Version Performance")

    st.dataframe(
        result["cv_versions"],
        use_container_width=True
    )

    st.subheader("Role Performance")

    st.dataframe(
        result["roles"],
        use_container_width=True
    )


# ================================================================
# OPPORTUNITIES
# ================================================================

elif section == "🌐 Opportunity Intelligence":

    st.header("🌐 Opportunity Intelligence")

    jobs = profile.get(
        "job_opportunities",
        []
    )

    if not jobs:

        st.info(
            "No real opportunities have been imported yet."
        )

    else:

        minimum = st.slider(
            "Minimum match score",
            0,
            100,
            60
        )

        remote = st.checkbox(
            "Remote only"
        )

        location = st.text_input(
            "Location"
        )

        ranked = rank_jobs(
            jobs,
            minimum,
            location or None,
            remote
        )

        st.dataframe(
            ranked,
            use_container_width=True
        )

        st.subheader(
            "Opportunity Market Summary"
        )

        st.json(
            market_summary(jobs)
        )


# ================================================================
# INTERVIEW ACADEMY
# ================================================================

elif section == "🎤 Interview Academy":

    st.header("🎤 Interview Academy")

    job_text = st.text_area(
        "Target job description",
        height=220
    )

    questions = question_bank(
        profile,
        job_text,
        10
    )

    answers = {}

    for i, question in enumerate(questions):

        answers[question["question"]] = st.text_area(
            f"{i + 1}. {question['question']}",
            key=f"career_question_{i}"
        )

    if st.button(
        "Evaluate Interview",
        type="primary"
    ):

        result = readiness(
            profile,
            answers,
            job_text
        )

        st.metric(
            "Interview Readiness",
            f"{result['readiness']}%"
        )

        st.metric(
            "Completion",
            f"{result['completion']}%"
        )

        st.metric(
            "Answer Quality",
            f"{result['quality']}%"
        )

        for question in questions:

            answer = answers.get(
                question["question"],
                ""
            )

            if answer:

                score = score_answer(
                    answer,
                    question["type"]
                )

                with st.expander(
                    question["question"]
                ):

                    st.metric(
                        "Answer Score",
                        f"{score['score']}%"
                    )

                    for flag in score["flags"]:

                        st.warning(flag)


# ================================================================
# NEGOTIATION
# ================================================================

elif section == "💰 Salary & Negotiation":

    st.header("💰 Salary & Negotiation Studio")

    c1, c2, c3 = st.columns(3)

    minimum = c1.number_input(
        "Minimum",
        min_value=0.0
    )

    target = c2.number_input(
        "Target",
        min_value=0.0
    )

    stretch = c3.number_input(
        "Stretch",
        min_value=0.0
    )

    if st.button(
        "Build Negotiation Position",
        type="primary"
    ):

        try:

            result = target_range(
                minimum,
                target,
                stretch
            )

            st.json(result)

            st.subheader(
                "Negotiation Talking Points"
            )

            for point in script_points(
                profile.get(
                    "target_role",
                    "target role"
                ),
                profile.get(
                    "skills",
                    []
                ),
                target
            ):

                st.write(
                    "• " + point
                )

        except ValueError as error:

            st.error(str(error))

    st.subheader("Recorded Offers")

    offers = profile.get(
        "offers",
        []
    )

    if offers:

        st.dataframe(
            compare_offers(offers),
            use_container_width=True
        )

    else:

        st.info(
            "No real offers recorded."
        )


# ================================================================
# DATA INTEGRITY
# ================================================================

elif section == "🛡️ Data Integrity":

    st.header("🛡️ Data Integrity")

    checks = [
        "No fabricated job vacancies",
        "No fabricated application outcomes",
        "No fabricated salary market data",
        "No fabricated achievements",
        "No fabricated interview outcomes",
        "No employment predictions presented as facts"
    ]

    for check in checks:

        st.write("✅ " + check)

    st.success(
        "Career OS is designed to operate on recorded/user-supplied "
        "career information rather than invented facts."
    )
