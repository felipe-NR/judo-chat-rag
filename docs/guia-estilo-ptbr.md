# Guia de estilo do corpus em pt-BR

Fonte primária (North Star): o material técnico da Federação Gaúcha de Judô (FGJ) enviado
pelo usuário em 2026-10-05.
- "Curso de Waza FGJ 2026": técnica, tradução, descrição Kodokan, princípio/ponto de
  atenção e kyo-grupo das 100 técnicas, além do glossário de termos e do guia de pronúncia.
  Importado em `data/fgj/` por `scripts/import_fgj.py`.
- "Técnicas Nage-Waza e Katame-Waza FGJ": lista das 100 técnicas com o kanji.
- "Material 40 (shodan)": as 40 técnicas do Gokyo no mesmo formato, usado para conferência.

## Regra geral

**Quando a FGJ tem o texto, ele é usado sem edição.** A tradução, a descrição Kodokan, o
princípio/ponto de atenção e o kyo-grupo das 100 técnicas oficiais vêm de `data/fgj/` tal
como estão no documento, e o mesmo vale para os termos do glossário da FGJ. Nenhum texto
redigido para o corpus substitui ou "melhora" esses campos.

**Quando a FGJ não tem o texto**, o que inclui técnicas fora do Kodokan, conceitos sem
verbete no glossário, regras, história, exames e respostas do assistente, escreva como o
material da FGJ. A técnica é explicada pelo significado dos seus termos japoneses, com o
vocabulário técnico em português que a FGJ usa, em dois registros:
1. **Descrição:** definição objetiva, no padrão Kodokan;
2. **Princípio/ponto de atenção:** orientação didática curta.

## 1. Vocabulário técnico

Use o termo em português que a FGJ dá para cada elemento do nome japonês. Ele explica o
movimento que dá nome à técnica.

| Termo | Em português (FGJ) | Princípio do movimento (FGJ) |
|-|-|-|
| nage | projeção | suspensão do uke para em seguida ser projetado |
| otoshi | derrubada (brusca) | derrubada brusca, diretamente para baixo, sem suspensão |
| gari | ceifa | o peso está na perna a ser ceifada, como no corte de uma raiz |
| harai | varredura | varrer como quem varre um objeto leve |
| gake | enganchamento | suspensão do uke e movimento de baixo para cima, como quem arranca uma raiz com um ancinho |
| guruma | rotação | movimento que causa uma rotação, um giro |
| tsurikomi | suspensão e puxada | suspensão e puxada para si |
| tsuri | puxada/içamento | puxar para cima |
| okuri | condução | levar de um lado para outro |
| sukui | colhimento/levantamento | colhida com levantamento |
| taoshi | tombamento | empurrão combinado com puxada para baixo; cai como um dominó |
| uki | flutuação | breve suspensão que resulta no desequilíbrio |
| hane | impulsão | |
| utsuri | transferência | |
| makikomi | enrolamento | o tori envolve o uke em si para cair junto, em sacrifício |
| wakare | separação | o tori de um lado e o uke de outro |
| sukashi | abertura de espaço | |
| gaeshi | contragolpe/inversão | |
| garami | entrelaçamento | |
| basami | pinça | |
| gatame | domínio | |
| shime, jime | estrangulamento | restrição do fluxo sanguíneo ou das vias aéreas |
| ude-hishigi | luxação de braço | |
| kuzushi | desestabilização (quebra do equilíbrio) | deixar o uke como precisamos para projetá-lo |
| tsukuri / kake | preparação / aplicação, execução | |
| hikite / tsurite | pegada que puxa (manga) / pegada que suspende (gola) | |
| ai-yotsu / kenka-yotsu | pegada mútua / pegada disputada | destro x destro / destro x canhoto |
| o / ko | maior / menor | |
| soto / uchi | exterior, por fora / interior, por dentro | |
| ushiro / ura | trás / retaguarda | |

O glossário completo, com 93 termos, está em `data/fgj/termos.yaml`.

Consequências práticas:
- "ceifa" e "varredura" são substantivos diferentes; nunca "ceifada" ou "varrida" no lugar
  deles;
- te-waza são "técnicas de membros superiores", ashi-waza "de membros inferiores",
  ma-sutemi-waza "de sacrifício pleno" e yoko-sutemi-waza "de sacrifício lateral";
- katame-waza são "técnicas de domínio"; osaekomi-waza "de imobilização ou retenção";
  kansetsu-waza "técnicas nas articulações".

## 2. Registro da descrição (padrão Kodokan)

- Abra com a finalidade, no infinitivo: "Uma técnica para derrubar o oponente...",
  "Técnica para segurar o oponente no chão...".
- Na descrição, a outra pessoa é "o oponente"; nas explicações e nos pontos de atenção, use
  "o tori" e "o uke".
- Encadeie com gerúndio as ações simultâneas, como faz o Kodokan: "quebrando seu equilíbrio
  para frente e girando o corpo para a esquerda".
- A ênclise é a forma do registro: "desequilibrando-o", "derrubá-lo", "carregá-lo nas
  costas".
- Deixe lado e direção explícitos, sempre para o tori destro: "pé direito", "com o pé
  esquerdo", "para o canto frontal direito", "para o canto traseiro direito".

## 3. Registro do princípio/ponto de atenção

- Defina pelo termo japonês: "OTOSHI = Movimento de uma derrubada brusca, diretamente para
  baixo, sem suspensão."
- Destaque em maiúsculas a ação ou o momento decisivo: "Ceifa APÓS ele ter DEPOSITADO seu
  peso no pé de apoio"; "ABRACE a cintura e APROXIME O QUADRIL".
- Nas técnicas de domínio, use listas nominais curtas: "Domínio em diagonal / Controle do
  braço / Quadril baixo".
- Nos contragolpes, diga de qual tentativa é o contragolpe e o que o tori faz: "Contragolpe
  de uma tentativa de O-uchi-gari."

## 4. Nomes e pronúncia

- Escreva o nome no romaji hifenizado da FGJ e do Kodokan ("O-soto-gari", "Ko-uchi-gari").
  O nome principal do corpus continua o do Kodokan.
- Quando houver, dê o kanji.
- "Tradução (FGJ)" e "Significado literal" são campos diferentes: o primeiro é o da FGJ e o
  segundo é o significado redigido para o corpus. Mostre os dois.
- Para orientar a pronúncia, siga o guia da FGJ: ch = "tch"; g sempre duro (nage = "nague");
  h aspirado (hiza = "riza"); j = "dj"; r fraco; s sempre "ss" (kesa = "kessa"); w = "u"
  (waza = "uáza").

## 5. Norma culta

- Tori e uke levam artigo e contração: "o tori", "o pé do uke", "ao uke".
- Concordância de gênero e número conferida; nomes de técnicas no masculino ("o
  Uchi-mata").
- Sem gírias ("pra", "a galera"). Termos de dojô em português, como "mata-leão" e
  "baiana", entram só como nomes populares.
