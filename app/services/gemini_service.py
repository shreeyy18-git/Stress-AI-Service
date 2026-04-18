"""
Gemini AI service layer.

Both functions return Pydantic response objects; all error handling and JSON
parsing is done here so routes stay thin.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.models.schemas import (
    ChatAnalysisRequest,
    ChatAnalysisResponse,
    DailySummaryRequest,
    DailySummaryResponse,
    HelpBeaconRequest,
    HelpBeaconResponse,
)
from app.utils.prompts import (
    CHAT_ANALYSIS_SYSTEM_PROMPT,
    CHAT_ANALYSIS_USER_TEMPLATE,
    DAILY_SUMMARY_SYSTEM_PROMPT,
    DAILY_SUMMARY_USER_TEMPLATE,
    HELP_BEACON_SYSTEM_PROMPT,
    HELP_BEACON_USER_TEMPLATE,
)

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client  (module-level singleton)
# ---------------------------------------------------------------------------

_API_KEY = os.getenv("GEMINI_API_KEY", "")
_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

if not _API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY is not set. Please add it to your .env file."
    )

_client = genai.Client(api_key=_API_KEY)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_json(raw: str) -> Dict[str, Any]:
    """
    Robustly parse a JSON object from the model output.
    Handles the case where the model wraps its answer in markdown code fences.
    """
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    # Find the first { ... } block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model response:\n{raw}")
    return json.loads(match.group())


def _format_history(history) -> str:
    """Turn a list of HistoryMessage objects into a readable string."""
    if not history:
        return "No previous conversation."
    lines = []
    for msg in history:
        label = "User" if msg.role.lower() == "user" else "Assistant"
        lines.append(f"{label}: {msg.content}")
    return "\n".join(lines)


async def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    """
    Single entry-point to call the Gemini API asynchronously.
    Uses a system instruction + user content pattern.
    """
    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.4,          # low temp → consistent, reliable JSON
            max_output_tokens=1024,
        ),
    )
    return response.text


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

from langchain_core.messages import HumanMessage, AIMessage
from app.services.graph_service import agent_app

async def analyze_message(request: ChatAnalysisRequest) -> ChatAnalysisResponse:
    """
    Analyze a message using LangGraph for stateful short-term memory.
    thread_id = user_id ensures continuity for the same user.
    """
    config = {"configurable": {"thread_id": request.user_id}}
    
    # Check current state to see if we need to seed history
    state = await agent_app.aget_state(config)
    
    # If state is empty and user provided history, seed it
    if not state.values and request.history:
        seed_messages = []
        for msg in request.history:
            if msg.role.lower() == "user":
                seed_messages.append(HumanMessage(content=msg.content))
            else:
                seed_messages.append(AIMessage(content=msg.content))
        
        # Initialize the state with the provided history
        await agent_app.aupdate_state(config, {"messages": seed_messages})
        logger.info("Seeded LangGraph state with provided history for thread: %s", request.user_id)

    # Prepare input for the graph (just the NEW message)
    input_data = {
        "messages": [HumanMessage(content=request.message)],
        "user_info": request.user_info or "Not provided",
        "memory_summary": request.memory_summary or "No background available."
    }
    
    # Run the graph (this will append the new message and call the agent)
    result = await agent_app.ainvoke(input_data, config=config)
    
    # The last message is the Assistant's response (JSON string)
    raw = result["messages"][-1].content
    logger.debug("Raw Graph response: %s", raw)

    try:
        data = _extract_json(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.error("Failed to parse AI JSON: %s | Raw: %s", exc, raw)
        raise ValueError(f"AI returned malformed JSON. Detail: {exc}") from exc

    # Normalise + validate
    emotions = data.get("emotions", [])
    if isinstance(emotions, str):
        emotions = [emotions]

    return ChatAnalysisResponse(
        user_id=request.user_id,
        emotions=emotions,
        risk=data.get("risk", "low"),
        stress_score=int(data.get("stress_score", 0)),
        response=data.get("response", ""),
        should_alert=bool(data.get("should_alert", False)),
    )


async def generate_daily_summary(request: DailySummaryRequest) -> DailySummaryResponse:
    """
    Produce a daily wellbeing summary for all of a user's messages today.

    Steps:
      1. Format all messages into the prompt.
      2. Call Gemini (ONE call).
      3. Parse JSON and return a DailySummaryResponse.
    """
    if not request.messages:
        return DailySummaryResponse(
            user_id=request.user_id,
            summary="No messages were recorded for today.",
            dominant_emotion="none",
            avg_stress=0,
            risk_trend="stable",
        )

    # Build a readable transcript
    lines = []
    for i, msg in enumerate(request.messages, start=1):
        ts = f" [{msg.timestamp}]" if msg.timestamp else ""
        label = "User" if msg.role.lower() == "user" else "Assistant"
        lines.append(f"{i}. {label}{ts}: {msg.content}")
    messages_text = "\n".join(lines)

    user_prompt = DAILY_SUMMARY_USER_TEMPLATE.format(
        user_id=request.user_id,
        messages=messages_text,
    )

    raw = await _call_gemini(DAILY_SUMMARY_SYSTEM_PROMPT, user_prompt)
    logger.debug("Raw Gemini response (daily-summary): %s", raw)

    try:
        data = _extract_json(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.error("Failed to parse Gemini JSON: %s | Raw: %s", exc, raw)
        raise ValueError(f"Gemini returned malformed JSON. Detail: {exc}") from exc

    return DailySummaryResponse(
        user_id=request.user_id,
        summary=data.get("summary", ""),
        dominant_emotion=data.get("dominant_emotion", "unknown"),
        avg_stress=int(data.get("avg_stress", 0)),
        risk_trend=data.get("risk_trend", "stable"),
    )


async def generate_help_beacon(request: HelpBeaconRequest) -> HelpBeaconResponse:
    """
    Generate a 2-4 line message for the user's support system based on a 7-day summary.
    """
    if not request.summary_0_7_days:
        return HelpBeaconResponse(
            user_id=request.user_id,
            message="No recent summary available to generate a medical beacon."
        )

    user_prompt = HELP_BEACON_USER_TEMPLATE.format(
        summary=request.summary_0_7_days
    )

    raw = await _call_gemini(HELP_BEACON_SYSTEM_PROMPT, user_prompt)
    logger.debug("Raw Gemini response (help-beacon): %s", raw)

    try:
        data = _extract_json(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.error("Failed to parse Gemini JSON: %s | Raw: %s", exc, raw)
        raise ValueError(f"Gemini returned malformed JSON. Detail: {exc}") from exc

    return HelpBeaconResponse(
        user_id=request.user_id,
        message=data.get("message", "The user has been going through a challenging period and could use some support right now.")
    )
