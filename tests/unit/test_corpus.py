import os
import subprocess
import sys
from pathlib import Path

import pytest

from judo_chat.corpus.loader import CorpusError, load_corpus
from judo_chat.corpus.models import Corpus
from judo_chat.corpus.render import render_corpus

from ..conftest import DATA_DIR


def test_corpus_counts(corpus: Corpus) -> None:
    techniques = [t for t in corpus.techniques if t.kind == "technique"]
    assert len(techniques) >= 100
    assert all(t.name_pt_br and t.description_pt_br for t in corpus.techniques)
    assert {d.theme for d in corpus.documents} == {"regras", "historia", "graduacao", "termos"}
    assert len([d for d in corpus.documents if d.id.startswith("graduacao/") and "faixa-" in d.id]) == 7


def test_kodokan_katame_waza_is_complete(corpus: Corpus) -> None:
    groups = [t.group for t in corpus.techniques if t.status != "nonstandard"]
    assert groups.count("katame-waza/osaekomi-waza") == 10
    assert groups.count("katame-waza/shime-waza") == 12
    assert groups.count("katame-waza/kansetsu-waza") == 10


def test_unrelated_video_is_removed(corpus: Corpus) -> None:
    assert all("dQw4w9WgXcQ" not in v.url for t in corpus.techniques for v in t.videos)


def test_kodokan_videos_cover_the_official_list(corpus: Corpus) -> None:
    with_kodokan = [t for t in corpus.techniques if any(v.source == "kodokan" for v in t.videos)]
    # 100 técnicas oficiais na lista da FECJU; o Sasae-tsurikomi-ashi não tem vídeo lá e o link
    # do Osoto-guruma aponta para o vídeo do O-guruma.
    assert len(with_kodokan) == 98
    assert corpus.technique("osoto-guruma").videos[0].source == "outro"
    assert corpus.technique("o-guruma").videos[0].source == "kodokan"


def _render_in_subprocess(seed: str) -> bytes:
    code = (
        "import sys; from pathlib import Path; from judo_chat.corpus.loader import load_corpus;"
        "from judo_chat.corpus.render import render_corpus;"
        f"sys.stdout.buffer.write(render_corpus(load_corpus(Path({str(DATA_DIR)!r}))).encode())"
    )
    env = {**os.environ, "PYTHONHASHSEED": seed}
    return subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, check=True).stdout


def test_render_is_byte_identical_across_hash_seeds() -> None:
    assert _render_in_subprocess("1") == _render_in_subprocess("2")


def test_render_lists_popular_names_sorted(corpus: Corpus) -> None:
    text = render_corpus(corpus)
    assert '"Ashi-barai" (ambíguo) -> Deashi-harai | Okuriashi-harai' in text


def _copy_data(tmp_path: Path) -> Path:
    for path in DATA_DIR.rglob("*"):
        if path.is_file():
            target = tmp_path / path.relative_to(DATA_DIR)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    return tmp_path


def test_loader_rejects_unknown_technique_id(tmp_path: Path) -> None:
    data = _copy_data(tmp_path)
    popular = data / "glossario" / "nomes_populares.yaml"
    popular.write_text(
        popular.read_text("utf-8") + "\n- name: Inexistente\n  technique_ids: [nao-existe]\n"
        "  confidence: baixa\n  source: teste\n",
        "utf-8",
    )
    with pytest.raises(CorpusError, match="nao-existe"):
        load_corpus(data)


def test_fgj_covers_the_100_official_techniques(corpus: Corpus) -> None:
    with_fgj = [t for t in corpus.techniques if t.fgj is not None]
    assert len(with_fgj) == 100
    assert all(t.status != "nonstandard" for t in with_fgj)
    assert sum(1 for t in with_fgj if t.fgj and t.fgj.kyo_grupo.gokyo) == 40
    seoi = corpus.technique("seoi-nage").fgj
    assert seoi is not None and seoi.kanji == "背負投"
    assert seoi.traducao == "PROJEÇÃO COM CARREGAMENTO NAS COSTAS"


def test_render_uses_fgj_description_verbatim(corpus: Corpus) -> None:
    from judo_chat.corpus.render import render_technique

    text = render_technique(corpus.technique("osoto-gari"))
    fgj = corpus.technique("osoto-gari").fgj
    assert fgj is not None
    assert f"Descrição Kodokan (FGJ): {fgj.descricao_kodokan}" in text
    assert "\nDescrição: " not in text


def test_block_leaves_out_recognizer_only_fields(corpus: Corpus) -> None:
    text = render_corpus(corpus)
    assert "youtu" not in text
    assert "Outras grafias" not in text and "Inglês:" not in text
    assert "背負投" not in text
    # Conceitos com verbete da FGJ aparecem só no glossário de termos.
    assert "### Kuzushi" not in text and "- KUZUSHI:" in text
