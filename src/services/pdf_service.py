import re

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from src.constants import PDF_STYLING
from src.utils.logger import logger


def parse_markdown_to_html(text: str) -> str:
    """
    Translates simple markdown tags (**bold**, *italic*, list items)
    into HTML tags compatible with ReportLab Paragraph parser.
    """
    if not text:
        return ""

    # Escape standard XML characters
    html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Convert bold **text** to <b>text</b>
    html = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", html)

    # Convert italic *text* to <i>text</i>
    html = re.sub(r"\*(.*?)\*", r"<i>\1</i>", html)

    return html


def draw_header_footer(canvas, doc):
    """Draws consistent headers and footers on every page."""
    canvas.saveState()
    canvas.setFont(PDF_STYLING["font_body"], 9)
    canvas.setFillColor(HexColor(PDF_STYLING["secondary_color"]))

    # Draw header (on pages > 1)
    if doc.page > 1:
        canvas.drawString(54, 750, "Automated Report Generator")
        canvas.setStrokeColor(HexColor(PDF_STYLING["secondary_color"]))
        canvas.setLineWidth(0.5)
        canvas.line(54, 742, 558, 742)

    # Draw footer
    page_text = f"Page {doc.page}"
    canvas.drawRightString(558, 40, page_text)
    canvas.drawString(
        54, 40, "Disclaimer: AI-generated content. Review before external publication."
    )
    canvas.restoreState()


class PDFService:
    """Service to convert markdown text into a styled PDF document using ReportLab."""

    def generate_pdf(self, markdown_text: str, output_path: str) -> None:
        """
        Parses Markdown text and outputs a beautifully formatted PDF.
        """
        logger.info(f"Generating PDF report at path: {output_path}")

        # Define Page template setup
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=72,
            bottomMargin=72,
        )

        # Styles
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "PDFTitle",
            parent=styles["Normal"],
            fontName=PDF_STYLING["font_title"],
            fontSize=22,
            leading=26,
            textColor=HexColor(PDF_STYLING["primary_color"]),
            spaceAfter=20,
        )

        h2_style = ParagraphStyle(
            "PDFH2",
            parent=styles["Normal"],
            fontName=PDF_STYLING["font_title"],
            fontSize=14,
            leading=18,
            textColor=HexColor(PDF_STYLING["primary_color"]),
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True,
        )

        body_style = ParagraphStyle(
            "PDFBody",
            parent=styles["Normal"],
            fontName=PDF_STYLING["font_body"],
            fontSize=10,
            leading=14,
            textColor=HexColor(PDF_STYLING["text_color"]),
            spaceAfter=8,
        )

        bullet_style = ParagraphStyle(
            "PDFBullet",
            parent=styles["Normal"],
            fontName=PDF_STYLING["font_body"],
            fontSize=10,
            leading=14,
            textColor=HexColor(PDF_STYLING["text_color"]),
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=4,
        )

        flowables = []
        lines = markdown_text.split("\n")

        in_bullet_list = False

        for line in lines:
            line_str = line.strip()

            if not line_str:
                in_bullet_list = False
                continue

            # 1. Check for headings
            if line_str.startswith("# "):
                title_text = parse_markdown_to_html(line_str[2:])
                flowables.append(Paragraph(title_text, title_style))
                flowables.append(Spacer(1, 10))
                in_bullet_list = False

            elif line_str.startswith("## "):
                h2_text = parse_markdown_to_html(line_str[3:])
                flowables.append(Paragraph(h2_text, h2_style))
                in_bullet_list = False

            elif line_str.startswith("### "):
                h3_text = parse_markdown_to_html(line_str[4:])
                flowables.append(Paragraph(h3_text, h2_style))
                in_bullet_list = False

            # 2. Check for bullet list items
            elif line_str.startswith("- ") or line_str.startswith("* "):
                bullet_content = parse_markdown_to_html(line_str[2:])
                flowables.append(Paragraph(f"&bull; {bullet_content}", bullet_style))
                in_bullet_list = True

            # 3. Standard paragraphs
            else:
                body_content = parse_markdown_to_html(line_str)
                # If we were in a bullet list but this line has no prefix, keep indenting or treat as body
                if in_bullet_list:
                    flowables.append(Paragraph(body_content, bullet_style))
                else:
                    flowables.append(Paragraph(body_content, body_style))

        # Build Document
        doc.build(flowables, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
        logger.info(f"PDF successfully written to: {output_path}")
