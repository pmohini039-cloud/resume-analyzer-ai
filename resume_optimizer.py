from analyzer import ask_llm
from prompts import RESUME_OPTIMIZER_PROMPT, RESUME_REWRITE_PROMPT


def optimize_resume(
    resume_text: str, job_role: str, missing_skills: list, model: str
) -> str:
    """Generate ATS optimized summary and project bullet points."""
    skills_str = ", ".join(missing_skills) if missing_skills else "None"

    prompt = RESUME_OPTIMIZER_PROMPT.format(
        job_role=job_role,
        missing_skills=skills_str,
        resume_text=resume_text,
    )

    return ask_llm(prompt, model)


def generate_rewritten_resume(
    resume_text: str, job_role: str, missing_skills: list, model: str
) -> str:
    """Rewrite the complete candidate resume tailored to the target role."""
    skills_str = ", ".join(missing_skills) if missing_skills else "None"

    prompt = RESUME_REWRITE_PROMPT.format(
        job_role=job_role,
        missing_skills=skills_str,
        resume_text=resume_text,
    )

    return ask_llm(prompt, model)