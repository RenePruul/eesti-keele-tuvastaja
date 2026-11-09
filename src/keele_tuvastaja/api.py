"""Keeletuvastaja HTTP API."""

from __future__ import annotations

import argparse
import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import __version__
from .detector import Verdict, _warm_up, detect
from .settings import Settings

_DETECT_PATH = "/detect"


class DetectRequestGuard:
    """Piira ``/detect`` päringu keha suurust ja keela vastuste vahemälu.

    Keha loetakse siin ise ja loendatakse baite, sest ``Content-Length`` võib
    puududa (``Transfer-Encoding: chunked``). Piiri ületamisel lõpetatakse
    lugemine kohe ega hoita ülejäänud keha mälus.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] != _DETECT_PATH:
            await self.app(scope, receive, send)
            return

        async def send_no_store(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "no-store"
                headers["Pragma"] = "no-cache"
            await send(message)

        async def reject(status_code: int, detail: str) -> None:
            response = JSONResponse(status_code=status_code, content={"detail": detail})
            await response(scope, receive, send_no_store)

        content_length = Headers(scope=scope).get("content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                await reject(status.HTTP_400_BAD_REQUEST, "Vigane Content-Length päis")
                return
            if declared > self.max_bytes:
                await reject(413, "Päring on liiga suur")
                return

        body = bytearray()
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body += message.get("body", b"")
            if len(body) > self.max_bytes:
                await reject(413, "Päring on liiga suur")
                return
            more_body = message.get("more_body", False)

        body_sent = False

        async def replay_body() -> Message:
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay_body, send_no_store)


class DetectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str


class DetectionResponse(BaseModel):
    verdict: Verdict


class HealthResponse(BaseModel):
    status: str


def create_app(settings: Settings | None = None, *, load_model: bool = True) -> FastAPI:
    config = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if load_model:
            await asyncio.to_thread(_warm_up)
        yield

    app = FastAPI(
        title="Eesti keele tuvastaja",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(DetectRequestGuard, max_bytes=config.max_request_bytes)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.post(_DETECT_PATH, response_model=DetectionResponse)
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
            verdict=result.verdict,
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
