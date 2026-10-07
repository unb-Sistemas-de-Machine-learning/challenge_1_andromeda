# Sobre o Sistema

## 1. Objetivo

O sistema ajuda uma pessoa a decidir se deve compartilhar uma notícia. Ele não diz se a notícia é verdadeira ou falsa. Ele reúne sinais, calcula uma nota e explica o resultado em linguagem simples.

## 2. Entrada e Saída de Dados

Entrada de Dados do Sistema

| Formato | Situação | O que o sistema faz |
| ------- | -------- | ------------------- |
| Link da notícia | Disponível | Baixa a página e analisa a matéria do próprio link. |
| Texto copiado e colado | Previsto, ainda não disponível | O sistema procuraria matérias sobre o conteúdo e as analisaria. Hoje o back-end aceita apenas links. |

Em relação a Saída

## 3. Fluxo 

1. **Inserção:** Usuário insere o link da matéria que quer verificar.
1. **Validação e download:** O endereço precisa ser HTTP ou HTTPS. A página é baixada em até 10 segundos, com limite de 5 MB e de 5 redirecionamentos.
2. **Extração:** O HTML é transformado no texto principal da matéria e em metadados (título, autor, data, veículo). Se o texto tiver menos de 1.000 caracteres, a análise é interrompida.
3. **Três análises:** 
- 3.1 **Análise dos Fatos:**
- 3.2 **Análise do Tipo de Escrita:**
- 3.3 **Análise da Credibilidade da Fonte:**
4. **Nota final.** As análises são combinadas em um índice de 0 a 100.
5. **Explicação.** Um SML (Small Language Model) escreve uma explicação curta a partir do que foi encontrado.
6. **Resultado.** A tela mostra um veredito em três níveis, a explicação, as fontes para conferir e o próximo passo.

---

## 4. Análise dos fatos: Google Fact Check

### 4.1 Funcionamento

A primeira análise procura **checagens que agências de checagem já publicaram** sobre a afirmação da notícia. Ela usa a **Google Fact Check Tools API** (`claims:search`).

A API não é um detector de fake news. Ela não avalia se um texto é verdadeiro. Ela devolve checagens feitas por pessoas, com o nome da agência, a avaliação e o link.

```text
Afirmação escolhida
        │
        ▼
Busca na Google Fact Check API
        │
        ▼
Checagens publicadas (agência, avaliação, link)
        │
        ▼
Comparação com a afirmação da notícia
        │
        ▼
Nota F, de 0 a 1
```

**Qual afirmação é pesquisada.** O sistema usa, nesta ordem: a afirmação informada pelo usuário, o título da matéria ou a primeira frase do texto. Até 3 frases candidatas são testadas. A frase principal é a que gera nota. As demais são só consultadas e não entram na nota.

**Como uma checagem é aceita.** A comparação entre a afirmação da notícia e a afirmação checada é **léxica e controlada**, não semântica. Uma checagem só conta quando:

- os números e as datas são os mesmos;
- os locais citados são os mesmos;
- negações, desmentidos e ações não se contradizem;
- quem fez a declaração é o mesmo;
- há sobreposição suficiente de palavras (pelo menos 3 palavras em comum e 80% de similaridade).

Checagens que tratam de um assunto parecido, mas que não passam nesses testes, ficam como **relacionadas**. Elas aparecem para consulta, mas **não entram na nota**.

### 4.2 Cálculo da Nota

Cada avaliação em texto é convertida em um valor de 0 a 1:

| Valor | Avaliações reconhecidas (exemplos) |
| ----: | ---------------------------------- |
| **1,00** | verdadeiro, correto, true |
| **0,75** | majoritariamente verdadeiro, mostly true |
| **0,50** | meia verdade, impreciso, misto, partly true |
| **0,25** | enganoso, fora de contexto, descontextualizado, majoritariamente falso |
| **0,00** | falso, fake, não é verdade, false |

Avaliações com outros rótulos não têm conversão. Elas ficam registradas, mas não geram nota.

**Fórmula:**

```text
1. Para cada agência: média das suas checagens únicas e aceitas.
2. F = média das médias das agências (todas com o mesmo peso).
```

Assim, uma agência que publicou várias checagens não pesa mais do que as outras.

**Leitura do resultado** (`evidence_status`):

