# Checagem de fatos verificáveis

O critério `verifiable_facts` usa a Google Fact Check Tools API para recuperar
checagens publicadas sobre **uma afirmação selecionada**. Não atribui reputação
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

`claim` é opcional, de 3 a 500 caracteres. Sem esse campo, o sistema utiliza
o título limpo da notícia, ou a primeira frase extraída quando não há título,
como **afirmação candidata**. Esse procedimento não é extração semântica de
alegações. Quando o título é uma pergunta, opinião ou desmentido, prefira
informar a afirmação precisa no campo da interface.

A afirmação informada pelo usuário tem prioridade e sua checagem não significa
que a notícia a endossa. O BERTimbau continua recebendo o texto extraído da
notícia, independentemente da afirmação selecionada.

## Busca e correspondência

A busca começa com a afirmação e um trecho representativo e utiliza consultas
alternativas até encontrar um resultado utilizável. Os resultados da primeira
consulta utilizável definem o conjunto avaliado. Cada consulta usa
`languageCode=pt`, `pageSize=10` e até três páginas. A paginação mantém os
parâmetros e usa `nextPageToken`; limite ou repetição do token são sinalizados
em `search_truncated`. A ausência de revisão não significa verdadeiro nem falso.

A correspondência compara a afirmação selecionada com `Claim.text`, sem usar
o título da revisão como prova de identidade. O filtro rejeita diferenças nas
sequências numéricas, na presença de negações e nos marcadores de desmentido.
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
| `reviews_count` | Quantidade de revisões recuperadas na consulta selecionada, inclusive excluídas. |
| `applicable_reviews_count` | Revisões com afirmação correspondente; não necessariamente usadas na nota. |
| `scored_reviews_count` | Revisões únicas efetivamente usadas. |
| `publishers_count` / `publisher_scores` | Quantidade de agências identificadas e médias de suas revisões. |
| `conflicting_verdicts` | Valores usados dos dois lados de 0,5. |
| `search_attempts` / `search_truncated` | Consultas tentadas e limite de paginação. |
| `reviews` | Afirmação, responsável, datas, agência, link, veredito original, nota e motivos de inclusão/exclusão. |

A interface mantém o cartão visível mesmo quando o critério está indisponível
ou ausente na resposta. Exibe status, peso previsto e efetivo, contagens,
motivo da indisponibilidade e as consultas registradas. Respostas antigas
com `source_credibility` são reconhecidas e identificadas como formato anterior,
sem inventar detalhes de cálculo ausentes. Uma nota calculada apenas com escrita
recebe a indicação “Somente estilo de escrita”, sem sugerir checagem factual.

## Índice e cobertura

O índice operacional mantém os pesos previstos de 60% para fatos verificáveis
e 40% para escrita: `Índice = (0,60 × F + 0,40 × W) × 100`.
Com um critério indisponível, o peso efetivo do outro é 100%. As coberturas
continuam 100%, 60%, 40% ou 0%. Elas medem disponibilidade dos critérios,
não a proporção de fatos da notícia verificados.

Sem chave, correspondência, veredito mapeado ou agência identificável, o critério
fica indisponível. Falhas de rede/API geram `FACT_CHECK_API_ERROR`.
Nenhum desses casos produz nota zero por falta de evidência.

## Auditoria e versões

As evidências e decisões do critério são armazenadas em SQLite. O texto
integral extraído não é persistido. As regras são identificadas por
`analysis-rules-v3-verifiable-facts`, e o mapeamento por
`fact-check-exact-labels-publisher-mean-v2`.
