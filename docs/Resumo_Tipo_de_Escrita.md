# Portuguese Fake News Classifier — BERTimbau Combined

## 1. O que é o modelo?

O modelo **`vzani/portuguese-fake-news-classifier-bertimbau-combined`**, disponibilizado no Hugging Face, é um modelo de **classificação binária de textos em português**, desenvolvido para classificar notícias nas categorias:

* **Fake** — notícia considerada falsa pelo classificador;
* **True** — notícia considerada verdadeira pelo classificador.

O modelo é baseado no **BERTimbau**, uma versão do BERT treinada especificamente para o português brasileiro, e passou por um processo de **fine-tuning** para a tarefa de classificação de notícias.

O modelo-base utilizado é:

```text
neuralmind/bert-base-portuguese-cased
```

Portanto, é importante destacar que o BERTimbau originalmente **não é um detector de fake news**. Ele é um modelo de linguagem para português. O modelo `portuguese-fake-news-classifier-bertimbau-combined` é o resultado da adaptação desse modelo para a tarefa específica de classificação de fake news.

---

# 2. Funcionamento geral

O funcionamento pode ser representado da seguinte forma:

```text
                    TEXTO DA NOTÍCIA
                           │
                           ▼
                    ┌─────────────┐
                    │  Tokenizer  │
                    └──────┬──────┘
                           │
                           ▼
                  Tokens / IDs / Máscara
                           │
                           ▼
                    ┌─────────────┐
                    │  BERTimbau  │
                    │     Base    │
                    └──────┬──────┘
                           │
                           ▼
                 Representação do texto
                           │
                           ▼
                  ┌─────────────────┐
                  │  Classificador  │
                  │     binário     │
                  └────────┬────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                  Fake          True
```

O texto é inicialmente convertido em tokens pelo tokenizer. Esses tokens são processados pelo BERTimbau, que produz uma representação contextualizada do texto. Em seguida, uma camada de classificação utiliza essa representação para determinar a classe da notícia.

---

# 3. O que é o BERTimbau?

O BERTimbau é uma versão do modelo **BERT** adaptada para o português brasileiro.

BERT significa:

> **Bidirectional Encoder Representations from Transformers**

Uma das principais características do BERT é sua capacidade de analisar uma palavra considerando o contexto em que ela aparece.

Por exemplo:

```text
O banco aprovou o empréstimo.
```

e:

```text
Sentei no banco da praça.
```

A palavra `banco` possui significados diferentes nos dois casos.

O BERT consegue utilizar as palavras que aparecem ao redor para construir uma representação contextualizada da palavra.

Isso é especialmente importante para notícias, pois o significado das palavras depende do contexto em que elas são utilizadas.

---

# 4. Por que utilizar BERTimbau para português?

O BERTimbau foi desenvolvido para trabalhar com características da língua portuguesa, incluindo:

* flexões verbais;
* gênero;
* número;
* acentuação;
* concordância;
* estruturas sintáticas;
* vocabulário do português brasileiro;
* palavras compostas;
* expressões características do português.

Por exemplo:

```text
O governo anunciou novas medidas econômicas.
```

O modelo não analisa apenas cada palavra individualmente. Ele utiliza o contexto da frase para construir uma representação numérica do texto.

---

# 5. O significado de `combined`

O termo `combined` é importante porque indica que essa versão do modelo foi treinada utilizando uma combinação de diferentes conjuntos de dados.

A estrutura utilizada pode ser representada como:

```text
Fake.br
   +
FakeTrue.Br
   │
   ▼
Corpus combinado
   │
   ▼
Fine-tuning do BERTimbau
   │
   ▼
Modelo final
```

O model card do modelo identifica o dataset `vzani/corpus-combined` como conjunto utilizado no treinamento.

---

# 6. Qual é a tarefa do modelo?

A tarefa realizada pelo modelo é uma **classificação binária de textos**.

Isso significa que existem duas classes possíveis:

