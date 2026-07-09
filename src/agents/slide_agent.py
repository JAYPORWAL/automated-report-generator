from src.services.slide_service import PresentationContent, SlideService
from src.utils.logger import logger


class SlideAgent:
    """Agent responsible for summarizing the report into structured presentation content."""

    def __init__(self, slide_service: SlideService):
        self.slide_service = slide_service

    def run(
        self, report_markdown: str, slide_count: int = 8, model: str | None = None
    ) -> PresentationContent:
        """Generates structured presentation content from the final report."""
        logger.info(
            f"Slide Agent generating presentation layout with target slide count: {slide_count}"
        )
        return self.slide_service.generate_presentation(
            report_markdown=report_markdown, slide_count=slide_count, model=model
        )
