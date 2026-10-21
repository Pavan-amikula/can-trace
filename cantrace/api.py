"""Local replay workspace: recomputes MPS scores as the event stream is read."""

import asyncio
from functools import lru_cache
import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .data import FEATURES, sha256
from .forensics import package_case
from .conditional import ConditionalMPS

ROOT = Path(__file__).resolve().parents[1]


def create_app(root=ROOT):
    root = Path(root)
    app = FastAPI(title="CAN Trace", version="0.1.0", docs_url=None, redoc_url=None)

    @lru_cache(maxsize=1)
    def resources():
        try:
            model, encoder = ConditionalMPS.load(root / "artifacts/model.npz")
            replay = json.loads((root / "artifacts/replay.json").read_text())
            metrics = json.loads((root / "artifacts/metrics.json").read_text())
            return model, encoder, replay, metrics
        except FileNotFoundError:
            raise HTTPException(
                503,
                "Run python scripts/download_data.py and python -m cantrace.evaluate first",
            )

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        )
        return response

    @app.get("/api/health")
    def health():
        ready = all(
            (root / "artifacts" / f).exists()
            for f in ("model.npz", "replay.json", "metrics.json")
        )
        return {
            "status": "ready" if ready else "setup_required",
            "mode": "software replay / passive monitoring prototype",
        }

    @app.get("/api/summary")
    def summary():
        model, encoder, replay, metrics = resources()
        return {
            "threshold": model.threshold,
            "source": replay["source"],
            "selection": replay["selection"],
            "source_sha256": replay["source_sha256"],
            "model_sha256": sha256(root / "artifacts/model.npz"),
            "events": len(replay["events"]),
            "metrics": metrics,
            "feature_names": FEATURES,
        }

    @app.get("/api/stream")
    async def stream(start: int = Query(0, ge=0), speed: int = Query(8, ge=1, le=50)):
        model, _, replay, _ = resources()

        async def event_source():
            for position, e in enumerate(replay["events"][start:], start):
                value = float(model.score_samples(np.array(e["features"])[None])[0])
                public = {k: v for k, v in e.items() if k != "features"}
                public.update(
                    position=position, score=value, alert=value > model.threshold
                )
                yield f"data: {json.dumps(public)}\n\n"
                await asyncio.sleep(1 / speed)
            yield "event: complete\ndata: {}\n\n"

        return StreamingResponse(
            event_source(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    def get_case(position):
        model, encoder, replay, _ = resources()
        if not 0 <= position < len(replay["events"]):
            raise HTTPException(404, "window not found")
        event = replay["events"][position]
        explanation = model.explain(
            np.array(event["features"]), FEATURES, encoder["window"]
        )
        evidence = {k: v for k, v in event.items() if k != "features"}
        return package_case(
            [{**evidence, "explanation": explanation}],
            replay["source_sha256"],
            sha256(root / "artifacts/model.npz"),
            {
                "encoder": encoder,
                "threshold": model.threshold,
                "rank": model.rank,
                "angle": model.angle,
                "selection": replay["selection"],
            },
        )

    @app.get("/api/case/{position}")
    def case(position: int):
        return get_case(position)

    @app.get("/api/case/{position}/export")
    def export(position: int):
        return JSONResponse(
            get_case(position),
            headers={
                "Content-Disposition": f'attachment; filename="can-trace-case-{position}.json"'
            },
        )

    @app.get("/")
    def index():
        return FileResponse(root / "web/index.html")

    app.mount("/static", StaticFiles(directory=root / "web"), name="static")
    return app


app = create_app()
