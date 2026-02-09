from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.internal.ops.dependencies import ops_guard
from app.api.deps.internal import get_system_metrics_service
from app.application.ports.system_metrics import SystemMetricsQueryService
from app.application.services.system_metrics_service import InvalidWindow
from app.schemas.internal_admin import (  # Reuse shared system metrics schemas
    SystemOverviewResponse,
    PerformanceResponse,
    ErrorSummaryResponse,
)

router = APIRouter(prefix="/system", dependencies=[Depends(ops_guard)])


@router.get("/overview", response_model=SystemOverviewResponse)
async def system_overview(service: SystemMetricsQueryService = Depends(get_system_metrics_service)) -> SystemOverviewResponse:
    try:
        result = await service.get_overview()
        return SystemOverviewResponse.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="System overview unavailable") from exc


@router.get("/performance", response_model=PerformanceResponse)
async def system_performance(
    period: str = Query("1h", description="Allowed: 15m, 1h, 24h"),
    granularity: str = Query("5m", description="Allowed: 1m, 5m, 15m, 1h"),
    service: SystemMetricsQueryService = Depends(get_system_metrics_service),
) -> PerformanceResponse:
    try:
        result = await service.get_performance(period=period, granularity=granularity)
        return PerformanceResponse.model_validate(result)
    except InvalidWindow as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="Performance data unavailable") from exc


@router.get("/errors", response_model=ErrorSummaryResponse)
async def system_errors(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of recent errors to return"),
    service: SystemMetricsQueryService = Depends(get_system_metrics_service),
) -> ErrorSummaryResponse:
    try:
        result = await service.get_errors(limit=limit)
        return ErrorSummaryResponse.model_validate(result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="Error summary unavailable") from exc
