from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdCampaign, AdEvent, AdEventKind
from app.schemas.ads import AdCampaignResponse


async def get_active_ad_for_placement(session: AsyncSession, placement_name: str) -> AdCampaign | None:
    return await session.scalar(
        select(AdCampaign)
        .where(AdCampaign.placement_name == placement_name, AdCampaign.is_active.is_(True))
        .order_by(AdCampaign.id.asc())
    )


async def record_ad_impression(session: AsyncSession, campaign_code: str) -> AdCampaign:
    campaign = await _get_campaign_by_code(session, campaign_code)
    campaign.impressions_count += 1
    session.add(AdEvent(campaign_id=campaign.id, kind=AdEventKind.IMPRESSION))
    await session.commit()
    await session.refresh(campaign)
    return campaign


async def record_ad_click(session: AsyncSession, campaign_code: str) -> AdCampaign:
    campaign = await _get_campaign_by_code(session, campaign_code)
    campaign.clicks_count += 1
    session.add(AdEvent(campaign_id=campaign.id, kind=AdEventKind.CLICK))
    await session.commit()
    await session.refresh(campaign)
    return campaign


def serialize_ad_campaign(campaign: AdCampaign) -> AdCampaignResponse:
    return AdCampaignResponse(
        id=campaign.id,
        code=campaign.code,
        title=campaign.title,
        body=campaign.body,
        placement_name=campaign.placement_name,
        target_url=campaign.target_url,
        impressions_count=campaign.impressions_count,
        clicks_count=campaign.clicks_count,
    )


async def list_ad_campaigns(session: AsyncSession) -> list[AdCampaign]:
    return (await session.scalars(select(AdCampaign).order_by(AdCampaign.id.asc()))).all()


async def _get_campaign_by_code(session: AsyncSession, campaign_code: str) -> AdCampaign:
    campaign = await session.scalar(select(AdCampaign).where(AdCampaign.code == campaign_code))
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad campaign not found.")
    return campaign
