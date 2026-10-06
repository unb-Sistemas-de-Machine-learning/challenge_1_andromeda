# Checagem de fatos verificáveis

O critério `verifiable_facts` usa a Google Fact Check Tools API para recuperar
checagens publicadas sobre **uma afirmação principal selecionada** e até duas
frases candidatas complementares, apresentadas separadamente. Não atribui reputação
ao veículo, ao autor ou à agência de checagem. Também não executa uma investigação
factual nova sobre todos os fatos da notícia.

Consulte o [manual de integração](Manual_Google_Fact_Check_Tools_API.md) para
requisições, paginação, configuração e uso do cliente, e o
[guia da interface e API](InterfaceEAPI.md) para exibição e diagnóstico.

## O que o Google retorna

[`claims.search`](https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims/search)
retorna afirmações já checadas. Cada
[`Claim`](https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims)
contém `text`, o texto da afirmação, e pode incluir `claimant`, `claimDate` e
`claimReview[]`. Uma revisão contém `publisher`, `url`, `title`, `reviewDate`,
`textualRating` e `languageCode`.

`textualRating` é o veredito textual da agência sobre a afirmação.
`publisher` identifica a agência responsável pela checagem. O endpoint não
fornece uma escala numérica universal de veracidade ou de reputação.

## Entradas e escopo

```json
{
  "url": "https://example.com/noticia",
  "user_id": "demo",
  "claim": "Uma afirmação verificável que desejo consultar"
}
```

`claim` é opcional, de 3 a 500 caracteres. Quando informado, somente ele é
consultado. Sem esse campo, o sistema seleciona até três candidatos: título
limpo e frases iniciais do texto, sem repetir frases iguais. Candidatos automáticos
têm 15 a 500 caracteres e pelo menos três palavras; perguntas são ignoradas.
São examinadas até vinte frases. O primeiro candidato é a afirmação principal.

As frases são preservadas, sem inventar sujeitos, reescrever alegações ou separar
orações por conjunções. Essa seleção heurística não garante afirmações atômicas
nem extrai todos os fatos. Para uma afirmação precisa, use o campo `claim`.
Afirmações complementares ficam em `additional_claims` e **não entram na nota**.

A afirmação informada pelo usuário tem prioridade e sua checagem não significa
que a notícia a endossa. O BERTimbau continua recebendo o texto extraído da
notícia, independentemente da afirmação selecionada.

## Busca e correspondência

Cada candidato usa até duas consultas: sua própria frase e uma alternativa de
até dez palavras significativas. Não se concatena título com corpo. Consultas
são limitadas a 300 caracteres e deduplicadas; a afirmação original é preservada
para correspondência. Consultas idênticas entre candidatos reutilizam a resposta.

As respostas das consultas são reunidas antes do cálculo, mesmo após encontrar
uma revisão utilizável. Isso permite expor divergências de outras consultas;
duplicatas continuam excluídas do cálculo. Há no máximo seis buscas, três páginas
por busca e dez afirmações por página: até dezoito requisições HTTP, sem retries.
Os limites não garantem completude do acervo nem tempo total fixo.

Cada consulta usa `languageCode=pt`. Paginação mantém os parâmetros e usa
`nextPageToken`; limite ou repetição são sinalizados em `search_truncated`.
Falhas posteriores preservam evidências anteriores e marcam `search_incomplete`.
Chave ausente ou respostas 401/403/429 encerram novas buscas. Sem evidência
utilizável não há nota; uma falha é distinguida da ausência de resultados.

A correspondência compara a afirmação selecionada com `Claim.text`, sem usar
o título da revisão como prova de identidade. O filtro rejeita diferenças nas
sequências numéricas, na presença de negações e nos marcadores de desmentido.
Também preserva siglas estaduais explícitas (DF, SP, RJ etc.), reconhece
DF/Distrito Federal e protege formas de aumentar/reduzir e retomar/suspender.
Depois aceita igualdade normalizada ou pelo menos três palavras significativas
com interseção de 80% em ambas as direções.

Esse filtro é lexical e conservador: não demonstra equivalência semântica,
identidade temporal ou concordância factual. Paráfrases podem ser excluídas e
textos semelhantes ainda podem exigir inspeção humana. Datas, afirmações e
links originais são apresentados para permitir essa inspeção.

## Escala do projeto

O projeto converte somente rótulos completos reconhecidos, após normalização
de acentos, espaços e pontuação. A escala é uma convenção operacional local,
não uma nota fornecida ou recomendada pelo Google.

| Tipo de veredito reconhecido | Exemplos | Valor |
| --- | --- | --- |
| Verdadeiro | `True`, `Verdadeiro`, `Correto`, `É verdadeiro` | 1,00 |
| Majoritariamente verdadeiro | `Mostly true`, `Majoritariamente verdadeiro` | 0,75 |
| Parcial ou misto | `Partly true`, `Half true`, `Meia verdade`, `Mixed`, `Impreciso` | 0,50 |
| Enganoso ou majoritariamente falso | `Mostly false`, `Majoritariamente falso`, `Misleading`, `Enganoso` | 0,25 |
| Falso | `False`, `Falso`, `Fake`, `Não é verdade`, `Não é verdadeiro`, `É falso` | 0,00 |

