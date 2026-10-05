# Três propostas de assistente de judô em pt-BR

## Contexto

O assistente responde em pt-BR a perguntas em linguagem natural de usuários brasileiros. O escopo se limita a técnicas, história e regras do judô (uma resposta pode cruzar os três temas), e qualquer outro assunto é recusado. As propostas juntam o que as sessões dos repositórios vizinhos relataram em 2026-10-03 e 2026-10-04. A proposta A está implementada neste repositório (ver o README).

| Repo | Oferece | Não oferece |
|-|-|-|
| `judobase` (cliente async da API não oficial da IJF, MIT) | Nomes de técnica da IJF em romaji (`EventTag.name`), código estável (`code_short`, `id_tag`), classe da técnica via `id_groups` e estatística de uso por competição | Texto sobre técnicas, regras ou história, conteúdo em pt-BR. A API vem de engenharia reversa e os termos de uso da IJF não foram verificados. O `ftechique` dos atletas é vocabulário controlado, não traz nomes populares |
| `judo-techniques-bot` (bot do Reddit, regex, sem LLM) | 132 linhas com nome japonês, variantes, nomes em inglês e vídeo (`judo_techniques_bot/data/techniques_fixtures.csv`) | Descrições, regras, história, pt-BR. O LICENSE está vazio: reusar o CSV exige permissão do autor (AbundantSalmon). A regex de reconhecimento casa substrings ("Ko-uchi-gari" dispara O-uchi-gari) |
| `production-agentic-rag-course` (referência de RAG) | Esqueleto FastAPI (lifespan, Depends), guardrail por LLM, busca híbrida no OpenSearch, grafo LangGraph, tracing Langfuse | Avaliação offline, prompts em pt-BR. Os fallbacks do guardrail e do grading falham aberto |

Nenhum repositório tem o texto em pt-BR sobre técnicas, regras e história. Desde 2026-10-05, a fonte primária das técnicas é o Curso de Waza da Federação Gaúcha de Judô (FGJ, 2026), com tradução, descrição Kodokan, princípio e kyo-grupo das 100 técnicas oficiais, importado em `data/fgj/`. Esse corpus foi redigido para a proposta A a partir dos dados locais (`provenance: generated`) e precisa de revisão por alguém do judô.

## Base comum às três propostas

### Glossário de técnicas com nomes populares

Cada técnica tem um nome principal e um conjunto de nomes populares. No Brasil é comum uma técnica ser conhecida pelo nome oficial do Kodokan e também por outro nome, às vezes usado de forma errada há anos ("ashi barai", "morote seoi-nage", "mata-leão").

| Campo | Conteúdo |
|-|-|
| `name` | Nome oficial do Kodokan, nome principal |
| `ijf_name` | Nome curto da IJF quando difere (`Juji-gatame` para `Ude-hishigi-juji-gatame`). É o padrão de competição, não conta como erro |
| `aliases` | Só variantes de grafia: hífen, espaço, caixa, macron, rendaku |
| `popular_names` | Conjunto derivado de `data/glossario/nomes_populares.yaml` |
| `english_names` | `{name, usage: judo/bjj}`; os de BJJ nunca viram base de tradução |
| `name_pt_br`, `description_pt_br`, `provenance` | Texto em pt-BR e sua origem (`generated`, `translated_from_en`, `reviewed`, `web:<url>`) |
| `kind`, `group`, `status` | technique/category/concept/grip; grupo do Kodokan; kodokan/nonstandard/forbidden_ijf |
| `video_url`, `judobase` | Vídeo do CSV do bot; `code_short` e `id_tag` da IJF |

Cada nome popular é guardado uma única vez, como entidade própria: `{name, technique_ids, kind, confidence, source, note}`. Um nome com mais de um `technique_ids` é ambíguo (Ashi-barai → Deashi-harai ou Okuriashi-harai; Seoi; Drop Seoi; Sankaku; Rasteira; Jigoku-jime). O conjunto `popular_names` de cada técnica é calculado no carregamento, o que evita duas cópias divergentes.

Regra de classificação, aplicada pelo `scripts/build_glossary.py`:
- Iguala o nome oficial ou o nome da IJF depois da normalização → vai para `aliases`.
- Tem um elemento japonês mas não iguala (truncamento, elemento trocado, nome fora do Kodokan) ou é termo de dojô em português → vai para `nomes_populares.yaml`. O build falha se um nome do CSV não se encaixar em nenhum dos dois.
- Não tem elemento japonês (Kimura, Side Control) → vai para `english_names` com `usage=bjj`; os de uso comum no Brasil também viram nome popular `kind: bjj`.