```text
LABEL_0 → Fake
LABEL_1 → True
```

Portanto:

| Label     | Classe |
| --------- | ------ |
| `LABEL_0` | Fake   |
| `LABEL_1` | True   |

Essa associação é específica desse modelo e não deve ser generalizada para todos os modelos disponíveis no Hugging Face.

---

# 7. Tokenização

Antes que o texto seja processado pelo BERTimbau, ele precisa ser convertido em tokens.

Por exemplo:

```text
O governo anunciou uma nova medida econômica.
```

Pode ser dividido conceitualmente em:

```text
O
governo
anunciou
uma
nova
medida
econômica
.
```

Esses tokens são então convertidos em identificadores numéricos.

De maneira simplificada:

```text
"O"          → ID numérico
"governo"    → ID numérico
"anunciou"   → ID numérico
"uma"        → ID numérico
...
```

Os números reais dependem do vocabulário utilizado pelo tokenizer do BERTimbau.

Além dos tokens, o tokenizer produz informações como:

```text
input_ids
attention_mask
```

---

# 8. Limite de 512 tokens

O modelo utiliza uma sequência máxima de aproximadamente:

```text
512 tokens
```

Isso significa que uma notícia com 100 ou 300 tokens pode ser processada normalmente.

Porém, uma notícia muito longa, por exemplo:

```text
2.000 tokens
```

não pode ser inserida integralmente em uma única sequência de 512 tokens.

Se for utilizado:

```python
truncation=True
```

parte do texto poderá ser descartada.

Isso pode ser problemático porque uma informação importante pode estar no final da notícia.

Para textos longos, uma alternativa seria dividir a notícia em partes e realizar a classificação separadamente, agregando os resultados posteriormente.

---

# 9. O que acontece dentro do BERT?

Depois da tokenização:

```text
Texto
  ↓
Tokenizer
  ↓
Tokens
  ↓
BERTimbau
```

O BERT transforma os tokens em representações vetoriais.

Conceitualmente:

```text
"O governo anunciou novas medidas"
                │
                ▼
      Representação vetorial
                │
                ▼
      Informação contextual
```

O Transformer utiliza o mecanismo de **self-attention**, que permite ao modelo relacionar diferentes partes do texto.

Por exemplo:

```text
O presidente anunciou a medida porque ela...
```

O modelo pode relacionar o pronome `ela` com elementos anteriores da frase.

---

# 10. Camada de classificação

Depois do processamento pelo BERTimbau, existe uma camada responsável pela classificação.

O processo pode ser representado como:

```text
BERTimbau
    │
    ▼
Representação contextual
    │
    ▼
Camada de classificação
    │
    ▼
┌───────────────┐
│     Fake      │
│     True      │
└───────────────┘
```

O modelo produz valores chamados **logits**.

Por exemplo, conceitualmente:

```text
Fake =  4.8
True = -2.3
```

Esses valores são posteriormente convertidos em probabilidades.

Por exemplo:

```text
Fake = 99,99%
True =  0,01%
```

A classe com maior probabilidade é selecionada como resultado.

---

# 11. Instalação

Para utilizar o modelo em Python, é necessário instalar o PyTorch e o Transformers.

```bash
pip install transformers torch
```

Também pode ser utilizado:

```bash
pip install transformers torch sentencepiece
```

Para verificar a instalação do Transformers:

```bash
python -c "import transformers; print(transformers.__version__)"
```

---

# 12. Utilização com `pipeline`

A maneira mais simples de utilizar o modelo é através da função `pipeline` da biblioteca Transformers.

```python
from transformers import pipeline

classifier = pipeline(
    "text-classification",
    model="vzani/portuguese-fake-news-classifier-bertimbau-combined"
)

texto = """
O governo anunciou nesta segunda-feira uma nova medida econômica.
"""

resultado = classifier(texto)

print(resultado)
```

Na primeira execução, os arquivos do modelo serão baixados do Hugging Face.

