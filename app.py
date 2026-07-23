import streamlit as st

from analyzer import (
    analyze_resume,
    extract_resume_json,
    generate_missing_skill_questions,
)
from comparison import compare_resume_jd
from jd_analyzer import extract_jd_json
from job_generator import generate_job_description
from pdf_reader import extract_text
from resume_optimizer import generate_rewritten_resume

AVAILABLE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "llama3.2:3b",
    "gemma3:270m",
]

st.set_page_config(page_title="AI Resume Matcher & ATS Engine", layout="wide")

st.title("📄 AI Resume Matcher & ATS Engine")
st.caption("GenAI Scoring & Candidate Optimization Platform")

# Initialize Session States
if "eval_completed" not in st.session_state:
    st.session_state.eval_completed = False
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "resume_data" not in st.session_state:
    st.session_state.resume_data = {}
if "jd_data" not in st.session_state:
    st.session_state.jd_data = {}
if "comparison" not in st.session_state:
    st.session_state.comparison = {}
if "qualitative_review" not in st.session_state:
    st.session_state.qualitative_review = ""
if "raw_jd" not in st.session_state:
    st.session_state.raw_jd = ""

# --- Sidebar ---
with st.sidebar:
    st.header("Configuration")
    selected_model = st.selectbox("LLM Engine", AVAILABLE_MODELS)
    st.divider()
    st.info("Upload a candidate's resume (PDF) and provide target job requirements.")

# --- Inputs ---
uploaded_file = st.file_uploader("Candidate Resume (PDF)", type=["pdf"])

st.subheader("💼 Role Context")
job_role = st.text_input("Target Job Title", placeholder="e.g. Data Analyst")
experience_level = st.radio("Level", ["Fresher", "Experienced"], horizontal=True)

st.subheader("📋 Job Description")
job_description = st.text_area(
    "Paste JD text (Optional)",
    height=140,
    placeholder="Paste raw JD text here. If left empty, AI will generate a concise JD.",
)

if uploaded_file and not (job_role.strip() or job_description.strip()):
    st.warning("Please enter a Target Job Title or paste a Job Description.")

# --- Pipeline Trigger ---
if uploaded_file and (job_role.strip() or job_description.strip()):
    if st.button("🚀 Run Evaluation", type="primary"):
        with st.spinner("Processing PDF and running AI assessment..."):
            st.session_state.resume_text = extract_text(uploaded_file)
            st.session_state.qualitative_review = analyze_resume(
                st.session_state.resume_text, selected_model
            )
            st.session_state.resume_data = extract_resume_json(
                st.session_state.resume_text, selected_model
            )

            if job_description.strip():
                st.session_state.raw_jd = job_description
                st.session_state.jd_data = extract_jd_json(
                    st.session_state.raw_jd, selected_model
                )
            else:
                st.session_state.raw_jd, st.session_state.jd_data = generate_job_description(
                    job_role, experience_level, selected_model
                )

            st.session_state.comparison = compare_resume_jd(
                st.session_state.resume_data,
                st.session_state.jd_data,
                model=selected_model,
            )
            st.session_state.eval_completed = True

