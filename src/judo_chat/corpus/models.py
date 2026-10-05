from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Kind = Literal["technique", "category", "concept", "grip"]
Status = Literal["kodokan", "nonstandard", "forbidden_ijf"]
Usage = Literal["judo", "bjj"]
PopularKind = Literal["popular", "pt_br", "truncation", "nonstandard", "bjj"]
Confidence = Literal["alta", "media", "baixa"]
Theme = Literal["regras", "historia", "graduacao", "termos"]
KyoClass = Literal["habukareta-waza", "shinmeisho-no-waza"]
VideoSource = Literal["kodokan", "outro"]

_PROVENANCE_PREFIXES = ("local", "translated_from_en", "generated", "reviewed", "web:")


def _check_provenance(value: str) -> str:
    if not value.startswith(_PROVENANCE_PREFIXES):
        raise ValueError(f"provenance inválida: {value!r}")
    return value


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EnglishName(_Frozen):
    name: str
    usage: Usage = "judo"


class Video(_Frozen):
    url: str
    # "kodokan": canal oficial do Kodokan (lista da FECJU); "outro": CSV do judo-techniques-bot.
    source: VideoSource
    title: str | None = None


class KyoGrupo(_Frozen):
    # Texto da coluna KYO-GRUPO da FGJ, normalizado só nos espaços ("1º - TE-WAZA").
    original: str
    gokyo: int | None = Field(default=None, ge=1, le=5)
    classe: KyoClass | None = None


class FgjTechnique(_Frozen):
    """Campos do "Curso de Waza FGJ 2026", copiados sem edição: fonte primária para tradução,
    descrição, princípio e kyo-grupo das 100 técnicas oficiais."""

    tecnica: str
    kanji: str
    traducao: str
    descricao_kodokan: str
    principio: str
    kyo_grupo: KyoGrupo


class FgjTerm(_Frozen):
    """Verbete do glossário do "Curso de Waza FGJ 2026", sem edição."""

    termo: str
    traducao: str
    conceito: str | None = None


class JudobaseRef(_Frozen):
    code_short: str
    id_tag: str


class Technique(_Frozen):
    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    name: str
    kind: Kind = "technique"
    group: str | None = None
    status: Status = "kodokan"
    ijf_name: str | None = None
    aliases: tuple[str, ...] = ()
    english_names: tuple[EnglishName, ...] = ()
    name_pt_br: str | None = None
    description_pt_br: str | None = None
    provenance: str = "generated"
    # Em ordem de exibição: vídeos do Kodokan primeiro.
    videos: tuple[Video, ...] = ()
    judobase: JudobaseRef | None = None
    notes: tuple[str, ...] = ()
    # Derivados pelo loader; não são editados à mão.
    popular_names: frozenset[str] = frozenset()
    fgj: FgjTechnique | None = None
    # Para categorias, conceitos e pegadas: o verbete do glossário da FGJ, quando existe.
    fgj_term: FgjTerm | None = None

    _provenance = field_validator("provenance")(_check_provenance)

    @field_validator("videos")
    @classmethod
    def _kodokan_first(cls, videos: tuple[Video, ...]) -> tuple[Video, ...]:
        sources = [v.source for v in videos]
        if sources != sorted(sources, key=lambda s: s != "kodokan"):
            raise ValueError("vídeos do Kodokan devem vir antes dos outros")
        return videos


class PopularName(_Frozen):
    name: str
    technique_ids: tuple[str, ...]
    kind: PopularKind = "popular"
    confidence: Confidence
    source: str
    note: str | None = None

    @property
    def ambiguous(self) -> bool:
        return len(self.technique_ids) > 1


class Document(_Frozen):
    id: str
    theme: Theme
    title: str
    body: str
    provenance: str

    _provenance = field_validator("provenance")(_check_provenance)


class Corpus(_Frozen):
    techniques: tuple[Technique, ...]
    popular_names: tuple[PopularName, ...]
    documents: tuple[Document, ...]

    def technique(self, technique_id: str) -> Technique:
        for technique in self.techniques:
            if technique.id == technique_id:
                return technique
        raise KeyError(technique_id)
