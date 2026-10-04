"""Reconhecimento de nomes de técnicas em texto livre.

Substitui a regex do judo-techniques-bot, que casava substrings ("Ko-uchi-gari"
disparava O-uchi-gari) e não aceitava macron nem grafia separada por sílaba.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from judo_chat.corpus.models import Corpus

MatchType = Literal["oficial", "ijf", "grafia", "popular", "pt_br"]

# Rendaku e grafias brasileiras: os dois lados da comparação passam pela mesma troca.
_SUBSTITUTIONS = (
    ("barai", "harai"),
    ("gaeshi", "kaeshi"),
    ("gatame", "katame"),
    ("guruma", "kuruma"),
    ("goshi", "koshi"),
    ("gari", "kari"),
    ("gake", "kake"),
    ("jime", "shime"),
    ("nague", "nage"),
    ("ou", "o"),
)
_TOKEN = re.compile(r"[a-z0-9]+")
_WORD = re.compile(r"[^\W_]+")
_DOUBLE = re.compile(r"(.)\1+")
_MAX_WINDOW = 6


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(_fold(text))


def canonical(text: str) -> str:
    """Forma de comparação: sem acento, espaço, hífen, rendaku nem letra dobrada."""
    fused = "".join(tokenize(text))
    for old, new in _SUBSTITUTIONS:
        fused = fused.replace(old, new)
    return _DOUBLE.sub(r"\1", fused)


@dataclass(frozen=True)
class Entry:
    technique_ids: tuple[str, ...]
    match_type: MatchType
    label: str


@dataclass(frozen=True)
class Match:
    term: str
    technique_ids: tuple[str, ...]
    match_type: MatchType
    label: str

    @property
    def ambiguous(self) -> bool:
        return len(self.technique_ids) > 1


# Prioridade quando duas fontes produzem a mesma chave canônica.
_PRIORITY: dict[MatchType, int] = {"oficial": 0, "ijf": 1, "grafia": 2, "pt_br": 3, "popular": 4}


class Recognizer:
    def __init__(self, corpus: Corpus) -> None:
        self._index: dict[str, Entry] = {}
        for technique in corpus.techniques:
            ids = (technique.id,)
            self._add(technique.name, Entry(ids, "oficial", technique.name))
            if technique.ijf_name:
                self._add(technique.ijf_name, Entry(ids, "ijf", technique.name))
            for alias in technique.aliases:
                self._add(alias, Entry(ids, "grafia", technique.name))
            if technique.name_pt_br:
                self._add(technique.name_pt_br, Entry(ids, "pt_br", technique.name))
        for popular in corpus.popular_names:
            self._add(popular.name, Entry(popular.technique_ids, "popular", popular.name))

    def _add(self, name: str, entry: Entry) -> None:
        key = canonical(name)
        if not key:
            return
        current = self._index.get(key)
        if current is None or _PRIORITY[entry.match_type] < _PRIORITY[current.match_type]:
            self._index[key] = entry

    def lookup(self, name: str) -> Entry | None:
        """Igualdade da forma canônica; serve para nomes inteiros como EventTag.name."""
        return self._index.get(canonical(name))

    def find(self, text: str) -> list[Match]:
        """Casamentos em texto livre, do mais longo para o mais curto, sem sobreposição."""
        spans = [("".join(tokenize(m.group())), m.start(), m.end()) for m in _WORD.finditer(text)]
        matches: list[Match] = []
        position = 0
        while position < len(spans):
            for size in range(min(_MAX_WINDOW, len(spans) - position), 0, -1):
                window = spans[position : position + size]
                tokens = [token for token, _, _ in window]
                key = canonical("".join(tokens))
                entry = self._index.get(key)
                # Uma palavra de borda que some na canonização ("é", "ou") não entra no termo.
                if entry is not None and size > 1:
                    if key in (canonical("".join(tokens[1:])), canonical("".join(tokens[:-1]))):
                        entry = None
                if entry is not None:
                    term = text[window[0][1] : window[-1][2]]
                    matches.append(Match(term, entry.technique_ids, entry.match_type, entry.label))
                    position += size
                    break
            else:
                position += 1
        return matches
