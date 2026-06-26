import json
import anthropic
from models import ParsedCV, ScreenedCV, MatchLevel

SYSTEM = "You are an expert recruiter helping a college placement cell screen student CVs against a job description. Respond with ONLY valid JSON."

PROMPT = """Score this student's CV against the job description below.

=== JOB DESCRIPTION ===
{job_description}

=== STUDENT CV ===
{cv_text}

Return this exact JSON structure:
{{
  "student_name": "full name extracted from CV, or 'Unknown'",
  "email": "email address or 'Not found'",
  "phone": "phone number or 'Not found'",
  "score": <integer 0-100>,
  "match_level": "strong" | "partial" | "poor",
  "why_strong": ["reason the CV already fits the role", ...],
  "suggestions": ["specific change that would improve the match", ...],
  "missing_keywords": ["important JD keyword missing from CV", ...]
}}

Scoring guide:
- 70 to 100 (strong): Student has most required skills and relevant experience. Minor gaps only.
- 50 to 69 (partial): Some relevant skills but clear gaps that are addressable through edits.
- 0 to 49 (poor): Missing core requirements. Would need significant upskilling, not just a CV edit.

why_strong should list 2-4 concrete things already in the CV that match the JD.
suggestions should list 2-5 specific, actionable edits the student could make to improve their score.
missing_keywords should list the important JD terms completely absent from this CV.
"""


def screen_cv(client: anthropic.Anthropic, parsed: ParsedCV, job_description: str) -> ScreenedCV:
    prompt = PROMPT.format(job_description=job_description, cv_text=parsed.raw_text)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",  # faster + cheaper for screening
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    data = json.loads(raw)
    score = max(0, min(100, int(data.get("score", 0))))

    # Derive match_level from score in case model is inconsistent
    if score >= 70:
        level = MatchLevel.strong
    elif score >= 50:
        level = MatchLevel.partial
    else:
        level = MatchLevel.poor

    return ScreenedCV(
        filename=parsed.filename,
        student_name=data.get("student_name", "Unknown"),
        email=data.get("email", parsed.email or "Not found"),
        phone=data.get("phone", parsed.phone or "Not found"),
        original_text=parsed.raw_text,
        score=score,
        match_level=level,
        why_strong=data.get("why_strong", []),
        suggestions=data.get("suggestions", []),
        missing_keywords=data.get("missing_keywords", []),
    )
