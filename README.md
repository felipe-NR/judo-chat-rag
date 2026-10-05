# Judô Chat

Assistente que responde em português do Brasil a perguntas sobre técnicas, história e
regras do judô, e recusa qualquer outro assunto. Implementa a proposta A de
[`docs/propostas.md`](docs/propostas.md): o corpus inteiro vai no contexto do Claude, com
prompt caching, depois de um guardrail de escopo que falha fechado.

## Rodar

```bash
uv sync
cp .env.example .env   # preencha ANTHROPIC_API_KEY
uv run uvicorn judo_chat.main:app --reload
```

A página de chat fica em http://localhost:8000 e a API em `POST /api/perguntar`
(`{"query": "como faço o ashi barai?"}`).

## Publicar (GitHub Pages + API local via ngrok)

A página de chat fica em https://felipe-nr.github.io/judo-chat-rag/, publicada pelo
workflow `.github/workflows/pages.yml` a cada push que mexe em `src/judo_chat/static/`.
O GitHub Pages só serve arquivos estáticos, então a API roda nesta máquina e é exposta pelo
domínio fixo do ngrok da conta (`https://quadrantal-glenda-interstream.ngrok-free.dev`):

```bash
./start-ngrok.sh   # sobe a API na porta 8010 (JUDO_CHAT_PORT) e o túnel ngrok
./stop-ngrok.sh    # derruba os dois
```

A chave da Anthropic fica só no `.env` local; a página nunca a vê. Com a API desligada, a
página carrega mas avisa que não conseguiu falar com o servidor. A conta ngrok gratuita tem
um túnel por vez: o script se recusa a subir se o túnel de outro projeto (por exemplo o
`delivery-platform`) estiver no ar. Para usar outra URL de API, crie a variável de
repositório `JUDO_CHAT_API_URL` e rode o workflow de novo.

## Como funciona

1. `normalizer.Recognizer` acha nomes de técnica na pergunta: nome oficial, nome da IJF,
   grafias variadas e nomes populares (ambíguos devolvem todas as candidatas).
2. `guardrail.Guardrail` classifica a pergunta em `tecnica`, `historia`, `regras` ou `fora`
   com o Claude Haiku 4.5. Qualquer erro bloqueia a resposta.
3. `answer.Answerer` chama o Claude Haiku 4.5 com instruções e corpus (~27 mil tokens) num
   bloco de system cacheado por 5 minutos; a pergunta e as técnicas reconhecidas vão na
   mensagem do usuário.

## Custo

Medido em 2026-10-05 com o Haiku 4.5 (US$ 1/M de entrada, US$ 5/M de saída, cache: gravação
US$ 1,25/M com TTL de 5 minutos e leitura US$ 0,10/M), dólar a R$ 5, sem IOF. O corpus tem
~53 mil tokens desde que entrou o material da FGJ.

| Caso | US$ | R$ |
|-|-|-|
| Pergunta com cache quente | ~0,008 | ~0,04 |
| Primeira pergunta após 5 min parado (grava o cache) | ~0,07 | ~0,35 |
| Pergunta fora do escopo (só o guardrail) | ~0,001 | ~0,005 |

O Sonnet 5.5 dá respostas mais fiéis à base por cerca de 3-4x o custo; veja `.env.example`.

## Dados

| Caminho | Conteúdo | Editar? |
|-|-|-|
| `data/curadoria/*.yaml` | Nome oficial, grupo, status e textos pt-BR de cada técnica | Sim |
| `data/glossario/nomes_populares.yaml` | Nomes populares, com as técnicas a que se referem | Sim |
| `data/regras/*.md`, `data/historia/*.md` | Textos de regras e história | Sim |
| `data/graduacao/*.md` | Exames de faixa (cinza a marrom), Gokyo, sequências e contragolpes, do Projeto Budô | Sim |
| `docs/fontes/fecju_kodokan_videos.csv` | Vídeos do canal do Kodokan listados pela FECJU | Sim |
| `data/fgj/*.yaml` | Fonte primária: tradução, descrição Kodokan, princípio, kyo-grupo e kanji das 100 técnicas, glossário e pronúncia da FGJ | Não, gerado por `scripts/import_fgj.py` |
| `data/glossario/tecnicas.yaml` | Glossário final | Não, é gerado |

Depois de editar a curadoria, gere o glossário de novo (o script lê o CSV do
`judo-techniques-bot` na pasta vizinha):

```bash
uv run python scripts/build_glossary.py
```

O build falha quando um nome do CSV não é grafia do nome oficial nem consta de
`nomes_populares.yaml`, quando uma linha das fontes fica sem destino ou quando duas
técnicas disputam o mesmo nome.

A fonte primária das técnicas é o Curso de Waza da Federação Gaúcha de Judô (FGJ, 2026),
importado com `uv run --with pdfplumber python scripts/import_fgj.py CURSO.pdf LISTA_KANJI.pdf`.
O texto da FGJ é usado sem edição; o que não vem dela segue `docs/guia-estilo-ptbr.md`, e
`tests/unit/test_corpus_style.py` pega regressões. As fichas de técnica estão com `provenance: generated`; os exames de faixa
trazem a URL da página do Projeto Budô de onde vieram.

## Testes

```bash
uv run pytest            # sem rede: reconhecedor, corpus, guardrail com fakes, API
uv run pytest -m eval    # chama a API de verdade (custa dinheiro) e grava tests/eval/report.json
uv run ruff check . && uv run ruff format --check .
```
