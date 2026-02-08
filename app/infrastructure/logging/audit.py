from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict
import logging


@dataclass
class AuditRecord:
    timestamp: datetime
    principal: str
    auth_type: str
    endpoint: str
    method: str
    status: int
    path_params: Dict[str, Any]
    query_params: Dict[str, Any]
    headers: Dict[str, str]


class AuditLogger:
    """Lightweight audit logger that emits structured events to standard logging.

    Persistence (DB, SIEM, etc.) can be swapped by replacing this implementation
    without changing API handlers.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("audit")

    def log(self, record: AuditRecord) -> None:
        payload = asdict(record)
        # Ensure datetime is ISO formatted for downstream processors
        payload["timestamp"] = record.timestamp.isoformat()
        self._logger.info("admin_audit", extra={"audit": payload})

