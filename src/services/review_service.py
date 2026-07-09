from src.constants import SYSTEM_PROMPTS
from src.schemas.report import ReportDraft
from src.schemas.research import ResearchNotes
from src.schemas.review import ReviewResult
from src.services.gemini_service import GeminiService
from src.utils.logger import logger


class ReviewService:
    """Service to review, edit, and improve generated reports using Gemini."""

    def __init__(self, gemini_service: GeminiService):
        self.gemini_service = gemini_service

    def review_report(
        self, draft: ReportDraft, research_notes: ResearchNotes | None, model: str | None = None
    ) -> ReviewResult:
        """
        Reviews a draft report against research notes, producing a ReviewResult
        including score, issues, improvements, and the final corrected report markdown.
        """
        logger.info("Reviewing and editing the report...")

        # format context
        draft_md = draft.to_markdown()
        notes_summary = (
            research_notes.summary
            if research_notes
            else "No live research conducted; relied on user context."
        )

        prompt = (
            f"Please review the following draft report:\n\n"
            f"--- DRAFT REPORT ---\n{draft_md}\n\n"
            f"--- RESEARCH NOTES BACKGROUND ---\n{notes_summary}\n\n"
            "Compare the draft with the notes, checking for factual alignment, "
            "missing references, professional tone, structural clarity, grammar, and reduntant statements. "
            "Return the ReviewResult schema including a quality score (0 to 100) and the fully edited, "
            "complete improved markdown report in 'improved_report'."
        )

        system_instruction = SYSTEM_PROMPTS["reviewer"]

        # Call structured generation (with optionally Pro model if selected)
        review_result = self.gemini_service.generate_structured(
            prompt=prompt,
            response_schema=ReviewResult,
            system_instruction=system_instruction,
            model=model,
            temperature=0.2,
        )

        logger.info(f"Report review completed. Quality Score: {review_result.quality_score}/100")
        return review_result
