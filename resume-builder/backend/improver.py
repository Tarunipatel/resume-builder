import json
import anthropic
from models import ParsedCV, ImprovedCV, MatchLevel

SYSTEM_PROMPT = """You are an expert resume coach helping a college placement cell improve student resumes for specific job roles.

Rewrite the resume to better match the job description. Add relevant keywords naturally, strengthen bullet points with action verbs and quantifiable results where possible. Respond with ONLY valid JSON."""

IMPROVE_PROMPT = """Improve this student's resume for the job description below.

=== JOB DESCRIPTION ===
{job_description}

=== STUDENT RESUME ===
{resume_text}

Respond with this exact JSON:
{{
  "student_name": "full name or 'Unknown'",
  "email": "email or 'Not found'",
  "phone": "phone or 'Not found'",
  "improved_resume": "the full improved resume in plain text with clear section headers",
  "key_changes": ["the 3-5 most impactful changes made"],
  "missing_keywords": ["important JD keywords still absent after improvement"],
  "ats_score_before": <integer 0-100>,
  "ats_score_after": <integer 0-100>
}}

Keep improved_resume as plain text (no markdown). Preserve all existing sections."""


def improve_cv(client: anthropic.Anthropic, cv_text: str, filename: str, job_description: str) -> ImprovedCV:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": IMPROVE_PROMPT.format(
            job_description=job_description,
            resume_text=cv_text,
        )}],
        system=SYSTEM_PROMPT,
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    data = json.loads(raw)
    before = int(data.get("ats_score_before", 0))
    after  = int(data.get("ats_score_after", 0))

    if before >= 70:
        level = MatchLevel.strong
    elif before >= 50:
        level = MatchLevel.partial
    else:
        level = MatchLevel.poor

    return ImprovedCV(
        filename=filename,
        student_name=data.get("student_name", "Unknown"),
        email=data.get("email", "Not found"),
        phone=data.get("phone", "Not found"),
        original_text=cv_text,
        improved_text=data.get("improved_resume", ""),
        key_changes=data.get("key_changes", []),
        missing_keywords=data.get("missing_keywords", []),
        match_level=level,
        ats_score_before=before,
        ats_score_after=after,
    )
