from judo_chat.corpus.models import Corpus
from judo_chat.normalizer import Recognizer
from judo_chat.relations import Relations


def test_uchi_mata_counters(corpus: Corpus, recognizer: Recognizer) -> None:
    relations = Relations(corpus, recognizer).of("uchi-mata", ["contragolpe"])
    counters = {r.target for r in relations if r.source == "uchi-mata"}
    assert counters == {"uchi-mata-gaeshi", "uchi-mata-sukashi", "tai-otoshi"}


def test_every_gaeshi_with_a_named_attack_is_linked(corpus: Corpus, recognizer: Recognizer) -> None:
    targets = {r.target for r in Relations(corpus, recognizer).all() if r.kind == "contragolpe"}
    for technique_id in (
        "osoto-gaeshi",
        "ouchi-gaeshi",
        "kouchi-gaeshi",
        "harai-goshi-gaeshi",
        "hane-goshi-gaeshi",
        "uchi-mata-gaeshi",
        "tsubame-gaeshi",
        "tawara-gaeshi",
    ):
        assert technique_id in targets, technique_id


def test_no_self_or_concept_relations(corpus: Corpus, recognizer: Recognizer) -> None:
    for relation in Relations(corpus, recognizer).all():
        assert relation.source != relation.target
        assert corpus.technique(relation.source).kind == "technique"
        assert corpus.technique(relation.target).kind == "technique"


def test_variations(corpus: Corpus, recognizer: Recognizer) -> None:
    pairs = {(r.source, r.target) for r in Relations(corpus, recognizer).all() if r.kind == "variacao"}
    assert ("seoi-nage", "ippon-seoi-nage") in pairs
    assert ("kesa-gatame", "kuzure-kesa-gatame") in pairs
    assert ("uchi-mata", "uchi-mata-makikomi") in pairs
