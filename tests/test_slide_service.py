import os
import tempfile
from unittest.mock import MagicMock

import pytest

from src.services.pdf_service import PDFService
from src.services.slide_service import PresentationContent, SlideContent, SlideService
from src.utils.file_utils import temporary_directory


def test_slide_content_pydantic():
    slide = SlideContent(
        title="Slide 1", bullets=["Point A", "Point B"], speaker_notes="Talk about A and B"
    )
    assert slide.title == "Slide 1"
    assert len(slide.bullets) == 2


def test_build_pptx_success():
    mock_gemini = MagicMock()
    service = SlideService(gemini_service=mock_gemini)

    content = PresentationContent(
        title="Test Presentation",
        subtitle="Audience - Date",
        agenda=["Intro", "Findings"],
        slides=[
            SlideContent(title="Intro", bullets=["bullet 1"], speaker_notes="Notes 1"),
            SlideContent(title="Findings", bullets=["bullet 2"], speaker_notes="Notes 2"),
        ],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        pptx_path = os.path.join(tmpdir, "test.pptx")

        # Build
        service.build_pptx(content, pptx_path)

        # Verify file exists and is not empty
        assert os.path.exists(pptx_path)
        assert os.path.getsize(pptx_path) > 0


def test_pdf_generation_success():
    pdf_service = PDFService()
    markdown_content = (
        "# Title\n\n## Section 1\n- Bullet A\n- Bullet B\n\nNormal paragraph text here."
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "report.pdf")
        pdf_service.generate_pdf(markdown_content, pdf_path)

        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 0


def test_pdf_generation_empty_markdown():
    pdf_service = PDFService()
    # Generation should not crash on empty input
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "empty.pdf")
        pdf_service.generate_pdf("", pdf_path)
        assert os.path.exists(pdf_path)


def test_cleanup_on_write_error():
    """Test that file cleanups handle writing failures gracefully."""
    # Try to write to a directory path instead of a file path (causes PermissionError or IsADirectoryError)
    pdf_service = PDFService()
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(OSError):
            pdf_service.generate_pdf("some text", tmpdir)


def test_temporary_directory_cleanup():
    path = None
    with temporary_directory() as temp_dir:
        path = temp_dir
        assert os.path.exists(path)
        # Write temporary file
        temp_file = os.path.join(temp_dir, "test.txt")
        with open(temp_file, "w") as f:
            f.write("hello")
        assert os.path.exists(temp_file)

    # Outside context manager, it should be deleted
    assert not os.path.exists(path)
