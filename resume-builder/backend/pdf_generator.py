import io
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from models import BatchScreenResult


def generate_pdf(improved_text: str, student_name: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    name_style = ParagraphStyle(
        "NameStyle",
        parent=styles["Heading1"],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    section_style = ParagraphStyle(
        "SectionStyle",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=10,
        spaceAfter=4,
        borderPad=2,
    )
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
    )

    story = []
    lines = improved_text.split("\n")
    first_line_done = False

    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 4))
            continue

        if not first_line_done:
            story.append(Paragraph(line, name_style))
            first_line_done = True
            continue

        # Heuristic: lines that are all caps or short (<40 chars) with no lowercase are section headers
        if line.isupper() or (len(line) < 40 and line == line.title() and ":" not in line and not line.startswith("-")):
            story.append(Spacer(1, 6))
            story.append(Paragraph(line, section_style))
        else:
            safe_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe_line, body_style))

    doc.build(story)
    return buffer.getvalue()


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


TIER_LABELS = {
    "strong": "Strong fit (70-100)",
    "partial": "Worth improving (35-69)",
    "poor": "Poor fit (0-34)",
}


def generate_report_pdf(screen_result: BatchScreenResult) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Heading1"], fontSize=18, alignment=TA_CENTER, spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        "ReportSub", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER,
        textColor="#555555", spaceAfter=16,
    )
    tier_style = ParagraphStyle(
        "TierHeading", parent=styles["Heading2"], fontSize=13, spaceBefore=16, spaceAfter=8,
    )
    name_style = ParagraphStyle(
        "CandidateName", parent=styles["Heading3"], fontSize=11.5, spaceBefore=10, spaceAfter=2,
    )
    meta_style = ParagraphStyle(
        "CandidateMeta", parent=styles["Normal"], fontSize=9, textColor="#555555", spaceAfter=4,
    )
    label_style = ParagraphStyle(
        "SectionLabel", parent=styles["Normal"], fontSize=9.5, spaceBefore=3, textColor="#333333",
    )
    body_style = ParagraphStyle(
        "ReportBody", parent=styles["Normal"], fontSize=9.5, leading=13,
    )

    story = [
        Paragraph(_esc(screen_result.job_title), title_style),
        Paragraph(
            f"CV Analysis Report &mdash; {screen_result.screened} screened, "
            f"{screen_result.failed} failed &mdash; generated {date.today().isoformat()}",
            sub_style,
        ),
    ]

    for tier in ("strong", "partial", "poor"):
        cvs = [r for r in screen_result.results if not r.error and r.match_level == tier]
        if not cvs:
            continue

        story.append(HRFlowable(width="100%", color="#dddddd", thickness=0.75, spaceAfter=6))
        story.append(Paragraph(f"{TIER_LABELS[tier]} &mdash; {len(cvs)}", tier_style))

        for cv in cvs:
            story.append(Paragraph(f"{_esc(cv.student_name)} &mdash; Score: {cv.score}", name_style))
            story.append(Paragraph(_esc(f"{cv.email}  |  {cv.phone}  |  {cv.filename}"), meta_style))

            if cv.why_strong:
                story.append(Paragraph("<b>Why it matches:</b> " + _esc("; ".join(cv.why_strong)), body_style))
            if cv.matched_keywords:
                story.append(Paragraph("<b>Matched keywords:</b> " + _esc(", ".join(cv.matched_keywords)), body_style))
            if cv.missing_keywords:
                story.append(Paragraph("<b>Missing keywords:</b> " + _esc(", ".join(cv.missing_keywords)), body_style))
            if cv.suggestions:
                story.append(Paragraph("<b>Suggestions:</b> " + _esc("; ".join(cv.suggestions)), body_style))
            story.append(Spacer(1, 6))

    failed = [r for r in screen_result.results if r.error]
    if failed:
        story.append(HRFlowable(width="100%", color="#dddddd", thickness=0.75, spaceAfter=6))
        story.append(Paragraph(f"Could not process &mdash; {len(failed)}", tier_style))
        for cv in failed:
            story.append(Paragraph(_esc(f"{cv.filename}: {cv.error}"), body_style))

    doc.build(story)
    return buffer.getvalue()
