# Visão Geral

Dado um título ou um link de reportagem, o app devolve:

- Uma classificação de confiabilidade: alta, média, baixa ou baixíssima.
- Um texto explicativo montado por frases fixas em Kotlin.
- Opcionalmente, um botão de detalhes que abre um modal com checagens factuais correspondentes.

---

## 1. Componentes do Sistema

O sistema é dividido em três componentes principais, cada um com uma responsabilidade bem definida:

<p align="center">Tabela 1 - Componentes do sistema</p>

| Número | Componente | Função |
|---|---|---|
| 01 | App Android | Interface com a pessoa, orquestração do pipeline, inferência do BERTimbau no aparelho e aplicação das regras que geram o feedback. |
| 02 | Backend de checagem | Proxy FastAPI no Render que esconde a chave do Google, exige token Bearer e repassa o JSON de checagens sem transformá-lo. |
| 03 | Serviços externos | GDELT: Busca por título. <br> Google Fact Check: Checagens factuais. <br> Atlas da Notícia: Domínios de veículos. <br> Git LFS: Armazenamento do modelo `.onnx`. |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

---

## 2. Fluxo de Funcionamento

<p align="center">Tabela 2 - Etapas detalhadas do fluxo</p>

| Número | Etapa | O que acontece |
|---|---|---|
| 01 | Entrada | A pessoa informa um título ou um link. Para link, valida-se HTTPS. Para título, consulta-se a GDELT e a pessoa escolhe uma reportagem. |
| 02 | Download e extração | A página é baixada e o **Jsoup** extrai informações do HTML. |
| 03 | Filtro de opinião | Se a reportagem parece opinião ou editorial, a avaliação é interrompida. |
| 04 | Aplicação de Métricas | **1. Checagens factuais;** <br> **2. Credibilidade da Fonte;** <br> **3. Tipo de Escrita.** |
| 05 | Cálculo dos scores | Cada métrica possui um peso. É gerado um score de 0 a 1 para cada métrica. Scores ausentes saem da conta e os pesos são renormalizados. |
| 06 | Geração do texto | O texto não é gerado por LLM: é montado por **frases fixas** escolhidas por condições (faixa, checagens, critérios disponíveis, Atlas, institucional, escrita) e unidas com espaço. |
| 07 | Nível de confiabilidade | A nota final (0–100) define a faixa: **alta** (> 85), **média** (> 70), **baixa** (> 40) ou **baixíssima** (≤ 40). |
| 08 | Exibição | A tela mostra a explicação. O botão de detalhes só aparece se houver evidência (ver seção 8). |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

<p align="center"><b>Figura 1 - Fluxo de funcionamento do app</b></p>

<p align="center">
  <img src="/02_Sobre/fluxo.png" alt="Fluxo de funcionamento do app">
</p>

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

---

## 3. Qualidade e segurança do conteúdo

### 3.1 O que reduz o risco de erro

- Frases fixas: o texto não inventa nomes de fontes nem links.
- Filtros de correspondência, tabela de vereditos e deduplicação (tópico 6).
- Links do modal validados quanto a esquema HTTP(S) e domínio.
- Aviso explícito de que a análise não confirma fatos.

### 3.2 O que não existe

- Conferência independente do conteúdo das páginas de checagem.
- Validação da autoridade do publicador.
- Prova de que a heurística identificou a afirmação correta.
- Validação por esquema do `AnalysisResult` final.

---

## 4. Limites

<p align="center">Tabela 3 - Limites conhecidos</p>

| Tema | Limite conhecido | Não definido |
|---|---|---|
| Tempo | 10 s conexão, 20 s leitura (app); 15 s (backend → Google) | Prazo total do fluxo; tempo do ONNX |
| Custo | Inferência local; uma chamada ao proxy por análise | Preço e consumo da API do Google |
| Idioma | Frases em português; consulta com `languageCode: "pt"` | Verificação de que a reportagem é PT-BR |
| Tamanho | Artigo 3 MB; resposta da checagem 1 MB; texto mínimo 120 caracteres; 20 mil caracteres e 256 tokens para o modelo; título 300 caracteres | — |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

### 4.1 Falhas que interrompem a análise

- Download ou serviço com resposta não `2xx`.
- Conteúdo grande demais.
- HTML sem texto suficiente.
- Notícia identificada como opinião.
- JSON inválido.

A tela mostra a mensagem da exceção ou uma mensagem genérica.

### 4.2 Falha que não interrompe

Falha no ONNX gera `writingScore = null` e a frase **"Análise da escrita indisponível."**

---

## 5. Como rodar e testar

### 5.1 App Android

**Pré-requisitos:** JDK 17, Android SDK API 36 com Build Tools, Gradle Wrapper e arquivo ONNX via Git LFS.

O token `FACTCHECK_PROXY_TOKEN` pode vir de variável de ambiente, de `~/.gradle/gradle.properties` (`factcheckProxyToken=...`) ou do `.env` local.

```powershell
git lfs pull
$env:FACTCHECK_PROXY_TOKEN = "SEU_TOKEN"
cd android
.\gradlew.bat testDebugUnitTest
.\gradlew.bat assembleDebug
```

`testDebugUnitTest` roda os testes JUnit, incluindo `AnalysisRulesTest.kt`. Não há comando para executar a geração do feedback isoladamente.

### 5.2 Backend

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

### 5.3 Resultados esperados

<p align="center">Tabela 4 - Resultados esperados do backend</p>

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
