# Plano e implementação da explicabilidade local com SML

Este documento descreve a explicação gerada localmente por um modelo pequeno (SML), considerando o estado real do projeto em outubro de 2026. O `google/flan-t5-small` é o engine implementado e sua ativação é controlada por configuração; ele não altera o resultado atual das análises.

## 1. Diagnóstico do projeto atual

O backend é uma aplicação FastAPI em `src/news_analysis/api/app.py`. A interface também está embutida nesse arquivo, na constante `INDEX_HTML`; não existe hoje um aplicativo Android separado nem um runtime de inferência no dispositivo.

O fluxo principal está em `src/news_analysis/pipeline/analyzer.py`:

1. valida e busca a URL;
2. extrai artigo, título, texto e metadados;
3. executa a busca do Google Fact Check em `src/news_analysis/criteria/fact_check_search.py`;
4. classifica estilo de escrita com BERTimbau em `src/news_analysis/criteria/writing_style.py`;
5. calcula a credibilidade da fonte e os sinais Atlas;
6. agrega os critérios e aplica o veto de fonte quando aplicável;
7. grava o resultado auditável em SQLite.

O contrato público de análise é o modelo `Analysis` em `src/news_analysis/pipeline/models.py`. Ele já contém material suficiente para uma explicação curta, mas mistura evidência, metadados de auditoria e detalhes internos. O SML deve receber uma visão derivada e mínima desse contrato, nunca o objeto inteiro nem o HTML do artigo.

O resultado atual distingue ausência de evidência de evidência negativa. No Fact Check existem `evidence_status` (`SUPPORTED`, `REFUTED`, `MIXED`, `MATCHED_UNSCORED` e `UNAVAILABLE`), contagens, classificações de correspondência e avaliações dos revisores. O score final também expõe `score_before_veto`, `source_veto_applied`, `coverage`, pesos efetivos, fórmula e limitações. Esses campos devem ser preservados como fonte de verdade.

## 2. Dados disponíveis e seleção para explicação

| Origem | Usar no contexto do SML | Tratamento |
|---|---|---|
| `final.score` | Sim, quando disponível | Passar como número inteiro ou decimal já arredondado e com a unidade definida. |
| `final.score_before_veto` e `source_veto_applied` | Sim | Explicar a diferença somente quando o veto ocorreu. |
| `final.coverage` e `effective_weights` | Sim | Mostrar quais critérios contribuíram e quais ficaram indisponíveis. |
| Fact Check: `available`, `status`, `evidence_status` | Sim | Diferenciar `UNAVAILABLE` de `MATCHED_UNSCORED` e de veredicto. |
| Fact Check: `target_claim` e `claim_origin` | Sim | Usar somente a afirmação selecionada, truncada por limite fixo. |
| Fact Check: contagens de avaliações, editoras, conflitos e relacionadas | Sim | Resumir em números; não enviar o JSON bruto. |
| Fact Check: `textual_rating` e `rating_interpretation` | Sim, agregado | Usar categorias já normalizadas; não deixar o modelo inventar o significado de um rótulo. |
| Fact Check: URLs, HTML, `raw`, títulos e datas de todas as avaliações | Não no primeiro contexto | Manter no relatório auditável e na UI de evidência, fora do prompt. |
| Estilo: `score`, `prediction.label`, `qualitative_state`, `segments_analyzed` | Sim | Apresentar como sinal de estilo, nunca como veredito factual. |
| Estilo: logits, tokens, segmentos completos e exceções | Não | São detalhes internos e podem induzir explicações falsas. |
| Credibilidade/Atlas: score, confiança, flags, veto e estados | Sim, resumido | Informar sinais e limitações; não transformar credibilidade da fonte em prova de falsidade. |
| Atlas: respostas brutas de provedores, hashes, evidências e caminhos locais | Não | São dados de auditoria e podem conter informação irrelevante ou sensível. |
| Artigo: título, editor e domínio | Opcional | Preferir título e domínio; não enviar texto integral, autor ou URL completa sem necessidade. |
| `pipeline_version` | Somente metadado | Guardar para auditoria e suporte, sem pedir ao SML que o interprete. |
| erros e limitações | Sim, estruturados | Passar códigos e mensagens controladas, nunca stack traces ou exceções livres. |

O contexto deve declarar explicitamente quando um valor é desconhecido. Campo ausente não significa `0`, falso ou refutado. Essa regra é essencial para que uma falha de rede do Google não vire uma conclusão negativa.

A prioridade da explicação é fixa: **evidência factual > sinais dos analisadores > score agregado**. O score descreve o resultado operacional e não deve ser apresentado como causa ou evidência factual.

## 3. Contrato implementado

