from fastapi import APIRouter

from judo_chat.answer import REFUSAL_MESSAGE, UNAVAILABLE_MESSAGE, technique_videos
from judo_chat.dependencies import AnswererDep, CorpusDep, GuardrailDep, RecognizerDep
from judo_chat.schemas import AskRequest, AskResponse, DetectedTechnique, VideoLink

router = APIRouter(prefix="/api", tags=["perguntas"])


@router.post("/perguntar", response_model=AskResponse)
async def ask(
    body: AskRequest,
    recognizer: RecognizerDep,
    guardrail: GuardrailDep,
    answerer: AnswererDep,
    corpus: CorpusDep,
) -> AskResponse:
    matches = recognizer.find(body.query)
    detected = [
        DetectedTechnique(
            term=m.term, technique_ids=list(m.technique_ids), match_type=m.match_type, ambiguous=m.ambiguous
        )
        for m in matches
    ]
    verdict = await guardrail.classify(body.query)
    if not verdict.allowed:
        # Falha do guardrail também bloqueia a resposta, mas sem dizer que a pergunta saiu do escopo.
        message = UNAVAILABLE_MESSAGE if verdict.failed else REFUSAL_MESSAGE
        return AskResponse(answer=message, category="fora", refused=True, techniques_detected=detected)

    answer = await answerer.answer(body.query, matches)
    videos = [] if answer.refused else technique_videos(matches, corpus)
    return AskResponse(
        answer=answer.text,
        category="fora" if answer.refused else verdict.category,
        refused=answer.refused,
        techniques_detected=detected,
        videos=[VideoLink(technique=v.technique, url=v.url, kodokan=v.kodokan) for v in videos],
    )
