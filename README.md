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
3. `answer.Answerer` chama o Claude Sonnet 5.5 com instruções e corpus num bloco de system
   cacheado; a pergunta e as técnicas reconhecidas vão na mensagem do usuário.

## Dados

| Caminho | Conteúdo | Editar? |
|-|-|-|
| `data/curadoria/*.yaml` | Nome oficial, grupo, status e textos pt-BR de cada técnica | Sim |
| `data/glossario/nomes_populares.yaml` | Nomes populares, com as técnicas a que se referem | Sim |
| `data/regras/*.md`, `data/historia/*.md` | Textos de regras e história | Sim |
| `data/glossario/tecnicas.yaml` | Glossário final | Não, é gerado |

Depois de editar a curadoria, gere o glossário de novo (o script lê o CSV do
`judo-techniques-bot` na pasta vizinha):

```bash
uv run python scripts/build_glossary.py
```

O build falha quando um nome do CSV não é grafia do nome oficial nem consta de
`nomes_populares.yaml`, quando uma linha das fontes fica sem destino ou quando duas
técnicas disputam o mesmo nome.

Todo o texto em pt-BR está com `provenance: generated` e precisa de revisão por alguém do
judô; as pendências estão no fim de `docs/propostas.md`.

## Testes

```bash
uv run pytest            # sem rede: reconhecedor, corpus, guardrail com fakes, API
uv run pytest -m eval    # chama a API de verdade (custa dinheiro) e grava tests/eval/report.json
uv run ruff check . && uv run ruff format --check .
```
