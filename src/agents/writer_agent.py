from src.schemas.report import ReportDraft
from src.schemas.research import ResearchNotes
from src.services.report_service import ReportService
from src.utils.logger import logger


class WriterAgent:
    """Agent responsible for writing the initial draft of the report."""

    def __init__(self, report_service: ReportService):
        self.report_service = report_service

    def run(
        self,
        topic: str,
        research_notes: ResearchNotes | None,
        tone: str = "Professional",
        length: str = "Medium",
        user_context: str = "",
        audience: str = "",
        requirements: str = "",
        model: str | None = None,
    ) -> ReportDraft:
        """Invokes the report service to generate a structured draft of the report."""
        logger.info(f"Writer Agent running report draft for topic: {topic}")
        return self.report_service.draft_report(
            topic=topic,
            research_notes=research_notes,
            tone=tone,
            length=length,
            user_context=user_context,
            audience=audience,
            requirements=requirements,
            model=model,
        )