Política de resposta: o assistente usa o nome oficial e avisa quando o usuário usou um nome popular. Diante de um nome ambíguo, ele não escolhe em silêncio: apresenta as candidatas com o que distingue cada uma e responde sobre todas ou pergunta.

### Reconhecimento de nomes

A forma canônica de comparação usa minúsculas, remove diacríticos, espaço e hífen, troca `ou`→`o`, equaliza o rendaku (barai/harai, gari/kari, gatame/katame, jime/shime etc.) e a grafia "nague", e colapsa letras dobradas. No texto livre, o reconhecedor procura janelas de até 6 palavras, fica com a mais longa e descarta palavras de borda que somem na canonização ("é", "ou"). Os casos que a regex do bot errava estão nos testes.

### Guardrail que falha fechado

Um classificador (Haiku 4.5, saída estruturada) devolve `tecnica|historia|regras|fora`. Exceção, timeout, saída fora do schema, `stop_reason` diferente de `end_turn` ou resposta vazia bloqueiam a resposta. Quando o bloqueio vem de falha, a mensagem é de indisponibilidade, e não de fora do escopo. A pergunta vai delimitada em `<pergunta>` e é tratada como dado.

### Avaliação

`tests/eval/cases.yaml` tem 157 perguntas: 122 dentro do escopo (técnica com grafias variadas, nomes populares e ambíguos, conceitos, regras, história, misto) e 35 fora (25 temas gerais e 10 adversariais). O reconhecedor roda contra todas sem rede, no CI. Guardrail e resposta rodam com `pytest -m eval`, com as metas de falso-aceite adversarial igual a 0, recusa correta de 95% ou mais e falsa recusa de 5% ou menos.

## Proposta A: LLM com o corpus inteiro no contexto (implementada)

- **Fluxo:** pergunta → reconhecedor → guardrail (Haiku 4.5) → Haiku 4.5 com instruções e corpus num bloco de system cacheado → resposta. A primeira versão usava o Sonnet 5.5; a troca em 2026-10-04 cortou o custo projetado para 23-30% do anterior (ver README).
- **Corpus no contexto:** 27 mil tokens no Haiku 4.5 (38 mil no tokenizador do Sonnet 5.5): 124 entradas de glossário (104 técnicas), 41 nomes populares, 4 textos de regras e 3 de história.
- **Cache:** o bloco de system é montado uma vez no startup e serializado de forma determinística (ordenado, sem set iterado sem `sorted`, sem data). Um teste compara os bytes gerados com `PYTHONHASHSEED` diferentes. As técnicas reconhecidas e os candidatos dos nomes ambíguos vão na mensagem do usuário, depois do breakpoint. TTL de 5 minutos, porque o uso esperado (sessões espaçadas de horas) nunca reaproveitaria o de 1 hora; um modelo só para a resposta.
- **Recusa por política do modelo:** `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`) só com modelos da geração 5; ligável em `JUDO_CHAT_USE_REFUSAL_FALLBACKS` ao voltar para o Sonnet 5.5.
- **Prós:** poucas peças e resposta que cruza temas porque o modelo vê tudo. Atualizar o conteúdo é editar a curadoria e rodar o build.
- **Contras:** o custo cresce com o corpus (o cache reduz a leitura a cerca de 10%). Não escala além do contexto. A citação de fonte é por seção, não por trecho.

## Proposta B: RAG clássico com busca híbrida

- **Fluxo:** pergunta → reconhecedor → guardrail → expansão de consulta → busca híbrida (BM25 com analyzer `portuguese` + vetor, fundidos por RRF) filtrada pelo tema → top-k trechos → resposta citando os trechos.
- **Expansão pelo glossário:** os nomes populares e as grafias reconhecidas são reescritos para o nome oficial antes da busca, e a ficha da técnica entra direto no contexto pelo `id`. Isso resolve o caso em que "ashi barai" não aparece em nenhum trecho do regulamento.
- **Stack:** OpenSearch seguindo `src/services/opensearch/index_config_hybrid.py` do curso com o analyzer trocado; embeddings multilíngues (jina-embeddings-v3 via API ou bge-m3 local); chunk por ficha de técnica e por artigo de regra. Docling só para o PDF do regulamento.
- **Prós:** o corpus pode crescer (regulamentos de vários anos, textos longos de história) e a resposta cita o trecho.
- **Contras:** índice e pipeline de ingestão para manter. Exige avaliação de retrieval (recall@k), a ser acrescentada aos casos de avaliação.