O contrato deve separar o contexto determinístico do texto produzido pelo modelo:

```text
ExplanationContext -> ExplanationEngine -> SmlExplanation
```

Os modelos Pydantic implementados são:

```python
class ExplanationContext(BaseModel):
    analysis_id: str
    language: Literal["pt-BR"]
    final_score: float | None
    score_before_veto: float | None
    source_veto_applied: bool | None
    coverage: float
    fact_check: FactCheckSummary
    writing_style: WritingSummary
    source: SourceSummary
    limitations: list[str]
    allowed_numbers: list[str]  # auxiliar da validação, não prova semântica
    allowed_names: list[str]  # auxiliar da validação, não prova semântica
    context_version: str

class SmlExplanation(BaseModel):
    status: Literal["IDLE", "LOADING", "SUCCESS", "ERROR", "UNAVAILABLE"]
    text: str | None
    model_id: str | None
    model_revision: str | None
    validation: Literal["VALID", "REJECTED", "FALLBACK"] | None
    generated_ms: int | None
    error_code: str | None
```

O contrato deve ser fechado (`extra="forbid"`), versionado e independente de `Analysis`. A UI só deve conhecer `status`, `text` e um estado de indisponibilidade. O runtime, o tokenizer e o formato do artefato ficam atrás de `ExplanationEngine`.

Estados previstos:

- `IDLE`: nenhuma explicação solicitada;
- `LOADING`: modelo ou geração em andamento;
- `SUCCESS`: texto validado e pronto para exibição;
- `ERROR`: falha técnica registrada sem alterar a análise;
- `UNAVAILABLE`: o modelo não está instalado, não cabe no dispositivo ou foi desativado por configuração.

## 4. Arquitetura implementada, sem alterar o cálculo atual

Os módulos isolados utilizados são:

- `src/news_analysis/explanation/context.py`: transforma `Analysis` em `ExplanationContext`, com truncamento e remoção de dados sensíveis;
- `src/news_analysis/explanation/prompt.py`: prompt versionado, delimitadores e instruções de saída;
- `src/news_analysis/explanation/engine.py`: protocolo do engine e adaptação do runtime escolhido;
- `src/news_analysis/explanation/validation.py`: validação determinística;
- `src/news_analysis/explanation/version.py`: versão do contexto, prompt e artefato.

O primeiro ponto de integração deve ser posterior ao término de `NewsAnalyzer.analyze`. A explicação é derivada do `Analysis` persistido e não participa de `aggregate_final_score`, do veto de fonte nem das regras do Fact Check. Se o modelo falhar, a análise original continua idêntica.

O fluxo implementado é:

1. salvar a análise atual;
2. construir o contexto seguro e compacto;
3. tentar gerar a explicação em uma tarefa separada;
4. validar o texto;
5. exibir `SUCCESS`, `ERROR` ou `UNAVAILABLE`; nenhum texto substituto é fabricado sem o SML;
6. registrar apenas métricas e versões, sem salvar prompt com artigo bruto.

## 5. Avaliação do FLAN-T5-small

