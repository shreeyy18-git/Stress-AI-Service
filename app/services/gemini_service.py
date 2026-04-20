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


FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",       # Equivalent to Gemini 2 Flash
    "gemini-2.0-flash-lite",  # Equivalent to Gemini 2 Flash Lite
    "gemini-1.5-flash",       # Equivalent to Gemini 3 Flash because Gemini 3 does not yet exist in Google GenAI
    "gemini-1.5-flash-8b",    # Equivalent to Gemini 3.1 Flash Lite because Gemini 3 does not yet exist in Google GenAI 
]

async def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    """
    Single entry-point to call the Gemini API asynchronously with fallback models and fallback API keys.
    Uses a system instruction + user content pattern.
    """
    models_to_try = [_MODEL] + [m for m in FALLBACK_MODELS if m != _MODEL]
    
    api_keys = []
    for key_name in ["GEMINI_API_KEY", "GEMINI_API_KEY2", "GEMINI_API_KEY3"]:
        val = os.getenv(key_name)
        if val:
            api_keys.append(val)
            
    if not api_keys:
         raise EnvironmentError("No GEMINI_API_KEY environment variables found.")
    
    last_exception = None
    
    # Try each key, and for each key, try the fallback models if needed.
    for api_key in api_keys:
        # Re-initialize the client with the current key
        client = genai.Client(api_key=api_key)
        
        for model_name in models_to_try:
            try:
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.4,          # low temp → consistent, reliable JSON
                        max_output_tokens=1024,
                    ),
                )
                return response.text
            except Exception as e:
                logger.warning("Failed with key (ending '%s') and model %s: %s. Switching to fallback...", 
                               api_key[-4:] if len(api_key)>4 else '...', model_name, e)
                last_exception = e
            
    raise Exception(f"All API keys and fallback models failed. Last error: {last_exception}") from last_exception


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
    Produce a cumulative daily wellbeing summary with timestamped entries.

    Steps:
      1. Format old_summary (previous days) for context.
      2. Format today's messages into the prompt.
      3. Call Gemini (ONE call) to generate today's 100-200 word entry.
      4. Merge today's entry into the existing summary dict under request.date.
      5. Return sorted chronological DailySummaryResponse.
    """
    old_summary = request.old_summary or {}

    if not request.messages:
        # No messages today — preserve old + add empty entry for today
        updated_summary = dict(old_summary)
        updated_summary[request.date] = "No messages were recorded for today."
        updated_summary = dict(sorted(updated_summary.items()))
        return DailySummaryResponse(
            user_id=request.user_id,
            summary=updated_summary,
            dominant_emotion="none",
            avg_stress=0,
            risk_trend="stable",
        )

    # Build a readable transcript of today's messages
    lines = []
    for i, msg in enumerate(request.messages, start=1):
        ts = f" [{msg.timestamp}]" if msg.timestamp else ""
        label = "User" if msg.role.lower() == "user" else "Assistant"
        lines.append(f"{i}. {label}{ts}: {msg.content}")
    messages_text = "\n".join(lines)

    # Format old summaries for prompt context (read-only reference for AI)
    if old_summary:
        old_summary_lines = [
            f"{date_key}: {text}" for date_key, text in sorted(old_summary.items())
        ]
        old_summary_text = "\n\n".join(old_summary_lines)
    else:
        old_summary_text = "No previous summaries available."

    user_prompt = DAILY_SUMMARY_USER_TEMPLATE.format(
        user_id=request.user_id,
        date=request.date,
        old_summary_text=old_summary_text,
        messages=messages_text,
    )

    raw = await _call_gemini(DAILY_SUMMARY_SYSTEM_PROMPT, user_prompt)
    logger.debug("Raw Gemini response (daily-summary): %s", raw)

    try:
        data = _extract_json(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.error("Failed to parse Gemini JSON: %s | Raw: %s", exc, raw)
        raise ValueError(f"Gemini returned malformed JSON. Detail: {exc}") from exc

    # Merge today's new entry into the cumulative dict and sort chronologically
    updated_summary = dict(old_summary)
    updated_summary[request.date] = data.get("today_summary", "")
    updated_summary = dict(sorted(updated_summary.items()))

    return DailySummaryResponse(
        user_id=request.user_id,
        summary=updated_summary,
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
