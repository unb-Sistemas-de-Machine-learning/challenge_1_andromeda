# Qualidade, Limites e Execução

## 1. Qualidade e segurança do conteúdo

### 1.1 O que reduz o risco de erro

- **Frases fixas:** o texto não inventa nomes de fontes nem links.
- **Filtros de correspondência:** a afirmação checada precisa corresponder ao título (`sameClaim`).
- **Tabela de vereditos:** só vereditos conhecidos pontuam.
- **Deduplicação:** checagens repetidas são descartadas.
- **Links validados:** o modal só aceita URLs com esquema HTTP(S) e domínio válido.
- **Aviso explícito:** quando não há checagem pontuada, o próprio texto informa que a análise não confirma os fatos.

### 1.2 O que não existe

- Conferência independente do conteúdo das páginas de checagem.
- Validação da autoridade do publicador.
- Prova de que a heurística de correspondência identificou a afirmação correta.
- Validação por esquema do `AnalysisResult` final.
- Verificação de que a reportagem está em PT-BR.

---

## 2. Limites

<p align="center">Tabela 1 - Limites conhecidos</p>

| Tema | Limite conhecido | Não definido |
|---|---|---|
| Tempo | 10 s conexão e 20 s leitura (app → backend); 15 s (backend → Google) | Prazo total do fluxo; tempo do ONNX |
| Custo | Inferência local; uma chamada ao proxy por análise | Preço e consumo da API do Google |
| Idioma | Frases em português; consulta com `languageCode: "pt"` | Verificação de que a reportagem é PT-BR |
| Tamanho | Artigo 3 MB; resposta da checagem 1 MB; texto mínimo 120 caracteres; 20 mil caracteres e 256 tokens para o modelo; título 300 caracteres | — |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

### 2.1 Falhas que interrompem a análise

- Download ou serviço com resposta não `2xx`.
- Conteúdo grande demais.
- HTML sem texto suficiente.
- Notícia identificada como opinião.
- JSON inválido.

A tela mostra a mensagem da exceção ou uma mensagem genérica.

### 2.2 Falha que não interrompe

Falha no ONNX gera `writingScore = null` e a frase **"Análise da escrita indisponível."** A análise segue com as outras métricas.

---

## 3. Como rodar e testar

### 3.1 App Android

**Pré-requisitos:** JDK 17, Android SDK API 36 com Build Tools, Gradle Wrapper e o arquivo ONNX obtido via Git LFS.

O token `FACTCHECK_PROXY_TOKEN` pode vir de:

- variável de ambiente;
- `~/.gradle/gradle.properties` (`factcheckProxyToken=...`);
- `.env` local.

No PowerShell, a partir da raiz do repositório:

```powershell
git lfs pull
$env:FACTCHECK_PROXY_TOKEN = "SEU_TOKEN"
cd android
.\gradlew.bat testDebugUnitTest
.\gradlew.bat assembleDebug
```

- `testDebugUnitTest` roda os testes JUnit, incluindo `AnalysisRulesTest.kt`.
- `assembleDebug` gera o APK de debug.
- Não há comando para executar a geração do feedback isoladamente.

### 3.2 Backend

Defina as variáveis e suba o servidor (assumindo que o arquivo se chama `main.py`; ajuste se for outro nome):

```bash
export GOOGLE_FACT_CHECK_API_KEY="sua-chave"
export FACTCHECK_PROXY_TOKEN="seu-token"
pip install fastapi httpx uvicorn
uvicorn main:app --reload
```

Verificar saúde:

```bash
curl http://127.0.0.1:8000/
# {"status":"ok","missing_env":[]}
```

Testar a checagem:

```bash
curl -X POST http://127.0.0.1:8000/fact-check \
  -H "Authorization: Bearer seu-token" \
  -H "Content-Type: application/json" \
  -d '{"query":"Governo publica medida","pageSize":10,"languageCode":"pt"}'
```

### 3.3 Resultados esperados

<p align="center">Tabela 2 - Resultados esperados do backend</p>

| Cenário | Resposta |
|---|---|
| Tudo configurado e token correto | `200` com `claims` (ou `{}` sem claims) |
| Token errado | `401` |
| Variável ausente | `503` |
| `languageCode` diferente de `pt` | `422` |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

---

## Histórico de Versão

<table class="full-width-table">
  <thead>
    <tr>
      <th>Versão</th>
      <th>Descrição</th>
      <th>Autor</th>
      <th>Revisor</th>
      <th>Data</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>1.0</td>
      <td>Criação da documentação</td>
      <td><a href="https://github.com/bolzanMGB">Othavio Bolzan</a></td>
      <td> - </td>
      <td>06/10/2026</td>
    </tr>
  </tbody>
</table>
