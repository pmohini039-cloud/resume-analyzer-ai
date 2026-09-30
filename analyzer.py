import json
import os
import re
import time
import requests
import streamlit as st
from google import genai

# Securely fetch API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass

client = genai.Client(api_key=api_key) if api_key else genai.Client()
OLLAMA_URL = "http://localhost:11434/api/generate"

# Active 2026 model fallback chain
MODEL_FALLBACK_CHAIN = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
]

def ask_llm(prompt: str, model: str = "gemini-3.8-flash", max_retries: int = 2) -> str:
    clean_model = model.split(" ")[0].strip()

    # Map deprecated models automatically
    if any(old_ver in clean_model for old_ver in ["1.5", "2.0", "2.5", "3.6"]):
        clean_model = "gemini-3.8-flash"

    if "llama" in clean_model.lower() or "gemma" in clean_model.lower():
        try:
            payload = {"model": clean_model, "prompt": prompt, "stream": False}
            res = requests.post(OLLAMA_URL, json=payload, timeout=300)
            res.raise_for_status()
            return res.json().get("response", "")
        except Exception as e:
            raise RuntimeError(f"Ollama execution error ({clean_model}): {e}") from e

    models_to_try = [clean_model]
    for fb in MODEL_FALLBACK_CHAIN:
        if fb not in models_to_try:
            models_to_try.append(fb)

    last_error = None
    for current_model in models_to_try:
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=current_model, contents=prompt
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                if any(k in err_str for k in ["429", "503", "resource_exhausted", "quota"]):
                    if attempt == max_retries:
                        break
                    time.sleep(2 * attempt)
                    continue
                else:
                    raise RuntimeError(f"API Error ({current_model}): {e}") from e

    raise RuntimeError(f"All models failed. Last error: {last_error}")

# --- PROMPTS ---

GENERATE_JD_PROMPT = """
You are an expert HR Specialist. Generate a concise, tailored Job Description for the target role: {job_title} ({experience_level} level).
Return ONLY a structured Markdown job description containing Job Title, Job Summary, and Key Responsibilities.
"""

PARSE_JD_PROMPT = """
Extract required skills from this Job Description:
{jd_text}

Return ONLY valid JSON with structure:
{{
    "target_role": "Role Name",
    "required_skills": ["Skill1", "Skill2"]
}}
"""

EVALUATE_MATCH_PROMPT = """
Compare Candidate Resume against Job Requirements.

Resume:
{resume_text}

Job Requirements JSON:
{jd_json_str}

Return ONLY a JSON object:
{{
    "overall_match_score": 85,
    "skills_alignment_score": 90,
    "education_alignment_score": 85,
    "experience_alignment_score": 60,
    "certifications_alignment_score": "N/A (Not Required)",
    "summary_bullets": ["✓ Bullet 1", "✓ Bullet 2"],
    "matched_skills": ["Skill1", "Skill2"],
    "missing_skills": ["Skill3"],
    "qualitative_analysis": {{
        "summary": "Executive summary paragraph...",
        "strengths": ["Strength 1", "Strength 2"],
        "weaknesses": ["Weakness 1", "Weakness 2"],
        "missing_skills_list": ["Missing 1"],
        "improvements": ["Suggestion 1"],
        "suitable_roles": ["Role 1"],
        "interview_questions": ["Question 1", "Question 2"]
    }}
}}
"""

REWRITE_RESUME_PROMPT = """
You are a Professional Resume Writer.
Rewrite the following resume into a beautifully formatted, ATS-optimized Markdown resume that naturally integrates these missing skills: {missing_skills}.

Resume:
{resume_text}

Return ONLY the complete Markdown formatted resume.
"""

QUESTIONS_PROMPT = """
Generate 5 targeted, high-quality technical interview questions for role: {job_role} based on missing skills: {missing_skills}.
"""

# --- CORE WRAPPER FUNCTIONS ---

def generate_jd(job_title: str, level: str, model: str = "gemini-3.8-flash") -> str:
    return ask_llm(GENERATE_JD_PROMPT.format(job_title=job_title, experience_level=level), model)

def evaluate_candidate(resume_text: str, jd_text: str, model: str = "gemini-3.8-flash") -> dict:
    jd_json_raw = ask_llm(PARSE_JD_PROMPT.format(jd_text=jd_text), model)
    eval_raw = ask_llm(EVALUATE_MATCH_PROMPT.format(resume_text=resume_text, jd_json_str=jd_json_raw), model)
    
    try:
        jd_match = re.search(r"\{[\s\S]*\}", jd_json_raw)
        eval_match = re.search(r"\{[\s\S]*\}", eval_raw)
        
        parsed_jd = json.loads(jd_match.group()) if jd_match else {}
        parsed_eval = json.loads(eval_match.group()) if eval_match else {}
        
        return {"parsed_jd": parsed_jd, "evaluation": parsed_eval}
    except Exception:
        return {"parsed_jd": {}, "evaluation": {}}

def rewrite_resume(resume_text: str, missing_skills: list, model: str = "gemini-3.8-flash") -> str:
    skills_str = ", ".join(missing_skills) if missing_skills else "N/A"
    return ask_llm(REWRITE_RESUME_PROMPT.format(resume_text=resume_text, missing_skills=skills_str), model)

def generate_missing_skill_questions(job_role: str, missing_skills: list, model: str = "gemini-3.8-flash") -> str:
    skills_str = ", ".join(missing_skills) if missing_skills else "General technical stack"
    return ask_llm(QUESTIONS_PROMPT.format(job_role=job_role, missing_skills=skills_str), model)