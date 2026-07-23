import re
from semantic_matcher import is_semantic_match

# Expansion & Synonym Maps
TERM_ALIASES = {
    # EDA & Statistics
    "exploratory data analysis": "eda",
    "exploratory data analysis (eda)": "eda",
    "eda": "eda",
    "statistical analysis": "statistics",
    "statistical modeling": "statistics",
    # SQL & Python cleaning
    "basic knowledge of sql": "sql",
    "knowledge of sql": "sql",
    "sql skills": "sql",
    "structured query language": "sql",
    "basic knowledge of python": "python",
    "knowledge of python": "python",
    "python programming": "python",
    "ms excel": "excel",
    "microsoft excel": "excel",
    "excel skills": "excel",
    "pivot tables": "excel",
    # Data visualization umbrella mapping
    "power bi": "data visualization",
    "powerbi": "data visualization",
    "tableau": "data visualization",
    "matplotlib": "data visualization",
    "seaborn": "data visualization",
    "data visualization tools": "data visualization",
    # Degree & Exp aliases
    "bca": "bachelor",
    "btech": "bachelor",
    "b.tech": "bachelor",
    "bachelor's": "bachelor",
    "fresher": "entry level",
    "0-1 year": "entry level",
    "0-1 years": "entry level",
}

SOFT_SKILL_STOPWORDS = [
    "ability to learn",
    "adapt to new tools",
    "communication",
    "team player",
    "problem solving",
    "detail oriented",
    "interpersonal",
    "adaptability",
]


def normalize_term(term: str) -> str:
    """Normalize phrases, strip noise words, and unify abbreviations like EDA."""
    term = str(term).lower().strip()
    term = re.sub(r"^(basic knowledge of|knowledge of|proficiency in|familiarity with|experience with)\s+", "", term)

    # Direct match check against aliases
    if term in TERM_ALIASES:
        return TERM_ALIASES[term]

    # Clean characters
    term = re.sub(r"[^a-z0-9+#.\- ]", " ", term)
    term = re.sub(r"\s+", " ", term).strip()

    for raw, alias in TERM_ALIASES.items():
        if raw == term or raw in term:
            return alias

    return term


def is_soft_skill(term: str) -> bool:
    term_lower = term.lower()
    return any(phrase in term_lower for phrase in SOFT_SKILL_STOPWORDS)


def match_lists(resume_items: list, jd_items: list, model: str = "llama3.2:3b") -> tuple:
    if not jd_items:
        return 100, [], []

    clean_resume = [normalize_term(i) for i in resume_items if i]
    clean_jd = [normalize_term(i) for i in jd_items if i]

    matched, missing = set(), set()

    for target in clean_jd:
        if is_soft_skill(target):
            continue

        is_found = False
        for candidate in clean_resume:
            if target == candidate or target in candidate or candidate in target:
                matched.add(target)
                is_found = True
                break
            elif is_semantic_match(candidate, target, model=model):
                matched.add(target)
                is_found = True
                break

        if not is_found:
            missing.add(target)

    score = round((len(matched) / len(clean_jd)) * 100) if clean_jd else 100
    return score, sorted(list(matched)), sorted(list(missing))


def generate_score_explanation(breakdown: dict, matched_skills: list, missing_skills: list) -> tuple:
    points = []

    if breakdown["skills"] >= 70:
        points.append(f"✓ Strong technical match ({len(matched_skills)} core skills aligned)")
    elif breakdown["skills"] >= 40:
        points.append(f"⚠ Moderate technical match ({len(matched_skills)} core skills matched)")
    else:
        points.append("⚠ Significant technical skill gaps identified")

    if breakdown["education"] >= 80:
        points.append("✓ Relevant degree / academic background detected")
    else:
        points.append("⚠ Education partially aligns with requirements")

    if breakdown["experience"] >= 50:
        points.append("✓ Relevant projects or internships found")
    else:
        points.append("⚠ Limited experience matched")

    top_missing = [s.upper() if len(s) <= 4 else s.title() for s in missing_skills[:4]]
    return points, top_missing


def compare_resume_jd(resume_data: dict, jd_data: dict, model: str = "llama3.2:3b") -> dict:
    # 1. Skills Match
    skill_score, matched_skills, missing_skills = match_lists(
        resume_data.get("skills", []), jd_data.get("skills", []), model=model
    )

    # 2. Education Match
    edu_list = []
    for item in resume_data.get("education", []):
        if isinstance(item, dict):
            edu_list.append(item.get("degree", ""))
        elif isinstance(item, str):
            edu_list.append(item)

    raw_edu_score, _, _ = match_lists(edu_list, jd_data.get("education", []), model=model)
    edu_score = min(raw_edu_score, 85) if "bca" in str(edu_list).lower() else raw_edu_score

    # 3. Experience Match
    exp_list = []
    for item in resume_data.get("experience", []):
        if isinstance(item, dict):
            val = item.get("duration", "") or item.get("designation", "")
            if val.strip():
                exp_list.append(val)
        elif isinstance(item, str) and item.strip():
            exp_list.append(item)

    if not exp_list and resume_data.get("projects"):
        exp_score = 60  # Project credit for freshers
    elif exp_list:
        exp_score, _, _ = match_lists(exp_list, jd_data.get("experience", []), model=model)
    else:
        exp_score = 20

    # 4. Certification Check (Smart Weighting)
    jd_certs = jd_data.get("certifications", [])
    if jd_certs:
        cert_score, _, _ = match_lists(
            resume_data.get("certifications", []), jd_certs, model=model
        )
        skill_weight = 0.60
        cert_weight = 0.10
    else:
        # If JD doesn't require certifications, reallocate 10% weight to skills
        cert_score = 0
        skill_weight = 0.70
        cert_weight = 0.00

    overall_score = round(
        (skill_score * skill_weight)
        + (edu_score * 0.15)
        + (exp_score * 0.15)
        + (cert_score * cert_weight)
    )

    expl_points, top_missing = generate_score_explanation(
        {
            "skills": skill_score,
            "education": edu_score,
            "experience": exp_score,
            "certifications": cert_score,
        },
        matched_skills,
        missing_skills,
    )

    return {
        "overall_score": overall_score,
        "breakdown": {
            "skills": skill_score,
            "education": edu_score,
            "experience": exp_score,
            "certifications": cert_score if jd_certs else "N/A (Not Required)",
        },
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "explanation": expl_points,
        "top_missing": top_missing,
    }