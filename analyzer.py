import json
import os
import re
from google import genai
import ollama
import streamlit as st

from prompts import INTERVIEW_PROMPT, JSON_PROMPT, PROMPT


def get_gemini_client():
    """Retrieve Gemini API client using Streamlit secrets or env vars."""
    api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
    if not api_key:
        raise ValueError(
            "Missing GEMINI_API_KEY. Add it to .streamlit/secrets.toml or set as an environment variable."
        )
    return genai.Client(api_key=api_key)


def ask_llm(prompt: str, model: str, retries: int = 2) -> str:
    """Unified LLM execution supporting Gemini API and local Ollama."""
    # Handle Gemini Models
    if "gemini" in model.lower():
        try:
            client = get_gemini_client()
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            return response.text or ""
        except Exception as e:
            raise RuntimeError(f"Failed to communicate with Gemini API ({model}).\nDetails: {e}") from e

    # Handle Ollama Models
    last_err = None
    for _ in range(retries):
        try:
            res = ollama.chat(
                model=model, messages=[{"role": "user", "content": prompt}]
            )
            return res["message"]["content"]
        except Exception as e:
            last_err = e

    raise RuntimeError(
        f"Failed to communicate with Ollama ({model}). "
        f"Ensure Ollama is running.\nDetails: {last_err}"
    )


def analyze_resume(resume_text: str, model: str) -> str:
    """Run full qualitative resume review."""
    return ask_llm(PROMPT.format(resume=resume_text), model)


def generate_missing_skill_questions(
    job_role: str, missing_skills: list, model: str
) -> str:
    """Generate interview questions focused on detected skill gaps."""
    gap_str = (
        ", ".join(missing_skills)
        if missing_skills
        else "General Core Competencies"
    )

    prompt = INTERVIEW_PROMPT.format(
        job_role=job_role,
        missing_skills=gap_str,
    )
    return ask_llm(prompt, model)


def clean_json_str(text: str) -> str:
    """Sanitize LLM output to fix common JSON formatting issues."""
    text = text.replace("```json", "").replace("```", "")
    text = re.sub(r"[\x00-\x1F]+", " ", text)  # Strip control characters
    text = re.sub(r",\s*}", "}", text)  # Fix trailing commas
    text = re.sub(r",\s*]", "]", text)
    return text.strip()


def extract_resume_json(resume_text: str, model: str) -> dict:
    """Extract structured data from resume text using LLM."""
    prompt = JSON_PROMPT.replace("{resume}", resume_text)
    raw_response = ask_llm(prompt, model)

    match = re.search(r"\{[\s\S]*\}", raw_response)
    if not match:
        raise ValueError("LLM response did not contain a valid JSON block.")

    cleaned = clean_json_str(match.group())

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as err:
        print("Raw Response:\n", raw_response)
        raise ValueError(f"Failed to parse JSON response: {err}") from err