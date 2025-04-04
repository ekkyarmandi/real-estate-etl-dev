from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class ReportBase(BaseModel):
    """Base schema for Report data."""

    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReportResponse(ReportBase):
    """Schema for Report response from the API."""

    id: str
    total_listings: int
    success_count: Optional[int] = None
    error_count: Optional[int] = None
    duration: Optional[float] = None  # duration in seconds


class ReportList(BaseModel):
    """Schema for a list of Report responses."""

    reports: List[ReportResponse]


class QueueReportResponse(BaseModel):
    """Schema for individual Queue report item."""

    id: int
    url: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class QueueReport(BaseModel):
    """Schema for a list of Queue reports."""

    status: str
    data: List[QueueReportResponse]


class QueueStatsResponse(BaseModel):
    """Schema for Queue statistics."""

    status: str
    data: dict = {
        "total": int,
        "available": int,
        "errors": int,
        "delisted": int,
        "sold": int,
    }
