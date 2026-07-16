import json
import os
import shutil

from src.config import settings
from src.services.pdf_service import PDFService
from src.services.slide_service import PresentationContent, SlideService
from src.utils.logger import logger
from src.utils.validators import sanitize_filename


class ExportError(Exception):
    """Custom exception raised when file exporting fails."""

    pass


class ExportService:
    """Service to export generated assets (reports, slides, notes) to files."""

    def __init__(self, pdf_service: PDFService, slide_service: SlideService):
        self.pdf_service = pdf_service
        self.slide_service = slide_service

    def prepare_exports(
        self,
        topic: str,
        research_notes_md: str,
        final_report_md: str,
        review_summary_json: dict,
        presentation_content: PresentationContent,
    ) -> dict[str, str]:
        """
        Creates exportable files in the temp directory and returns a dictionary
        mapping file format (keys) to their absolute filesystem paths.
        Raises ExportError if any generation step fails.
        """
        sanitized = sanitize_filename(topic).replace(" ", "_").lower()
        if not sanitized:
            sanitized = "report"

        temp_dir = settings.temp_dir
        os.makedirs(temp_dir, exist_ok=True)

        export_paths = {}

        # 1. Export Research Notes (Markdown)
        notes_path = os.path.join(temp_dir, f"{sanitized}_research_notes.md")
        try:
            with open(notes_path, "w", encoding="utf-8") as f:
                f.write(research_notes_md)
            export_paths["notes_md"] = os.path.abspath(notes_path)
        except Exception as e:
            logger.error(f"Failed to export research notes: {e}")
            raise ExportError(f"Failed to generate research notes file: {e}") from e

        # 2. Export Final Report (Markdown)
        report_md_path = os.path.join(temp_dir, f"{sanitized}_final_report.md")
        try:
            with open(report_md_path, "w", encoding="utf-8") as f:
                f.write(final_report_md)
            export_paths["report_md"] = os.path.abspath(report_md_path)
        except Exception as e:
            logger.error(f"Failed to export report markdown: {e}")
            raise ExportError(f"Failed to generate report markdown file: {e}") from e

        # 3. Export Final Report (TXT)
        report_txt_path = os.path.join(temp_dir, f"{sanitized}_final_report.txt")
        try:
            # Simple conversion: strip heading markdown characters or keep plain text format
            plain_text = final_report_md.replace("# ", "").replace("## ", "").replace("### ", "")
            with open(report_txt_path, "w", encoding="utf-8") as f:
                f.write(plain_text)
            export_paths["report_txt"] = os.path.abspath(report_txt_path)
        except Exception as e:
            logger.error(f"Failed to export report text: {e}")
            raise ExportError(f"Failed to generate report text file: {e}") from e

        # 4. Export Final Report (PDF)
        pdf_path = os.path.join(temp_dir, f"{sanitized}_final_report.pdf")
        try:
            self.pdf_service.generate_pdf(final_report_md, pdf_path)
            export_paths["report_pdf"] = os.path.abspath(pdf_path)
        except Exception as e:
            logger.error(f"Failed to export report PDF: {e}")
            raise ExportError(f"Failed to generate report PDF: {e}") from e

        # 5. Export Presentation (PPTX)
        pptx_path = os.path.join(temp_dir, f"{sanitized}_presentation.pptx")
        try:
            self.slide_service.build_pptx(presentation_content, pptx_path)
            export_paths["presentation_pptx"] = os.path.abspath(pptx_path)
        except Exception as e:
            logger.error(f"Failed to export presentation PPTX: {e}")
            raise ExportError(f"Failed to generate presentation PPTX: {e}") from e

        # 6. Export Presentation Notes (Markdown)
        notes_txt_path = os.path.join(temp_dir, f"{sanitized}_speaker_notes.md")
        try:
            notes_str = self.slide_service.generate_speaker_notes_text(presentation_content)
            with open(notes_txt_path, "w", encoding="utf-8") as f:
                f.write(notes_str)
            export_paths["speaker_notes_md"] = os.path.abspath(notes_txt_path)
        except Exception as e:
            logger.error(f"Failed to export speaker notes text: {e}")
            raise ExportError(f"Failed to generate speaker notes: {e}") from e

        # 7. Export Review Summary (JSON)
        review_path = os.path.join(temp_dir, f"{sanitized}_review_summary.json")
        try:
            with open(review_path, "w", encoding="utf-8") as f:
                json.dump(review_summary_json, f, indent=2)
            export_paths["review_json"] = os.path.abspath(review_path)
        except Exception as e:
            logger.error(f"Failed to export review JSON: {e}")
            raise ExportError(f"Failed to generate review feedback JSON: {e}") from e

        return export_paths

    def cleanup_exports(self) -> None:
        """Deletes all files in the temp_dir to prevent temporary file leakage."""
        temp_dir = settings.temp_dir
        if os.path.exists(temp_dir):
            logger.info(f"Initiating cleanup of temporary export directory: {temp_dir}")
            for file_name in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file_name)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logger.error(f"Failed to clean up path {file_path}: {e}")
