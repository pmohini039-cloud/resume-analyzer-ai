import streamlit as st
from pypdf import PdfReader
from analyzer import (
    generate_jd,
    evaluate_candidate,
    rewrite_resume,
    generate_missing_skill_questions,
)

st.set_page_config(page_title="AI Resume Matcher & ATS Engine", page_icon="📄", layout="wide")

# --- CACHED HELPERS ---
@st.cache_data(show_spinner="Generating Job Description...")
def cached_generate_jd(job_title, level, model_name):
    return generate_jd(job_title, level, model_name)

@st.cache_data(show_spinner="Evaluating Resume & ATS Match Score...")
def cached_evaluate_candidate(resume_text, jd_text, model_name):
    return evaluate_candidate(resume_text, jd_text, model_name)

@st.cache_data(show_spinner="Rewriting Resume for ATS Optimization...")
def cached_rewrite_resume(resume_text, missing_skills, model_name):
    return rewrite_resume(resume_text, missing_skills, model_name)

@st.cache_data(show_spinner="Generating Skill Gap Interview Questions...")
def cached_generate_questions(job_role, missing_skills, model_name):
    return generate_missing_skill_questions(job_role, missing_skills, model_name)

def extract_pdf_text(pdf_file) -> str:
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.title("Configuration")
    model_name = st.selectbox(
        "LLM Engine",
        ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash", "llama3.2:3b"],
        index=0
    )
    st.info("Upload a candidate's resume (PDF) and provide target job requirements.")

# --- MAIN APP INTERFACE ---
st.title("📄 AI Resume Matcher & ATS Engine")
st.caption("GenAI Scoring & Candidate Optimization Platform")

# Candidate Resume Section
st.subheader("📄 Candidate Resume (PDF)")
uploaded_file = st.file_uploader("Upload", type=["pdf"], label_visibility="collapsed")

# Role Context Section
st.subheader("💼 Role Context")
col_role, col_level = st.columns([3, 1])
with col_role:
    job_title = st.text_input("Target Job Title", value="Data Analyst", placeholder="e.g. Data Analyst")
with col_level:
    level = st.radio("Level", ["Fresher", "Experienced"], horizontal=True)

# Job Description Section
st.subheader("📋 Job Description")
paste_jd = st.text_area("Paste JD text (Optional)", placeholder="Paste raw JD text here. If left empty, AI will generate a concise JD.")

# EVALUATION RUNNER
if st.button("🚀 Run Evaluation", type="primary"):
    if not uploaded_file:
        st.error("Please upload a candidate resume PDF.")
    else:
        resume_text = extract_pdf_text(uploaded_file)
        
        # Auto-generate JD if empty
        jd_text = paste_jd.strip()
        if not jd_text:
            jd_text = cached_generate_jd(job_title, level, model_name)
            st.session_state.generated_jd = jd_text
        else:
            st.session_state.generated_jd = None

        # Execute full evaluation
        eval_data = cached_evaluate_candidate(resume_text, jd_text, model_name)
        st.session_state.resume_text = resume_text
        st.session_state.eval_data = eval_data

