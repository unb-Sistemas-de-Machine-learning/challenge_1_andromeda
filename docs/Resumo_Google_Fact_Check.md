# Google Fact Check Tools API — Manual de Utilização

## 1. O que é a API?

A **Google Fact Check Tools API** é uma API REST do Google que oferece acesso programático a **verificações de fatos (fact-checks)** publicadas por organizações de checagem ao redor do mundo. O serviço é hospedado em:

```text
https://factchecktools.googleapis.com
```

A API expõe a mesma funcionalidade das ferramentas web do Google para checagem de fatos, e está organizada em dois grupos de operações:

* **Busca de alegações verificadas** (`claims`) — consulta um banco de *claims* (alegações) que já foram checadas por publicadores de fact-checking, usando **texto** ou **imagem**;
* **Gerenciamento de marcação ClaimReview** (`pages`) — permite que organizações de checagem **criem, consultem, listem, atualizem e removam** a marcação `ClaimReview` associada às suas páginas.

É importante destacar que a API **não é um detector de fake news**. Ela não analisa se um texto é verdadeiro ou falso: ela **recupera verificações que humanos (organizações de checagem) já publicaram** sobre alegações semelhantes à consultada.

> **Versão atual:** `v1alpha1`. Como o próprio nome indica, trata-se de uma versão *alpha*, portanto contratos e comportamentos podem mudar.

---

# 2. Funcionamento geral

O funcionamento pode ser representado da seguinte forma:

```text
                    ┌──────────────────────┐
                    │   Sua aplicação      │
                    └──────────┬───────────┘
                               │
                       Requisição HTTPS
                               │
                               ▼
              ┌──────────────────────────────────┐
              │  factchecktools.googleapis.com   │
              │           /v1alpha1              │
              └───────────────┬──────────────────┘
                              │
              ┌───────────────┴────────────────┐
              ▼                                ▼
     ┌─────────────────┐              ┌─────────────────┐
     │  Recurso claims │              │  Recurso pages  │
     │   (somente      │              │   (CRUD de      │
     │    leitura)     │              │  ClaimReview)   │
     └────────┬────────┘              └────────┬────────┘
              │                                │
              ▼                                ▼
     Claims já verificadas           Marcação ClaimReview
     por publicadores                de páginas de checagem
```

O recurso `claims` serve para **consumidores** de fact-checks (por exemplo, um aplicativo que quer mostrar checagens relacionadas a um texto). O recurso `pages` serve para **publicadores** de fact-checks (por exemplo, uma agência de checagem que quer registrar a marcação de suas matérias).

---

# 3. Endpoints disponíveis

A API possui **7 métodos**, distribuídos em dois recursos:

| # | Método | Verbo e caminho | Finalidade |
| - | ------ | --------------- | ---------- |
| 1 | `claims.search` | `GET /v1alpha1/claims:search` | Buscar claims verificadas por texto |
| 2 | `claims.imageSearch` | `GET /v1alpha1/claims:imageSearch` | Buscar claims verificadas por imagem |
| 3 | `pages.list` | `GET /v1alpha1/pages` | Listar páginas com marcação ClaimReview |
| 4 | `pages.get` | `GET /v1alpha1/pages/{page_id}` | Obter a marcação de uma página |
| 5 | `pages.create` | `POST /v1alpha1/pages` | Criar marcação ClaimReview |
| 6 | `pages.update` | `PUT /v1alpha1/pages/{page_id}` | Substituir a marcação de uma página |
| 7 | `pages.delete` | `DELETE /v1alpha1/pages/{page_id}` | Remover a marcação de uma página |

Todos os caminhos são relativos à URL base:

```text
https://factchecktools.googleapis.com
```

---

# 4. Pré-requisitos e configuração

Antes da primeira requisição, é necessário configurar um projeto no Google Cloud:

```text
Projeto no Google Cloud
        │
        ▼
Ativar a "Fact Check Tools API"
        │
        ▼
Criar credencial
        │
   ┌────┴────────────┐
   ▼                 ▼
Chave de API      Cliente OAuth 2.0
(claims)          (pages)
```

Passo a passo resumido:

1. Criar (ou selecionar) um projeto no **Google Cloud Console**;
2. Ativar a **Fact Check Tools API** em *APIs e serviços*;
3. Criar uma **chave de API** (para buscas) e/ou um **ID de cliente OAuth 2.0** (para gerenciar marcações);
4. Guardar as credenciais fora do código-fonte, por exemplo em variáveis de ambiente.

Nos exemplos deste manual, será utilizada a variável:

```bash
export FACTCHECK_API_KEY="SUA_CHAVE_DE_API"
```

---

# 5. Autenticação

A API utiliza dois mecanismos, dependendo do recurso:

| Recurso | Métodos | Autenticação |
| ------- | ------- | ------------ |
| `claims` | `search`, `imageSearch` | **Chave de API** enviada como parâmetro `key` na query string |
| `pages` | `list`, `get`, `create`, `update`, `delete` | **OAuth 2.0** com o escopo abaixo, enviado no cabeçalho `Authorization: Bearer` |

Escopo OAuth exigido por todos os métodos de `pages`:

