from pydantic import BaseModel, ConfigDict, Field

from judo_chat.guardrail import Category


class AskRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"query": "Como se faz o ashi barai?"}]})

    query: str = Field(min_length=1, max_length=1000)


class DetectedTechnique(BaseModel):
    term: str
    technique_ids: list[str]
    match_type: str
    ambiguous: bool


class VideoLink(BaseModel):
    technique: str
    url: str
    kodokan: bool


class AskResponse(BaseModel):
    answer: str
    category: Category
    refused: bool
    techniques_detected: list[DetectedTechnique]
    # Vídeos das técnicas reconhecidas, com o do Kodokan primeiro; vazio quando há recusa.
    videos: list[VideoLink] = []
