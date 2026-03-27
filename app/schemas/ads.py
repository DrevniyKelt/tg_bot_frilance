from __future__ import annotations

from pydantic import BaseModel, Field


class AdCampaignResponse(BaseModel):
    id: int
    code: str
    title: str
    body: str
    placement_name: str
    target_url: str
    impressions_count: int
    clicks_count: int


class AdEventRequest(BaseModel):
    campaign_code: str = Field(min_length=2, max_length=64)
