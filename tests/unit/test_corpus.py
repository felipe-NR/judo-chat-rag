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
    assert {d.theme for d in corpus.documents} == {"regras", "historia"}


def test_kodokan_katame_waza_is_complete(corpus: Corpus) -> None:
    groups = [t.group for t in corpus.techniques if t.status != "nonstandard"]
    assert groups.count("katame-waza/osaekomi-waza") == 10
    assert groups.count("katame-waza/shime-waza") == 12
    assert groups.count("katame-waza/kansetsu-waza") == 10


def test_unrelated_video_is_removed(corpus: Corpus) -> None:
    assert all("dQw4w9WgXcQ" not in (t.video_url or "") for t in corpus.techniques)


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
    assert '"Ashi-barai" (nome popular, ambíguo, confiança média) -> Deashi-harai | Okuriashi-harai' in text


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