```text
https://www.googleapis.com/auth/factchecktools
```

## 5.1 Chave de API

```text
GET https://factchecktools.googleapis.com/v1alpha1/claims:search?query=...&key=SUA_CHAVE_DE_API
```

A documentação oficial dos métodos `claims.*` não lista escopo OAuth, o que é consistente com o uso de chave de API para consultas públicas.

## 5.2 OAuth 2.0

```text
Authorization: Bearer SEU_ACCESS_TOKEN
```

O *access token* deve ser obtido com o escopo `https://www.googleapis.com/auth/factchecktools`. Como esses métodos alteram ou consultam marcações ligadas a uma organização, uma chave de API isolada não é suficiente.

---

# 6. Convenções gerais

## 6.1 Formato de datas

Campos do tipo `Timestamp` (por exemplo, `claimDate` e `reviewDate`) utilizam o formato **RFC 3339 em UTC**:

```text
2014-10-02T15:01:23Z
2014-10-02T15:01:23.045123456Z
```

## 6.2 Paginação

Os métodos de listagem e busca retornam, quando há mais resultados, o campo `nextPageToken`.

```text
Requisição 1 ─────────► resultados + nextPageToken
                                   │
                                   ▼
Requisição 2 (pageToken=...) ─► resultados + nextPageToken
                                   │
                                   ▼
Requisição N ─────────► resultados + (token vazio) → fim
```

Regras:

* `pageSize` define o máximo de resultados por página (padrão: **10**);
* `pageToken` recebe o `nextPageToken` da resposta anterior;
* ao usar `pageToken`, **todos os outros parâmetros devem ser idênticos** aos da requisição anterior;
* um `nextPageToken` vazio ou ausente indica que não há mais resultados;
* `offset` só é considerado quando `pageToken` **não** é informado.

## 6.3 Códigos de status HTTP

Como as demais APIs do Google, os erros seguem os códigos HTTP padrão:

| Código | Situação típica |
| ------ | --------------- |
| `200` | Requisição bem-sucedida |
| `400` | Parâmetro inválido ou ausente (por exemplo, `claims.search` sem `query`) |
| `401` | Credencial ausente ou inválida |
| `403` | Sem permissão, API não ativada ou escopo insuficiente |
| `404` | Recurso inexistente (por exemplo, `page_id` desconhecido) |
| `429` | Limite de requisições excedido |

---

# 7. `claims.search` — Buscar claims por texto

## 7.1 Descrição

Pesquisa alegações que já foram verificadas por organizações de checagem, a partir de uma **consulta em texto**. É o principal endpoint da API e o ponto de partida para quem quer exibir fact-checks relacionados a um assunto.

**Caso de uso principal:** dado um trecho de texto (uma frase de uma notícia, uma publicação em rede social), recuperar checagens já publicadas sobre a mesma alegação ou sobre alegações semelhantes.

## 7.2 Método HTTP e endpoint

```http
GET https://factchecktools.googleapis.com/v1alpha1/claims:search
```

O corpo da requisição deve estar vazio.

## 7.3 Parâmetros (query)

| Parâmetro | Tipo | Obrigatório | Descrição |
| --------- | ---- | ----------- | --------- |
| `query` | `string` | **Condicional** | Texto da consulta. Obrigatório, **exceto** quando `reviewPublisherSiteFilter` é informado. |
| `languageCode` | `string` | Não | Código de idioma BCP-47, como `pt-BR`, `en-US` ou `sr-Latn`. Restringe os resultados por idioma; a região não é considerada atualmente. |
| `reviewPublisherSiteFilter` | `string` | Não | Filtra por site do publicador da checagem, por exemplo `nytimes.com`. |
| `maxAgeDays` | `integer` | Não | Idade máxima dos resultados, em dias. A idade é calculada pela data da claim ou da revisão, **a que for mais recente**. |
| `pageSize` | `integer` | Não | Máximo de resultados por página. Padrão: `10`. |
| `pageToken` | `string` | Não | Token da página seguinte, obtido em `nextPageToken`. |
| `offset` | `integer` | Não | Posição inicial nos resultados. `0` começa no primeiro; `10` começa no 11º. Ignorado se `pageToken` for informado. |
| `key` | `string` | **Sim** (na prática) | Chave de API, conforme a seção de autenticação. |

## 7.4 Autenticação

Chave de API no parâmetro `key`.

## 7.5 Exemplo de requisição

**cURL**

```bash
curl -G "https://factchecktools.googleapis.com/v1alpha1/claims:search" \
  --data-urlencode "query=vacinas causam autismo" \
  --data-urlencode "languageCode=pt-BR" \
  --data-urlencode "maxAgeDays=365" \
  --data-urlencode "pageSize=5" \
  --data-urlencode "key=$FACTCHECK_API_KEY"
```

**Python (`requests`)**

```python
import os
import requests

URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

params = {
    "query": "vacinas causam autismo",
    "languageCode": "pt-BR",
    "maxAgeDays": 365,
    "pageSize": 5,
    "key": os.environ["FACTCHECK_API_KEY"],
}

resposta = requests.get(URL, params=params, timeout=30)
resposta.raise_for_status()

for claim in resposta.json().get("claims", []):
    print(claim["text"])
    for review in claim.get("claimReview", []):
        print("  ->", review["publisher"]["name"], "|", review["textualRating"])
```