Rótulos desconhecidos ou compostos ficam sem nota, preservando o original.
Por exemplo, `not true` não recebe a nota de `true` por conter essa palavra.
A nota não é uma probabilidade calibrada de veracidade.

## Cálculo da nota

Uma revisão só participa se a afirmação corresponder, o rótulo estiver mapeado
e a agência puder ser identificada. A identidade utiliza domínio informado,
domínio do link da revisão ou nome normalizado como alternativa.

Revisões repetidas com o mesmo link e afirmação não somam peso. Sem link,
a deduplicação usa agência, afirmação, data e veredito. As revisões excluídas
continuam no resultado com o motivo.

```text
P_agência = média das notas de revisões únicas dessa agência
F = média dos valores P_agência
```

Agências recebem peso igual. Isso limita a influência do volume de publicações
de uma agência, sem afirmar que suas decisões sejam independentes ou que todas
tenham a mesma qualidade. As médias por agência são avaliações da afirmação;
não são reputações das agências.

Exemplo: agência A publica duas revisões com nota 1 e agência B uma com nota 0.
As médias das agências são 1 e 0, e `F = 0,50`. A revisão duplicada não altera
o resultado. Essa nota representa uma combinação de vereditos divergentes,
não uma conclusão de “meia verdade”. Valores presentes abaixo e acima de 0,5
ativam `conflicting_verdicts`.

## Saídas

| Campo | Significado |
| --- | --- |
| `name` | Checagem de fatos verificáveis. |
| `method` | `google_fact_check_claim_reviews`. |
| `target_claim` / `claim_origin` | Afirmação selecionada e origem: usuário ou título/trecho. |
| `scope` / `limitation` | Limites da análise e da correspondência. |
| `score` | Nota F de 0 a 1, arredondada a quatro casas; sem nota quando indisponível. |
| `reviews_count` | Revisões das consultas da afirmação principal, inclusive duplicatas e excluídas. |
| `applicable_reviews_count` | Revisões com afirmação correspondente; não necessariamente usadas na nota. |
| `scored_reviews_count` | Revisões únicas efetivamente usadas. |
| `publishers_count` / `publisher_scores` | Quantidade de agências identificadas e médias de suas revisões. |
| `conflicting_verdicts` | Valores usados dos dois lados de 0,5. |
| `search_attempts` / `search_truncated` | Consultas, alvo, contagens, sucesso/falha/cache e limite de paginação. |
| `search_incomplete` | Parte da busca falhou; evidências anteriores foram preservadas. |
| `evidence_status` | `SUPPORTED`, `REFUTED`, `MIXED`, `MATCHED_UNSCORED` ou `UNAVAILABLE`; ausente/nulo em registros antigos. |
| `additional_claims` | Evidências complementares separadas, sem peso ou contribuição ao índice. |
| `reviews` | Afirmação, responsável, datas, agência, link, veredito original, nota e motivos de inclusão/exclusão. |

A interface mantém o cartão visível mesmo quando o critério está indisponível
ou ausente na resposta. Exibe status, peso previsto e efetivo, contagens,
motivo da indisponibilidade e as consultas registradas. Respostas antigas
com `source_credibility` são reconhecidas e identificadas como formato anterior,
sem inventar detalhes de cálculo ausentes. Uma nota calculada apenas com escrita
recebe a indicação “Somente estilo de escrita”, sem sugerir checagem factual.

`evidence_status` descreve apenas os vereditos utilizáveis recuperados: todos
acima de 0,5 → `SUPPORTED`; todos abaixo de 0,5 → `REFUTED`; valores dos dois
lados ou qualquer 0,5 → `MIXED`; nenhum utilizável → `UNAVAILABLE`. O estado é
separado de `status` (execução) e não é um veredito global sobre a notícia.
Resultados parciais devem ser interpretados junto com `search_incomplete`.

## Índice e cobertura

O índice operacional mantém os pesos previstos de 60% para fatos verificáveis
e 40% para escrita: `Índice = (0,60 × F + 0,40 × W) × 100`.
A média é sujeita ao teto de 35 por veto da fonte, conforme
[Credibilidade](Credibilidade.md). Somente a afirmação principal determina F.
Com um critério indisponível, o peso efetivo do outro é 100%. As coberturas
continuam 100%, 60%, 40% ou 0%. Elas medem disponibilidade dos critérios,
não a proporção de fatos da notícia verificados.

Sem chave, correspondência, veredito mapeado ou agência identificável, o critério
fica indisponível. Falhas de rede/API geram `FACT_CHECK_API_ERROR`.
Nenhum desses casos produz nota zero por falta de evidência.

## Auditoria e versões

As evidências e decisões do critério são armazenadas em SQLite. O texto
integral extraído não é persistido. As regras são identificadas por
`analysis-rules-v8-explainable-claim-matching`, e o mapeamento por
`fact-check-exact-labels-publisher-mean-v2`.