Posteriormente, eles normalmente ficam armazenados no cache local.

---

# 13. Interpretando a saída

Uma saída possível seria:

```python
[
    {
        'label': 'LABEL_1',
        'score': 0.97
    }
]
```

Nesse caso:

```text
LABEL_1
   ↓
True
```

e:

```text
0.97
   ↓
97%
```

Portanto, o resultado poderia ser interpretado como:

```text
Classificação: True
Score: 97%
```

---

# 14. Convertendo `LABEL_0` e `LABEL_1`

Para tornar a saída mais compreensível, podemos fazer a conversão manualmente:

```python
from transformers import pipeline

classifier = pipeline(
    "text-classification",
    model="vzani/portuguese-fake-news-classifier-bertimbau-combined"
)

texto = """
O governo anunciou nesta segunda-feira uma nova medida econômica.
"""

resultado = classifier(texto)[0]

if resultado["label"] == "LABEL_1":
    classe = "True"
else:
    classe = "Fake"

print("Classe:", classe)
print("Score:", resultado["score"])
```

A lógica é:

```text
LABEL_0 → Fake
LABEL_1 → True
```

---

# 15. Exemplo completo

Uma implementação mais organizada poderia ser:

```python
from transformers import pipeline

MODEL_NAME = "vzani/portuguese-fake-news-classifier-bertimbau-combined"

classifier = pipeline(
    "text-classification",
    model=MODEL_NAME
)


def classificar_noticia(texto):
    resultado = classifier(texto)[0]

    if resultado["label"] == "LABEL_1":
        classe = "True"
    else:
        classe = "Fake"

    confianca = resultado["score"]

    return {
        "classe": classe,
        "confianca": confianca
    }


texto = """
BOMBA! Uma nova medida foi anunciada pelo governo nesta manhã.
"""

resultado = classificar_noticia(texto)

print(resultado)
```

Uma saída possível:

```text
{
    'classe': 'Fake',
    'confianca': 0.91
}
```

---

# 16. O que significa o `score`?

O campo `score` representa a confiança/probabilidade atribuída pelo modelo à classe escolhida.

Por exemplo:

```python
{
    "label": "LABEL_0",
    "score": 0.93
}
```

significa que o modelo atribuiu aproximadamente:

```text
93%
```

à classe `LABEL_0`.

Porém, isso **não significa necessariamente que existe 93% de probabilidade de a notícia ser realmente falsa**.

Essa distinção é fundamental.

O score representa a confiança do **modelo em sua classificação**, e não uma comprovação independente da veracidade da notícia.

Por exemplo:

```text
Modelo:
Fake → 99%

Realidade:
A notícia pode ser verdadeira.
```

O modelo não consulta automaticamente jornais, órgãos governamentais ou serviços de fact-checking para confirmar o conteúdo.

---

# 17. O modelo realmente detecta fake news?

É importante diferenciar:

> **Classificação de texto**

de:

> **Verificação factual.**

O modelo realiza classificação de texto.

Por exemplo:

```text
"NASA descobriu água em Marte ontem."
```

O modelo pode analisar o texto e produzir:

```text
Fake → 97%
```

Mas ele não necessariamente sabe se a NASA realmente anunciou isso.

Um sistema de verificação factual precisaria consultar fontes externas.

Portanto, uma descrição tecnicamente mais correta seria:

> O modelo é um classificador de textos baseado em BERTimbau, ajustado para classificar notícias em português nas categorias Fake e True.

Não é adequado descrevê-lo simplesmente como:

> "Uma IA que verifica se uma notícia é verdadeira."

Essa segunda descrição sugere uma capacidade de verificação factual que o modelo não possui.

---

# 18. Como o modelo foi treinado?

Segundo as informações disponibilizadas no model card, o modelo foi treinado com os seguintes parâmetros:

