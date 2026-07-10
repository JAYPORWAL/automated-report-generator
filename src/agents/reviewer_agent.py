from src.schemas.report import ReportDraft
from src.schemas.research import ResearchNotes
from src.schemas.review import ReviewResult
from src.services.review_service import ReviewService
from src.utils.logger import logger


class ReviewerAgent:
    """Agent responsible for editing, correcting, scoring, and improving the report."""

    def __init__(self, review_service: ReviewService):
        self.review_service = review_service

    def run(
        self,
        draft: ReportDraft,
        research_notes: ResearchNotes | None,
        model: str | None = None,
        tone: str = "Professional",
    ) -> ReviewResult:
        """Invokes the review service to grade the report and compile the finalized version."""
        logger.info("Reviewer Agent running quality assurance check on the report.")
        return self.review_service.review_report(
            draft=draft, research_notes=research_notes, model=model, tone=tone
        )