**Python (biblioteca cliente do Google)**

```python
import os
from googleapiclient.discovery import build

servico = build(
    "factchecktools", "v1alpha1",
    developerKey=os.environ["FACTCHECK_API_KEY"],
)

resposta = servico.claims().search(
    query="vacinas causam autismo",
    languageCode="pt-BR",
).execute()
```

## 7.6 Exemplo de resposta

> Os valores abaixo são **ilustrativos**. A estrutura segue o schema oficial.

```json
{
  "claims": [
    {
      "text": "Vacinas causam autismo em crianças.",
      "claimant": "Publicação em rede social",
      "claimDate": "2024-03-10T00:00:00Z",
      "claimReview": [
        {
          "publisher": {
            "name": "Agência de Checagem Exemplo",
            "site": "agenciaexemplo.com.br"
          },
          "url": "https://agenciaexemplo.com.br/checagem/vacinas-autismo",
          "title": "É falso que vacinas causam autismo",
          "reviewDate": "2024-03-12T14:30:00Z",
          "textualRating": "Falso",
          "languageCode": "pt"
        }
      ]
    }
  ],
  "nextPageToken": "CAoQAA"
}
```

## 7.7 Observações importantes

* A busca **não** exige correspondência exata: ela retorna claims relacionadas à consulta;
* Uma claim pode ter **várias revisões** (`claimReview[]`), de publicadores diferentes e com avaliações diferentes;
* É possível buscar apenas por publicador, informando `reviewPublisherSiteFilter` sem `query`.

---

# 8. `claims.imageSearch` — Buscar claims por imagem

## 8.1 Descrição

Pesquisa alegações verificadas usando uma **imagem** como consulta.

**Caso de uso principal:** dada uma imagem que circula em redes sociais (montagem, print, meme, foto fora de contexto), verificar se ela já foi objeto de alguma checagem.

## 8.2 Método HTTP e endpoint

```http
GET https://factchecktools.googleapis.com/v1alpha1/claims:imageSearch
```

O corpo da requisição deve estar vazio.

## 8.3 Parâmetros (query)

| Parâmetro | Tipo | Obrigatório | Descrição |
| --------- | ---- | ----------- | --------- |
| `imageUri` | `string` | **Sim** | URL **pública** (HTTP/HTTPS) da imagem de origem. |
| `languageCode` | `string` | Não | Código de idioma BCP-47, como `pt-BR`. |
| `pageSize` | `integer` | Não | Máximo de resultados por página. Padrão: `10`. |
| `pageToken` | `string` | Não | Token da página seguinte, obtido em `nextPageToken`. |
| `offset` | `integer` | Não | Posição inicial nos resultados. Ignorado se `pageToken` for informado. |
| `key` | `string` | **Sim** (na prática) | Chave de API. |

> **Atenção:** o Google busca a imagem a partir da URL informada e **não garante** que a requisição será concluída. Ela pode falhar se o servidor de origem bloquear o acesso (limitação de taxa, proteção contra DoS) ou se o Google limitar requisições àquele site. A documentação recomenda **não depender de imagens hospedadas externamente** em aplicações de produção.

## 8.4 Autenticação

Chave de API no parâmetro `key`.

## 8.5 Exemplo de requisição

**cURL**

```bash
curl -G "https://factchecktools.googleapis.com/v1alpha1/claims:imageSearch" \
  --data-urlencode "imageUri=https://exemplo.com/imagens/montagem-viral.jpg" \
  --data-urlencode "languageCode=pt-BR" \
  --data-urlencode "key=$FACTCHECK_API_KEY"
```

**Python**

```python
import os
import requests

URL = "https://factchecktools.googleapis.com/v1alpha1/claims:imageSearch"

params = {
    "imageUri": "https://exemplo.com/imagens/montagem-viral.jpg",
    "languageCode": "pt-BR",
    "key": os.environ["FACTCHECK_API_KEY"],
}

resposta = requests.get(URL, params=params, timeout=30)
resposta.raise_for_status()

for resultado in resposta.json().get("results", []):
    claim = resultado["claim"]
    print(claim.get("text"))
```

## 8.6 Exemplo de resposta

A diferença em relação a `claims.search` é que cada item fica dentro de um objeto `Result`, na lista `results`, e não diretamente em `claims`.

```json
{
  "results": [
    {
      "claim": {
        "text": "Imagem mostra manifestação em 2024.",
        "claimant": "Conta anônima",
        "claimDate": "2024-05-02T00:00:00Z",
        "claimReview": [
          {
            "publisher": {
              "name": "Agência de Checagem Exemplo",
              "site": "agenciaexemplo.com.br"
            },
            "url": "https://agenciaexemplo.com.br/checagem/foto-manifestacao",
            "title": "Foto é de 2018, não de 2024",
            "reviewDate": "2024-05-03T10:00:00Z",
            "textualRating": "Enganoso",
            "languageCode": "pt"
          }
        ]
      }
    }
  ],
  "nextPageToken": ""
}
```

