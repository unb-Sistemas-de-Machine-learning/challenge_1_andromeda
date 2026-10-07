# Métricas de Avaliação

O app **não confirma se os fatos são verdadeiros**. Ele avalia a reportagem por **três métricas independentes**, cada uma com um peso. Os scores são somados para indicar um nível de confiabilidade.

<p align="center">Tabela 1 - Métricas de avaliação</p>

| Número | Métrica | Método | Peso | Descrição |
|---|---|---|---|---|
| 01 | Checagens Pré-Existentes | Google Fact Check | 0,65 | Avalia se agências já verificaram uma afirmação equivalente ao título. |
| 02 | Credibilidade da Fonte | Atlas da Notícia | 0,20 | Mede se o veículo é conhecido e se o site é institucional. |
| 03 | Estilo de Escrita | BERTimbau | 0,15 | Reconhece nuances da escrita que fogem das boas práticas jornalísticas. |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

---

## 1. Checagens Pré-Existentes

### 1.1 Funcionamento

1. O app envia o **título** ao backend (`POST /fact-check`).
2. O backend repassa ao Google Fact Check e devolve o JSON.
3. As regras leem `claims[].text` (a afirmação checada) e `claims[].claimReview[]` (as revisões de agências).
4. Cada checagem passa por **filtros**:
    - A afirmação corresponde ao título? (`sameClaim`)
    - Diverge em número, local ou negação? → descarta
    - O veredito está na tabela conhecida? → se não, não pontua
    - É duplicada? → descarta
5. Só as aprovadas entram no cálculo.

### 1.2 Geração do Score

Cada checagem possui um veredito que é transformado em um valor. É retirada a média entre as checagens de um mesmo publicador e depois é feita uma média geral.

```text
factScore = média( média(checagens de cada publicador) )
```

<p align="center">Tabela 2 - Tabela de Vereditos </p>

| Veredito | `value` |
|---|---|
| verdadeiro | 1,0 |
| majoritariamente verdadeiro | 0,75 |
| meia verdade / impreciso | 0,5 |
| enganoso / fora de contexto | 0,25 |
| falso | 0,0 |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>


---

## 2. Credibilidade da Fonte

### 2.1 Funcionamento

1. O app carrega do APK a lista de domínios do **Atlas da Notícia** (`Set<String>`).
2. As regras comparam o domínio da reportagem com essa lista.
3. As regras verificam se o domínio é de **governo** ou **institucional oficial**.

### 2.2 Geração do Score

É uma **soma de pontos**, limitada a 100.

<p align="center">Tabela 3 - Composição do `sourceScore`</p>

| Sinal | Pontos |
|---|---|
| Domínio consta no Atlas da Notícia | +40 |
| Autor identificado no HTML | +12 |
| Data de publicação no HTML | +6 |
| Link interno para "sobre", "contato", "quem somos" etc. | +12 |
| HTTPS (validado no download) | +5 |
| Domínio institucional (`.gov.br`, `.edu.br`, `.jus.br`, `.leg.br`, `.mp.br`) | +100 (teto 100) |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

---

## 3. Estilo de Escrita

### 3.1 Funcionamento

Um sinal numérico sobre a escrita da reportagem é produzido pelo **BERTimbau** (BERT em português), exportado para ONNX e executado **no próprio aparelho**. O modelo não escreve texto: devolve só um número.

### 3.2 Geração do Score

```text
writingScore = exp(z1) / ( exp(z0) + exp(z1) )
```

1. **Texto:** pega-se o texto extraído, limitado a 20 mil caracteres.
2. **Tokenização:** o texto vira até 256 tokens, usando o vocabulário do APK.
3. **Entrada:** o modelo recebe três tensores, todos `[1, 256]`: `input_ids`, `attention_mask`, `token_type_ids`.
4. **Saída bruta:** o ONNX devolve dois valores (*logits*), `z0` e `z1`.
5. **Score:** converte-se em probabilidade da classe de índice 1:


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
