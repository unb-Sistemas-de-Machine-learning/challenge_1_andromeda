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
API e na interface, com SCORE_FONTE, bases locais configuráveis e peso previsto
de 20% na nota final. O veto da fonte ainda pode aplicar um teto à média.
Fonte totalmente indisponível não aplica veto. A [decisão de reconciliação](docs/DecisaoCredibilidade.md)
documenta a auditoria e a leitura dos formatos históricos. A média atual usa
65% para checagem factual, 20% para credibilidade da fonte e 15% para escrita.

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

The application ships two optimized, pinned ONNX models in ZIP parts under
`src/news_analysis/assets/bundles`: BERTimbau (INT8) and FLAN-T5 (FP32 encoder,
INT8 decoders). Both load exclusively from local files. The BERTimbau artifact is the
default writing classifier. FLAN-T5 is enabled by default as a copy editor for
the already generated explanation. It receives only that explanation, not the
article or criterion data. Installation and analysis do not download model weights.

An ordinary Git clone contains every ZIP part; Git LFS is not required. On first
use of each model, the application verifies SHA-256 checksums and extracts it to
`.data/models/bundled` (or `NEWS_ANALYSIS_MODEL_DIR`). Later runs reuse the
extracted files. Keep enough free disk space for both the compressed parts and
roughly 370 MB of extracted models. Missing or corrupted parts cause an error
instead of triggering a download. The writing model's artifact hash is included in the
analysis version. `NEWS_ANALYSIS_WRITING_ONNX_PATH` can override its bundled
path with another local artifact.

The FLAN engine has a local SHA-256 manifest and loads on first use. Its inference
timeout starts after loading. The tokenizer, configuration, and three required
ONNX graphs are included in the package. A generated edit is used only if a
conservative check confirms that the substantive words, score band and numbers
are preserved. Otherwise the original explanation is shown. Set
`NEWS_ANALYSIS_SML_ENABLED=false` to skip the copy-edit attempt.

Copy editing uses greedy decoding (`num_beams=1`), the decoder cache and
`torch.inference_mode()`. The prompt contains only the original summary and
does not silently truncate it. The defaults allow 256 input and 160 output tokens.
The configured time limit is also passed to Transformers as `max_time`: this is
a cooperative stop that finishes the current decoding step, not a hard process
deadline. A timed-out draft is discarded and reported as `sml_timeout`.

`NEWS_ANALYSIS_SML_MANIFEST` and `NEWS_ANALYSIS_SML_MODEL` may override the
bundled local paths. Build scripts under `scripts/` regenerate the optimized
artifacts from already cached pinned source weights; users do not run them.
The generation path does not require a GPU.

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
from scoring. Its intended weight is 15%; fact-checking is 65% and source
credibility is 20%. Available weights are renormalized when a criterion is missing.
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
