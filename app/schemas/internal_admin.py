from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class SystemOverviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: str = Field(description="Overall system health status")
    db_connected: bool
    redis_connected: bool
    uptime_seconds: Optional[int] = None
    version: Optional[str] = None


class PerformancePointModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    timestamp: str
    db_latency_ms: Optional[float]
    redis_latency_ms: Optional[float]


class PerformanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    period: str
    granularity: str
    points: List[PerformancePointModel]


class ErrorItemModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    message: str
    count: int


class ErrorSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total: int
    items: List[ErrorItemModel]
