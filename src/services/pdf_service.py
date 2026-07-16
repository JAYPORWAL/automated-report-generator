import re

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.constants import PDF_STYLING
from src.utils.logger import logger


def remove_emojis_and_unsupported_chars(text: str) -> str:
    """
    Strips emoji characters and Unicode code points that standard ReportLab
    built-in fonts (like Helvetica) cannot render, which would otherwise
    cause generation crashes or visual bugs.
    """
    if not text:
        return ""
    cleaned = []
    for char in text:
        cp = ord(char)
        # Filter out non-BMP characters (which include all standard emojis)
        # and standard Miscellaneous Symbols (0x2600-0x26FF) / Dingbats (0x2700-0x27BF)
        if cp > 0xFFFF or (0x2600 <= cp <= 0x26FF) or (0x2700 <= cp <= 0x27BF):
            continue
        cleaned.append(char)
    return "".join(cleaned)


def parse_markdown_to_html(text: str) -> str:
    """
    Translates simple markdown tags (**bold**, *italic*, links, inline code)
    into clean XML-compliant tags compatible with ReportLab Paragraph parser.
    Escapes raw XML entities first to prevent parsing exceptions.
    """
    if not text:
        return ""

    # 1. Strip emojis and non-supported characters
    cleaned_text = remove_emojis_and_unsupported_chars(text)

    # 2. Escape XML characters (order matters: & first, then < and >)
    escaped = cleaned_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # 3. Convert inline code `code` to monospaced font
    escaped = re.sub(r"`(.*?)`", r'<font face="Courier">\1</font>', escaped)

    # 4. Convert bold **text** to <b>text</b>
    escaped = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", escaped)

    # 5. Convert italic *text* to <i>text</i>
    escaped = re.sub(r"\*(.*?)\*", r"<i>\1</i>", escaped)

    # 6. Convert markdown links [text](url) to ReportLab <a> links
    escaped = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2" color="#3B82F6"><b>\1</b></a>', escaped)

    return escaped


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


def build_reportlab_table(rows: list[list[str]], col_width_total: float) -> Table:
    """
    Builds a styled ReportLab Table from markdown cells, wrapping all text
    inside Paragraph flowables to support auto-wrapping and avoid text overflow.
    """
    cell_style = ParagraphStyle(
        "TableCell",
        fontName=PDF_STYLING["font_body"],
        fontSize=9,
        leading=12,
        textColor=HexColor(PDF_STYLING["text_color"]),
    )
    header_style = ParagraphStyle(
        "TableHeader",
        fontName=PDF_STYLING["font_title"],
        fontSize=9,
        leading=12,
        textColor=colors.whitesmoke,
    )

    formatted_rows = []
    for r_idx, row in enumerate(rows):
        formatted_row = []
        for cell in row:
            cell_html = parse_markdown_to_html(cell)
            style = header_style if r_idx == 0 else cell_style
            formatted_row.append(Paragraph(cell_html, style))
        formatted_rows.append(formatted_row)

    # Distribute columns evenly
    num_cols = len(rows[0]) if rows else 1
    col_width = col_width_total / num_cols
    col_widths = [col_width] * num_cols

    t = Table(formatted_rows, colWidths=col_widths)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor(PDF_STYLING["primary_color"])),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#F8FAFC")]),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
            ]
        )
    )
    return t


class PDFService:
    """Service to convert markdown text into a styled PDF document using ReportLab."""

    def generate_pdf(self, markdown_text: str, output_path: str) -> None:
        """
        Parses Markdown text and outputs a beautifully formatted PDF.
        Robustly handles code blocks, tables, lists, and character encoding.
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

        code_block_style = ParagraphStyle(
            "PDFCodeBlock",
            parent=styles["Normal"],
            fontName="Courier",
            fontSize=9,
            leading=12,
            textColor=HexColor("#1E293B"),
            backColor=HexColor("#F1F5F9"),
            borderPadding=6,
            spaceAfter=8,
        )

        flowables = []
        lines = markdown_text.split("\n")

        in_bullet_list = False
        in_code_block = False
        in_table = False
        table_rows = []

        for line in lines:
            line_str = line.strip()

            # Handle code block tags
            if line_str.startswith("```"):
                # If we were building a table, clean it up before switching context
                if in_table and table_rows:
                    flowables.append(build_reportlab_table(table_rows, doc.width))
                    table_rows = []
                    in_table = False
                in_code_block = not in_code_block
                in_bullet_list = False
                continue

            if in_code_block:
                # Inside code blocks, escape HTML structures but preserve spaces
                code_line = parse_markdown_to_html(line)
                flowables.append(Paragraph(code_line, code_block_style))
                continue

            # Handle Markdown table parsing
            if line_str.startswith("|") and line_str.endswith("|"):
                in_bullet_list = False
                # Skip separator rows like |---|---|
                if re.match(r"^\|[\s\-\|:]+\|$", line_str):
                    continue
                cells = [c.strip() for c in line_str.split("|")[1:-1]]
                table_rows.append(cells)
                in_table = True
                continue
            elif in_table:
                # Table context ended, render table flowable
                if table_rows:
                    flowables.append(build_reportlab_table(table_rows, doc.width))
                    flowables.append(Spacer(1, 10))
                    table_rows = []
                in_table = False

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

        # Check for remaining unrendered table at end of markdown
        if in_table and table_rows:
            flowables.append(build_reportlab_table(table_rows, doc.width))

        # Build Document
        doc.build(flowables, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
        logger.info(f"PDF successfully written to: {output_path}")