| Estado | Quando acontece | O que significa |
| ------ | --------------- | --------------- |
| `SUPPORTED` | Todas as notas aceitas são maiores que 0,5 | As checagens encontradas apoiam a afirmação. |
| `REFUTED` | Todas as notas aceitas são menores que 0,5 | As checagens encontradas contradizem a afirmação. |
| `MIXED` | Há notas dos dois lados, ou exatamente 0,5 | As checagens divergem entre si. |
| `MATCHED_UNSCORED` | Há checagem correspondente, mas sem nota utilizável | Existe checagem, mas ela não pôde ser convertida em nota. |
| `UNAVAILABLE` | Nenhuma checagem encontrada, ou chave da API ausente | Não há base para concluir. |

---

## 5. Análise do tipo de escrita: BERTimbau

### 5.1 Funcionamento

A segunda análise observa **como o texto é escrito**. Ela usa o modelo `vzani/portuguese-fake-news-classifier-bertimbau-combined`, disponível no Hugging Face.

O **BERTimbau** é uma versão do BERT treinada para o português brasileiro. Ele entende uma palavra pelo contexto em que ela aparece. Esse modelo passou por um ajuste fino (*fine-tuning*) para classificar notícias em duas classes:

| Classe | Rótulo do modelo |
| ------ | ---------------- |
| Fake | `LABEL_0` |
| True | `LABEL_1` |

```text
Texto da notícia
      │
      ▼
Divisão em trechos de até 512 tokens
      │
      ▼
Tokenizer → BERTimbau → classificador binário
      │
      ▼
Probabilidade de True em cada trecho
      │
      ▼
Média ponderada pelo tamanho dos trechos
      │
      ▼
Nota W, de 0 a 1
```

O modelo lê no máximo 512 tokens por vez. Por isso o texto é dividido em trechos, e o resultado de cada trecho entra na média, ponderado pelo número de caracteres.

### 5.2 Cálculo da Nota

| Item | Regra |
| ---- | ----- |
| Nota **W** | Média ponderada por caracteres da pontuação de cada trecho, de 0 a 1 |
| Classe do texto | `True` se a média for 0,5 ou mais. Caso contrário, `Fake` |
| Sinal na tela | Se a classe for `Fake`, aparece o aviso "Sinal de escrita suspeito" |
| Execução | Em CPU. A primeira chamada baixa os pesos do modelo |

### O que esta análise não faz

- **Não confere fatos.** O modelo reconhece padrões de linguagem. Ele não consulta jornais nem órgãos oficiais.
- **O score do modelo não é a chance de a notícia ser falsa.** É a confiança do modelo na própria classificação.
- **O desempenho de 99,2% de acurácia** foi medido pelo autor em 2.157 amostras de teste (bases Fake.br e FakeTrue.Br). Em outros tipos de texto, como posts de rede social ou manchetes curtas, o desempenho pode ser diferente.

Por isso, na tela, o resultado desta análise aparece como um sinal de apoio e nunca como veredito.

---

## 6. Análise da Credibilidade da Fonte

### 6.1 Funcionamento

A terceira análise avalia o **site que publicou a notícia**, e não o conteúdo. Ela olha cinco sinais:

| Sinal | O que verifica |
| ----- | -------------- |
| Veículo reconhecido | O domínio consta no Atlas da Notícia ou em uma lista local de veículos |
| Transparência editorial | Se a página informa dados editoriais, como autoria e expediente |
| Idade do domínio | Há quanto tempo o domínio foi registrado (consulta RDAP) |
| Domínio institucional | Se o domínio termina em um sufixo institucional |
| HTTPS | Se a página usa conexão segura |

> **A preencher:** pontos máximos de cada sinal e o limite de corte do veto. Esses valores ficam na política de credibilidade do back-end (`credibility_policy.py`).

### 6.2 Cálculo da Nota

```text
Nota da fonte = pontos obtidos ÷ pontos possíveis × 100
```

Só entram no cálculo os sinais que puderam ser consultados.

| Situação | Efeito |
| -------- | ------ |
| Domínio em lista de bloqueio | Nota da fonte vai a 0 |
| Nota da fonte abaixo do limite de corte | **Veto aplicado:** a nota final fica limitada a 35 |
| Sinais indisponíveis | O critério se abstém e **não aplica veto** |

