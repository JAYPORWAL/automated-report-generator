import os
import tempfile
from unittest.mock import MagicMock

from src.services.export_service import ExportService
from src.services.slide_service import PresentationContent


def test_prepare_exports():
    mock_pdf = MagicMock()
    mock_slide = MagicMock()
    mock_slide.generate_speaker_notes_text.return_value = "Notes content"

    service = ExportService(pdf_service=mock_pdf, slide_service=mock_slide)

    presentation = PresentationContent(title="Title", subtitle="Subtitle", agenda=[], slides=[])

    with tempfile.TemporaryDirectory() as tmpdir:
        # Override temp_dir configured value
        from src.config import settings

        original_temp = settings.temp_dir
        settings.temp_dir = tmpdir

        try:
            paths = service.prepare_exports(
                topic="Test Topic",
                research_notes_md="# Notes",
                final_report_md="# Final Report",
                review_summary_json={"score": 100},
                presentation_content=presentation,
            )

            assert "notes_md" in paths
            assert "report_md" in paths
            assert "report_txt" in paths
            assert "report_pdf" in paths
            assert "presentation_pptx" in paths
            assert "speaker_notes_md" in paths
            assert "review_json" in paths

            for key, path in paths.items():
                # For pdf and pptx, the files are created by the mocked service methods,
                # which won't create files unless mocked to do so. But notes_md, report_md,
                # report_txt, speaker_notes_md, review_json are written directly by ExportService!
                if "pdf" not in key and "pptx" not in key:
                    assert os.path.exists(path)
                    assert os.path.getsize(path) > 0

        finally:
            settings.temp_dir = original_temp
