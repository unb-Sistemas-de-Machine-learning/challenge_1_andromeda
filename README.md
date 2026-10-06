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

The local explanation model is opt-in. On first use, Transformers downloads
`google/flan-t5-small` into the configured local cache; subsequent requests reuse
the cache and the in-memory model. Enable it with:

```env
NEWS_ANALYSIS_SML_ENABLED=true
NEWS_ANALYSIS_SML_MODEL=google/flan-t5-small
NEWS_ANALYSIS_SML_REVISION=<pinned-revision>
NEWS_ANALYSIS_SML_MAX_INPUT_TOKENS=160
NEWS_ANALYSIS_SML_MAX_NEW_TOKENS=80
NEWS_ANALYSIS_SML_TIMEOUT_SECONDS=8
```

The timeout is an **inference budget**, not a download/startup deadline.
Initialization happens once through `prepare()` before timing the summary;
`generated_ms` measures inference, including the wait for the engine's generation
lock. The first request can still take longer while model files are downloaded
or loaded. Prepare the artifacts below before serving traffic to avoid a download
in that request.

Summary generation uses greedy decoding (`num_beams=1`), the decoder cache and
`torch.inference_mode()`. The compact prompt keeps the score and factual state;
if necessary, optional source/writing details are shortened instead of silently
truncating the results. The existing 160 input / 80 output token defaults remain.
The configured time limit is also passed to Transformers as `max_time`: this is
a cooperative stop that finishes the current decoding step, not a hard process
deadline. A timed-out draft is discarded and reported as `sml_timeout`.

`NEWS_ANALYSIS_SML_MANIFEST` may point to a JSON SHA-256 manifest for the local
model files. If the model is disabled, missing or rejected by validation, the API
returns an explicit explanation state and keeps the original analysis unchanged.

The optional preparation command can warm the cache outside the request path:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_sml_model.py `
  --output .data\models\flan-t5-small `
  --model google/flan-t5-small `
  --revision <pinned-revision>
```

To use those prepared files directly, set `NEWS_ANALYSIS_SML_MODEL` to the
absolute output directory and `NEWS_ANALYSIS_SML_MANIFEST` to its `manifest.json`.
The generation path does not require a GPU and does not change Torch's global
CPU thread settings used by the other models.

Regression checks for the summary path:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_explanation.py tests/unit/test_explanation_service.py tests/unit/test_explanation_engine.py
```

Local verification on a Ryzen 5 3600 CPU (Torch 2.14.0, Transformers 5.17.0):
the previous cold load took 30.5 seconds and was charged against the 8-second
summary budget. Its 402-token prompt was cut to 160 tokens before any results
reached the model. With the corrected prompt, five factual states used 87–115
input tokens and produced structurally valid summaries in 0.75–1.88 seconds
(initialization excluded). These are local measurements, not a latency or
semantic-quality guarantee; the existing output validator is still applied.

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
the cleaned title or an opening sentence is the primary candidate. Up to two
additional sentences provide separate evidence without affecting the score.
Each candidate uses its own query plus at most one keyword alternative; results
are combined, and partial failures retain earlier evidence.
`evidence_status` summarizes retrieved verdicts, not the whole article. Outputs use
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
