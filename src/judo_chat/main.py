import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from anthropic import AsyncAnthropic
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from judo_chat.answer import Answerer
from judo_chat.config import get_settings
from judo_chat.corpus.loader import load_corpus
from judo_chat.errors import register_error_handlers
from judo_chat.guardrail import Guardrail
from judo_chat.keepalive import CacheKeepAlive
from judo_chat.normalizer import Recognizer
from judo_chat.relations import Relations
from judo_chat.routers.ask import router as ask_router

logging.basicConfig(level=logging.INFO)
_STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    corpus = load_corpus(settings.data_dir)
    async with AsyncAnthropic() as client:
        app.state.corpus = corpus
        app.state.recognizer = recognizer = Recognizer(corpus)
        app.state.guardrail = Guardrail(
            client,
            settings.guardrail_model,
            settings.guardrail_timeout_s,
            effort=settings.guardrail_effort,
            max_tokens=settings.guardrail_max_tokens,
        )
        app.state.answerer = Answerer(client, settings, corpus, Relations(corpus, recognizer))
        task = None
        if settings.keepalive_enabled:
            keepalive = CacheKeepAlive(
                app.state.answerer,
                interval_s=settings.keepalive_interval_s,
                start=settings.keepalive_window_start,
                end=settings.keepalive_window_end,
                timezone=settings.keepalive_timezone,
            )
            task = asyncio.create_task(keepalive.run())
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task


app = FastAPI(title="Judô Chat", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().cors_origins),
    allow_methods=["POST"],
    allow_headers=["Content-Type", "ngrok-skip-browser-warning"],
)
register_error_handlers(app)
app.include_router(ask_router)
# Depois das rotas da API: serve index.html e config.js na raiz.
app.mount("/", StaticFiles(directory=_STATIC, html=True), name="static")