---

# 9. `pages.list` — Listar páginas com ClaimReview

## 9.1 Descrição

Lista as páginas de marcação `ClaimReview` de **uma URL específica** ou de **uma organização**.

**Caso de uso principal:** uma agência de checagem quer auditar quais de suas páginas já possuem marcação registrada.

## 9.2 Método HTTP e endpoint

```http
GET https://factchecktools.googleapis.com/v1alpha1/pages
```

O corpo da requisição deve estar vazio.

## 9.3 Parâmetros (query)

| Parâmetro | Tipo | Obrigatório | Descrição |
| --------- | ---- | ----------- | --------- |
| `url` | `string` | Um dos dois | URL da qual se quer obter a marcação. Retorna **no máximo um** resultado. Se a marcação estiver associada a uma versão mais canônica da URL, ela será retornada. **Não pode** ser usado junto com `organization`. |
| `organization` | `string` | Um dos dois | Organização cujas marcações serão listadas, por exemplo `site.com`. **Não pode** ser usado junto com `url`. |
| `pageSize` | `integer` | Não | Máximo de resultados por página. Padrão: `10`. **Sem efeito** se `url` for informado. |
| `pageToken` | `string` | Não | Token da página seguinte. |
| `offset` | `integer` | Não | Posição inicial. Só é considerado sem `pageToken` e quando **não** se consulta uma URL específica. |

## 9.4 Autenticação

OAuth 2.0 com o escopo `https://www.googleapis.com/auth/factchecktools`.

## 9.5 Exemplo de requisição

**cURL**

```bash
curl -G "https://factchecktools.googleapis.com/v1alpha1/pages" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode "organization=agenciaexemplo.com.br" \
  --data-urlencode "pageSize=20"
```

**Python**

```python
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import AuthorizedSession

ESCOPOS = ["https://www.googleapis.com/auth/factchecktools"]

fluxo = InstalledAppFlow.from_client_secrets_file("client_secret.json", ESCOPOS)
credenciais = fluxo.run_local_server(port=0)
sessao = AuthorizedSession(credenciais)

resposta = sessao.get(
    "https://factchecktools.googleapis.com/v1alpha1/pages",
    params={"organization": "agenciaexemplo.com.br", "pageSize": 20},
)
resposta.raise_for_status()
print(resposta.json())
```

## 9.6 Exemplo de resposta

```json
{
  "claimReviewMarkupPages": [
    {
      "name": "pages/abc123",
      "pageUrl": "https://agenciaexemplo.com.br/checagem/vacinas-autismo",
      "publishDate": "2024-03-12",
      "claimReviewAuthor": {
        "name": "Agência de Checagem Exemplo",
        "imageUrl": "https://agenciaexemplo.com.br/logo.png"
      },
      "claimReviewMarkups": [
        {
          "claimReviewed": "Vacinas causam autismo em crianças.",
          "rating": {
            "textualRating": "Falso",
            "ratingValue": 1,
            "worstRating": 1,
            "bestRating": 5
          }
        }
      ],
      "versionId": "1"
    }
  ],
  "nextPageToken": ""
}
```

---

# 10. `pages.get` — Obter a marcação de uma página

## 10.1 Descrição

Retorna **toda** a marcação `ClaimReview` de uma página, a partir do identificador do recurso.

**Caso de uso principal:** recuperar a marcação atual antes de atualizá-la, já que `pages.update` é uma substituição completa.

## 10.2 Método HTTP e endpoint

```http
GET https://factchecktools.googleapis.com/v1alpha1/pages/{page_id}
```

O corpo da requisição deve estar vazio.

## 10.3 Parâmetros (path)

| Parâmetro | Tipo | Obrigatório | Descrição |
| --------- | ---- | ----------- | --------- |
| `name` | `string` | **Sim** | Nome do recurso no formato `pages/{page_id}`. O `page_id` é obtido em `pages.list` ou na resposta de `pages.create` (campo `name`). |

## 10.4 Autenticação

OAuth 2.0 com o escopo `https://www.googleapis.com/auth/factchecktools`.

## 10.5 Exemplo de requisição

**cURL**