## Proposta C: RAG agentic com roteamento (LangGraph)

- **Fluxo:** o grafo do curso adaptado: guardrail → roteador → tools → grading por documento → rewrite (no máximo 2 tentativas) → geração → checagem de grounding.
- **Tools:** `ficha_tecnica(nome)` (consulta o reconhecedor e devolve a ficha, incluindo os candidatos de um nome ambíguo); `buscar_corpus(tema, consulta)` (a busca da proposta B); `estatistica_tecnica(code_short, competicao?)` (uso das técnicas nos eventos do judobase, a partir de um snapshot periódico ligado ao glossário pelo `code_short`).
- **Correções ao copiar o curso:** fallbacks que falham fechado, prompts e mensagens em pt-BR, remoção do código morto `DECISION_PROMPT` e grading por documento.
- **Prós:** recusa auditável no trace; combina texto com estatística ("qual técnica mais pontuou nos Jogos de Paris").
- **Contras:** 3-5 chamadas de LLM por pergunta; mais peças; depende da API instável do judobase.

## Comparação

| | A | B | C |
|-|-|-|-|
| Estado | implementada | proposta | proposta |
| Infra | API de LLM | + OpenSearch, embeddings | + LangGraph, Langfuse, snapshot do judobase |
| Chamadas de LLM por pergunta | 2 | 2 | 3-5 |
| Tamanho do corpus | limitado ao contexto | cresce | cresce |
| Cita a fonte | por seção | por trecho | por trecho |
| Estatística de técnicas | não | não | sim |

**Recomendação:** manter a A enquanto o corpus couber no contexto e a avaliação passar nas metas. Migrar para a B quando entrarem textos longos (regulamento completo, várias edições). Adotar a C só se as perguntas estatísticas entrarem no produto.

## Pendências

- **Licença:** pedir ao autor do judo-techniques-bot permissão para usar o CSV (o glossário gerado deriva dele) e verificar os termos de uso do data.ijf.org.
- **Revisão de conteúdo:** todas as descrições, regras e textos de história estão com `provenance: generated`. Foram conferidos na web, em 2026-10-04, só o retorno do yuko em 2025 e os tempos de imobilização (5, 10 e 20 segundos).
- **Lista do Kodokan:** confirmada em 2026-10-05 pela lista oficial da FECJU (100 técnicas: 68 nage-waza e 32 katame-waza), que bate com a classificação do corpus em todas. As formas curtas da IJF para as chaves de braço fora da amostra (Ude-gatame, Hiza-gatame, Waki-gatame, Hara-gatame, Ashi-gatame, Te-gatame, Sankaku-gatame) continuam sem confirmação.
- **Vídeos:** 98 técnicas têm vídeo do canal do Kodokan, listado primeiro. Na FECJU, o link do Osoto-guruma aponta para o vídeo do O-guruma e o do Sasae-tsurikomi-ashi não é vídeo; essas duas ficam só com o vídeo do CSV do bot.
- **Mecânica revisada:** 18 fichas reescritas e revisadas pela sessão do judo-techniques-bot em 2026-10-05; o Harai-tsurikomi-ashi e o pé exato do Okuriashi-harai ficaram com confiança baixa e devem ser conferidos nos vídeos do Kodokan.
- **Nomes populares de confiança média ou baixa:** conferir nas fontes autorizadas pelo usuário (sites das federações estaduais, Projeto Budô, @rafaelsilvajudo, @judoparatodosoficial). Reverse seoi-nage, Yagura-nage e Jigoku-jime continuam sem classificação oficial segura.
- **Vídeo removido:** a linha "Kake" do CSV do bot apontava para um vídeo sem relação com judô (`dQw4w9WgXcQ`).
- **ai-memory:** o `judo-chat-rag` não tem `.ai-memory.toml`.

Os arquivos de evidência das sessões estão em `docs/glossario/`: `judobase_tag_mapping.csv` (96 rótulos da IJF com o casamento com o CSV do bot) e `match_test.py` (teste da regex do bot, roda a partir da raiz do judo-techniques-bot).
