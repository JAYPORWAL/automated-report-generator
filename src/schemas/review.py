from pydantic import BaseModel, Field, field_validator


class ReviewResult(BaseModel):
    quality_score: int = Field(..., description="Quality score of the report out of 100")
    issues_found: list[str] = Field(
        default_factory=list, description="Issues found in the draft report"
    )
    improvements_made: list[str] = Field(
        default_factory=list, description="List of improvements implemented in the reviewed version"
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Suggestions for future research or report expansions"
    )
    improved_report: str = Field(..., description="The finalized, improved markdown report content")

    @field_validator("quality_score")
    @classmethod
    def validate_score(cls, v: int) -> int:
        if v < 0 or v > 100:
            raise ValueError("Quality score must be between 0 and 100 inclusive.")
        return v
