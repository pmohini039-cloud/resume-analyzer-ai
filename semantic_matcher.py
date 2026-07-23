import numpy as np
import ollama


def get_vector(text: str, model: str = "llama3.2:3b") -> list:
    """Fetch text embeddings from local Ollama instance."""
    try:
        res = ollama.embeddings(model=model, prompt=text)
        return res.get("embedding", [])
    except Exception:
        # Silently fail to trigger standard string fallback if embedding model is down or using Gemini
        return []


def cosine_sim(v1: list, v2: list) -> float:
    """Basic cosine similarity between two 1D vectors."""
    if not v1 or not v2:
        return 0.0

    a, b = np.array(v1), np.array(v2)
    norm = np.linalg.norm(a) * np.linalg.norm(b)

    return float(np.dot(a, b) / norm) if norm != 0 else 0.0


def is_semantic_match(
    skill_a: str,
    skill_b: str,
    model: str = "gemini-2.5-flash",
    threshold: float = 0.72,
) -> bool:
    """Check if two skills are semantically equivalent using clean string rules or embeddings."""
    a_clean = skill_a.lower().strip()
    b_clean = skill_b.lower().strip()

    # Fast path: substring or exact check
    if a_clean == b_clean or a_clean in b_clean or b_clean in a_clean:
        return True

    # If model is Gemini or cloud API, string normalization handles matching
    if "gemini" in model.lower():
        return False

    # Vector distance lookup for Ollama
    vec1 = get_vector(skill_a, model)
    vec2 = get_vector(skill_b, model)

    if not vec1 or not vec2:
        return False

    return cosine_sim(vec1, vec2) >= threshold