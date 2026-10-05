"""Gera data/glossario/tecnicas.yaml a partir da curadoria e das duas fontes locais.

Fontes:
- data/curadoria/*.yaml: nome oficial, grupo, status e textos em pt-BR (editado à mão);
- CSV do judo-techniques-bot: grafias, nomes em inglês e vídeos;
- docs/glossario/judobase_tag_mapping.csv: nomes, códigos e classes da IJF;
- docs/fontes/fecju_kodokan_videos.csv: vídeos do canal do Kodokan listados pela FECJU
  (https://www.fecju.com.br/o-judo), casados pela técnica que o título do vídeo indica.

O script falha quando uma grafia do CSV não é variante do nome oficial nem consta de
nomes_populares.yaml, ou quando uma linha de alguma fonte fica sem destino.

Uso: uv run python scripts/build_glossary.py [--bot-csv CAMINHO]
"""

import argparse
import csv
import sys
from pathlib import Path

import yaml

from judo_chat.normalizer import canonical

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BOT_CSV = ROOT.parent / "judo-techniques-bot" / "judo_techniques_bot" / "data" / "techniques_fixtures.csv"
IJF_CSV = ROOT / "docs" / "glossario" / "judobase_tag_mapping.csv"
KODOKAN_CSV = ROOT / "docs" / "fontes" / "fecju_kodokan_videos.csv"
CURADORIA = ROOT / "data" / "curadoria"
POPULARES = ROOT / "data" / "glossario" / "nomes_populares.yaml"
OUTPUT = ROOT / "data" / "glossario" / "tecnicas.yaml"

_CURATION_KEYS = {
    "id", "name", "csv", "kind", "group", "status", "ijf_name", "name_pt_br", "description_pt_br",
    "notes", "bjj", "drop_english", "english_extra", "video_url",
}  # fmt: skip