```bash
curl "https://factchecktools.googleapis.com/v1alpha1/pages/abc123" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Python**

```python
resposta = sessao.get(
    "https://factchecktools.googleapis.com/v1alpha1/pages/abc123"
)
resposta.raise_for_status()
pagina = resposta.json()
print(pagina["pageUrl"])
```

## 10.6 Exemplo de resposta

```json
{
  "name": "pages/abc123",
  "pageUrl": "https://agenciaexemplo.com.br/checagem/vacinas-autismo",
  "publishDate": "2024-03-12",
  "claimReviewAuthor": {
    "name": "Agência de Checagem Exemplo",
    "imageUrl": "https://agenciaexemplo.com.br/logo.png"
  },
  "claimReviewMarkups": [
    {
      "claimReviewed": "Vacinas causam autismo em crianças.",
      "claimDate": "2024-03-10",
      "claimAuthor": {
        "name": "Publicação em rede social"
      },
      "rating": {
        "textualRating": "Falso",
        "ratingValue": 1,
        "worstRating": 1,
        "bestRating": 5,
        "ratingExplanation": "Não há evidência científica dessa associação."
      }
    }
  ],
  "versionId": "1"
}
```

---

# 11. `pages.create` — Criar marcação ClaimReview

## 11.1 Descrição

Cria a marcação `ClaimReview` para uma página.

**Caso de uso principal:** uma organização de checagem publica uma nova matéria e registra, via API, os dados estruturados da verificação (alegação, autor da alegação, avaliação).

## 11.2 Método HTTP e endpoint

```http
POST https://factchecktools.googleapis.com/v1alpha1/pages
```

O corpo da requisição é uma instância de `ClaimReviewMarkupPage`.

## 11.3 Parâmetros

Este método **não possui parâmetros de query ou de path**. Os dados são enviados no corpo (JSON). Os campos do corpo são:

| Campo | Tipo | Obrigatório | Descrição |
| ----- | ---- | ----------- | --------- |
| `pageUrl` | `string` | Sim (na prática) | URL da página associada à marcação. Campo de nível de página, usado por cada `ClaimReview`, salvo sobrescrita individual. Corresponde a `ClaimReview.url`. |
| `publishDate` | `string` | Recomendado | Data de publicação da checagem. Corresponde a `ClaimReview.datePublished`. |
| `claimReviewAuthor` | `object` | Recomendado | Autor da revisão (`name`, `imageUrl`). |
| `claimReviewMarkups[]` | `object[]` | Sim (na prática) | Lista de revisões individuais da página, cada uma correspondendo a um elemento `ClaimReview`. |
| `name` | `string` | Não | **Somente saída.** Não deve ser definido na criação. |
| `versionId` | `string` | Não | **Somente saída.** Não deve ser definido na criação. |

> A documentação oficial não marca explicitamente campos como "obrigatórios" no schema. A coluna "Obrigatório" acima reflete o que é necessário para que a marcação faça sentido e para atender às diretrizes de `ClaimReview` do Google Search; consulte o guia de ClaimReview para as regras de elegibilidade.

Estrutura de cada item de `claimReviewMarkups[]`:

| Campo | Tipo | Descrição |
| ----- | ---- | --------- |
| `url` | `string` | Opcional. Por padrão usa a URL da página. A única sobrescrita permitida é a URL da página com âncora opcional. |
| `claimReviewed` | `string` | Resumo curto da alegação avaliada. |
| `claimDate` | `string` | Data em que a alegação foi feita ou entrou no debate público. |
| `claimLocation` | `string` | Local onde a alegação foi feita. |
| `claimFirstAppearance` | `string` | Link para a obra em que a alegação apareceu pela primeira vez. |
| `claimAppearances[]` | `string[]` | Links para outras obras em que a alegação aparece. |
| `claimAuthor` | `object` | Autor da alegação: `name`, `jobTitle`, `imageUrl`, `sameAs`. |
| `rating` | `object` | Avaliação: `textualRating`, `ratingValue`, `worstRating`, `bestRating`, `ratingExplanation`, `imageUrl`. |

## 11.4 Autenticação

OAuth 2.0 com o escopo `https://www.googleapis.com/auth/factchecktools`.

## 11.5 Exemplo de requisição

**cURL**

```bash
curl -X POST "https://factchecktools.googleapis.com/v1alpha1/pages" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pageUrl": "https://agenciaexemplo.com.br/checagem/vacinas-autismo",
    "publishDate": "2024-03-12",
    "claimReviewAuthor": {
      "name": "Agência de Checagem Exemplo",
      "imageUrl": "https://agenciaexemplo.com.br/logo.png"
    },
    "claimReviewMarkups": [
      {
        "claimReviewed": "Vacinas causam autismo em crianças.",
        "claimDate": "2024-03-10",
        "claimAuthor": { "name": "Publicação em rede social" },
        "rating": {
          "textualRating": "Falso",
          "ratingValue": 1,
          "worstRating": 1,
          "bestRating": 5,
          "ratingExplanation": "Não há evidência científica dessa associação."
        }
      }
    ]
  }'
```

**Python**

```python
corpo = {
    "pageUrl": "https://agenciaexemplo.com.br/checagem/vacinas-autismo",
    "publishDate": "2024-03-12",
    "claimReviewAuthor": {
        "name": "Agência de Checagem Exemplo",
        "imageUrl": "https://agenciaexemplo.com.br/logo.png",
    },
    "claimReviewMarkups": [
        {
            "claimReviewed": "Vacinas causam autismo em crianças.",
            "claimDate": "2024-03-10",
            "claimAuthor": {"name": "Publicação em rede social"},
            "rating": {
                "textualRating": "Falso",
                "ratingValue": 1,
                "worstRating": 1,
                "bestRating": 5,
                "ratingExplanation": "Não há evidência científica dessa associação.",
            },
        }
    ],
}

resposta = sessao.post(
    "https://factchecktools.googleapis.com/v1alpha1/pages",
    json=corpo,
)
resposta.raise_for_status()
print(resposta.json()["name"])  # pages/{page_id}
```