Esta análise **não soma pontos** à nota final. Ela só pode **limitar** a nota. A nota original é guardada junto com a nota limitada.


---

## 5. Nota final

As análises dos fatos (F) e do tipo de escrita (W) formam o índice:

```text
Nota = (0,6 × F + 0,4 × W) × 100
```

| Critério | Peso previsto |
| -------- | ------------: |
| Análise dos fatos (F) | 60% |
| Tipo de escrita (W) | 40% |
| Credibilidade da fonte | não soma, só limita |

Quando um critério está indisponível, o outro assume o peso inteiro. A **cobertura** mostra isso:

| Critérios disponíveis | Cobertura |
| --------------------- | --------: |
| Fatos e escrita | 100% |
| Só fatos | 60% |
| Só escrita | 40% |
| Nenhum | 0% |

Se a fonte tiver o veto, a nota final passa a ser `mínimo(35, nota)`.

---

## 6. Explicação: SML

Depois da nota, um **modelo de linguagem pequeno** (`flan-t5-small`) escreve uma explicação curta em português.

- O modelo recebe apenas um **resumo estruturado** do que foi encontrado: nota, cobertura, quantidade de checagens, sinais da fonte e limitações.
- A resposta passa por uma **validação**. Números e nomes que não estavam no resumo fazem a resposta ser rejeitada, para evitar que o modelo invente dados.
- O SML vem **desligado por padrão** (`NEWS_ANALYSIS_SML_ENABLED`). Quando ele está desligado ou falha, o front mostra um texto fixo no lugar.

---

## 7. Resultado mostrado ao usuário

O veredito da tela vem **somente** do estado da análise dos fatos. As outras análises aparecem como frases de apoio e não mudam a cor.

| Estado da análise dos fatos | Resultado na tela | Cor |
| --------------------------- | ----------------- | --- |
| `SUPPORTED` | Informação confirmada | Verde |
| `REFUTED` ou `MIXED` | Falta contexto | Laranja |
| `UNAVAILABLE`, `MATCHED_UNSCORED` ou ausente | Sem provas suficientes | Cinza |

A tela de resultado mostra, nesta ordem:

1. o veredito em uma faixa grande;
2. o que foi encontrado;
3. por que se chegou a esse resultado;
4. as fontes para conferir (as checagens que entraram na nota);
5. o próximo passo recomendado;
6. a notícia que foi enviada.

---

## 8. Limitações

- A análise cobre **uma afirmação** da notícia, não todos os fatos dela.
- A comparação entre afirmações é **lexical**. Paráfrases fortes podem ser tratadas como relacionadas e ficar fora da nota.
- Sem a chave da Google Fact Check API, a análise dos fatos fica indisponível e a maioria dos resultados será "Sem provas suficientes".
- O controle de limite de pedidos (10 por minuto) funciona na memória de um único processo.
- O classificador de escrita roda em CPU e processa um texto por vez.
- A API do Google Fact Check está na versão `v1alpha1`, que pode mudar.
- O sistema **não substitui** a leitura das fontes. O resultado pode conter erros.

---

## Referências

- Modelo de classificação: [vzani/portuguese-fake-news-classifier-bertimbau-combined](https://huggingface.co/vzani/portuguese-fake-news-classifier-bertimbau-combined)
- Modelo-base: [neuralmind/bert-base-portuguese-cased](https://huggingface.co/neuralmind/bert-base-portuguese-cased) (BERTimbau)
- Google Fact Check Tools API: [guia](https://developers.google.com/fact-check/tools/api) e [referência REST](https://developers.google.com/fact-check/tools/api/reference/rest)
- Marcação ClaimReview: [schema.org/ClaimReview](https://schema.org/ClaimReview) e [guia do Google Search](https://developers.google.com/search/docs/data-types/factcheck)

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
      <td>Criação inicial da documentação</td>
      <td><a href="https://github.com/bolzanMGB">Othavio Bolzan</a></td>
      <td></td>
      <td>06/10/2026</td>
    </tr>
    <tr>
      <td>1.1</td>
      <td>Refinamento das métricas de negócio e modelo</td>
      <td><a href="https://github.com/bolzanMGB">Othavio Bolzan</a></td>
      <td></td>
      <td>06/10/2026</td>
    </tr>
  </tbody>
</table>