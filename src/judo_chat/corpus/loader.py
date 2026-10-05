from collections import Counter
from pathlib import Path

import yaml

from judo_chat.corpus.models import Corpus, Document, PopularName, Technique, Theme


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

    documents = [
        _read_document(path, theme)
        for theme in ("regras", "historia", "graduacao")
        for path in sorted((data_dir / theme).glob("*.md"))
    ]

    return Corpus(
        techniques=tuple(
            sorted(
                (t.model_copy(update={"popular_names": frozenset(popular_by_technique[t.id])}) for t in techniques),
                key=lambda t: t.id,
            )
        ),
        popular_names=tuple(sorted(popular, key=lambda p: p.name.lower())),
        documents=tuple(documents),
    )
