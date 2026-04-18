"""
Pydantic models for request / response validation.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class HistoryMessage(BaseModel):
    """A single turn in the conversation history."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="The message text")


# ---------------------------------------------------------------------------
# /analyze-chat
# ---------------------------------------------------------------------------

class ChatAnalysisRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    user_info: Optional[str] = Field(
        default="",
        description="User demographics/meta (age, gender, marital status, etc.)",
    )
    message: str = Field(..., description="Current message from the user")
    history: Optional[List[HistoryMessage]] = Field(
        default=[],
        description="Last 5–10 messages of the conversation (role + content)",
    )
    memory_summary: Optional[str] = Field(
        default="",
        description="Long-term memory summary for this user",
    )


class ChatAnalysisResponse(BaseModel):
    user_id: str
    emotions: List[str] = Field(
        ...,
        description="Detected emotions, e.g. ['fear', 'anxiety']",
    )
    risk: str = Field(
        ...,
        description="Risk level: low | medium | high | critical",
    )
    stress_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Stress score from 0 to 100",
    )
    response: str = Field(
        ...,
        description="Empathetic, actionable response to the user",
    )
    should_alert: bool = Field(
        ...,
        description="True if the situation requires an emergency alert",
    )


# ---------------------------------------------------------------------------
# /daily-summary
# ---------------------------------------------------------------------------

class DailyMessage(BaseModel):
    """A single analysed message record for the daily-summary endpoint."""
    role: str = Field(default="user", description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")
    timestamp: Optional[str] = Field(
        default=None,
        description="ISO-8601 timestamp (optional)",
    )


class DailySummaryRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    messages: List[DailyMessage] = Field(
        ...,
        description="All user messages recorded for the day",
    )


class DailySummaryResponse(BaseModel):
    user_id: str
    summary: str = Field(
        ...,
        description="Narrative summary of the day's emotional state",
    )
    dominant_emotion: str = Field(
        ...,
        description="The most frequently detected emotion of the day",
    )
    avg_stress: int = Field(
        ...,
        ge=0,
        le=100,
        description="Average stress score across all messages",
    )
    risk_trend: str = Field(
        ...,
        description="Overall risk trend: stable | increasing | decreasing | volatile",
    )
# ---------------------------------------------------------------------------
# /i-need-help (Help Beacon)
# ---------------------------------------------------------------------------

class HelpBeaconRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    summary_0_7_days: str = Field(..., description="Summary of the last 0–7 days of chat")


class HelpBeaconResponse(BaseModel):
    user_id: str
    message: str = Field(..., description="A 2-4 line summary message for friends/family")
