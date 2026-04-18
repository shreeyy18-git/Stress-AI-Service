"""
Route: POST /daily-summary

Thin router — all logic lives in gemini_service.
"""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import (
    DailySummaryRequest, 
    DailySummaryResponse,
    HelpBeaconRequest,
    HelpBeaconResponse
)
from app.services.gemini_service import (
    generate_daily_summary,
    generate_help_beacon
)

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


@router.post(
    "/i-need-help",
    response_model=HelpBeaconResponse,
    status_code=status.HTTP_200_OK,
    summary="I_Need_Help: Generate a summary for closed ones",
    description=(
        "Accepts a 0-7 day wellbeing summary and transforms it into a "
        "2-4 line message suitable for friends and family."
    ),
)
async def i_need_help(request: HelpBeaconRequest) -> HelpBeaconResponse:
    """
    Generate a help beacon message for the support system.
    """
    try:
        return await generate_help_beacon(request)
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
