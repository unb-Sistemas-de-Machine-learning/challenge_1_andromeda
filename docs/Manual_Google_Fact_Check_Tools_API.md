# Google Fact Check Tools API — integração no projeto

## Finalidade

A Google Fact Check Tools API recupera checagens de afirmações publicadas por
organizações de fact-checking. A aplicação utiliza `claims.search` no critério
**Checagem de fatos verificáveis**, identificado como `verifiable_facts`.

O serviço não atribui uma reputação ao portal de origem da notícia. O campo
`textualRating` é o veredito textual de uma agência sobre uma afirmação.
`publisher` identifica a organização que publicou essa checagem. A nota numérica
é calculada pelo projeto a partir dos vereditos reconhecidos.

## Endpoint utilizado

```text
GET https://factchecktools.googleapis.com/v1alpha1/claims:search
```

O corpo da requisição é vazio. O projeto utiliza os seguintes parâmetros:

| Parâmetro | Uso |
| --- | --- |
| `query` | Consulta textual construída a partir da afirmação selecionada. |
| `key` | Chave de API configurada localmente. |
| `languageCode` | `pt`, para restringir as revisões por idioma. |
| `pageSize` | `10`, máximo solicitado de afirmações por página. |
| `pageToken` | Token recebido em `nextPageToken`, quando existe uma próxima página. |

Os filtros opcionais `reviewPublisherSiteFilter`, `maxAgeDays` e `offset`
existem na API, mas não são enviados pelo cliente deste projeto. Não há filtro
automático de idade das checagens; datas devem ser consideradas ao interpretar
as evidências. Os métodos de busca por imagem e gerenciamento `pages.*` não
participam do fluxo da aplicação.

## Configuração

Instale as dependências na raiz do repositório:

```powershell
uv sync --extra dev
```

Configure a chave no arquivo `.env`, ignorado pelo Git:

```text
FACTCHECK_API_KEY=<sua-chave>
```

Ou defina a variável na sessão do PowerShell antes de iniciar o servidor:

```powershell
$env:FACTCHECK_API_KEY = "<sua-chave>"
uv run uvicorn news_analysis.api.app:app --reload
```

A configuração combina `.env` e variáveis de ambiente; as variáveis de ambiente
têm precedência. `/config` informa apenas se a chave está configurada, sem
retornar seu valor. Esse indicador não garante que uma consulta encontre
checagens, que a chave tenha autorização ou que a cota esteja disponível.

## Seleção da afirmação

`POST /analyses` recebe `url`, `user_id` opcional e `claim` opcional.

```json
{
  "url": "https://example.com/noticia",
  "user_id": "demo",
  "claim": "Vacina reduz casos graves"
}
```

`claim` aceita de 3 a 500 caracteres. Uma afirmação informada tem prioridade;
espaços nas extremidades são removidos antes da análise. Sem afirmação explícita,
o título limpo e frases iniciais fornecem até três candidatos. O primeiro
determina a nota; os demais são evidências complementares, sem peso no índice.
A seleção preserva as frases originais, remove duplicatas e ignora perguntas.
Não há extração semântica automática de todos os fatos da notícia.

Em matérias que citam ou desmentem um boato, a nota factual refere-se à afirmação
selecionada e não implica que o artigo a endosse. O BERTimbau continua analisando
o texto principal extraído, independentemente dessa seleção.

## Construção das consultas

Cada candidato produz sua própria consulta, sem título concatenado com corpo,
e uma alternativa de até dez palavras significativas. Consultas vazias ou
repetidas após normalização são removidas. Cada consulta é limitada a 300
caracteres. A correspondência usa a afirmação original, não as palavras-chave.
Com `claim` explícito, não se selecionam candidatos adicionais do artigo.

As respostas das consultas são reunidas, com deduplicação das revisões no cálculo,
em vez de encerrar na primeira resposta utilizável. Evidências contraditórias
continuam visíveis. Consultas iguais entre candidatos usam cache durante aquela
análise, mantendo a comparação independente para cada afirmação.

