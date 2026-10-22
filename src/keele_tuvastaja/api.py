"""Keeletuvastaja HTTP API."""

from __future__ import annotations

import argparse
import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .detector import detect, warm_up
from .settings import Settings


class DetectionRequest(BaseModel):
    text: str


class DetectionResponse(BaseModel):
    verdict: str
    is_estonian: bool
    language: str | None
    confidence: float
    method: str


class HealthResponse(BaseModel):
    status: str


def create_app(settings: Settings | None = None, *, load_model: bool = True) -> FastAPI:
    config = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if load_model:
            await asyncio.to_thread(warm_up)
        yield

    app = FastAPI(
        title="Eesti keele tuvastaja",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def limit_request_size(request: Request, call_next) -> Response:
        if request.url.path == "/detect":
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    too_large = int(content_length) > config.max_request_bytes
                except ValueError:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": "Vigane Content-Length päis"},
                    )
                if too_large:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Päring on liiga suur"},
                    )
        return await call_next(request)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.post("/detect", response_model=DetectionResponse)
    async def detect_language(payload: DetectionRequest) -> DetectionResponse:
        if not payload.text.strip():
            raise HTTPException(
                status_code=422,
                detail="text ei tohi olla tühi",
            )
        if len(payload.text) > config.max_text_length:
            raise HTTPException(
                status_code=413,
                detail=f"text võib sisaldada kuni {config.max_text_length} märki",
            )

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(detect, payload.text),
                timeout=config.request_timeout_seconds,
            )
        except TimeoutError as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Keeletuvastus ületas vastamise ajalimiidi",
            ) from exc

        return DetectionResponse(
            verdict=result.verdict.value,
            is_estonian=result.is_estonian,
            language=result.language,
            confidence=result.confidence,
            method=result.method,
        )

    return app


app = create_app()


def main(argv: list[str] | None = None) -> None:
    """Käivita API Uvicorni serveriga."""

    import uvicorn

    parser = argparse.ArgumentParser(description="Käivita eesti keele tuvastuse API")
    parser.add_argument(
        "--host",
        default=os.getenv("KEELETUVASTAJA_HOST", "127.0.0.1"),
        help="serveri võrguliides",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("KEELETUVASTAJA_PORT", "8000")),
        help="serveri port",
    )
    args = parser.parse_args(argv)
    uvicorn.run(
        "keele_tuvastaja.api:app",
        host=args.host,
        port=args.port,
        workers=1,
    )


if __name__ == "__main__":
    main()