| Característica   | Valor                                   |
| ---------------- | --------------------------------------- |
| Modelo-base      | `neuralmind/bert-base-portuguese-cased` |
| Dataset          | Fake.br + FakeTrue.Br                   |
| Batch size       | 16                                      |
| Épocas           | 7                                       |
| Learning rate    | aproximadamente `3,126 × 10⁻⁵`          |
| Otimizador       | AdamW                                   |
| Função de perda  | Cross-Entropy                           |
| Sequência máxima | 512 tokens                              |

Além disso, oito camadas do BERT foram congeladas durante o treinamento, enquanto as quatro camadas superiores foram ajustadas para a tarefa de classificação.

---

# 19. O que significa congelar camadas?

Um modelo BERT possui diversas camadas Transformer.

Podemos representar simplificadamente:

```text
BERT
├── Camada 1
├── Camada 2
├── Camada 3
├── ...
├── Camada 12
└── Classificador
```

Nesse treinamento:

```text
Camada 1  → congelada
Camada 2  → congelada
Camada 3  → congelada
...
Camada 8  → congelada

Camada 9  → treinada
Camada 10 → treinada
Camada 11 → treinada
Camada 12 → treinada
```

As primeiras camadas preservam boa parte das representações linguísticas aprendidas durante o pré-treinamento.

As camadas superiores são adaptadas à tarefa de classificação de fake news.

Essa estratégia reduz a quantidade de parâmetros que precisam ser ajustados durante o fine-tuning.

---

# 20. Desempenho informado pelo autor

No conjunto de teste combinado, o autor informa aproximadamente:

| Métrica            | Resultado |
| ------------------ | --------: |
| Accuracy           |     0,992 |
| Precision macro    |     0,992 |
| Recall macro       |     0,992 |
| F1 macro           |     0,992 |
| Precision weighted |     0,992 |
| Recall weighted    |     0,992 |
| F1 weighted        |     0,992 |
| Amostras de teste  |     2.157 |

Assim, a **accuracy reportada é de aproximadamente 99,2%**.

É importante observar que esses valores correspondem ao conjunto de teste utilizado no trabalho do autor.

Eles não significam que o modelo necessariamente apresentará 99,2% de acerto em qualquer conjunto de notícias encontrado na Internet.

---

# 21. Por que o desempenho pode mudar?

Imagine que o modelo tenha sido treinado e avaliado principalmente com:

```text
Fake.br
+
FakeTrue.Br
```

Mas posteriormente seja utilizado em:

```text
Posts do X/Twitter
```

ou:

```text
TikTok
```

ou:

```text
WhatsApp
```

ou:

```text
Notícias de 2026
```

ou:

```text
Manchetes extremamente curtas
```

A distribuição dos dados pode ser diferente.

Isso é conhecido como **distribution shift** ou mudança na distribuição dos dados.

Podemos representar:

```text
Dados de treinamento
        │
        ▼
Notícias estruturadas
        │
        ▼
      Modelo
        │
        ▼
Desempenho conhecido


Dados reais
        │
        ▼
Posts + memes + abreviações
        │
        ▼
Possível mudança de desempenho
```

Por esse motivo, a accuracy de 99,2% deve ser interpretada dentro do contexto do conjunto de dados utilizado na avaliação.

---

# 22. Limitação importante

Considere uma mensagem como:

```text
URGENTE!!! COMPARTILHE!!!
PRESIDENTE VAI PROIBIR PIX!!!
```

O modelo pode reconhecer padrões linguísticos semelhantes aos presentes em exemplos classificados como fake.

Porém, isso não significa que ele sabe se:

```text
O presidente realmente anunciou isso?
```

A resposta exigiria uma verificação factual.

O modelo não consulta automaticamente:

* jornais;
* agências de notícias;
* sites governamentais;
* bases de dados;
* serviços de fact-checking.

Ele realiza uma classificação baseada nos padrões aprendidos durante o treinamento.

---

# 23. Utilizando o modelo com várias notícias

Também é possível fornecer uma lista de textos:

