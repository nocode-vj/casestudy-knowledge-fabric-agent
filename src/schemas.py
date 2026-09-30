"""Strict Pydantic Input and Output JSON Schemas for Tools and Agent Handoffs."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class KnowledgeGraphQueryInput(BaseModel):
    """Strict input schema for querying the Spanner Graph Knowledge Fabric."""

    component_name: str = Field(
        ...,
        min_length=2,
        description="Exact or partial name of the legacy component (e.g., 'AxisControlPanel').",
    )
    search_mode: Literal["HYBRID_GQL_ANN", "GQL_ONLY", "SEMANTIC_ANN_ONLY"] = Field(
        default="HYBRID_GQL_ANN",
        description="Retrieval strategy combining Graph Query Language (GQL), ANN vectors, and keyword search.",
    )
    max_hops: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum dependency traversal hops in Spanner Graph.",
    )


class CodeDependencyNode(BaseModel):
    """Represents a single code or requirement node in the Spanner Knowledge Graph."""

    node_id: str = Field(..., description="Unique Spanner Graph vertex identifier.")
    node_type: Literal["CLASS", "FUNCTION", "MODULE", "DESIGN_DOC", "JIRA_TICKET"]
    name: str = Field(..., description="Identifier of the function, class, or requirement doc.")
    file_path: str = Field(..., description="Repository path or document URI.")
    linked_requirement_id: Optional[str] = Field(
        default=None, description="ID of the 10+ year legacy functional spec linked in the graph."
    )
    similarity_score: float = Field(..., ge=0.0, le=1.0)


class KnowledgeGraphQueryOutput(BaseModel):
    """Validated output schema returned by the Knowledge Fabric graph search tool."""

    status: Literal["SUCCESS", "RECOVERABLE_ERROR"]
    target_component: str
    gql_executed: str
    dependencies: List[CodeDependencyNode] = Field(default_factory=list)
    recovery_suggestion: Optional[str] = Field(
        default=None,
        description="Actionable recovery guidance for the LLM if status is RECOVERABLE_ERROR.",
    )


class UserStoryItem(BaseModel):
    """Schema for an agile user story linked to legacy industrial system contexts."""

    story_id: str
    title: str
    as_a: str
    i_want: str
    so_that: str
    acceptance_criteria: List[str]
    linked_graph_nodes: List[str]


class ArchitectureImpactReport(BaseModel):
    """Schema for the Architecture Impact Agent's blast-radius analysis."""

    component_under_change: str
    affected_functions: List[str]
    compliance_risks: List[str]
    estimated_blast_radius: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    requires_hitl_signoff: bool = True


class ModernizationTask(BaseModel):
    """Schema for an atomic refactoring task produced by the Task Breakdown Agent."""

    task_id: str
    title: str
    target_file: str
    context_summary: str
    verification_steps: List[str]