## 11.6 Exemplo de resposta

A resposta é a instância recém-criada de `ClaimReviewMarkupPage`, agora com os campos de saída `name` e `versionId` preenchidos:

```json
{
  "name": "pages/abc123",
  "pageUrl": "https://agenciaexemplo.com.br/checagem/vacinas-autismo",
  "publishDate": "2024-03-12",
  "claimReviewAuthor": {
    "name": "Agência de Checagem Exemplo",
    "imageUrl": "https://agenciaexemplo.com.br/logo.png"
  },
  "claimReviewMarkups": [
    {
      "claimReviewed": "Vacinas causam autismo em crianças.",
      "claimDate": "2024-03-10",
      "claimAuthor": { "name": "Publicação em rede social" },
      "rating": {
        "textualRating": "Falso",
        "ratingValue": 1,
        "worstRating": 1,
        "bestRating": 5,
        "ratingExplanation": "Não há evidência científica dessa associação."
      }
    }
  ],
  "versionId": "1"
}
```

---

# 12. `pages.update` — Atualizar a marcação de uma página

## 12.1 Descrição

Atualiza **toda** a marcação `ClaimReview` de uma página.

**Caso de uso principal:** corrigir a avaliação de uma checagem, adicionar uma nova alegação à mesma página ou ajustar metadados.

> **Atenção:** trata-se de uma **atualização completa** (*full update*), e não parcial. Qualquer `ClaimReview` que não for enviado no corpo será perdido.

O fluxo recomendado pela documentação é:

```text
pages.get
   │
   ▼
Modificar o JSON retornado
   │
   ▼
pages.update (com a marcação completa)
```

## 12.2 Método HTTP e endpoint

```http
PUT https://factchecktools.googleapis.com/v1alpha1/pages/{page_id}
```

O corpo da requisição é uma instância de `ClaimReviewMarkupPage`.

## 12.3 Parâmetros

**Path**

| Parâmetro | Tipo | Obrigatório | Descrição |
| --------- | ---- | ----------- | --------- |
| `claimReviewMarkupPage.name` | `string` | **Sim** | Nome do recurso no formato `pages/{page_id}`. |

**Corpo (JSON)**

Mesma estrutura de `ClaimReviewMarkupPage` descrita em `pages.create`. Nas requisições de atualização, os campos `name` e `versionId` são exceção à regra de "somente saída" e podem ser informados.

## 12.4 Autenticação

OAuth 2.0 com o escopo `https://www.googleapis.com/auth/factchecktools`.

## 12.5 Exemplo de requisição

**cURL**

```bash
curl -X PUT "https://factchecktools.googleapis.com/v1alpha1/pages/abc123" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "pages/abc123",
    "pageUrl": "https://agenciaexemplo.com.br/checagem/vacinas-autismo",
    "publishDate": "2024-03-12",
    "claimReviewAuthor": {
      "name": "Agência de Checagem Exemplo"
    },
    "claimReviewMarkups": [
      {
        "claimReviewed": "Vacinas causam autismo em crianças.",
        "rating": {
          "textualRating": "Falso",
          "ratingValue": 1,
          "worstRating": 1,
          "bestRating": 5
        }
      }
    ]
  }'
```

**Python (fluxo get → modificar → update)**

```python
URL = "https://factchecktools.googleapis.com/v1alpha1/pages/abc123"

pagina = sessao.get(URL).json()

pagina["claimReviewMarkups"][0]["rating"]["ratingExplanation"] = (
    "Estudos amplos não encontraram relação entre vacinas e autismo."
)

resposta = sessao.put(URL, json=pagina)
resposta.raise_for_status()
print(resposta.json()["versionId"])
```

## 12.6 Exemplo de resposta

```json
{
  "name": "pages/abc123",
  "pageUrl": "https://agenciaexemplo.com.br/checagem/vacinas-autismo",
  "publishDate": "2024-03-12",
  "claimReviewAuthor": {
    "name": "Agência de Checagem Exemplo"
  },
  "claimReviewMarkups": [
    {
      "claimReviewed": "Vacinas causam autismo em crianças.",
      "rating": {
        "textualRating": "Falso",
        "ratingValue": 1,
        "worstRating": 1,
        "bestRating": 5,
        "ratingExplanation": "Estudos amplos não encontraram relação entre vacinas e autismo."
      }
    }
  ],
  "versionId": "2"
}
```

---

# 13. `pages.delete` — Remover a marcação de uma página

## 13.1 Descrição

Remove **toda** a marcação `ClaimReview` de uma página.

**Caso de uso principal:** retirar o registro de uma checagem que foi despublicada ou registrada por engano.

> **Atenção:** a operação remove **todos** os `ClaimReview` da página, e não apenas um deles. Para remover só um item, use o fluxo `get → modificar → update`.

## 13.2 Método HTTP e endpoint

```http
DELETE https://factchecktools.googleapis.com/v1alpha1/pages/{page_id}
```

O corpo da requisição deve estar vazio.

## 13.3 Parâmetros (path)

| Parâmetro | Tipo | Obrigatório | Descrição |
| --------- | ---- | ----------- | --------- |
| `name` | `string` | **Sim** | Nome do recurso a remover, no formato `pages/{page_id}`. |

