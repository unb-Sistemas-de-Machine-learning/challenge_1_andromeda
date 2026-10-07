# Estilo de escrita com BERTimbau

O critério **Estilo de escrita** classifica o texto extraído da notícia usando
exclusivamente o modelo
[`vzani/portuguese-fake-news-classifier-bertimbau-combined`](https://huggingface.co/vzani/portuguese-fake-news-classifier-bertimbau-combined).
A classificação é um sinal textual para o índice operacional; não comprova a
veracidade dos acontecimentos relatados.

## Modelo e execução

O classificador é baseado no BERTimbau Base Cased
(`neuralmind/bert-base-portuguese-cased`) e foi ajustado para classificação
binária de notícias em português com dados de Fake.br e FakeTrue.Br.

| Índice | Rótulo original | Rótulo na aplicação |
| --- | --- | --- |
| 0 | `LABEL_0` | `Fake` |
| 1 | `LABEL_1` | `True` |

A revisão dos pesos é `86971e56e7f5ad781cf56673df73a57375455793`.
O aplicativo carrega por padrão o modelo ONNX de 8 bits incluído no pacote.
O carregamento é feito na primeira análise que chega ao critério e reutilizado
em memória por processo. Um bloqueio serializa a inferência.

O artefato é gerado pelo script `scripts/optimize_writing_model.py` a partir
da revisão acima; o usuário não precisa executá-lo nem baixar pesos.
O tokenizer, as janelas de 512 tokens e a média por caracteres são mantidos.
O manifesto verifica a revisão original e a integridade do arquivo; a versão
da análise distingue o artefato otimizado. Os pesos quantizados ocupam cerca de
110 MB, contra 436 MB do arquivo original. A quantização altera algumas
probabilidades; a versão incluída foi testada com textos curtos e longos no
computador. Ainda falta medir desempenho em celulares reais.

Não há lista de palavras suspeitas, notas fixas ou classificação alternativa
por regras. Termos como “falso” e “boato” fazem parte do contexto recebido pelo
modelo, sem determinar diretamente sua saída.

## Fluxo

```text
Texto principal extraído
        ↓
Normalização dos espaços em branco
        ↓
Tokenizer: tokens, máscaras e posições no texto
        ↓
Janelas sem sobreposição de até 512 tokens
        ↓
BERTimbau → logits → softmax por janela
        ↓
Probabilidade da classe True por segmento
        ↓
Média ponderada pelos caracteres dos segmentos
        ↓
Score, previsão agregada, confiança e detalhes por segmento
```

## Segmentos e cobertura do texto

Tokens são unidades do tokenizer: palavras, partes de palavras e pontuação.
Não são frases, parágrafos nem caracteres. Cada entrada do modelo contém até
**512 tokens, incluindo tokens especiais**. As janelas de excedente usam
`stride=0`, sem sobreposição. Todas as janelas são processadas; o restante do
texto não é descartado depois do primeiro bloco. O último bloco pode ser menor.

`segments_analyzed = 2` significa duas entradas do modelo. Para conhecer o
tamanho e a previsão de cada uma, consulte `criteria.writing_style.segments`
na resposta da API. A análise cobre o texto principal obtido pelo extrator,
que pode excluir menus, comentários ou outros elementos visíveis na página.
A extração precisa fornecer pelo menos 1.000 caracteres para a análise por
URL prosseguir.

## Notas e confiança

Os logits do modelo são convertidos por softmax em saídas para as duas classes:

```text
writing_score do segmento = P_modelo(True)
```

O segmento recebe `True` se essa saída for pelo menos 0,5, ou `Fake` caso
contrário. Sua confiança é a saída da classe escolhida: `P_modelo(True)` ou
`P_modelo(Fake)`. Uma previsão `Fake` com confiança 0,90 tem writing score
próximo de 0,10; confiança e nota orientada a `True` são campos distintos.

A nota agregada do critério é:

```text
W = soma(caracteres_i × writing_score_i) / soma(caracteres_i)
```

Os pesos vêm dos intervalos de caracteres no texto com espaços normalizados,
obtidos pelas posições dos tokens. `token_count` inclui tokens especiais e
não é o peso da média. Segmentos maiores influenciam mais o resultado.
Por exemplo, pesos de 2.000 e 500 caracteres com notas 0,90 e 0,60 produzem
`W = (2.000 × 0,90 + 500 × 0,60) / 2.500 = 0,84`.

A classe agregada é `True` para média não arredondada de pelo menos 0,5;
caso contrário, é `Fake`. A confiança agregada é `W` para `True` e `1 − W`
para `Fake`. Esse valor resume os segmentos, não é uma inferência adicional
da notícia inteira. Para classe agregada `Fake`, o resultado inclui
“Sinal de escrita suspeito”. Nota e previsão agregadas são arredondadas a
quatro casas decimais; as probabilidades por segmento são preservadas.

## Saída e interface

| Campo | Significado |
| --- | --- |
| `available` | Se a inferência terminou com sucesso. |
| `status` | `EXECUTED` em caso de sucesso; `ERROR` se o modelo falhar. |
| `score` | Média ponderada orientada à classe `True`, de 0 a 1. |
| `model` / `model_version` | Identificador e revisão fixa do modelo. |
| `prediction` | Rótulo, confiança e writing score agregados. |
| `segments_analyzed` | Número de janelas classificadas. |
| `segments` | Índice a partir de zero, caracteres, tokens, rótulo, confiança e nota por janela. |
| `qualitative_state` | “Sinal de escrita suspeito” para classe agregada `Fake`. |
| `effective_weight` | Peso considerando os critérios disponíveis. |
| `contribution` | Parcela da nota final na escala de 0 a 100. |

A interface mostra nota, peso, contribuição, modelo, revisão, quantidade de
segmentos, classe e confiança agregadas. Os detalhes por segmento são
retornados pela API, exibidos na seção expansível “Resultados por segmento” e
conservados no registro de auditoria, sem o texto integral.
Uma nota interna `0.9945` pode aparecer como `0.99`, enquanto sua contribuição,
com peso de 100%, aparece como `99.5`. Cada campo tem precisão de exibição própria.

## Índice final e cobertura

Com os três critérios disponíveis, `Índice = (0,65 × F + 0,20 × C + 0,15 × W) × 100`.
`F` representa checagens da afirmação selecionada, `C` é a credibilidade da fonte
normalizada entre 0 e 1 e `W` representa escrita. Com apenas
escrita disponível, seu peso efetivo é 100% e o índice é `W × 100`, mas a
cobertura permanece **15%**. Cobertura mede a participação dos critérios
previstos, não a proporção de segmentos nem a certeza da classificação.
A busca Google Fact Check Tools é independente deste classificador.

Nesse caso, o resumo da interface informa que só o estilo de escrita contribuiu e
que o resultado não confirma os fatos. A fórmula e os pesos efetivos permitem
identificar exatamente como o índice foi composto.

## Instalação e teste

Na raiz do repositório:

```powershell
uv sync --extra dev
uv run python teste_bertimbau.py
```

Para informar o texto diretamente:

```powershell
uv run python teste_bertimbau.py --texto "A reportagem desmente um boato sobre a saúde."
```

O script usa o mesmo componente da aplicação, com revisão, segmentação e
agregação. Os pesos são baixados quando não estão no cache local.
Opcionalmente, escolha um diretório antes da execução:

```powershell
$env:NEWS_ANALYSIS_MODEL_CACHE = "C:\modelos\huggingface"
```

Para executar a aplicação:

```powershell
uv run uvicorn news_analysis.api.app:app --reload
```

Interface: `http://127.0.0.1:8000/`. Documentação da API:
`http://127.0.0.1:8000/docs`.

## Falhas e limitações

Se carregamento, tokenização ou inferência falharem, o critério retorna
`available=false`, `status=ERROR` e `WRITING_MODEL_ERROR`, sem nota ou previsão
utilizável. Campos nulos podem ser omitidos na serialização JSON. Não há
substituição por palavras-chave. O índice utiliza o outro critério quando
disponível; sem nenhum critério disponível, não há índice e a cobertura é 0%.

`Fake` e `True` expressam a previsão aprendida nos dados de treinamento.
O modelo não consulta fatos, fontes ou evidências externas. Confiança alta
pode ocorrer em previsões incorretas, e textos que desmentem boatos precisam
ser considerados na avaliação do classificador.

## Referências

- [Modelo e mapeamento de classes](https://huggingface.co/vzani/portuguese-fake-news-classifier-bertimbau-combined)
- [Tokenizer e janelas de excedente](https://huggingface.co/docs/transformers/main_classes/tokenizer)
- [Código de treinamento do autor](https://github.com/viniciuszani/portuguese-fake-new-classifiers)