```python
noticias = [
    "O governo anunciou novas medidas econômicas.",
    "URGENTE!!! COMPARTILHE ESTA MENSAGEM!!!",
    "A universidade publicou o calendário acadêmico."
]

resultados = classifier(noticias)

for noticia, resultado in zip(noticias, resultados):
    print(noticia)
    print(resultado)
    print()
```

Dessa maneira, o modelo pode processar várias notícias em sequência.

---

# 24. Utilização com GPU

Caso exista uma GPU compatível com PyTorch, pode-se utilizar:

```python
classifier = pipeline(
    "text-classification",
    model="vzani/portuguese-fake-news-classifier-bertimbau-combined",
    device=0
)
```

Nesse caso:

```text
device=0
```

representa a primeira GPU disponível.

Para CPU, pode ser utilizado:

```python
device=-1
```

Em muitos casos, a configuração padrão já utiliza a CPU automaticamente quando nenhuma GPU é especificada.

---

# 25. Utilizando o modelo diretamente

Outra possibilidade é carregar diretamente o tokenizer e o modelo:

```python
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification
)

tokenizer = AutoTokenizer.from_pretrained(
    "vzani/portuguese-fake-news-classifier-bertimbau-combined"
)

model = AutoModelForSequenceClassification.from_pretrained(
    "vzani/portuguese-fake-news-classifier-bertimbau-combined"
)
```

Essa abordagem oferece maior controle sobre o processo de inferência.

---

# 26. `pipeline` versus utilização direta

A `pipeline` é mais adequada para:

* testes rápidos;
* protótipos;
* aplicações simples;
* demonstrações.

Por exemplo:

```text
Texto
 ↓
pipeline
 ↓
Resultado
```

Já o carregamento direto do tokenizer e do modelo é mais adequado quando é necessário controlar detalhes da inferência:

```text
Texto
 ↓
Tokenizer
 ↓
input_ids
 ↓
attention_mask
 ↓
BERTimbau
 ↓
Logits
 ↓
Softmax
 ↓
Classificação
```

Isso pode ser particularmente útil no desenvolvimento de uma API ou aplicação maior.

---

# 27. Utilização em uma aplicação web

Uma possível arquitetura seria:

```text
                    ┌─────────────────┐
                    │     Usuário     │
                    └────────┬────────┘
                             │
                       Envia notícia
                             │
                             ▼
                    ┌─────────────────┐
                    │    Front-end    │
                    └────────┬────────┘
                             │
                         HTTP/JSON
                             │
                             ▼
                    ┌─────────────────┐
                    │       API       │
                    │     FastAPI     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    BERTimbau    │
                    │  Fake News      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Classificação │
                    │ Fake / True     │
                    │ Confiança       │
                    └─────────────────┘
```

A API poderia receber:

```json
{
    "texto": "Uma notícia qualquer..."
}
```

e retornar:

```json
{
    "classe": "Fake",
    "confianca": 0.97
}
```

---

# 28. Arquitetura mais robusta

Para construir um sistema real de verificação de notícias, não seria recomendável depender exclusivamente desse classificador.

Uma arquitetura mais completa poderia ser:

```text
                    NOTÍCIA
                       │
                       ▼
                ┌──────────────┐
                │ Pré-process. │
                └──────┬───────┘
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
        ┌───────────┐     ┌───────────────┐
        │ BERTimbau │     │ Busca de fontes│
        └─────┬─────┘     └───────┬───────┘
              │                   │
              │                   ▼
              │             Fontes confiáveis
              │                   │
              └─────────┬─────────┘
                        ▼
                 Análise conjunta
                        │
                        ▼
                  Resultado final
```

Nesse cenário, o BERTimbau seria responsável pela **classificação textual**, enquanto outro componente realizaria a **verificação factual por meio de fontes externas**.

---

# 29. Aplicação em um projeto acadêmico

Para um projeto acadêmico de detecção de fake news, uma arquitetura interessante seria:

