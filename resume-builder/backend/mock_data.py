"""Canned Claude responses used when MOCK_MODE=true, so the app can be
exercised end-to-end without a working Anthropic API key."""
import hashlib

from models import ImprovedCV, MatchLevel, ParsedCV, ScreenedCV


def _score_for(filename: str) -> int:
    # Deterministic pseudo-random score per filename so results are stable
    # across runs but spread across all three tiers.
    digest = hashlib.sha256(filename.encode()).hexdigest()
    return int(digest[:4], 16) % 101


def mock_screen_cv(parsed: ParsedCV, job_description: str) -> ScreenedCV:
    score = _score_for(parsed.filename)
    level = MatchLevel.strong if score >= 70 else MatchLevel.partial if score >= 35 else MatchLevel.poor

    return ScreenedCV(
        filename=parsed.filename,
        student_name=parsed.filename.rsplit(".", 1)[0].replace("_", " ").title(),
        email=parsed.email or "Not found",
        phone=parsed.phone or "Not found",
        original_text=parsed.raw_text,
        score=score,
        match_level=level,
        why_strong=["Relevant project experience", "Matches core tech stack", "Good academic background"],
        suggestions=["Add more quantifiable results", "Include missing keywords from the JD", "Tighten bullet points with action verbs"],
        matched_keywords=["Python", "Git", "SQL"],
        missing_keywords=["Docker", "CI/CD", "REST APIs"],
    )


def mock_improve_cv(cv_text: str, filename: str, job_description: str) -> ImprovedCV:
    before = _score_for(filename)
    after = min(100, before + 20)
    level = MatchLevel.strong if before >= 70 else MatchLevel.partial if before >= 35 else MatchLevel.poor

    return ImprovedCV(
        filename=filename,
        student_name=filename.rsplit(".", 1)[0].replace("_", " ").title(),
        email="Not found",
        phone="Not found",
        original_text=cv_text,
        improved_text=cv_text + "\n\n[MOCK] Rewritten with stronger action verbs and JD keywords.",
        key_changes=["Added quantifiable metrics to project bullets", "Inserted missing JD keywords naturally", "Reworded summary to match target role"],
        missing_keywords=["Docker"],
        match_level=level,
        ats_score_before=before,
        ats_score_after=after,
    )
