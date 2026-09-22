import os
import time
import asyncio
import io
from collections import defaultdict, deque
from typing import List

import anthropic
from fastapi import FastAPI, File, Form, Request, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from parser import parse_cv
from screener import screen_cv
# from improver import improve_cv
from mock_data import mock_screen_cv  # , mock_improve_cv
from pdf_generator import generate_report_pdf
from models import BatchScreenResult, MatchLevel, ScreenedCV

load_dotenv()

MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

DEFAULT_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
extra_origins = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = DEFAULT_ORIGINS + [o.strip() for o in extra_origins.split(",") if o.strip()]

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB per CV

# Per-IP sliding-window limit on the costly (Claude-backed) screening endpoint.
# In-memory only — fine for a single-process deployment like this one.
RATE_LIMIT_WINDOW_SECONDS = 3600
RATE_LIMIT_MAX_REQUESTS = 10
_screen_request_log: dict[str, deque] = defaultdict(deque)

app = FastAPI(title="Orca")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY is not configured. Add it to backend/.env"
        )
    return anthropic.Anthropic(api_key=api_key)


def extract_job_title(jd: str) -> str:
    for line in jd.strip().split("\n"):
        if line.strip():
            return line.strip()[:60]
    return "Target Role"


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(ip: str) -> None:
    now = time.time()
    log = _screen_request_log[ip]
    while log and log[0] < now - RATE_LIMIT_WINDOW_SECONDS:
        log.popleft()
    if len(log) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded — max {RATE_LIMIT_MAX_REQUESTS} screening requests per hour. Try again later.",
        )
    log.append(now)


# ── Phase 1: Screen all CVs ──────────────────────────────────────────
@app.post("/api/screen", response_model=BatchScreenResult)
async def screen_cvs(
    request: Request,
    job_description: str = Form(...),
    files: List[UploadFile] = File(...),
):
    enforce_rate_limit(get_client_ip(request))

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    if len(files) > 200:
        raise HTTPException(status_code=400, detail="Maximum 200 CVs per batch.")
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")

    client = None if MOCK_MODE else get_client()
    # Higher concurrency for screening — haiku is fast and cheap
    semaphore = asyncio.Semaphore(15)

    async def screen_one(file: UploadFile) -> ScreenedCV:
        async with semaphore:
            contents = await file.read()
            try:
                if len(contents) > MAX_FILE_SIZE_BYTES:
                    raise ValueError(
                        f"File exceeds the {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB size limit."
                    )
                parsed = parse_cv(file.filename, contents)
                if MOCK_MODE:
                    return mock_screen_cv(parsed, job_description)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, screen_cv, client, parsed, job_description)
            except Exception as e:
                return ScreenedCV(
                    filename=file.filename,
                    student_name="Unknown",
                    email="Not found",
                    phone="Not found",
                    original_text="",
                    score=0,
                    match_level=MatchLevel.poor,
                    why_strong=[],
                    suggestions=[],
                    missing_keywords=[],
                    error=str(e),
                )

    results = list(await asyncio.gather(*[screen_one(f) for f in files]))

    # Sort best score first
    results.sort(key=lambda r: r.score, reverse=True)

    screened = [r for r in results if not r.error]
    failed   = [r for r in results if r.error]

    return BatchScreenResult(
        job_title=extract_job_title(job_description),
        total=len(files),
        screened=len(screened),
        failed=len(failed),
        results=results,
    )


# ── Phase 3: Improve a single CV — disabled for now, replaced by the ────
# ── analysis report below (see /api/report-pdf).                     ──
# @app.post("/api/improve-one", response_model=ImprovedCV)
# async def improve_one(
#     job_description: str = Form(...),
#     filename: str = Form(...),
#     cv_text: str = Form(...),
# ):
#     if not cv_text.strip():
#         raise HTTPException(status_code=400, detail="CV text is empty.")
#
#     if MOCK_MODE:
#         return mock_improve_cv(cv_text, filename, job_description)
#
#     client = get_client()
#     loop = asyncio.get_event_loop()
#     try:
#         result = await loop.run_in_executor(None, improve_cv, client, cv_text, filename, job_description)
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @app.post("/api/single-pdf")
# async def single_pdf(student_name: str = Form(...), improved_text: str = Form(...)):
#     pdf_bytes = generate_pdf(improved_text, student_name)
#     safe_name = student_name.replace(" ", "_").replace("/", "-")
#     return StreamingResponse(
#         io.BytesIO(pdf_bytes),
#         media_type="application/pdf",
#         headers={"Content-Disposition": f"attachment; filename={safe_name}_improved.pdf"},
#     )


# ── Phase 3: Downloadable analysis report from Phase 1 screening ────────
@app.post("/api/report-pdf")
async def report_pdf(screen_result: BatchScreenResult):
    pdf_bytes = generate_report_pdf(screen_result)
    safe_title = screen_result.job_title.encode("ascii", "ignore").decode().replace(" ", "_").replace("/", "-")[:50]
    safe_title = safe_title.strip("_") or "cv_analysis_report"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={safe_title}_cv_analysis_report.pdf"},
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}
