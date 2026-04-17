"""
Route: POST /daily-summary

Thin router — all logic lives in gemini_service.
"""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import DailySummaryRequest, DailySummaryResponse
from app.services.gemini_service import generate_daily_summary

router = APIRouter()


@router.post(
    "/daily-summary",
    response_model=DailySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a daily emotional wellbeing summary",
    description=(
        "Accepts all messages recorded for a user during a single day. "
        "Returns a narrative summary, the dominant emotion, average stress score, "
        "and the risk trend across the day."
    ),
)
async def daily_summary(request: DailySummaryRequest) -> DailySummaryResponse:
    """
    One-call Gemini daily-summary endpoint.
    """
    try:
        return await generate_daily_summary(request)
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
