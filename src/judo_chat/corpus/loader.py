from collections import Counter
from pathlib import Path

import yaml

from judo_chat.corpus.models import Corpus, Document, FgjTechnique, FgjTerm, PopularName, Technique, Theme
from judo_chat.normalizer import canonical

# Entradas do corpus cujo verbete na FGJ tem outro nome.
_TERM_ALIASES = {"osaekomi-waza": "OSAE-WAZA"}


class CorpusError(ValueError):
    pass


def _read_yaml_list(path: Path) -> list[dict[str, object]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise CorpusError(f"{path}: esperava uma lista de objetos")
    return data


def _read_document(path: Path, theme: Theme) -> Document:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise CorpusError(f"{path}: falta o cabeçalho YAML")
    header_text, _, body = text[4:].partition("\n---\n")
    header = yaml.safe_load(header_text)
    if not isinstance(header, dict):
        raise CorpusError(f"{path}: cabeçalho YAML inválido")
    return Document(
        id=f"{theme}/{path.stem}",
        theme=theme,
        title=str(header["title"]),
        provenance=str(header["provenance"]),
        body=body.strip(),
    )


def _read_fgj(fgj_dir: Path, known: set[str]) -> dict[str, FgjTechnique]:
    path = fgj_dir / "tecnicas.yaml"
    if not path.exists():
        return {}
    result = {}
    for item in _read_yaml_list(path):
        technique_id = str(item.pop("id"))
        if technique_id not in known:
            raise CorpusError(f"{path}: técnica inexistente {technique_id!r}")
        result[technique_id] = FgjTechnique.model_validate(item)
    return result


def _read_fgj_terms(fgj_dir: Path, techniques: list[Technique]) -> dict[str, FgjTerm]:
    path = fgj_dir / "termos.yaml"
    if not path.exists():
        return {}
    terms = {canonical(str(item["termo"])): FgjTerm.model_validate(item) for item in _read_yaml_list(path)}
    result = {}
    for technique in techniques:
        if technique.kind == "technique":
            continue
        key = canonical(_TERM_ALIASES.get(technique.id, technique.name))
        if key in terms:
            result[technique.id] = terms[key]
    return result


def _fgj_documents(fgj_dir: Path) -> list[Document]:
    """Glossário de termos e guia de pronúncia do "Curso de Waza FGJ 2026"."""
    documents = []
    terms_path = fgj_dir / "termos.yaml"
    if terms_path.exists():
        lines = []
        for term in _read_yaml_list(terms_path):
            line = f"- {term['termo']}: {term['traducao']}"
            lines.append(f"{line}. {term['conceito']}" if term.get("conceito") else line)
        documents.append(
            Document(
                id="termos/glossario-fgj",
                theme="termos",
                title="Glossário de termos do judô (FGJ)",
                body="\n".join(lines),
                provenance="local:Curso de Waza FGJ 2026",
            )
        )
    pronunciation_path = fgj_dir / "pronuncia.yaml"
    if pronunciation_path.exists():
        lines = [
            f"- {row['letra']}: som {row['som']}; exemplo {row['exemplo']}, pronuncia-se {row['pronuncia']}"
            for row in _read_yaml_list(pronunciation_path)
        ]
        documents.append(
            Document(
                id="termos/pronuncia-fgj",
                theme="termos",
                title="Pronúncia dos termos japoneses (FGJ)",
                body="\n".join(lines),
                provenance="local:Curso de Waza FGJ 2026",
            )
        )
    return documents


def load_corpus(data_dir: Path) -> Corpus:
    techniques = [Technique.model_validate(item) for item in _read_yaml_list(data_dir / "glossario" / "tecnicas.yaml")]
    popular = [
        PopularName.model_validate(item) for item in _read_yaml_list(data_dir / "glossario" / "nomes_populares.yaml")
    ]

    duplicated = [tid for tid, count in Counter(t.id for t in techniques).items() if count > 1]
    if duplicated:
        raise CorpusError(f"ids de técnica repetidos: {duplicated}")
    duplicated = [name for name, count in Counter(p.name.lower() for p in popular).items() if count > 1]
    if duplicated:
        raise CorpusError(f"nomes populares repetidos: {duplicated}")

    known = {t.id for t in techniques}
    popular_by_technique: dict[str, set[str]] = {tid: set() for tid in known}
    for name in popular:
        unknown = [tid for tid in name.technique_ids if tid not in known]
        if unknown:
            raise CorpusError(f"nome popular {name.name!r} aponta para ids inexistentes: {unknown}")
        for tid in name.technique_ids:
            popular_by_technique[tid].add(name.name)

    fgj = _read_fgj(data_dir / "fgj", known)
    fgj_terms = _read_fgj_terms(data_dir / "fgj", techniques)

    documents = [
        _read_document(path, theme)
        for theme in ("regras", "historia", "graduacao")
        for path in sorted((data_dir / theme).glob("*.md"))
    ]
    documents += _fgj_documents(data_dir / "fgj")

    variants_path = data_dir / "glossario" / "variantes_digitacao.yaml"
    variants = yaml.safe_load(variants_path.read_text("utf-8")) if variants_path.exists() else {}
    if not isinstance(variants, dict):
        raise CorpusError(f"{variants_path}: esperava um mapa palavra -> palavra")

    return Corpus(
        techniques=tuple(
            sorted(
                (
                    t.model_copy(
                        update={
                            "popular_names": frozenset(popular_by_technique[t.id]),
                            "fgj": fgj.get(t.id),
                            "fgj_term": fgj_terms.get(t.id),
                        }
                    )
                    for t in techniques
                ),
                key=lambda t: t.id,
            )
        ),
        popular_names=tuple(sorted(popular, key=lambda p: p.name.lower())),
        documents=tuple(documents),
        typo_variants=tuple(sorted((str(k).lower(), str(v).lower()) for k, v in variants.items())),
    )
