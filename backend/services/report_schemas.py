"""
Pydantic schemas for structured report generation
Ensures consistent, validated output from LLM
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ReportSection(BaseModel):
    """Individual section of the evaluation report"""
    title: str = Field(..., description="Section title (e.g., 'Introduction', 'Investigation Summary')")
    content: str = Field(..., description="Section content in plain text, no markdown, no placeholders")


class EvaluationReport(BaseModel):
    """Structured evaluation report schema"""
    introduction: str = Field(
        ..., 
        description="Brief greeting and context. Plain text, no markdown, no placeholders like [Your Name] or [Bank Name]"
    )
    investigation_summary: str = Field(
        ..., 
        description="What was investigated. Plain text, no markdown, no placeholders"
    )
    findings_overview: str = Field(
        ..., 
        description="Key findings from the investigation. Plain text, no markdown, no placeholders"
    )
    resolution_explanation: str = Field(
        ..., 
        description="Why this decision was made. Plain text, no markdown, no placeholders"
    )
    conclusion: str = Field(
        ..., 
        description="Closing statement. Plain text, no markdown, no placeholders"
    )


class NextSteps(BaseModel):
    """Structured next steps guidance"""
    immediate_actions: List[str] = Field(
        ..., 
        description="Immediate actions the customer should take (if any)"
    )
    required_documents: Optional[List[str]] = Field(
        default=None,
        description="Documents or information they may need to provide"
    )
    timeline: Optional[str] = Field(
        default=None,
        description="Timeline expectations"
    )
    contact_info: Optional[str] = Field(
        default=None,
        description="Contact information for questions"
    )
    what_happens_next: Optional[str] = Field(
        default=None,
        description="What happens next in the process"
    )

