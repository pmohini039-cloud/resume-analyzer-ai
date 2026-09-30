import json
import os
import re
import time
import requests
import streamlit as st
from google import genai
from google.genai import errors

# Initialize Gemini Client (reads GEMINI_API_KEY from environment/secrets)
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass

client = genai.Client(api_key=api_key) if api_key else genai.Client()

OLLAMA_URL = "http://localhost:11434/api/generate"


def ask_llm(
    prompt: str, model: str = "gemini-2.0-flash", max_retries: int = 3
) -> str:
    """Routes requests to either Google Gemini API or local Ollama depending on selected model,
    including automatic multi-model fallbacks for Gemini rate limits (429) and outages (503)."""
    
    # Strip extra labels (e.g., "llama3.2:3b (Local)" -> "llama3.2:3b")
    clean_model = model.split(" ")[0].strip()

    # --- 1. LOCAL OLLAMA MODELS ---
    if "llama" in clean_model.lower() or "gemma" in clean_model.lower():
        try:
            payload = {
                "model": clean_model,
                "prompt": prompt,
                "stream": False,
            }
            response = requests.post(OLLAMA_URL, json=payload, timeout=300)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "Could not connect to local Ollama server. Please ensure Ollama is running on your machine."
            )
        except Exception as e:
            raise RuntimeError(f"Ollama execution error ({clean_model}): {e}") from e

    # --- 2. GOOGLE GEMINI MODELS (WITH FALLBACK CHAIN) ---
    # Build model attempt list starting with the requested model followed by stable alternatives
    models_to_try = [clean_model]
    fallback_chain = ["gemini-2.0-flash", "gemini-1.5-flash"]
    
    for fallback in fallback_chain:
        if fallback not in models_to_try:
            models_to_try.append(fallback)

    for current_model in models_to_try:
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=current_model,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text

            except Exception as e:
                error_str = str(e).lower()

                # Handle transient errors: 429 Rate Limit, 503 Server Unavailable, Quota Errors
                is_transient = any(
                    err in error_str
                    for err in ["429", "503", "resource_exhausted", "unavailable", "quota", "demand"]
                )

                if is_transient:
                    match = re.search(r"retry in (\d+(\.\d+)?)s", error_str)
                    wait_time = int(float(match.group(1))) + 2 if match else (2 * attempt)

                    if attempt < max_retries:
                        try:
                            st.warning(
                                f"⏳ Gemini (`{current_model}`) is busy or rate-limited. Retrying in {wait_time}s... (Attempt {attempt}/{max_retries})"
                            )
                        except Exception:
                            pass
                        
                        time.sleep(wait_time)
                        continue
                    else:
                        # Retries exhausted for this model, move to the next fallback model in line
                        break
                else:
                    # Raise non-recoverable client/API key errors immediately
                    raise RuntimeError(
                        f"Failed to communicate with Gemini API ({current_model}): {e}"
                    ) from e

    raise RuntimeError(
        f"All Gemini models ({', '.join(models_to_try)}) are currently experiencing high demand or quota limits. "
        "Please wait 30 seconds and try again."
    )


# --- Prompts ---

PROMPT = """
You are an expert HR Specialist and Technical Recruiter.
Analyze the following resume and provide a detailed evaluation.

Resume Text:
{resume}

Provide your feedback in clear Markdown with the following sections:
1. Executive Resume Summary
2. Key Strengths
3. Critical Weaknesses
4. Missing High-Impact Skills
5. Actionable Improvement Suggestions
6. Suitable Job Roles
7. 5 Tailored Interview Questions
"""

EXTRACT_JSON_PROMPT = """
Extract profile data from the resume below into a clean JSON object.

Resume Text:
{resume}

Return ONLY valid JSON with this exact structure (no commentary):
{{
    "name": "Candidate Name",
    "skills": ["Skill1", "Skill2"],
    "education": ["Degree - Institution"],
    "experience": ["Role - Company"],
    "certifications": ["Cert Name"]
}}
"""

QUESTIONS_PROMPT = """
You are a Senior Technical Interviewer.
The candidate is applying for the role of: {job_role}
They are missing the following required technical skills: {missing_skills}

Generate 5 high-quality, scenario-based technical interview questions that specifically test or explore these missing skill areas.
For each question, provide "Solid Answer Guidance" so an interviewer knows what to look for.
"""


# --- Core Functions ---


def analyze_resume(
    resume_text: str, model: str = "gemini-2.0-flash"
) -> str:
    """Generates qualitative resume review."""
    return ask_llm(PROMPT.format(resume=resume_text), model)


def extract_resume_json(
    resume_text: str, model: str = "gemini-2.0-flash"
) -> dict:
    """Extracts candidate profile data as a structured dictionary safely."""
    raw_response = ask_llm(
        EXTRACT_JSON_PROMPT.format(resume=resume_text), model
    )

    if not raw_response or not isinstance(raw_response, str):
        return {
            "name": "Candidate",
            "skills": [],
            "education": [],
            "experience": [],
            "certifications": [],
        }

    match = re.search(r"\{[\s\S]*\}", raw_response)
    if match:
        try:
            cleaned_json = (
                match.group().replace("```json", "").replace("```", "")
            )
            return json.loads(cleaned_json)
        except json.JSONDecodeError:
            pass

    return {
        "name": "Candidate",
        "skills": [],
        "education": [],
        "experience": [],
        "certifications": [],
    }


def generate_missing_skill_questions(
    job_role: str, missing_skills: list, model: str = "gemini-2.0-flash"
) -> str:
    """Generates targeted technical interview questions based on missing skill gaps."""
    if not missing_skills:
        skills_str = "General core competencies for the role"
    else:
        skills_str = ", ".join(missing_skills)

    prompt = QUESTIONS_PROMPT.format(
        job_role=job_role, missing_skills=skills_str
    )
    return ask_llm(prompt, model)