def _split(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for item in items:
        if item.lower() not in seen:
            seen.add(item.lower())
            result.append(item)
    return result


def _attach_kodokan_videos(output: list[dict[str, object]]) -> list[str]:
    """Põe os vídeos do Kodokan à frente dos outros. O casamento usa o título do vídeo
    ("足車 / Ashi-guruma"), porque na FECJU o rótulo do Osoto-guruma aponta para o O-guruma."""
    index: dict[str, dict[str, object]] = {}
    for item in output:
        for name in [item["name"], item.get("ijf_name"), *item.get("aliases", [])]:
            if name:
                index.setdefault(canonical(str(name)), item)
    errors = []
    for row in csv.DictReader(KODOKAN_CSV.open(encoding="utf-8")):
        if row["canal"] != "KODOKAN":
            continue
        romaji = row["titulo_video"].split("/")[-1]
        item = index.get(canonical(romaji))
        if item is None:
            errors.append(f"vídeo do Kodokan sem técnica: {row['titulo_video']!r}")
            continue
        current = item.get("videos", [])
        if any(v["url"] == row["url"] for v in current):
            continue
        kodokan = [v for v in current if v["source"] == "kodokan"]
        others = [v for v in current if v["source"] != "kodokan"]
        item["videos"] = [*kodokan, {"url": row["url"], "source": "kodokan", "title": row["titulo_video"]}, *others]
    return errors


def build(bot_csv: Path) -> list[dict[str, object]]:
    bot_rows = {row["japanese_display_name"]: row for row in csv.DictReader(bot_csv.open(encoding="utf-8"))}
    ijf_rows = [r for r in csv.DictReader(IJF_CSV.open(encoding="utf-8")) if r["kind"] == "technique"]
    ijf_by_csv = {r["csv_display_name"]: r for r in ijf_rows}
    popular_keys = {canonical(p["name"]) for p in yaml.safe_load(POPULARES.read_text(encoding="utf-8"))}

    curation = [item for path in sorted(CURADORIA.glob("*.yaml")) for item in yaml.safe_load(path.read_text("utf-8"))]
    errors: list[str] = []
    used_bot: set[str] = set()
    used_ijf: set[str] = set()
    output = []

    for entry in curation:
        tid = entry["id"]
        unknown_keys = set(entry) - _CURATION_KEYS
        if unknown_keys:
            errors.append(f"{tid}: chaves desconhecidas {sorted(unknown_keys)}")
        rows = []
        for name in entry["csv"]:
            if name not in bot_rows:
                errors.append(f"{tid}: linha {name!r} não existe no CSV do bot")
                continue
            used_bot.add(name)
            rows.append(bot_rows[name])

        official = entry["name"]
        ijf = next((ijf_by_csv[n] for n in entry["csv"] if n in ijf_by_csv), None)
        ijf_name = entry.get("ijf_name")
        if ijf is not None:
            used_ijf.add(ijf["judobase_name"])
            subclass = str(entry.get("group", "")).rsplit("/", 1)[-1]
            if subclass != ijf["inferred_class"]:
                errors.append(f"{tid}: grupo {entry.get('group')!r} diverge da IJF ({ijf['inferred_class']})")
            if ijf_name is None and canonical(ijf["judobase_name"]) != canonical(official):
                ijf_name = ijf["judobase_name"]
            elif ijf_name is not None and canonical(ijf_name) != canonical(ijf["judobase_name"]):
                errors.append(f"{tid}: ijf_name {ijf_name!r} diverge da IJF ({ijf['judobase_name']})")

        accepted = {canonical(official)} | ({canonical(ijf_name)} if ijf_name else set())
        candidates = [row["japanese_display_name"] for row in rows]
        candidates += [name for row in rows for name in _split(row["japanese_names"])]
        if ijf is not None:
            candidates.append(ijf["judobase_name"])
        aliases = []
        for name in _unique(candidates):
            key = canonical(name)
            if key in accepted:
                if name not in (official, ijf_name):
                    aliases.append(name)
            elif key not in popular_keys:
                errors.append(f"{tid}: {name!r} não é grafia de {official!r} nem está em nomes_populares.yaml")

        bjj = set(entry.get("bjj", []))
        dropped = set(entry.get("drop_english", []))
        english = [n for row in rows for n in _split(row["english_names"])] + entry.get("english_extra", [])
        english = [n for n in _unique(english + sorted(bjj)) if n not in dropped]

        # `video_url: null` na curadoria descarta o vídeo do CSV do bot.
        video = (
            entry["video_url"] if "video_url" in entry else next((r["video_url"] for r in rows if r["video_url"]), None)
        )
        videos = [{"url": video, "source": "outro"}] if video else []

        item: dict[str, object] = {"id": tid, "name": official, "kind": entry.get("kind", "technique")}
        for key in ("group", "status"):
            if key in entry:
                item[key] = entry[key]
        if ijf_name:
            item["ijf_name"] = ijf_name
        if aliases:
            item["aliases"] = aliases
        if english:
            item["english_names"] = [{"name": n, "usage": "bjj"} if n in bjj else {"name": n} for n in english]
        item["name_pt_br"] = entry["name_pt_br"]
        item["description_pt_br"] = " ".join(entry["description_pt_br"].split())
        item["provenance"] = "generated"
        if videos:
            item["videos"] = videos
        if ijf is not None:
            item["judobase"] = {"code_short": ijf["code_short"], "id_tag": ijf["id_tag"]}
        if entry.get("notes"):
            item["notes"] = entry["notes"]
        output.append(item)

    errors += _attach_kodokan_videos(output)

    for name in sorted(set(bot_rows) - used_bot):
        if canonical(name) not in popular_keys:
            errors.append(f"linha do CSV do bot sem destino: {name!r}")
    for name in sorted({r["judobase_name"] for r in ijf_rows} - used_ijf):
        errors.append(f"técnica da IJF sem destino: {name!r}")

    owners: dict[str, str] = {}
    for item in output:
        names = [item["name"], item.get("ijf_name"), item["name_pt_br"], *item.get("aliases", [])]
        for name in filter(None, names):
            key = canonical(str(name))
            if owners.setdefault(key, str(item["id"])) != item["id"]:
                errors.append(f"chave {key!r} ({name!r}) pertence a {owners[key]} e a {item['id']}")
    for key in popular_keys & owners.keys():
        errors.append(f"nome popular com a mesma forma canônica do nome de {owners[key]}: {key!r}")

    if errors:
        raise SystemExit("Erros na geração do glossário:\n- " + "\n- ".join(errors))
    return sorted(output, key=lambda item: str(item["id"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bot-csv", type=Path, default=DEFAULT_BOT_CSV)
    args = parser.parse_args()
    techniques = build(args.bot_csv)
    header = "# Gerado por scripts/build_glossary.py. Edite data/curadoria/ e rode o script de novo.\n"
    OUTPUT.write_text(header + yaml.safe_dump(techniques, allow_unicode=True, sort_keys=False, width=100), "utf-8")
    print(f"{len(techniques)} entradas gravadas em {OUTPUT.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