São no máximo três candidatos e duas consultas por candidato. Sem chave ou em
401/403/429, novas consultas param. Falhas posteriores preservam páginas e
consultas anteriores e são registradas sem mensagens que possam expor a chave.

## Paginação e limites

Cada consulta percorre até três páginas. O cliente usa `nextPageToken` como
`pageToken` e mantém os demais parâmetros. Token vazio encerra a paginação.
Token repetido ou limite atingido com resultados pendentes produz
`search_truncated=true`. A chamada HTTP utiliza timeout de dez segundos.

Esses limites restringem o custo da busca síncrona; não garantem recuperação
de todas as checagens existentes. O conjunto avaliado corresponde às páginas
recuperadas nas consultas realizadas, não ao acervo completo do Google.
No máximo dezoito requisições HTTP são feitas por análise, sem retries.
`search_incomplete` distingue falhas de `search_truncated`, que indica paginação
limitada. Resultados utilizáveis parciais podem fornecer nota, acompanhada do aviso.

## Estrutura dos dados

| Objeto | Campo | Interpretação |
| --- | --- | --- |
| `Claim` | `text` | Afirmação que foi submetida à checagem. |
| `Claim` | `claimant` | Pessoa ou organização que declarou a afirmação, quando informada. |
| `Claim` | `claimDate` | Data em que a afirmação foi feita. |
| `Claim` | `claimReview[]` | Uma ou mais checagens publicadas sobre a afirmação. |
| `ClaimReview` | `publisher.name` / `publisher.site` | Agência e domínio da checagem. |
| `ClaimReview` | `url` / `title` | Link e título da publicação de checagem. |
| `ClaimReview` | `reviewDate` | Data da revisão. |
| `ClaimReview` | `textualRating` | Veredito original, como `False` ou `Mostly true`. |
| `ClaimReview` | `languageCode` | Idioma da revisão. |

`Claim.text` e o título da revisão têm funções distintas: uma checagem pode
ter um título que desmente justamente a afirmação avaliada. O título da revisão
não determina a correspondência factual no projeto.

## Correspondência com a afirmação selecionada

O filtro compara a seleção com `Claim.text`. Primeiro rejeita diferenças nas
sequências numéricas e na presença de negações ou marcadores de desmentido.
Siglas estaduais explícitas são protegidas, DF/Distrito Federal são equivalentes
e formas de aumentar/reduzir ou retomar/suspender não são intercambiadas.
Depois aceita igualdade normalizada ou pelo menos três palavras significativas
em comum, com sobreposição de 80% em ambas as direções.

A normalização remove acentos e pontuação e padroniza espaços e caixa.
A comparação é lexical: não comprova equivalência semântica, identidade de
contexto ou validade temporal. Tanto exclusões de paráfrases quanto inclusão
de textos muito semelhantes são possíveis. Afirmação, datas e links permitem
inspecionar o contexto das revisões.

## Normalização e nota

A escala do projeto utiliza apenas rótulos completos reconhecidos:

| Categoria | Valores de exemplo | Nota |
| --- | --- | --- |
| Verdadeiro | `True`, `Verdadeiro`, `Correto`, `É verdadeiro` | 1,00 |
| Majoritariamente verdadeiro | `Mostly true`, `Majoritariamente verdadeiro` | 0,75 |
| Parcial ou misto | `Partly true`, `Half true`, `Meia verdade`, `Mixed`, `Impreciso` | 0,50 |
| Enganoso ou majoritariamente falso | `Mostly false`, `Majoritariamente falso`, `Misleading`, `Enganoso` | 0,25 |
| Falso | `False`, `Falso`, `Fake`, `Não é verdade`, `Não é verdadeiro`, `É falso` | 0,00 |

Rótulos desconhecidos ou compostos ficam sem conversão. A ocorrência de uma
palavra como `true` dentro de uma avaliação não é suficiente para atribuir nota.
O original é preservado mesmo quando não entra no cálculo.

