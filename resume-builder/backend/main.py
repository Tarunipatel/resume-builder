import os
import asyncio
import io
from typing import List

import anthropic
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from parser import parse_cv
from screener import screen_cv
from improver import improve_cv
from pdf_generator import generate_pdf
from models import BatchScreenResult, ImprovedCV, MatchLevel, ScreenedCV

load_dotenv()

app = FastAPI(title="Placement Cell Resume Builder")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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


# ── Phase 1: Screen all CVs ──────────────────────────────────────────
@app.post("/api/screen", response_model=BatchScreenResult)
async def screen_cvs(
    job_description: str = Form(...),
    files: List[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 CVs per batch.")
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")

    client = get_client()
    # Higher concurrency for screening — haiku is fast and cheap
    semaphore = asyncio.Semaphore(8)

    async def screen_one(file: UploadFile) -> ScreenedCV:
        async with semaphore:
            contents = await file.read()
            try:
                parsed = parse_cv(file.filename, contents)
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


# ── Phase 3: Improve a single CV (called per-card for 50-70% tier) ──
@app.post("/api/improve-one", response_model=ImprovedCV)
async def improve_one(
    job_description: str = Form(...),
    filename: str = Form(...),
    cv_text: str = Form(...),
):
    if not cv_text.strip():
        raise HTTPException(status_code=400, detail="CV text is empty.")

    client = get_client()
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, improve_cv, client, cv_text, filename, job_description)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── PDF generation ───────────────────────────────────────────────────
@app.post("/api/single-pdf")
async def single_pdf(student_name: str = Form(...), improved_text: str = Form(...)):
    pdf_bytes = generate_pdf(improved_text, student_name)
    safe_name = student_name.replace(" ", "_").replace("/", "-")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={safe_name}_improved.pdf"},
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}
