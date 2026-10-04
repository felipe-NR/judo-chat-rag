from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Kind = Literal["technique", "category", "concept", "grip"]
Status = Literal["kodokan", "nonstandard", "forbidden_ijf"]
Usage = Literal["judo", "bjj"]
PopularKind = Literal["popular", "pt_br", "truncation", "nonstandard", "bjj"]
Confidence = Literal["alta", "media", "baixa"]
Theme = Literal["regras", "historia"]

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
    video_url: str | None = None
    judobase: JudobaseRef | None = None
    notes: tuple[str, ...] = ()
    # Derivado de nomes_populares.yaml pelo loader; não é editado à mão.
    popular_names: frozenset[str] = frozenset()

    _provenance = field_validator("provenance")(_check_provenance)


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
