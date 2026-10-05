# Guia de estilo do corpus em pt-BR

Regras para os textos de `data/curadoria/`, `data/regras/`, `data/historia/` e
`data/graduacao/`. O modelo copia o estilo do corpus nas respostas: um texto duro aqui vira
uma resposta dura lá.

Referências de vocabulário e de visão técnica, por ordem de prioridade:
1. Projeto Budô: https://projetobudo.com.br/tecnicas-do-judo/ e
   https://projetobudo.com.br/exames-de-faixa/
2. FECJU: https://www.fecju.com.br/o-judo (lista oficial do Kodokan e vídeos do canal do
   Kodokan)

## 1. Explique o porquê, não só a sequência de ações

As fichas antigas eram listas de ações traduzidas do inglês ("o tori desequilibra o uke
para trás e ceifa a perna dele"). Diga como o desequilíbrio acontece e para que serve.

- Antes: "O tori desequilibra o uke para trás e ceifa por dentro a perna dele."
- Depois: "O tori movimenta o uke para a frente e depois para trás, ação e reação, para que
  ele jogue o peso nos calcanhares. Com o uke apoiado nos calcanhares, o tori ceifa..."

## 2. Escolha o verbo pela direção do movimento

| Verbo | Uso |
|-|-|
| puxar, trazer | só quando o uke vem na direção do tori |
| empurrar, conduzir, levar | quando o uke se afasta do tori |
| movimentar, deslocar | quando o movimento muda de direção (frente e depois trás) |
| elevar e trazer | tsurikomi; nunca "puxa e levanta" nem "puxando e levantando" |
| varrer | harai: a sola do pé tira o pé do uke do chão |
| ceifar | gari: a perna corta o apoio do uke como uma foice |
| enganchar | gake: o pé ou a perna prende o calcanhar do uke |
| bloquear | sasae: o pé serve de obstáculo, sem varrer |

Exemplo de erro: "puxe o uke para a frente e para trás". "Puxar" não serve para os dois
sentidos; o certo é "movimente o uke para a frente e depois para trás".

## 3. Subjuntivo nas orações de finalidade e consequência

Depois de "para que", "de modo que", "de forma que", "até que" e "antes que", o verbo vai
para o subjuntivo.

- Certo: "gire o corpo de forma que fique mais perto do uke"; "para que ele jogue o peso
  nos calcanhares".
- Errado: "de forma que fica mais perto do uke".

## 4. Tori e uke são papéis, com artigo

"O tori desequilibra o uke", "o pé do uke", "ao uke", "no uke", "pelo uke". Nunca
"tori desequilibra uke" nem "o pé de uke".

## 5. Nada de "dele" quando há duas pessoas na frase

O inglês usa "his" sem ambiguidade de gênero gramatical; em português, numa frase com o
tori e o uke, "o braço dele" pode ser de qualquer um. Repita o papel: "o braço do uke". Use
"dele" só quando o antecedente for único na frase.

## 6. Colocação pronominal brasileira

- Depois do sujeito, use próclise: "o tori se senta", "o tori o levanta". Evite "o tori
  senta-se", "levanta-o".
- Com infinitivo, a ênclise é natural: "em vez de carregá-lo".
- Na dúvida, repita o substantivo: "levanta o uke".

## 7. Gerúndio só para ação simultânea

"Projetando-o para a frente", "derrubando-o de lado" e cadeias de gerúndio vêm do "-ing"
inglês. Prefira uma oração nova ("e o projeta para a frente") ou uma oração de finalidade.
O gerúndio fica quando as ações são de fato simultâneas: "o tori ceifa a perna enquanto
empurra o tronco", "cai girando".

## 8. Nomes em português são significados, não nomes

No Brasil as técnicas são chamadas pelo nome japonês. O campo `name_pt_br` traz o
significado literal ("grande ceifada externa") e aparece no corpus como "Significado
literal". Prefira substantivos a gerúndios ("com elevação e puxada", não "puxando e
levantando").