O `google/flan-t5-small` é um modelo text-to-text de aproximadamente 77 milhões de parâmetros, licenciado sob Apache-2.0, com suporte multilíngue que inclui português e exemplos oficiais usando `transformers` com `AutoTokenizer` e `AutoModelForSeq2SeqLM`. A ficha oficial também alerta que ele não deve ser usado diretamente em uma aplicação real sem avaliação de segurança, justiça e desempenho. Consulte a [ficha oficial do modelo](https://huggingface.co/google/flan-t5-small).

Isso o torna adequado para um protótipo de explicações curtas e controladas, mas não garante qualidade em português brasileiro nem fidelidade aos campos do projeto. O modelo pode omitir uma condição, trocar a relação entre score e evidência ou inventar uma causa plausível. Portanto:

- o modelo não decide score, veredicto, aplicabilidade ou peso;
- o prompt recebe fatos já resumidos e delimitados;
- a saída precisa passar por validação determinística;
- a falha de validação retorna `ERROR` estruturado e não exibe texto não validado;
- nenhuma explicação do modelo deve ser tratada como evidência.

Não há motivo para fine-tuning na primeira versão. Antes de qualquer ajuste, deve existir um conjunto anotado de exemplos brasileiros, uma métrica de fidelidade e uma comparação com a ausência de explicação. Fine-tuning só será considerado se o modelo base não atingir o limiar de fidelidade depois de prompt, truncamento e validação adequados.

## 6. Runtime e estratégia de distribuição

O projeto atual executa Python no backend e não possui Android. Assim, “modelo embutido no app” é uma decisão futura de produto, não uma capacidade existente.

O caminho seguro é em fases:

1. **Protótipo de referência:** `transformers`/PyTorch em processo Python, somente para medir qualidade e tempo.
2. **Exportação:** testar ONNX com tokenizer e laço encoder-decoder completo. A exportação de T5 exige validar o decoder autoregressivo, máscaras, cache e parada por `eos_token`; exportar somente o encoder não é suficiente.
3. **Benchmark no dispositivo:** comparar ONNX Runtime Mobile e TensorFlow Lite/LiteRT em um aparelho Android representativo, medindo cold start, warm start, RAM, latência p50/p95, tamanho do APK e consumo de bateria.
4. **Escolha:** só embutir o artefato se a qualidade e os limites de memória forem aceitáveis. Caso contrário, manter o SML desativado e informar indisponibilidade, sem degradar a análise.

Quantização INT8 e redução de comprimento devem ser testadas como variantes do artefato, sempre comparadas a um conjunto de referência. Não se deve assumir que uma conversão automática de T5 preservará o comportamento do modelo.

## 7. Contexto compacto e limites de desempenho provisórios

O primeiro contexto deve conter apenas score, veto, cobertura, estado factual, afirmação truncada, estado do estilo e resumo mínimo da fonte. Fórmulas, pesos, URLs, hashes, avaliações brutas e detalhes de auditoria permanecem fora dele. O alvo inicial é até **600 caracteres ou 160 tokens**.

Estes são alvos para benchmark, não garantias:

| Medida | Alvo inicial |
|---|---:|
| Contexto enviado ao modelo | até 600 caracteres ou 160 tokens |
| Saída | até 80 tokens em português |
| Carregamento frio | até 3 s em aparelho de referência |
| Geração aquecida | p95 até 1,5 s |
| Memória adicional | até 300 MB durante a geração |
| Repetição | uma explicação por `analysis_id` e versão de contexto |

Se o alvo falhar, reduzir contexto e saída, usar quantização ou desativar o SML. O tempo de geração nunca pode bloquear a persistência nem atrasar indefinidamente `GET /analyses/{analysis_id}`.

## 8. Prompt e proteção contra alucinação

O prompt implementado é versionado conceitualmente e contém apenas dados do `ExplanationContext`:

```text
Você explica um resultado já calculado por um sistema de análise de notícias.
Responda em português brasileiro, em até 3 frases curtas.
Use somente os dados entre <contexto> e </contexto>.
Não crie fatos, números, URLs, nomes de pessoas, veículos ou causas.
Não diga que a notícia é verdadeira ou falsa se o contexto não trouxer esse veredicto.
Trate indisponível, desconhecido e sem avaliação como ausência de evidência.
Explique: (1) o resultado, (2) os sinais que contribuíram, (3) a principal limitação.
<contexto>{json_context}</contexto>
```

O contexto deve usar JSON serializado, campos enumerados e delimitadores. Texto vindo de título, claim ou rótulo externo deve ser normalizado e limitado antes de entrar no prompt, porque pode conter instruções de prompt injection.

O validador deve trabalhar em camadas, sem tentar ser um verificador semântico perfeito:

1. limite estrutural de tamanho e quantidade de frases;
2. números e URLs novos em relação ao contexto;
3. afirmações incompatíveis com estados explícitos;
4. termos proibidos, HTML ou instruções;
5. `VALID` ou `REJECTED`; rejeição não deve liberar texto para o usuário.

Listas como `allowed_numbers` são auxiliares para detectar valores novos, não a solução principal. Uma frase válida pode explicar uma qualidade sem repetir um número.

O validador deve rejeitar ou substituir a saída se ela:

- exceder o limite de caracteres ou frases;
- introduzir números, porcentagens, URLs ou nomes ausentes nos valores permitidos;
- afirmar certeza quando o estado é `UNAVAILABLE`, `MATCHED_UNSCORED` ou cobertura parcial;
- contradizer `score_before_veto`, `source_veto_applied`, `evidence_status` ou limitações;
- contiver instruções, HTML, stack trace ou conteúdo fora do propósito explicativo.

Quando o SML não puder responder, o contrato retorna somente o estado e o código do problema. Isso evita apresentar uma explicação que não foi produzida pelo modelo solicitado.

## 9. Segurança, privacidade e auditoria

- Não enviar texto integral do artigo, HTML, cookies, cabeçalhos ou URL completa ao prompt.
- Remover chaves, tokens, exceções e caminhos locais dos logs.
- Limitar tamanho de entrada, número de tokens, tempo de geração e número de tentativas.
- Fixar `model_id`, revisão, hash do artefato, tokenizer, prompt e `context_version`.
- Tratar o APK como extraível: o modelo embutido não é segredo e não deve conter credenciais.
- Não permitir que a explicação altere `Analysis`, score, evidências ou auditoria original.
- Registrar métricas agregadas de latência, status, rejeição e indisponibilidade; não registrar o prompt completo por padrão.

## 10. Interface implementada

Como a interface atual está em `INDEX_HTML`, a integração deve adicionar um cartão depois do resumo do score e dos critérios, sem reescrever a tela. O título deve deixar claro que o conteúdo explica a avaliação, e não resume a notícia. O cartão deve mostrar:

- “Por que esta notícia recebeu esta avaliação?”;
- estado de carregamento;
- texto validado;
- aviso curto quando estiver indisponível ou quando a resposta for rejeitada;
- versões apenas em uma área de detalhes para depuração.

O frontend não deve interpretar `evidence_status`, calcular pesos ou decidir se a frase é confiável. Ele apenas renderiza o contrato `SmlExplanation` e mantém os cartões de evidência existentes como fonte detalhada.

## 11. Implementação do SML

A integração implementada usa o SML como única fonte de texto explicativo:

- `src/news_analysis/explanation/models.py` define `ExplanationContext` e `SmlExplanation` com contrato fechado;
- `src/news_analysis/explanation/context.py` reduz `Analysis` a um contexto compacto e explicita indisponibilidade;
- `src/news_analysis/explanation/prompt.py` produz o prompt compacto e delimitado;
- `src/news_analysis/explanation/engine.py` carrega localmente o FLAN-T5, reutiliza o modelo em memória e limita a geração;
- `src/news_analysis/explanation/service.py` executa o SML e devolve estados explícitos quando ele está desativado, indisponível ou rejeitado;
- `src/news_analysis/explanation/validation.py` aplica validação estrutural, numérica, de compatibilidade e segurança;
- `Analysis.explanation` expõe o resultado de forma aditiva, sem alterar score, veto, Fact Check ou auditoria original;
- `INDEX_HTML` renderiza o cartão “Por que esta notícia recebeu esta avaliação?”.

O engine é criado uma vez por dependência da aplicação quando `NEWS_ANALYSIS_SML_ENABLED=true`. Assim como o classificador BERTimbau já existente, o primeiro uso baixa o modelo para `NEWS_ANALYSIS_MODEL_CACHE` e as chamadas seguintes reutilizam o cache e a instância em memória. Falha, timeout ou rejeição não fabricam texto alternativo: retornam `ERROR` ou `UNAVAILABLE` com código estruturado.

## 12. Testes e benchmark antes da ativação

Implementar testes somente quando os módulos forem criados:

1. **Contexto:** campos obrigatórios, truncamento, ausência explícita, remoção de HTML e dados sensíveis.
2. **Prompt:** versão estável, delimitadores e resistência a instruções inseridas no título/claim.
3. **Validador:** números novos, contradições, estados indisponíveis, excesso de tamanho e rejeição.
4. **Engine falso:** sucesso, erro, timeout, modelo ausente e cancelamento sem alterar `Analysis`.
5. **Contrato/API:** serialização fechada e estados `IDLE/LOADING/SUCCESS/ERROR/UNAVAILABLE`.
6. **Regressão:** os scores, critérios, veto, auditoria e respostas atuais permanecem iguais com o SML desligado.
7. **Qualidade:** conjunto fixo de análises brasileiras anotadas por humanos, avaliando fidelidade, cobertura dos três pontos do prompt, contradições e utilidade.
8. **Performance:** cold/warm, p50/p95, RAM, tamanho do artefato e bateria nas variantes PyTorch, ONNX e LiteRT.

O critério de ativação deve exigir que o SML atinja o limiar de fidelidade e que 100% das falhas sejam representadas por estado estruturado. A qualidade deve ser avaliada por revisão humana; BLEU ou ROUGE sozinhos não medem fidelidade às evidências.

## 13. Próximas etapas de validação e distribuição

1. Preparar o artefato local, fixar revisão e gerar o manifesto SHA-256.
2. Medir FLAN-T5-small em Python com prompt versionado e conjunto de referência.
3. Definir o limiar de fidelidade humana e os limites de latência/memória.
4. Exportar e comparar runtimes no dispositivo escolhido, caso exista alvo móvel.
5. Ativar por configuração e observar métricas antes de ampliar o uso.

As decisões que precisam permanecer abertas até os benchmarks são: ONNX Runtime Mobile versus LiteRT, quantização, limites finais de tokens, aparelho mínimo, limiar de fidelidade, política de atualização do artefato e eventual fine-tuning. O SML já está implementado sem modificar o score ou a busca do Google Fact Check.