Uma revisão participa apenas se corresponder à afirmação, tiver rótulo mapeado
e identificar a agência. O identificador utiliza domínio informado, domínio do
link da revisão ou nome normalizado. Duplicatas por URL e afirmação são
excluídas; sem URL, a identidade utiliza agência, afirmação, data e veredito.

```text
P_agência = média das revisões únicas utilizáveis da agência
F = média dos valores P_agência, com peso igual entre agências
```

As médias por agência são avaliações da afirmação, não reputações da agência.
Pesos iguais limitam a influência do volume de publicações sem afirmar
independência estatística ou qualidade equivalente entre organizações.

Uma agência com duas notas 1 e outra com uma nota 0 produzem `F=0,50`.
Esse resultado é uma combinação divergente, não necessariamente “meia verdade”.
Valores retidos abaixo e acima de 0,5 ativam `conflicting_verdicts`.

## Resultado, interface e auditoria

O resultado está em `criteria.verifiable_facts`. Inclui afirmação e origem,
status, score, pesos, contribuição, revisões originais, motivos de exclusão,
contagens, médias por agência, divergência e limites da busca.
`evidence_status` resume vereditos utilizáveis: todos acima de 0,5 são `SUPPORTED`,
todos abaixo são `REFUTED`, intermediários/divergentes são `MIXED` e ausência
é `UNAVAILABLE`. `additional_claims` contém as evidências complementares, sem
contribuição ao índice. Esses estados não são vereditos sobre a notícia inteira.

A interface mantém o cartão do critério visível mesmo sem evidências.
Mostra a afirmação avaliada, contagens, motivos e consultas registradas; quando
há revisões, mostra agências, vereditos, datas, links e participação no cálculo.
Os pesos previstos são 65% para fatos, 20% para credibilidade da fonte e 15%
para escrita. A cobertura informa
quais critérios têm nota, não quantos fatos da notícia foram checados.

SQLite conserva metadados, evidências e decisões necessárias para auditoria.
O texto integral extraído do artigo não é persistido. Registros históricos
mantêm sua nota e versão de regras; a leitura pode projetar a chave
`source_credibility` para `verifiable_facts` sem recalcular o resultado.

## Indisponibilidade e erros

| Situação | Resultado |
| --- | --- |
| Chave ausente | `UNAVAILABLE`, motivo `missing_api_key`. |
| Nenhuma revisão retornada | `UNAVAILABLE`, motivo `no_reviews_returned`. |
| Nenhuma afirmação correspondente | `UNAVAILABLE`, motivo `no_applicable_reviews`. |
| Vereditos sem mapeamento | `UNAVAILABLE`, motivo `no_normalizable_ratings`. |
| Agência não identificável | `UNAVAILABLE`, motivo `missing_publisher_identity`. |
| Erro de rede ou resposta HTTP malsucedida | `ERROR`, código `FACT_CHECK_API_ERROR`. |

Sem evidência utilizável não há score factual; o critério é excluído do índice.
Uma revisão utilizável com veredito falso, por outro lado, tem nota zero.
Esses dois casos são distintos. A análise pode retornar `SUCCESS` com cobertura
parcial, indicando que o fluxo terminou, sem confirmar todos os fatos.

## Uso do cliente do projeto

```python
from news_analysis.config import Settings
from news_analysis.criteria.fact_check import FactCheckClient, evaluate_fact_checks

afirmacao = "Vacina reduz casos graves"
raw = FactCheckClient(Settings.from_env()).search(afirmacao)
resultado = evaluate_fact_checks(
    raw, None, "", afirmacao,
    target_claim=afirmacao, claim_origin="user",
)
print(resultado.model_dump_json(indent=2))
```

Esse exemplo consulta uma única frase; o endpoint `/analyses` também prepara
o artigo, executa as consultas alternativas e combina os critérios.

## Referências

- [Método claims.search](https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims/search)
- [Objetos Claim, ClaimReview e Publisher](https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims)
- [Guia de marcação ClaimReview](https://developers.google.com/search/docs/appearance/structured-data/factcheck)
- [Regra do critério no projeto](ChecagemDeFatos.md)
- [Interface, API e fluxo do sistema](InterfaceEAPI.md)
