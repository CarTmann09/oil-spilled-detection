from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import Settings
from .monitor import OilSpillMonitor


def create_app(settings: Settings, monitor: OilSpillMonitor) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await monitor.start()
        try:
            yield
        finally:
            await monitor.stop()

    app = FastAPI(
        title="Oil Spill Monitoring API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
    )
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=False,
            allow_methods=["GET"],
            allow_headers=["X-API-Key", "Content-Type"],
        )

    def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
        if settings.api_key and x_api_key != settings.api_key:
            raise HTTPException(status_code=401, detail="API key tidak valid")

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "site": settings.site_name,
            "camera": settings.camera_name,
        }

    @app.get("/health")
    def health() -> dict[str, object]:
        status = monitor.public_status(include_metrics=True)
        return {
            "ok": status["systemStatus"] == "ONLINE",
            **status,
            "syncQueueSize": monitor.storage.queue_size(),
        }

    @app.get("/api/status", dependencies=[Depends(require_api_key)])
    def api_status() -> dict[str, object]:
        return monitor.public_status(include_metrics=True)

    @app.get("/api/events", dependencies=[Depends(require_api_key)])
    def api_events(
        limit: int = Query(default=50, ge=1, le=200),
        before_ms: int | None = Query(default=None),
    ) -> dict[str, object]:
        events = monitor.storage.recent_events(limit=limit, before_ms=before_ms)
        return {
            "items": events,
            "nextBeforeMs": events[-1]["timestampMs"] if len(events) == limit else None,
        }

    @app.get("/api/snapshot/latest", dependencies=[Depends(require_api_key)])
    def latest_snapshot() -> FileResponse:
        path_value = monitor.state.snapshot().get("latestSnapshotPath")
        if not path_value:
            raise HTTPException(status_code=404, detail="Snapshot belum tersedia")
        path = Path(str(path_value))
        if not path.exists():
            raise HTTPException(status_code=404, detail="File snapshot tidak ditemukan")
        return FileResponse(path, media_type="image/jpeg", filename=path.name)

    return app
