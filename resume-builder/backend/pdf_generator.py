import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT


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
