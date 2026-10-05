import logging

from fastapi import APIRouter

from judo_chat.answer import REFUSAL_MESSAGE, UNAVAILABLE_MESSAGE, Turn, fgj_quotes_intact, video_groups
from judo_chat.dependencies import AnswererDep, CorpusDep, GuardrailDep, RecognizerDep
from judo_chat.schemas import (
    AskRequest,
    AskResponse,
    DetectedTechnique,
    LegacyVideo,
    VideoGroupOut,
    VideoLink,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["perguntas"])

# Quanto do histórico vai ao guardrail: só o suficiente para entender a continuação.
_GUARDRAIL_TURNS = 4
_GUARDRAIL_TURN_CHARS = 400


@router.post("/perguntar", response_model=AskResponse)
async def ask(
    body: AskRequest,
    recognizer: RecognizerDep,
    guardrail: GuardrailDep,
    answerer: AnswererDep,
    corpus: CorpusDep,
) -> AskResponse:
    history = [Turn(role=t.role, text=t.text) for t in body.history]
    matches = recognizer.find(body.query)
    detected = [
        DetectedTechnique(
            term=m.term, technique_ids=list(m.technique_ids), match_type=m.match_type, ambiguous=m.ambiguous
        )
        for m in matches
    ]
    if not matches:
        # "E o outro?": as técnicas vêm da última pergunta do usuário.
        last_question = next((t.text for t in reversed(history) if t.role == "usuario"), "")
        matches = recognizer.find(last_question)

    technique_names = [corpus.technique(tid).name for m in matches for tid in m.technique_ids]
    guardrail_history = [
        f"{'Usuário' if t.role == 'usuario' else 'Assistente'}: {t.text[:_GUARDRAIL_TURN_CHARS]}"
        for t in history[-_GUARDRAIL_TURNS:]
    ]
    verdict = await guardrail.classify(body.query, guardrail_history, technique_names)
    if not verdict.allowed:
        # Falha do guardrail também bloqueia a resposta, mas sem dizer que a pergunta saiu do escopo.
        message = UNAVAILABLE_MESSAGE if verdict.failed else REFUSAL_MESSAGE
        return AskResponse(answer=message, category="fora", refused=True, techniques_detected=detected)

    answer = await answerer.answer(body.query, matches, history)
    groups = [] if answer.refused else video_groups(answer.text, matches, recognizer, corpus)
    for technique_id, intact in fgj_quotes_intact(answer.text, groups, corpus).items():
        logger.info("descrição FGJ %s: %s", "literal" if intact else "PARAFRASEADA", technique_id)
    return AskResponse(
        answer=answer.text,
        category="fora" if answer.refused else verdict.category,
        refused=answer.refused,
        techniques_detected=detected,
        video_groups=[
            VideoGroupOut(
                technique=g.technique,
                anchor=g.anchor,
                videos=[VideoLink(url=v.url, kodokan=v.kodokan) for v in g.videos],
            )
            for g in groups
        ],
        videos=[LegacyVideo(technique=g.technique, url=v.url, kodokan=v.kodokan) for g in groups for v in g.videos],
    )
