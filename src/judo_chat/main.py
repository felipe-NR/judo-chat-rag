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
from judo_chat.normalizer import Recognizer
from judo_chat.routers.ask import router as ask_router

logging.basicConfig(level=logging.INFO)
_STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    corpus = load_corpus(settings.data_dir)
    async with AsyncAnthropic() as client:
        app.state.corpus = corpus
        app.state.recognizer = Recognizer(corpus)
        app.state.guardrail = Guardrail(client, settings.guardrail_model, settings.guardrail_timeout_s)
        app.state.answerer = Answerer(client, settings, corpus)
        yield


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
