import json
import re
from analyzer import ask_llm

JOB_GENERATOR_PROMPT = """
You are an experienced HR Recruiter. 
Generate a concise, professional Job Description for the following role:

Role: {role}
Experience Level: {experience}

RULES:
1. Keep the total word count strictly between 250 and 300 words.
2. List 8 to 10 core technical skills required.
3. Keep soft skills separate from technical skills.

Return EXACTLY in this format:

===JOB_DESCRIPTION===
Job Title: {role}

Job Summary:
(2-3 sentences summary)

Required Technical Skills:
- Skill1
- Skill2
- Skill3
- Skill4
- Skill5
- Skill6
- Skill7
- Skill8

Education:
(1 line)

Experience:
(1 line)

===JSON===
{{
    "job_role": "{role}",
    "skills": ["SQL", "Python", "Excel", "Data Visualization", "Pandas", "NumPy", "Data Cleaning", "EDA", "Statistics", "Git"],
    "education": ["Bachelor's degree in Computer Science, Math, or related quantitative field"],
    "experience": ["0-1 years of experience or strong analytical project portfolio"],
    "certifications": []
}}
"""


def clean_jd_display(text: str) -> str:
    """Strips internal prompt artifact tags completely."""
    if "===JOB_DESCRIPTION===" in text:
        text = text.split("===JOB_DESCRIPTION===")[1]
    if "===JSON===" in text:
        text = text.split("===JSON===")[0]

    text = re.sub(r"===.*?===", "", text)
    return text.strip()


def generate_job_description(role: str, experience: str, model: str):
    """Generates concise JD markdown and clean JSON specifications."""
    prompt = JOB_GENERATOR_PROMPT.format(role=role, experience=experience)
    response = ask_llm(prompt, model)

    display_jd = clean_jd_display(response)

    # Extract clean JSON payload
    jd_data = None
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if match:
        try:
            cleaned = match.group().replace("```json", "").replace("```", "")
            jd_data = json.loads(cleaned)
        except Exception:
            jd_data = None

    if not jd_data or not jd_data.get("skills"):
        jd_data = {
            "job_role": role,
            "skills": [
                "SQL", "Python", "Excel", "Data Visualization", "Pandas",
                "NumPy", "Data Cleaning", "EDA", "Statistics", "Git"
            ],
            "education": ["Bachelor's degree in quantitative field"],
            "experience": [experience],
            "certifications": [],
        }

    return display_jd, jd_data