## 13.4 Autenticação

OAuth 2.0 com o escopo `https://www.googleapis.com/auth/factchecktools`.

## 13.5 Exemplo de requisição

**cURL**

```bash
curl -X DELETE "https://factchecktools.googleapis.com/v1alpha1/pages/abc123" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Python**

```python
resposta = sessao.delete(
    "https://factchecktools.googleapis.com/v1alpha1/pages/abc123"
)
resposta.raise_for_status()
print("Status:", resposta.status_code)
```

## 13.6 Exemplo de resposta

Em caso de sucesso, o corpo da resposta é **vazio**:

```json
{}
```

Na prática, o que confirma o sucesso é o status HTTP `200`. Uma consulta posterior com `pages.get` para o mesmo `page_id` deve retornar `404`.

---

# 14. Modelos de dados

## 14.1 Recurso `claims`

```text
Claim
 ├── text          → texto da alegação
 ├── claimant      → quem fez a alegação
 ├── claimDate     → quando foi feita
 └── claimReview[] → revisões (checagens)
       ├── publisher
       │     ├── name
       │     └── site
       ├── url
       ├── title
       ├── reviewDate
       ├── textualRating
       └── languageCode
```

| Objeto | Campo | Tipo | Descrição |
| ------ | ----- | ---- | --------- |
| `Claim` | `text` | `string` | Texto da alegação. Ex.: "Crime has doubled in the last 2 years." |
| `Claim` | `claimant` | `string` | Pessoa ou organização que fez a alegação. |
| `Claim` | `claimDate` | `string` (Timestamp) | Data em que a alegação foi feita. |
| `Claim` | `claimReview[]` | `object[]` | Uma ou mais revisões da alegação. |
| `ClaimReview` | `publisher` | `object` | Publicador da revisão. |
| `ClaimReview` | `url` | `string` | URL da revisão. |
| `ClaimReview` | `title` | `string` | Título da revisão, se puder ser determinado. |
| `ClaimReview` | `reviewDate` | `string` (Timestamp) | Data da revisão. |
| `ClaimReview` | `textualRating` | `string` | Avaliação textual. Ex.: "Mostly false". |
| `ClaimReview` | `languageCode` | `string` | Idioma da revisão. Ex.: `en`, `de`. |
| `Publisher` | `name` | `string` | Nome do publicador. |
| `Publisher` | `site` | `string` | Nome do site, sem protocolo e sem `www`. Baseado apenas na URL da revisão. |

## 14.2 Recurso `pages`

```text
ClaimReviewMarkupPage
 ├── name                 → pages/{page_id}   (saída)
 ├── pageUrl
 ├── publishDate
 ├── claimReviewAuthor
 │     ├── name
 │     └── imageUrl
 ├── claimReviewMarkups[]
 │     ├── url
 │     ├── claimReviewed
 │     ├── claimDate
 │     ├── claimLocation
 │     ├── claimFirstAppearance
 │     ├── claimAppearances[]
 │     ├── claimAuthor  (name, jobTitle, imageUrl, sameAs)
 │     └── rating       (textualRating, ratingValue, worstRating,
 │                       bestRating, ratingExplanation, imageUrl)
 └── versionId            (saída)
```

Os campos de `ClaimReviewMarkup` correspondem às propriedades de [schema.org/ClaimReview](https://schema.org/ClaimReview). Alguns mapeamentos:

| Campo da API | Propriedade schema.org |
| ------------ | ---------------------- |
| `pageUrl` | `ClaimReview.url` |
| `publishDate` | `ClaimReview.datePublished` |
| `claimReviewAuthor.name` | `ClaimReview.author.name` |
| `claimReviewed` | `ClaimReview.claimReviewed` |
| `claimDate` | `ClaimReview.itemReviewed.datePublished` |
| `claimAuthor.name` | `ClaimReview.itemReviewed.author.name` |
| `rating.textualRating` | `ClaimReview.reviewRating.alternateName` |
| `rating.ratingValue` | `ClaimReview.reviewRating.ratingValue` |
| `rating.worstRating` | `ClaimReview.reviewRating.worstRating` |
| `rating.bestRating` | `ClaimReview.reviewRating.bestRating` |

---

# 15. Percorrendo todas as páginas de resultados

Exemplo de função em Python que percorre a paginação de `claims.search`:

```python
import os
import requests

URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


def buscar_todas(query: str, language_code: str = "pt-BR", max_paginas: int = 5):
    params = {
        "query": query,
        "languageCode": language_code,
        "pageSize": 20,
        "key": os.environ["FACTCHECK_API_KEY"],
    }
    resultados = []

    for _ in range(max_paginas):
        resposta = requests.get(URL, params=params, timeout=30)
        resposta.raise_for_status()
        dados = resposta.json()

        resultados.extend(dados.get("claims", []))

        token = dados.get("nextPageToken")
        if not token:
            break
        params["pageToken"] = token  # os demais parâmetros permanecem iguais

    return resultados
