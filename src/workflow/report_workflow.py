import time
from typing import Any, Generator

from src.agents.research_agent import ResearchAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.slide_agent import SlideAgent
from src.agents.writer_agent import WriterAgent
from src.services.export_service import ExportService
from src.services.gemini_service import GeminiService
from src.services.pdf_service import PDFService
from src.services.report_service import ReportService
from src.services.research_service import ResearchService
from src.services.review_service import ReviewService
from src.services.slide_service import SlideService
from src.utils.logger import logger
from src.utils.validators import validate_api_keys, validate_topic


class ReportWorkflow:
    """Coordinates the execution of all agents in the automated report pipeline."""

    def __init__(self, gemini_api_key: str | None = None, tavily_api_key: str | None = None):
        # 1. Initialize core services
        self.gemini_service = GeminiService(api_key=gemini_api_key)
        self.research_service = ResearchService(tavily_api_key=tavily_api_key)

        self.report_service = ReportService(gemini_service=self.gemini_service)
        self.review_service = ReviewService(gemini_service=self.gemini_service)

        self.pdf_service = PDFService()
        self.slide_service = SlideService(gemini_service=self.gemini_service)
        self.export_service = ExportService(
            pdf_service=self.pdf_service, slide_service=self.slide_service
        )

        # 2. Initialize agents
        self.research_agent = ResearchAgent(research_service=self.research_service)
        self.writer_agent = WriterAgent(report_service=self.report_service)
        self.reviewer_agent = ReviewerAgent(review_service=self.review_service)
        self.slide_agent = SlideAgent(slide_service=self.slide_service)

    def execute(
        self,
        topic: str,
        tone: str = "Professional",
        length: str = "Medium",
        slide_count: int = 8,
        enable_research: bool = True,
        user_context: str = "",
        target_audience: str = "",
        report_requirements: str = "",
        model_selection: str = "gemini-2.5-flash",
    ) -> Generator[dict[str, Any], None, None]:
        """
        Executes the entire multi-agent report pipeline step-by-step.
        Yields status messages to update UI progress bars, followed by final results.
        """
        # Validate inputs
        topic = validate_topic(topic)
        validate_api_keys(self.gemini_service.api_key)

        logger.info(f"Starting ReportWorkflow for topic: '{topic}'")
        start_time = time.time()

        # Step 1: Researching
        yield {"step": "research", "message": "Agent 1: Researching topic using web search..."}
        research_notes = None
        if enable_research:
            try:
                research_notes = self.research_agent.run(topic)
                logger.info(f"Research phase done: {len(research_notes.items)} items gathered.")
            except Exception as e:
                logger.error(f"Research agent failed: {e}. Proceeding with fallback.")
                research_notes = self.research_agent.run(topic)
        else:
            logger.info("Research is disabled. Skipping web search step.")

        # Step 2: Writing Report
        yield {"step": "writing", "message": "Agent 2: Writing initial report draft..."}

        # Always use gemini-2.5-flash for faster drafting
        draft = self.writer_agent.run(
            topic=topic,
            research_notes=research_notes,
            tone=tone,
            length=length,
            user_context=user_context,
            audience=target_audience,
            requirements=report_requirements,
            model="gemini-2.5-flash",
        )

        # Step 3: Reviewing & Editing
        yield {
            "step": "reviewing",
            "message": "Agent 3: Reviewing draft report and editing for quality...",
        }

        # Decide which model to use for review
        # If the user selected Pro, use Pro to increase quality, else Flash
        review_model = (
            "gemini-2.5-pro" if model_selection == "gemini-2.5-pro" else "gemini-2.5-flash"
        )

        review_result = self.reviewer_agent.run(
            draft=draft, research_notes=research_notes, model=review_model
        )

        # Step 4: Generating Presentation
        yield {
            "step": "presentation",
            "message": "Agent 4: Generating professional slide deck presentation...",
        }

        # Use gemini-2.5-flash for faster slides summarization
        presentation = self.slide_agent.run(
            report_markdown=review_result.improved_report,
            slide_count=slide_count,
            model="gemini-2.5-flash",
        )

        # Step 5: Preparing Files for Export
        yield {"step": "export", "message": "Preparing export files (PDF, PPTX, MD, TXT, JSON)..."}

        # Format research notes markdown for export preview/download
        notes_md = f"# Research Notes: {topic}\n\n"
        notes_md += (
            f"**Summary**: {research_notes.summary if research_notes else 'Research disabled.'}\n\n"
        )
        if research_notes and research_notes.items:
            notes_md += "## Sources and Collected Facts\n\n"
            for item in research_notes.items:
                notes_md += f"- **[Score: {item.score}]** {item.fact}\n"
                notes_md += f"  *Source*: [{item.source_url}]({item.source_url}) (Date: {item.publication_date})\n\n"
        else:
            notes_md += "No external research findings were gathered."

        # Compile review details
        review_summary = {
            "quality_score": review_result.quality_score,
            "issues_found": review_result.issues_found,
            "improvements_made": review_result.improvements_made,
            "suggestions": review_result.suggestions,
        }

        # Prepare exports
        export_paths = self.export_service.prepare_exports(
            topic=topic,
            research_notes_md=notes_md,
            final_report_md=review_result.improved_report,
            review_summary_json=review_summary,
            presentation_content=presentation,
        )

        duration = time.time() - start_time
        logger.info(f"ReportWorkflow completed successfully in {duration:.2f} seconds.")

        # Yield final payload
        yield {
            "step": "complete",
            "message": "Workflow Completed!",
            "results": {
                "research_notes_md": notes_md,
                "draft_report": draft.to_markdown(),
                "final_report": review_result.improved_report,
                "review_summary": review_summary,
                "presentation": presentation,
                "export_paths": export_paths,
            },
        }
