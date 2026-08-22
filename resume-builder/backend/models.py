from pydantic import BaseModel
from typing import Optional
from enum import Enum


class MatchLevel(str, Enum):
    strong = "strong"
    partial = "partial"
    poor = "poor"


class ParsedCV(BaseModel):
    filename: str
    raw_text: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


# Phase 1 — screening (no rewriting, just score + suggestions)
class ScreenedCV(BaseModel):
    filename: str
    student_name: str
    email: str
    phone: str
    original_text: str
    score: int                    # 0-100
    match_level: MatchLevel
    why_strong: list[str]         # what already matches
    suggestions: list[str]        # what to improve (shown for partial tier)
    matched_keywords: list[str] = []  # JD keywords found in the CV, drove the score up
    missing_keywords: list[str]
    error: Optional[str] = None


class BatchScreenResult(BaseModel):
    job_title: str
    total: int
    screened: int
    failed: int
    results: list[ScreenedCV]     # sorted best-first


# Phase 3 — improvement (rewriting for a single CV)
class ImprovedCV(BaseModel):
    filename: str
    student_name: str
    email: str
    phone: str
    original_text: str
    improved_text: str
    key_changes: list[str]
    missing_keywords: list[str]
    match_level: MatchLevel
    ats_score_before: int
    ats_score_after: int
    error: Optional[str] = None
