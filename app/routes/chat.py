"""
Route: POST /analyze-chat

Thin router — all logic lives in gemini_service.
"""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import ChatAnalysisRequest, ChatAnalysisResponse
from app.services.gemini_service import analyze_message

router = APIRouter()


@router.post(
    "/analyze-chat",
    response_model=ChatAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a user message for emotion, risk and stress",
    description=(
        "Accepts the current message, optional conversation history, and an optional "
        "long-term memory summary. Returns detected emotions, risk level, stress score, "
        "an empathetic AI response, and an alert flag."
    ),
)
async def analyze_chat(request: ChatAnalysisRequest) -> ChatAnalysisResponse:
    """
    Single-call Gemini analysis endpoint.
    """
    try:
        return await analyze_message(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI service error: {exc}",
        )
