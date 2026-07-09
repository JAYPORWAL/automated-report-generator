from pydantic import BaseModel, Field, field_validator

from src.utils.validators import validate_url


class ResearchItem(BaseModel):
    fact: str = Field(..., description="A key fact, statistic, or finding from the source")
    source_url: str = Field(..., description="The URL of the research source")
    publication_date: str | None = Field(
        default="Unknown", description="Publication date of the content"
    )
    score: int = Field(default=1, description="Deterministic reliability score of the source (1-5)")

    @field_validator("source_url")
    @classmethod
    def check_url(cls, v: str) -> str:
        # Check if URL is formatted properly, or fallback/sanitize
        if not validate_url(v):
            return "https://unknown.source"
        return v


class ResearchNotes(BaseModel):
    topic: str = Field(..., description="The main topic of research")
    summary: str = Field(..., description="Brief overview of research findings")
    items: list[ResearchItem] = Field(
        default_factory=list, description="List of validated research items"
    )
