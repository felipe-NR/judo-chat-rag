"""Serializa o corpus no bloco fixo do system prompt.

O prompt caching é por prefixo: o texto precisa sair idêntico byte a byte entre
processos. Por isso tudo é ordenado e nenhum set é iterado sem `sorted`.
"""

from judo_chat.corpus.models import Corpus, Document, PopularName, Technique

# Linhas que se repetiriam em quase toda entrada ficam implícitas para encurtar o corpus:
# tipo "técnica", status "Kodokan" e origem "generated" (declarados no cabeçalho).
DEFAULT_PROVENANCE = "generated"
_STATUS = {
    "nonstandard": "fora da nomenclatura do Kodokan",
    "forbidden_ijf": "técnica do Kodokan proibida em competição pela IJF",
}
_KIND = {
    "technique": "técnica",
    "category": "categoria de técnicas",
    "concept": "conceito",
    "grip": "pegada (kumi-kata)",
}


def _sorted_names(names: frozenset[str]) -> str:
    return ", ".join(sorted(names, key=str.lower))


_KYO_CLASS = {"habukareta-waza": "habukareta-waza", "shinmeisho-no-waza": "shinmeisho-no-waza"}


def _kyo(technique: Technique) -> str | None:
    if technique.fgj is None:
        return None
    grupo = technique.fgj.kyo_grupo
    if grupo.gokyo:
        return f"{grupo.original} ({grupo.gokyo}º grupo do Gokyo)"
    return grupo.original


def render_technique(technique: Technique) -> str:
    lines = [f"### {technique.name} [{technique.id}]"]
    fgj = technique.fgj
    if fgj:
        lines.append(f"Kanji: {fgj.kanji}")
    if technique.kind != "technique":
        lines.append(f"Tipo: {_KIND[technique.kind]}")
    if technique.status in _STATUS:
        lines.append(f"Status: {_STATUS[technique.status]}")
    if technique.group:
        lines.append(f"Grupo: {technique.group}")
    if kyo := _kyo(technique):
        lines.append(f"Kyo-grupo (FGJ): {kyo}")
    if technique.ijf_name:
        lines.append(f"Nome usado pela IJF: {technique.ijf_name}")
    term = technique.fgj_term
    if fgj:
        lines.append(f"Tradução (FGJ): {fgj.traducao}")
    elif term:
        lines.append(f"Tradução (FGJ): {term.traducao}")
    if technique.name_pt_br:
        lines.append(f"Significado literal: {technique.name_pt_br}")
    if technique.popular_names:
        lines.append(f"Nomes populares: {_sorted_names(technique.popular_names)}")
    if technique.aliases:
        lines.append(f"Outras grafias: {', '.join(technique.aliases)}")
    judo_en = [e.name for e in technique.english_names if e.usage == "judo"]
    bjj_en = [e.name for e in technique.english_names if e.usage == "bjj"]
    if judo_en:
        lines.append(f"Inglês: {', '.join(judo_en)}")
    if bjj_en:
        lines.append(f"Nomes no jiu-jitsu (BJJ): {', '.join(bjj_en)}")
    if fgj:
        # Fonte primária: o texto da FGJ substitui a descrição redigida para o corpus.
        lines.append(f"Descrição Kodokan (FGJ): {fgj.descricao_kodokan}")
        lines.append(f"Princípio/ponto de atenção (FGJ): {fgj.principio}")
    elif term and term.conceito:
        lines.append(f"Conceito (FGJ): {term.conceito}")
    elif technique.description_pt_br:
        lines.append(f"Descrição: {technique.description_pt_br}")
    for video in technique.videos:
        label = "Vídeo do Kodokan" if video.source == "kodokan" else "Vídeo (outra fonte, não é do Kodokan)"
        lines.append(f"{label}: {video.url}")
    lines.extend(f"Observação: {note}" for note in technique.notes)
    if not fgj and not term and technique.provenance != DEFAULT_PROVENANCE:
        lines.append(f"Origem do texto: {technique.provenance}")
    return "\n".join(lines)


_POPULAR_KIND = {
    "popular": "nome popular",
    "truncation": "abreviação",
    "nonstandard": "nome fora do Kodokan",
    "pt_br": "termo em português",
    "bjj": "termo do jiu-jitsu",
}
_CONFIDENCE = {"alta": "alta", "media": "média", "baixa": "baixa"}


def render_popular(name: PopularName, corpus: Corpus) -> str:
    targets = " | ".join(corpus.technique(tid).name for tid in name.technique_ids)
    marker = "ambíguo" if name.ambiguous else "único"
    kind = _POPULAR_KIND[name.kind]
    line = f'- "{name.name}" ({kind}, {marker}, confiança {_CONFIDENCE[name.confidence]}) -> {targets}'
    return f"{line}. {name.note}" if name.note else line


def render_document(document: Document) -> str:
    header = f"### {document.title} [{document.id}]"
    if document.provenance != DEFAULT_PROVENANCE:
        header += f"\nOrigem do texto: {document.provenance}"
    return f"{header}\n\n{document.body}"


def render_corpus(corpus: Corpus) -> str:
    sections = [
        'Convenções: sem linha "Tipo", a entrada é uma técnica; sem linha "Status", é técnica da '
        'nomenclatura do Kodokan; sem linha "Origem do texto", o texto foi redigido automaticamente '
        f"({DEFAULT_PROVENANCE}) e ainda não foi revisado.",
        "# GLOSSÁRIO DE TÉCNICAS",
        "\n\n".join(render_technique(t) for t in corpus.techniques),
        "# NOMES POPULARES",
        "\n".join(render_popular(p, corpus) for p in corpus.popular_names),
        "# REGRAS",
        "\n\n".join(render_document(d) for d in corpus.documents if d.theme == "regras"),
        "# HISTÓRIA",
        "\n\n".join(render_document(d) for d in corpus.documents if d.theme == "historia"),
        "# EXAMES DE FAIXA (CINZA A MARROM), GOKYO E SÉRIES",
        "\n\n".join(render_document(d) for d in corpus.documents if d.theme == "graduacao"),
        "# TERMOS E PRONÚNCIA (FGJ)",
        "\n\n".join(render_document(d) for d in corpus.documents if d.theme == "termos"),
    ]
    return "\n\n".join(sections) + "\n"
