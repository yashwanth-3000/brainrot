from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ArticleSection(BaseModel):
    section_id: str
    heading: str
    heading_level: int
    position: int
    section_summary: str
    facts: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    source_span: dict[str, int] = Field(default_factory=dict)
    priority_score: float = 0.0
    raw_markdown: str


class SectionCluster(BaseModel):
    cluster_id: str
    position: int
    section_ids: list[str] = Field(default_factory=list)
    headings: list[str] = Field(default_factory=list)
    section_summary: str
    facts: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    source_span: dict[str, int] = Field(default_factory=dict)
    priority_score: float = 0.0
    raw_markdown: str


class CoverageSlotPlan(BaseModel):
    slot_index: int
    slot_id: str
    angle_family: str
    semantic_objective: str
    hook_direction: str
    audience_frame: str
    visual_mood: str
    music_mood: str
    cluster: SectionCluster
    anchor_fact: str = ""
    forbidden_overlap_section_ids: list[str] = Field(default_factory=list)
    forbidden_overlap_facts: list[str] = Field(default_factory=list)


class CoveragePlan(BaseModel):
    requested_count: int
    planned_count: int
    actual_count: int
    section_count: int
    sections: list[ArticleSection] = Field(default_factory=list)
    slots: list[CoverageSlotPlan] = Field(default_factory=list)
    fallback_flags: list[str] = Field(default_factory=list)


class CrewAIScriptPayload(BaseModel):
    title: str
    hook: str
    narration_text: str
    caption_text: str
    visual_beats: list[str] = Field(default_factory=list)
    music_tags: list[str] = Field(default_factory=list)
    gameplay_tags: list[str] = Field(default_factory=list)
    source_facts_used: list[str] = Field(default_factory=list)
    qa_notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CoverageValidationIssue(BaseModel):
    slot_index: int
    slot_id: str
    section_id: str | None = None
    angle_family: str | None = None
    problems: list[str] = Field(default_factory=list)

