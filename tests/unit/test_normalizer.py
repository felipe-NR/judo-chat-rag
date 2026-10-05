import pytest

from judo_chat.corpus.models import Corpus
from judo_chat.normalizer import Recognizer, canonical


def test_every_official_ijf_and_alias_name_resolves(corpus: Corpus, recognizer: Recognizer) -> None:
    for technique in corpus.techniques:
        for name in [technique.name, technique.ijf_name, *technique.aliases]:
            if name is None:
                continue
            entry = recognizer.lookup(name)
            assert entry is not None, name
            assert entry.technique_ids == (technique.id,), name


def test_every_popular_name_resolves_to_its_targets(corpus: Corpus, recognizer: Recognizer) -> None:
    for popular in corpus.popular_names:
        entry = recognizer.lookup(popular.name)
        assert entry is not None, popular.name
        assert entry.technique_ids == popular.technique_ids, popular.name


def test_popular_names_are_derived_on_techniques(corpus: Corpus) -> None:
    assert "Ashi-barai" in corpus.technique("deashi-harai").popular_names
    assert "Ashi-barai" in corpus.technique("okuriashi-harai").popular_names
    assert "Mata-leão" in corpus.technique("hadaka-jime").popular_names


@pytest.mark.parametrize(
    ("variant", "expected"),
    [
        ("O-soto-gari", "osoto-gari"),
        ("Ōsoto-gari", "osoto-gari"),
        ("osotogari", "osoto-gari"),
        ("Tsuri-komi-goshi", "tsurikomi-goshi"),
        ("Sode-tsuri-komi-goshi", "sode-tsurikomi-goshi"),
        ("De-ashi-barai", "deashi-harai"),
        ("Okuri-ashi-harai", "okuriashi-harai"),
        ("seoi nague", "seoi-nage"),
        ("ipon seoi nage", "ippon-seoi-nage"),
        ("Juji-gatame", "ude-hishigi-juji-gatame"),
        ("Kata-Guruma", "kata-guruma"),
        ("Ude-hishigui-juji-gatame", "ude-hishigi-juji-gatame"),
        ("Sassae Tsuri Komi Ashi", "sasae-tsurikomi-ashi"),
    ],
)
def test_spelling_variants(recognizer: Recognizer, variant: str, expected: str) -> None:
    entry = recognizer.lookup(variant)
    assert entry is not None
    assert entry.technique_ids == (expected,)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("como faço ko-uchi-gari?", [("ko-uchi-gari", ("kouchi-gari",))]),
        ("ko soto gari ou o soto gari?", [("ko soto gari", ("kosoto-gari",)), ("o soto gari", ("osoto-gari",))]),
        ("ippon seoi nage de joelho", [("ippon seoi nage", ("ippon-seoi-nage",))]),
        (
            "Ude-hishigi-juji-gatame é igual a juji?",
            [
                ("Ude-hishigi-juji-gatame", ("ude-hishigi-juji-gatame",)),
                ("juji", ("ude-hishigi-juji-gatame",)),
            ],
        ),
        ("Yoko-tomoe-nage existe?", [("Yoko-tomoe-nage", ("tomoe-nage",))]),
        ("o mata-leão do jiu-jitsu", [("mata-leão", ("hadaka-jime",))]),
        ("quem foi Jigoro Kano?", []),
        ("iPhone seoi", [("iPhone seoi", ("ippon-seoi-nage",))]),
        ("O que é o uchi mata?", [("uchi mata", ("uchi-mata",))]),
        ("como faço o uchi gari?", [("o uchi gari", ("ouchi-gari",))]),
        ("e o soto gari?", [("o soto gari", ("osoto-gari",))]),
    ],
)
def test_find_prefers_longest_match(
    recognizer: Recognizer, text: str, expected: list[tuple[str, tuple[str, ...]]]
) -> None:
    assert [(m.term, m.technique_ids) for m in recognizer.find(text)] == expected


def test_ambiguous_popular_name_returns_all_candidates(recognizer: Recognizer) -> None:
    [match] = recognizer.find("Como faço o ashi barai?")
    assert match.ambiguous
    assert set(match.technique_ids) == {"deashi-harai", "okuriashi-harai"}
    assert match.match_type == "popular"


def test_canonical_folds_case_accents_and_rendaku() -> None:
    assert canonical("Ōuchi-Gari") == canonical("ouchi kari") == canonical("OOUCHIGARI")
    assert canonical("Okuri Ashi Barai") == canonical("okuriashi-harai")


def test_autocorrect_is_flagged(recognizer: Recognizer) -> None:
    [match] = recognizer.find("iPhone seoi")
    assert match.match_type == "corretor"
    assert match.technique_ids == ("ippon-seoi-nage",)