# --- Dashboard Render (Persists across button clicks) ---
if st.session_state.eval_completed:
    comparison = st.session_state.comparison
    jd_data = st.session_state.jd_data
    resume_text = st.session_state.resume_text
    qualitative_review = st.session_state.qualitative_review

    if not job_description.strip():
        st.divider()
        st.subheader("📄 AI Generated Job Description")
        st.markdown(st.session_state.raw_jd)

    st.divider()

    # Score Dashboard
    st.subheader("📊 AI Resume Match Score Breakdown")

    col_score, col_bars = st.columns([1, 2])

    with col_score:
        st.metric(
            label="Overall Resume Match",
            value=f"{comparison['overall_score']}%",
        )

        st.markdown("#### **Evaluation Summary:**")
        for pt in comparison["explanation"]:
            st.markdown(f"- {pt}")

        if comparison["top_missing"]:
            st.markdown("**To improve further, add:**")
            for m in comparison["top_missing"]:
                st.markdown(f"• `{m}`")

    with col_bars:
        st.markdown("### Skill Coverage Charts")
        
        skills_val = comparison['breakdown']['skills']
        st.write(f"**Skills Alignment ({skills_val}%):**")
        st.progress(skills_val / 100)

        edu_val = comparison['breakdown']['education']
        st.write(f"**Education Alignment ({edu_val}%):**")
        st.progress(edu_val / 100)

        exp_val = comparison['breakdown']['experience']
        st.write(f"**Experience Alignment ({exp_val}%):**")
        st.progress(exp_val / 100)

        cert_val = comparison['breakdown']['certifications']
        if isinstance(cert_val, (int, float)):
            st.write(f"**Certifications Alignment ({cert_val}%):**")
            st.progress(cert_val / 100)
        else:
            st.write(f"**Certifications Alignment:** {cert_val}")

    st.divider()

    # Matches & Gaps
    col_match, col_gap = st.columns(2)

    with col_match:
        st.subheader("✅ Matched Skills")
        if comparison["matched_skills"]:
            for s in comparison["matched_skills"]:
                st.markdown(f"- `{s.upper() if len(s)<=4 else s.title()}`")
        else:
            st.info("No explicit skills matched.")

    with col_gap:
        st.subheader("❌ Missing Skills")
        if comparison["missing_skills"]:
            for s in comparison["missing_skills"]:
                st.markdown(f"- `{s.upper() if len(s)<=4 else s.title()}`")
        else:
            st.success("No critical skill gaps detected.")

    st.divider()

    with st.expander("📋 View Parsed Job Requirements"):
        st.markdown(f"**Target Role:** {jd_data.get('job_role', job_role)}")
        st.markdown("**Required Skills:**")
        for sk in jd_data.get("skills", []):
            st.markdown(f"- `{sk}`")

    st.divider()

    # AI Qualitative Review
    st.subheader("🤖 AI Resume Analysis")
    st.markdown(qualitative_review)

    st.divider()

    # --- Interactive Feature 1: Resume Rewriter ---
    st.subheader("🚀 Full AI Resume Rewriter")
    st.write("Generate an ATS-optimized Markdown resume tailored with missing keywords integrated.")
    if st.button("✨ Generate Rewritten Resume"):
        with st.spinner("Rewriting resume with missing skill integration..."):
            target_role_name = (
                job_role
                if job_role.strip()
                else jd_data.get("job_role", "Target Role")
            )
            rewritten_resume = generate_rewritten_resume(
                resume_text=resume_text,
                job_role=target_role_name,
                missing_skills=comparison["missing_skills"],
                model=selected_model,
            )
            st.session_state.rewritten_resume = rewritten_resume

    if "rewritten_resume" in st.session_state:
        st.markdown("### 📄 Rewritten ATS-Optimized Resume")
        st.markdown(st.session_state.rewritten_resume)
        st.download_button(
            label="📥 Download Rewritten Resume (.md)",
            data=st.session_state.rewritten_resume,
            file_name="optimized_resume.md",
            mime="text/markdown",
        )

    st.divider()

    # --- Interactive Feature 2: Interview Questions ---
    st.subheader("🎯 Targeted Technical Interview Questions")
    st.write("Generate technical interview questions tailored specifically to detected skill gaps.")
    if st.button("❓ Generate Skill-Gap Questions"):
        with st.spinner("Generating technical questions..."):
            target_role_name = (
                job_role
                if job_role.strip()
                else jd_data.get("job_role", "Target Role")
            )
            st.session_state.questions_text = generate_missing_skill_questions(
                job_role=target_role_name,
                missing_skills=comparison["missing_skills"],
                model=selected_model,
            )

    if "questions_text" in st.session_state:
        st.markdown(st.session_state.questions_text)

    st.divider()

    # --- Interactive Feature 3: Download Report ---
    st.subheader("📥 Download Candidate Evaluation Report")
    report_content = f"""AI RESUME MATCH EVALUATION REPORT
====================================
Target Role: {job_role if job_role else jd_data.get('job_role')}
Overall AI Match Score: {comparison['overall_score']}%

SKILL BREAKDOWN:
- Skills Alignment: {comparison['breakdown']['skills']}%
- Education Alignment: {comparison['breakdown']['education']}%
- Experience Alignment: {comparison['breakdown']['experience']}%

MATCHED SKILLS:
{', '.join(comparison['matched_skills'])}

MISSING SKILLS:
{', '.join(comparison['missing_skills'])}

====================================
QUALITATIVE ANALYSIS:
{qualitative_review}
"""
    st.download_button(
        label="📥 Download Full Evaluation Report (.txt)",
        data=report_content,
        file_name="candidate_evaluation_report.txt",
        mime="text/plain",
    )