```

---

# 16. Boas práticas e limitações

## 16.1 Boas práticas

* **Proteja a chave de API.** Use variáveis de ambiente e restrinja a chave no Cloud Console;
* **Nunca exponha credenciais OAuth** em código de front-end;
* **Trate `429`** com *retry* e espera exponencial;
* **Use `languageCode`** para reduzir ruído nos resultados;
* **Use `maxAgeDays`** quando a atualidade da checagem for relevante;
* **Exiba sempre a fonte.** Mostre o publicador (`publisher.name`) e o link (`url`) junto de cada avaliação;
* **Em `pages.update`, sempre faça `get` antes**, para não perder marcações existentes.

## 16.2 Limitações

* A API está na versão **`v1alpha1`**, então pode sofrer alterações;
* Uma busca sem resultados **não significa** que uma alegação é verdadeira. Significa apenas que nenhuma checagem correspondente foi encontrada;
* As avaliações (`textualRating`) **não são padronizadas**: cada publicador usa seus próprios termos ("Falso", "Enganoso", "Mostly false", "Pants on Fire" etc.);
* Em `claims.imageSearch`, a busca depende de o Google conseguir baixar a imagem da URL informada;
* Os limites exatos de cota devem ser consultados no Google Cloud Console do seu projeto.

---

# 17. Utilização em uma aplicação de verificação

Uma possível arquitetura para consumir a API em um sistema de verificação de notícias:

```text
                    ┌─────────────────┐
                    │     Usuário     │
                    └────────┬────────┘
                             │
                       Envia texto
                             │
                             ▼
                    ┌─────────────────┐
                    │       API       │
                    │  (seu backend)  │
                    └────────┬────────┘
                             │
                  Extrai a alegação principal
                             │
                             ▼
                    ┌─────────────────┐
                    │  claims:search  │
                    │  Fact Check     │
                    │  Tools API      │
                    └────────┬────────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
        Há checagens                Nenhuma checagem
        publicadas                     encontrada
                │                         │
                ▼                         ▼
     Exibir publicador,           Informar que não há
     avaliação e link             checagem disponível
```

O resultado apresentado ao usuário poderia ser algo como:

```text
Checagens encontradas: 2

1. Agência de Checagem Exemplo — "Falso"
   https://agenciaexemplo.com.br/checagem/vacinas-autismo

2. Outro Publicador — "Enganoso"
   https://outropublicador.com/checagem/...

Observação:
Os resultados são checagens publicadas por terceiros sobre
alegações semelhantes e não constituem uma verificação
independente do texto enviado.
```

---

# 18. Resumo das características

| Característica | Informação |
| -------------- | ---------- |
| **Serviço** | `factchecktools.googleapis.com` |
| **Versão** | `v1alpha1` |
| **Tipo** | API REST (JSON) |
| **Recursos** | `claims` e `pages` |
| **Total de métodos** | 7 |
| **Busca por texto** | `GET /v1alpha1/claims:search` |
| **Busca por imagem** | `GET /v1alpha1/claims:imageSearch` |
| **Listar marcações** | `GET /v1alpha1/pages` |
| **Obter marcação** | `GET /v1alpha1/pages/{page_id}` |
| **Criar marcação** | `POST /v1alpha1/pages` |
| **Atualizar marcação** | `PUT /v1alpha1/pages/{page_id}` (atualização completa) |
| **Remover marcação** | `DELETE /v1alpha1/pages/{page_id}` |
| **Auth. de `claims`** | Chave de API (`key`) |
| **Auth. de `pages`** | OAuth 2.0, escopo `https://www.googleapis.com/auth/factchecktools` |
| **Paginação** | `pageSize`, `pageToken`, `offset`, `nextPageToken` |
| **`pageSize` padrão** | 10 |
| **Formato de data** | RFC 3339 (UTC) |
| **Padrão de marcação** | schema.org `ClaimReview` |

---

# 19. Conclusão

A **Google Fact Check Tools API** permite integrar verificações de fatos publicadas por organizações de checagem a aplicações próprias, por meio de dois recursos: `claims`, para **consulta** por texto ou imagem, e `pages`, para **gerenciamento** da marcação `ClaimReview` de páginas.

Seu funcionamento pode ser resumido em:

```text
Texto ou imagem
      │
      ▼
claims:search / claims:imageSearch
      │
      ▼
Claims já verificadas
      │
      ▼
Publicador + Avaliação + Link
```

A principal limitação conceitual é que a API **recupera checagens existentes**, e não realiza uma verificação factual independente. Dessa forma, a ausência de resultados não comprova que uma alegação é verdadeira, assim como a presença de uma checagem deve ser interpretada considerando o publicador e a avaliação atribuída por ele.

Para um sistema de verificação mais robusto, a API pode ser usada como uma das etapas de uma arquitetura maior, combinando **recuperação de checagens existentes, classificação textual e consulta a fontes confiáveis**.

---

## Referência

Documentação oficial da Fact Check Tools API:

**Guia:** https://developers.google.com/fact-check/tools/api

**Referência REST:** https://developers.google.com/fact-check/tools/api/reference/rest

**Guia de marcação ClaimReview:** https://developers.google.com/search/docs/data-types/factcheck
