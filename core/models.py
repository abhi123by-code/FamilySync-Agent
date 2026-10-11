from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FamilyMember(BaseModel):
    name: str
    role: str = "member"
    preferences: dict[str, float] = Field(default_factory=dict)
    availability: list[str] = Field(default_factory=list)


class Event(BaseModel):
    id: str
    title: str
    member: str
    start: str
    end: str
    category: str = "personal"
    location: str = ""
    notes: str = ""

    @field_validator("start", "end")
    @classmethod
    def validate_iso_datetime(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Invalid datetime: {value}") from exc
        return value


class Task(BaseModel):
    id: str
    title: str
    owner: str
    start: str
    end: str
    priority: Literal["low", "medium", "high"] = "medium"
    completed: bool = False
    category: str = "household"
    description: str = ""

    @field_validator("start", "end")
    @classmethod
    def validate_iso_datetime(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Invalid datetime: {value}") from exc
        return value


class Conflict(BaseModel):
    event_id: str
    title: str
    member: str
    other_event_id: str | None = None
    other_title: str | None = None
    start: str
    end: str
    description: str


class CandidateResolution(BaseModel):
    member: str
    score: float
    reason: str


class CoordinationResult(BaseModel):
    request: str
    detected_conflicts: list[Conflict] = Field(default_factory=list)
    candidate_members: list[str] = Field(default_factory=list)
    recommendation: str = ""
    explanation: str = ""
    status: str = "pending"
    decision_log: list[str] = Field(default_factory=list)
