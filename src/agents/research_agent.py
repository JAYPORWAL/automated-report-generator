from src.schemas.research import ResearchNotes
from src.services.research_service import ResearchService
from src.utils.logger import logger


class ResearchAgent:
    """Agent responsible for researching the topic using web tools and structuring findings."""

    def __init__(self, research_service: ResearchService):
        self.research_service = research_service

    def run(self, topic: str) -> ResearchNotes:
        """Runs the research phase, deduplicates findings, and handles fallbacks gracefully."""
        logger.info(f"Research Agent starting research on topic: {topic}")

        try:
            # 1. Search the web
            raw_results = self.research_service.search(topic)

            # 2. Process and deduplicate
            if raw_results:
                research_notes = self.research_service.collect_and_deduplicate(topic, raw_results)
                return research_notes

        except Exception as e:
            logger.error(f"Research Agent encountered an error: {e}")

        # 3. Fallback if search failed or returned empty
        logger.warning("Research Agent returning empty research notes fallback.")
        return ResearchNotes(
            topic=topic,
            summary="Web research was attempted but yielded no search results or external keys were missing.",
            items=[],
        )
