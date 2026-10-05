"""Importa o material da Federação Gaúcha de Judô (FGJ) para data/fgj/.

Fontes (PDFs enviados pelo usuário em 2026-10-05):
- "Curso de Waza FGJ 2026" (Waza FGJ 2026.docx): tabelas com técnica, tradução, descrição
  Kodokan, princípio/ponto de atenção e kyo-grupo das 100 técnicas, glossário de termos e
  guia de pronúncia;
- "Técnicas Nage-Waza e Katame-Waza FGJ": lista das 100 técnicas com o nome em kanji.

O texto das descrições, traduções e princípios é copiado sem edição; só os nomes das
técnicas perdem os espaços que a quebra de linha do PDF inseriu ("Nami-juji-jim e").

Uso: uv run --with pdfplumber python scripts/import_fgj.py CURSO.pdf LISTA_KANJI.pdf
"""

import re
import subprocess
import sys
from pathlib import Path

import pdfplumber
import yaml

from judo_chat.corpus.loader import load_corpus
from judo_chat.normalizer import Recognizer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "fgj"
_GOKYO = re.compile(r"^(\d)º")
# Erros de digitação da lista em kanji da FGJ.
_ROMAJI_FIXES = {"Uki-otosh": "Uki-otoshi"}
_CLASSES = {"HABUKARETA-WAZA": "habukareta-waza", "SHIN-MEISHO-NO-WAZA": "shinmeisho-no-waza"}


def _clean_name(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _clean_group(text: str) -> dict[str, object]:
    joined = re.sub(r"(?<=\w)-\s+", "-", text)
    joined = re.sub(r"W\s*A\s*Z\s*A", "WAZA", joined).replace("TE-WAZA-WAZA", "TE-WAZA")
    joined = re.sub(r"º\s*-?\s*", "º - ", joined)
    joined = re.sub(r"\s+", " ", joined).strip()
    group: dict[str, object] = {"original": joined}
    if match := _GOKYO.match(joined):
        group["gokyo"] = int(match.group(1))
    for label, slug in _CLASSES.items():
        if label in joined:
            group["classe"] = slug
    return group


def _rows(pdf_path: Path) -> list[list[str]]:
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                rows.extend([" ".join((cell or "").split()) for cell in row] for row in table)
    return rows


def _kanji(list_pdf: Path) -> dict[str, str]:
    text = subprocess.run(["pdftotext", "-layout", str(list_pdf), "-"], capture_output=True, text=True, check=True)
    pairs = re.findall(r"([぀-ヿ一-鿿]+)\s*-\s*([A-Z][A-Za-z-]+)", text.stdout)
    return {_ROMAJI_FIXES.get(romaji, romaji): kanji for kanji, romaji in pairs}


def main() -> None:
    course_pdf, list_pdf = map(Path, sys.argv[1:3])
    recognizer = Recognizer(load_corpus(ROOT / "data"))
    kanji_by_romaji = _kanji(list_pdf)
    kanji = {}
    for romaji, value in kanji_by_romaji.items():
        entry = recognizer.lookup(romaji)
        if entry is None or len(entry.technique_ids) != 1:
            raise SystemExit(f"kanji sem técnica: {romaji}")
        kanji[entry.technique_ids[0]] = value

    techniques, terms, pronunciation = [], [], []
    for cells in _rows(course_pdf):
        if len(cells) == 5 and re.match(r"^\d+\.", cells[0]):
            name = _clean_name(re.sub(r"^\d+\.\s*", "", cells[0]))
            entry = recognizer.lookup(name)
            if entry is None or len(entry.technique_ids) != 1:
                raise SystemExit(f"técnica da FGJ sem correspondência: {name}")
            tid = entry.technique_ids[0]
            techniques.append(
                {
                    "id": tid,
                    "tecnica": name,
                    "kanji": kanji.get(tid),
                    "traducao": cells[1],
                    "descricao_kodokan": cells[2],
                    "principio": cells[3],
                    "kyo_grupo": _clean_group(cells[4]),
                }
            )
        elif len(cells) == 3 and cells[0] and cells[0] != "TERMO":
            terms.append({"termo": cells[0], "traducao": cells[1], "conceito": cells[2] or None})
        elif len(cells) == 4 and cells[0] and cells[0] != "LETRA OU DÍGRAFO":
            pronunciation.append({"letra": cells[0], "som": cells[1], "exemplo": cells[2], "pronuncia": cells[3]})

    ids = [t["id"] for t in techniques]
    if len(ids) != 100 or len(set(ids)) != 100:
        raise SystemExit(f"esperava 100 técnicas distintas, vieram {len(set(ids))}")
    missing_kanji = [t["id"] for t in techniques if not t["kanji"]]
    if missing_kanji:
        raise SystemExit(f"técnicas sem kanji: {missing_kanji}")

    OUT.mkdir(parents=True, exist_ok=True)
    header = "# Gerado por scripts/import_fgj.py a partir do material da FGJ. Não edite à mão.\n"
    for name, data in (("tecnicas.yaml", techniques), ("termos.yaml", terms), ("pronuncia.yaml", pronunciation)):
        (OUT / name).write_text(header + yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100), "utf-8")
    print(f"{len(techniques)} técnicas, {len(terms)} termos, {len(pronunciation)} regras de pronúncia", file=sys.stderr)


if __name__ == "__main__":
    main()
