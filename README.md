# Challenge 1 — Equipe Andrômeda
Sistemas de Machine Learning — UnB/FCTE — 2026/02

## Ideia inicial
Ajudar pessoas que recebem notícias sobre política pelas redes sociais e por
aplicativos de mensagem a avaliar se aquele conteúdo é confiável antes de
repassá-lo aos seus contatos.

A proposta é um assistente com interface simples, pensado para quem não tem
familiaridade com as ferramentas de checagem que já existem hoje.

## Status
O projeto está em **fase de exploração**. Ainda não definimos o nome, o escopo
final, as fontes de dados, a abordagem de modelagem nem os critérios de avaliação
— este repositório acompanha essas decisões conforme forem sendo tomadas.

## Próximos passos
1. Entender como jornalistas e agências de checagem verificam, hoje, se uma
   notícia é falsa — quais sinais eles observam e qual é o processo que seguem.
2. A partir disso, mapear quais dessas etapas podem ser apoiadas por Machine
   Learning e quais não podem.
3. Levantar que dados existem para isso e onde estão.
4. Investigar que modelos e abordagens já são usados para problemas parecidos.
5. Definir o escopo do sistema e como vamos medir se ele funciona.

## Documentação
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

Paste a news URL, submit it, and the page will show the operational
reliability index, criterion coverage, per-criterion scores, contribution
details, pipeline version, and limitations.

The home page also shows whether the Fact Check API key was detected, without
exposing the key value.

### Analyze A URL

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

If the key is configured but the criterion is still unavailable, the interface
will now distinguish whether Google returned no reviews, whether the returned
reviews did not clearly match the article, or whether the rating text could not
be normalized.
