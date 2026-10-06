# Challenge 1 — Equipe Andrômeda
Sistemas de Machine Learning — UnB/FCTE — 2026/02

## Ideia inicial
Ajudar pessoas que recebem notícias sobre política pelas redes sociais e por
aplicativos de mensagem a avaliar se aquele conteúdo é confiável antes de
repassá-lo aos seus contatos.

A proposta é um assistente com interface simples, pensado para quem não tem
familiaridade com as ferramentas de checagem que já existem hoje.

## Status
O projeto possui um MVP com interface web e API para analisar uma URL de notícia.
O índice operacional combina checagens publicadas recuperadas pela Google Fact
Check Tools API e classificação textual pelo BERTimbau. Credibilidade da fonte
usa cadastros do Atlas da Notícia e listas locais configuráveis. Os resultados incluem
cobertura, contribuições, versões e registro de auditoria em SQLite.

O critério **Checagem de fatos verificáveis** avalia uma afirmação selecionada,
não a reputação da fonte. Consulte [a regra de cálculo e o escopo](docs/ChecagemDeFatos.md).

## Próximos passos
1. Avaliar os sinais do BERTimbau em notícias reais, incluindo textos que desmentem boatos.
2. Avaliar a recuperação e a correspondência de checagens publicadas.
3. Validar a compreensão da nota e da cobertura com o público-alvo.

## Documentação

A [integração Atlas da Notícia](docs/Atlas.md) sincroniza cadastros em SQLite,
inclui evidências de reconhecimento e permite consulta local durante a análise.

O critério [Credibilidade da fonte](docs/Credibilidade.md) já está disponível na
API e na interface, com SCORE_FONTE independente, bases locais configuráveis e
teto na nota final quando houver veto da fonte.
Fonte totalmente indisponível não aplica veto. A [decisão de reconciliação](docs/DecisaoCredibilidade.md)
documenta os pesos 60/40 atuais, a auditoria e a leitura dos formatos históricos.

A documentação do projeto é publicada em:
<https://unb-sistemas-de-machine-learning.github.io/challenge_1_andromeda/>

## Equipe
<div align="center">
   <table style="margin-left: auto; margin-right: auto;">
        <tr>
            <td align="center">
                <a href="https://github.com/DaviNegreiros">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/75706873?v=4" width="150px;"/>
                    <h5 class="text-center">Davi Negreiros <br>232013971</h5>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/Bertolazi">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/122479691?v=4" width="150px;"/>
                    <h5 class="text-center">Gabriel Bertolazi <br>202023663</h5>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/joaopedrodasilvarodrigues">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/100419740?v=4" width="150px;"/>
                    <h5 class="text-center">João Pedro da Silva Rodrigues <br>211031074</h5>
                </a>
            </td>
        </tr>
        <tr>
            <td align="center">
                <a href="https://github.com/bolzanMGB">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/149620306?v=4" width="150px;"/>
                    <h5 class="text-center">Othavio Bolzan <br>231039150</h5>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/Pietrocv">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/86116655?v=4" width="150px;"/>
                    <h5 class="text-center">Pietro Visentin <br>232014754</h5>
                </a>
            </td>
        </tr>
    </table>
</div>

## Disciplina

Sistemas de Machine Learning — UnB/FCTE — Profs. Isaque Alves e Guilherme Fernandes — 2026/2
# Challenge 1 Andromeda

## News Analysis Service

This repository includes a FastAPI service that analyzes one HTTP/HTTPS news URL
and returns an operational reliability index with traceable criterion evidence.
The final score is not a probability that the news is true or false.

### Setup

```powershell
uv sync --extra dev
$env:FACTCHECK_API_KEY = "<your-api-key>"
uv run uvicorn news_analysis.api.app:app --reload
```

Alternatively, create a local `.env` file in the repository root so the key is
loaded automatically whenever the app starts:

```text
FACTCHECK_API_KEY=<your-api-key>
```

Open the API documentation at:

```text
http://127.0.0.1:8000/docs
```

Open the application screen at:

```text
http://127.0.0.1:8000/
```

Paste a news URL and optionally select a specific claim to check. The page
shows the operational index, formula, analysis ID, coverage, criterion status,
intended/effective weights, contributions, evidence and limitations. The
fact-check card remains visible when unavailable, displaying the reason and
recorded queries. Writing-only results are labeled "Somente estilo de escrita".
Expandable writing-segment details expose tokens, characters and predictions.

The home page also shows whether the Fact Check API key was detected, without
exposing the key value.

### Writing-style inference

The writing-style criterion runs the actual BERTimbau classifier
`vzani/portuguese-fake-news-classifier-bertimbau-combined` on CPU. Tokenizer and
weights are loaded lazily and reused within each server process. The first
analysis downloads the pinned revision if it is not already cached. Optionally,
set `NEWS_ANALYSIS_MODEL_CACHE` to choose a Hugging Face cache directory.

The entire extracted text is processed in non-overlapping windows of at most
512 tokens, including special tokens. Each segment reports the actual model
label, confidence, token count, and probability of class `True` (`LABEL_1`;
`LABEL_0` means `Fake`). The criterion score is the character-weighted average
of those probabilities. No keyword rules or heuristic fallback are used.
If loading or inference fails, this criterion is unavailable and excluded
from scoring. Its intended weight remains 40%; fact-checking remains 60%.
Class probabilities describe the model output, not factual verification.

### Analyze A URL

Optional `claim` (3 to 500 characters) selects an assertion to check; otherwise
the cleaned title or first sentence is a candidate. Outputs use
`criteria.verifiable_facts` and include the selected claim, original verdicts,
evidence URLs, exclusions, publisher means and search limits. Only whole mapped
labels and unique applicable reviews contribute. Values are averaged per checking
publisher, then equally across publishers. Google does not supply source ratings,
and this result does not verify all facts in the article.

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/analyses" `
  -ContentType "application/json" `
  -Body '{"url":"https://example.com/noticia","user_id":"demo"}'
```

The response includes article metadata, criterion availability, source/model
details, normalized criterion scores, contributions, coverage, pipeline version,
and explicit limitations. Full extracted article text is not returned or stored.

### Troubleshooting

If the result says fact-checking was skipped because `FACTCHECK_API_KEY` is not
configured, create `.env` as shown above or stop the server, set the key in the
same PowerShell session, and start it again:

```powershell
$env:FACTCHECK_API_KEY = "<your-api-key>"
uv run --extra dev uvicorn news_analysis.api.app:app --reload
```

If the key is configured but the criterion is unavailable, inspect its card:
Google may return no reviews, claims may not match the selected assertion,
ratings may be unmapped, publisher identity may be missing, or the API may fail.
Recorded queries and evidence exclusions remain available. Missing criterion
data is explicitly reported; legacy response keys are recognized without
inventing details. Refresh the page after restarting a server to load its UI.

See [Google Fact Check integration](docs/Manual_Google_Fact_Check_Tools_API.md),
[fact scoring](docs/ChecagemDeFatos.md), and [interface and API](docs/InterfaceEAPI.md).
