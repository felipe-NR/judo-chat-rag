"""Serializa o corpus no bloco fixo do system prompt.

O prompt caching é por prefixo: o texto precisa sair idêntico byte a byte entre
processos. Por isso tudo é ordenado e nenhum set é iterado sem `sorted`.
"""

from judo_chat.corpus.models import Corpus, Document, PopularName, Technique

# Linhas que se repetiriam em quase toda entrada ficam implícitas para encurtar o corpus:
# tipo "técnica", status "Kodokan" e origem "generated" (declarados nas convenções).
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


def _group(technique: Technique) -> str | None:
    if technique.fgj is not None:
        return f"Kyo-grupo (FGJ): {technique.fgj.kyo_grupo.original}"
    if technique.group:
        return f"Grupo: {technique.group.rsplit('/', 1)[-1]}"
    return None


def render_technique(technique: Technique) -> str:
    """Ficha no bloco fixo. Kanji, vídeos, grafias e nomes em inglês ficam fora: os dois
    primeiros vão na ficha anexada à pergunta, os dois últimos só servem ao reconhecedor."""
    lines = [f"### {technique.name}"]
    if technique.kind != "technique":
        lines.append(f"Tipo: {_KIND[technique.kind]}")
    if technique.status in _STATUS:
        lines.append(f"Status: {_STATUS[technique.status]}")
    if group := _group(technique):
        lines.append(group)
    if technique.ijf_name:
        lines.append(f"Nome usado pela IJF: {technique.ijf_name}")
    fgj = technique.fgj
    if fgj:
        lines.append(f"Tradução (FGJ): {fgj.traducao}")
    if technique.name_pt_br:
        lines.append(f"Significado literal: {technique.name_pt_br}")
    if fgj:
        lines.append(f"Descrição Kodokan (FGJ): {fgj.descricao_kodokan}")
        lines.append(f"Princípio/ponto de atenção (FGJ): {fgj.principio}")
    elif technique.description_pt_br:
        lines.append(f"Descrição: {technique.description_pt_br}")
    return "\n".join(lines)


def _in_block(technique: Technique) -> bool:
    # Conceitos com verbete da FGJ já estão no glossário de termos; repetir só infla o bloco.
    return technique.kind == "technique" or not (technique.fgj_term and technique.fgj_term.conceito)


def render_popular(name: PopularName, corpus: Corpus) -> str:
    targets = " | ".join(corpus.technique(tid).name for tid in name.technique_ids)
    marker = " (ambíguo)" if name.ambiguous else ""
    line = f'- "{name.name}"{marker} -> {targets}'
    return f"{line}. {name.note}" if name.note else line


def render_document(document: Document) -> str:
    # A origem fica no arquivo e no título da seção; repeti-la em cada documento só infla o bloco.
    return f"### {document.title}\n\n{document.body}"


def render_corpus(corpus: Corpus) -> str:
    sections = [
        'Convenções: sem linha "Tipo", a entrada é uma técnica; sem linha "Status", é técnica da '
        "nomenclatura do Kodokan. Os campos (FGJ) vêm do Curso de Waza da Federação Gaúcha de Judô "
        '(2026), fonte primária, e descrevem as técnicas para o tori destro; no kyo-grupo, "1º - '
        'TE-WAZA" é o 1º grupo do Gokyo. As linhas "Descrição" sem (FGJ) foram redigidas para esta '
        "base. Kanji e vídeos não estão aqui: vêm nas fichas anexadas à pergunta.",
        "# GLOSSÁRIO DE TÉCNICAS",
        "\n\n".join(render_technique(t) for t in corpus.techniques if _in_block(t)),
        "# NOMES POPULARES",
        "\n".join(render_popular(p, corpus) for p in corpus.popular_names),
        "# REGRAS",
        "\n\n".join(render_document(d) for d in corpus.documents if d.theme == "regras"),
        "# HISTÓRIA",
        "\n\n".join(render_document(d) for d in corpus.documents if d.theme == "historia"),
        "# EXAMES DE FAIXA (CINZA A MARROM), GOKYO E SÉRIES\n\nRequisitos do Projeto Budô "
        "(https://projetobudo.com.br/exames-de-faixa/), que segue o programa da Federação Paulista de "
        "Judô; os requisitos variam entre federações estaduais.",
        "\n\n".join(render_document(d) for d in corpus.documents if d.theme == "graduacao"),
        "# TERMOS E PRONÚNCIA (FGJ)",
        "\n\n".join(render_document(d) for d in corpus.documents if d.theme == "termos"),
    ]
    return "\n\n".join(sections) + "\n"
