from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from judo_chat.guardrail import Category


class HistoryTurn(BaseModel):
    role: Literal["usuario", "assistente"]
    text: str = Field(min_length=1, max_length=4000)


class AskRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"query": "Como se faz o ashi barai?"}]})

    query: str = Field(min_length=1, max_length=1000)
    # Últimas trocas da conversa, guardadas pela página; o servidor não guarda estado.
    history: list[HistoryTurn] = Field(default_factory=list, max_length=6)


class DetectedTechnique(BaseModel):
    term: str
    technique_ids: list[str]
    match_type: str
    ambiguous: bool


class VideoLink(BaseModel):
    url: str
    kodokan: bool


class LegacyVideo(BaseModel):
    technique: str
    url: str
    kodokan: bool


class VideoGroupOut(BaseModel):
    technique: str
    # Trecho da resposta (título ou item) onde a página põe os vídeos; null vai para o fim.
    anchor: str | None
    videos: list[VideoLink]


class AskResponse(BaseModel):
    answer: str
    category: Category
    refused: bool
    techniques_detected: list[DetectedTechnique]
    # Vídeos das técnicas apresentadas na resposta, com o do Kodokan primeiro em cada técnica.
    video_groups: list[VideoGroupOut] = []
    # Formato anterior, mantido para páginas ainda em cache no navegador.
    videos: list[LegacyVideo] = []
