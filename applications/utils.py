import re

def extract_score(ai_feedback: str) -> int | None:
    """
    Extracts a score (0–10) from the AI feedback text.
    Looks for patterns like 'Score: 7/10' or 'score is 9/10'.
    """
    match = re.search(r"\bscore[:\s]*(\d{1,2})[\/]10", ai_feedback, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None