```text
                  ┌─────────────────┐
                  │ Texto da notícia│
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │    Tokenizer    │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │    BERTimbau    │
                  └────────┬────────┘
                           │
                           ▼
                  ┌───────────────────┐
                  │    Classificador  │
                  └─────────┬─────────┘
                            │
                    ┌───────┴───────┐
                    ▼               ▼
                  Fake             True
                    │               │
                    └───────┬───────┘
                            ▼
                       Confiança
```

O resultado apresentado ao usuário poderia ser algo como:

```text
Classificação: POSSÍVEL FAKE NEWS

Confiança do modelo: 96,4%

Observação:
A classificação é baseada em padrões linguísticos
aprendidos pelo modelo e não constitui uma verificação
factual independente.
```

Essa observação é importante para evitar que o usuário interprete a saída do classificador como uma prova definitiva da veracidade ou falsidade da notícia.

---

# 30. Resumo das características

| Característica                  | Informação                                                 |
| ------------------------------- | ---------------------------------------------------------- |
| **Modelo**                      | `vzani/portuguese-fake-news-classifier-bertimbau-combined` |
| **Arquitetura**                 | BERTimbau Base Cased                                       |
| **Modelo-base**                 | `neuralmind/bert-base-portuguese-cased`                    |
| **Idioma**                      | Português brasileiro                                       |
| **Tarefa**                      | Classificação de texto                                     |
| **Classes**                     | Fake / True                                                |
| **LABEL_0**                     | Fake                                                       |
| **LABEL_1**                     | True                                                       |
| **Dataset**                     | Fake.br + FakeTrue.Br                                      |
| **Fine-tuning**                 | 7 épocas                                                   |
| **Batch size**                  | 16                                                         |
| **Learning rate**               | ≈ `3,126 × 10⁻⁵`                                           |
| **Otimizador**                  | AdamW                                                      |
| **Loss**                        | Cross-Entropy                                              |
| **Sequência máxima**            | 512 tokens                                                 |
| **Accuracy informada**          | 99,2%                                                      |
| **Número de amostras de teste** | 2.157                                                      |
| **Framework**                   | Hugging Face Transformers                                  |
| **Licença**                     | Apache 2.0                                                 |

---

# 31. Conclusão

O **`vzani/portuguese-fake-news-classifier-bertimbau-combined`** é um modelo baseado no **BERTimbau**, desenvolvido para classificação binária de textos em português entre as categorias **Fake** e **True**.

O modelo utiliza um BERT previamente treinado para português brasileiro e realiza um processo de **fine-tuning** utilizando dados provenientes dos conjuntos **Fake.br** e **FakeTrue.Br**.

Seu funcionamento pode ser resumido em:

```text
Texto
  ↓
Tokenização
  ↓
BERTimbau
  ↓
Representação contextual
  ↓
Camada de classificação
  ↓
Fake / True
  ↓
Score
```

O modelo apresentou aproximadamente **99,2% de accuracy** no conjunto de teste informado pelo autor. Entretanto, esse resultado deve ser interpretado considerando o conjunto de dados utilizado e não como uma garantia de 99,2% de acerto para qualquer notícia encontrada na Internet.

A principal limitação conceitual é que o modelo realiza **classificação baseada em padrões linguísticos**, e não uma verificação factual independente. Dessa forma, uma classificação `Fake` não constitui, por si só, uma prova de que o conteúdo é falso, assim como uma classificação `True` não comprova que o conteúdo é verdadeiro.

Para um sistema de produção mais robusto, o modelo pode ser utilizado como uma das etapas de uma arquitetura maior, combinando **classificação por BERTimbau, recuperação de informações e consulta a fontes confiáveis para verificação factual**.

---

## Referência

Modelo no Hugging Face:

**`vzani/portuguese-fake-news-classifier-bertimbau-combined`**

https://huggingface.co/vzani/portuguese-fake-news-classifier-bertimbau-combined