# DISPLAY RESULTS
if "eval_data" in st.session_state:
    eval_data = st.session_state.eval_data
    parsed_jd = eval_data.get("parsed_jd", {})
    evaluation = eval_data.get("evaluation", {})
    qual = evaluation.get("qualitative_analysis", {})

    # AI Generated JD Block
    if st.session_state.get("generated_jd"):
        st.subheader("📄 AI Generated Job Description")
        st.text_area("Generated JD (Scrollable Writing Block)", st.session_state.generated_jd, height=200)

    # ATS Match Score Breakdown
    st.markdown("---")
    st.subheader("📊 AI Resume Match Score Breakdown")
    
    col_score, col_bars = st.columns([1, 2])
    with col_score:
        st.caption("Overall Resume Match")
        st.title(f"{evaluation.get('overall_match_score', 0)}%")
        st.markdown("### Evaluation Summary:")
        for bullet in evaluation.get("summary_bullets", []):
            st.write(bullet)
        
        missing_skills = evaluation.get("missing_skills", [])
        if missing_skills:
            st.write("**To improve further, add:**")
            st.markdown(" ".join([f"`{s}`" for s in missing_skills]))

    with col_bars:
        st.markdown("### Skill Coverage")
        
        # Skill Alignment
        sk_score = evaluation.get("skills_alignment_score", 0)
        st.write(f"**Skills Alignment ({sk_score}%):**")
        st.progress(sk_score / 100 if isinstance(sk_score, (int, float)) else 0.0)

        # Education Alignment
        ed_score = evaluation.get("education_alignment_score", 0)
        st.write(f"**Education Alignment ({ed_score}%):**")
        st.progress(ed_score / 100 if isinstance(ed_score, (int, float)) else 0.0)

        # Experience Alignment
        ex_score = evaluation.get("experience_alignment_score", 0)
        st.write(f"**Experience Alignment ({ex_score}%):**")
        st.progress(ex_score / 100 if isinstance(ex_score, (int, float)) else 0.0)

        # Certifications
        cert = evaluation.get("certifications_alignment_score", "N/A")
        st.write(f"**Certifications Alignment:** {cert}")

    # Matched & Missing Skills
    st.markdown("---")
    col_match, col_miss = st.columns(2)
    with col_match:
        st.markdown("### ✅ Matched Skills")
        for s in evaluation.get("matched_skills", []):
            st.markdown(f"- `{s}`")
            
    with col_miss:
        st.markdown("### ❌ Missing Skills")
        for s in evaluation.get("missing_skills", []):
            st.markdown(f"- `{s}`")

    # Parsed Job Requirements
    with st.expander("📄 View Parsed Job Requirements"):
        st.write(f"**Target Role:** {parsed_jd.get('target_role', job_title)}")
        st.write("**Required Skills:**")
        for r_skill in parsed_jd.get("required_skills", []):
            st.markdown(f"- `{r_skill}`")

    # Qualitative Feedback Expandable
    with st.expander("💬 Detailed AI Qualitative Analysis & Feedback", expanded=True):
        if qual.get("summary"):
            st.markdown("## Resume Summary")
            st.write(qual["summary"])

        if qual.get("strengths"):
            st.markdown("## Strengths")
            for item in qual["strengths"]:
                st.markdown(f"* {item}")

        if qual.get("weaknesses"):
            st.markdown("## Weaknesses")
            for item in qual["weaknesses"]:
                st.markdown(f"* {item}")

        if qual.get("missing_skills_list"):
            st.markdown("## Missing Skills")
            for item in qual["missing_skills_list"]:
                st.markdown(f"* {item}")

        if qual.get("improvements"):
            st.markdown("## Improvement Suggestions")
            for item in qual["improvements"]:
                st.markdown(f"* {item}")

        if qual.get("suitable_roles"):
            st.markdown("## Suitable Job Roles")
            for item in qual["suitable_roles"]:
                st.markdown(f"* {item}")

        if qual.get("interview_questions"):
            st.markdown("## Five Interview Questions")
            for idx, q in enumerate(qual["interview_questions"], 1):
                st.markdown(f"{idx}. {q}")

    # Interview Questions Section
    st.markdown("---")
    st.subheader("🎯 Targeted Technical Interview Questions")
    st.caption("Generate technical questions tailored specifically to detected skill gaps.")
    
    if st.button("❓ Generate Skill-Gap Questions"):
        q_result = cached_generate_questions(job_title, evaluation.get("missing_skills", []), model_name)
        st.markdown(q_result)

    # Resume Rewriter Section
    st.markdown("---")
    st.subheader("✍️ Full AI Resume Rewriter")
    st.caption("Generate an ATS-optimized Markdown resume with missing keywords integrated.")
    
    if st.button("✨ Generate Rewritten Resume"):
        rewritten_text = cached_rewrite_resume(
            st.session_state.resume_text, evaluation.get("missing_skills", []), model_name
        )
        st.session_state.rewritten_resume = rewritten_text

    if "rewritten_resume" in st.session_state:
        st.markdown("### 📄 Rewritten ATS-Optimized Resume")
        st.code(st.session_state.rewritten_resume, language="markdown")
        st.download_button(
            label="💾 Download Rewritten Resume (.md)",
            data=st.session_state.rewritten_resume,
            file_name="ATS_Optimized_Resume.md",
            mime="text/markdown"
        )