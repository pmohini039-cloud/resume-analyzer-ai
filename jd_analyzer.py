import json
import re
from analyzer import ask_llm

JD_JSON_PROMPT = """
You are an expert ATS Job Description Parser.

Decompose all job requirements into ATOMIC, SINGLE-TECHNOLOGY SKILLS.

RULES:
1. Split grouped technologies into individual items.
   Example: "Excel with pivot tables and macros" -> ["Excel", "Pivot Tables", "Macros"]
   Example: "Statistical software (R, Python)" -> ["R", "Python"]
2. NEVER return whole sentences or soft skill fluff.
3. Return ONLY valid JSON.

JSON Structure:
{
    "job_role": "",
    "skills": ["Skill1", "Skill2"],
    "education": ["Degree required"],
    "experience": ["Years required"],
    "certifications": []
}

Job Description:
{jd}
"""


def clean_skill(skill: str) -> str:
    """Remove unwanted formatting from skill strings."""
    skill = skill.strip()
    skill = re.sub(r"\(.*?\)", "", skill)
    skill = re.sub(r"\s+", " ", skill)
    return skill.strip()


def extract_jd_json(jd_text: str, model: str) -> dict:
    """Parses JD text using the LLM and extracts clean atomic JSON data."""
    prompt = JD_JSON_PROMPT.format(jd=jd_text)
    response = ask_llm(prompt, model)

    match = re.search(r"\{.*\}", response, re.DOTALL)

    if match:
        json_text = match.group()
        json_text = json_text.replace("```json", "").replace("```", "")
        json_text = re.sub(r",\s*}", "}", json_text)
        json_text = re.sub(r",\s*]", "]", json_text)

        try:
            data = json.loads(json_text)

            raw_skills = data.get("skills", [])
            # Normalize dictionary indices if LLM returns index key-value pairs
            if isinstance(raw_skills, dict):
                raw_skills = list(raw_skills.values())

            skills = []
            seen = set()
            for skill in raw_skills:
                if isinstance(skill, str):
                    cleaned = clean_skill(skill)
                    if cleaned and cleaned.lower() not in seen:
                        seen.add(cleaned.lower())
                        skills.append(cleaned)

            data["skills"] = skills
            return data

        except Exception:
            pass

    return {
        "job_role": "Target Role",
        "skills": [],
        "education": [],
        "experience": [],
        "certifications": [],
    }