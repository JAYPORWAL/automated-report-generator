from pydantic import BaseModel, Field


class ReportDraft(BaseModel):
    title: str = Field(..., description="The title of the report")
    executive_summary: str = Field(..., description="A high-level executive summary of the report")
    introduction: str = Field(..., description="Introduction and context of the topic")
    key_findings: str = Field(..., description="Main key findings or observations")
    detailed_analysis: str = Field(..., description="Deep-dive analysis of the topic")
    challenges_risks: str = Field(..., description="Identified challenges, risks, or gaps")
    recommendations: str = Field(..., description="Actionable recommendations")
    conclusion: str = Field(..., description="Concluding remarks")
    references: list[str] = Field(
        default_factory=list, description="List of source URLs and citation details"
    )

    def to_markdown(self) -> str:
        """Converts the structured draft into a professionally formatted Markdown document."""
        ref_section = (
            "\n".join([f"- {ref}" for ref in self.references]) if self.references else "None"
        )

        return f"""# {self.title}

## Executive Summary
{self.executive_summary}

## Introduction
{self.introduction}

## Key Findings
{self.key_findings}

## Detailed Analysis
{self.detailed_analysis}

## Challenges / Risks
{self.challenges_risks}

## Recommendations
{self.recommendations}

## Conclusion
{self.conclusion}

## References
{ref_section}
"""
