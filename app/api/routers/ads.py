from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.ads import AdCampaignResponse, AdEventRequest
from app.services.ads import (
    get_active_ad_for_placement,
    record_ad_click,
    record_ad_impression,
    serialize_ad_campaign,
)


router = APIRouter()


@router.get("/ads/placement/{placement_name}", response_model=AdCampaignResponse)
async def api_get_ad_placement(
    placement_name: str,
    session: AsyncSession = Depends(get_db_session),
) -> AdCampaignResponse:
    campaign = await get_active_ad_for_placement(session, placement_name)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active ad for this placement.")
    return serialize_ad_campaign(campaign)


@router.post("/ads/impression", response_model=AdCampaignResponse)
async def api_ad_impression(
    payload: AdEventRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdCampaignResponse:
    campaign = await record_ad_impression(session, payload.campaign_code)
    return serialize_ad_campaign(campaign)


@router.post("/ads/click", response_model=AdCampaignResponse)
async def api_ad_click(
    payload: AdEventRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdCampaignResponse:
    campaign = await record_ad_click(session, payload.campaign_code)
    return serialize_ad_campaign(campaign)
