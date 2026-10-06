# Interface, API e fluxo do sistema

## Execução local

```powershell
uv sync --extra dev
uv run uvicorn news_analysis.api.app:app --reload
```

| Endereço | Finalidade |
| --- | --- |
| `http://127.0.0.1:8000/` | Interface de análise. |
| `http://127.0.0.1:8000/docs` | Documentação interativa da API. |
| `GET /config` | Indica se a chave Google Fact Check está configurada, sem expô-la. |
| `POST /analyses` | Analisa uma URL e retorna o resultado. |
| `GET /analyses/{analysis_id}` | Consulta o registro de auditoria por identificador. |

## Entradas

A interface recebe o link da notícia e uma afirmação opcional. O formulário
envia `user_id=web-user`. Clientes da API podem informar seu próprio `user_id`.
O limite é de dez análises por minuto por identificador; sem identificador,
a URL é usada como chave do contador em memória.

```json
{
  "url": "https://example.com/noticia",
  "user_id": "demo",
  "claim": "Afirmação verificável a consultar"
}
```

A URL deve ser HTTP/HTTPS. `claim` é opcional e aceita de 3 a 500 caracteres.
A análise exige pelo menos 1.000 caracteres extraídos da notícia. A afirmação
informada é usada na checagem factual, enquanto o BERTimbau recebe o texto
principal extraído. Sem afirmação, o título limpo e frases iniciais fornecem até
três candidatos. Somente o primeiro determina a nota; os outros aparecem como
evidências complementares. Com `claim`, somente a afirmação informada é consultada.

## Fluxo de análise

```text
URL + afirmação opcional
          |
Validação, download e extração
          |
          +-- Afirmação selecionada
          |       |
          |   Google Fact Check: checagens publicadas
          |       |
          |   Correspondência, rótulos completos e deduplicação
          |       |
          |   Média por agência -> média entre agências -> F
          |
          +-- Texto principal extraído
                  |
              Tokenizer -> janelas de até 512 tokens
                  |
              BERTimbau -> notas por segmento -> média ponderada -> W

F e W disponíveis -> pesos efetivos -> índice e cobertura
          |
          +-- Interface e resposta JSON
          +-- Auditoria SQLite e consulta por ID
```

## Resumo do resultado

O resumo exibe índice operacional, cobertura, status, fórmula, identificador da
análise, título, URL final, versão da pipeline e limitações. `SUCCESS` significa
que a análise concluiu o fluxo; não significa que a notícia foi comprovada.

| Critérios disponíveis | Média antes do veto | Cobertura |
| --- | --- | --- |
| Fatos e escrita | `(0,60 × F + 0,40 × W) × 100` | 100% |
| Apenas fatos | `F × 100` | 60% |
| Apenas escrita | `W × 100` | 40% |
| Nenhum | Sem índice | 0% |

A nota final é essa média, limitada a 35 quando houver veto comprovado da fonte.
`final.score_before_veto` preserva a média e `final.source_veto_applied` indica
a aplicação do teto. As contribuições somam a média anterior ao teto, não
necessariamente a nota final. Fonte totalmente indisponível não aplica veto;
blocklist comprovada continua aplicando. Sem média disponível, a nota permanece nula.
Cobertura final mede fatos e escrita; a cobertura dos sinais da fonte é separada.

Com apenas escrita disponível, a interface utiliza **“Somente estilo de escrita”**
e informa que a nota não confirma os fatos. Mesmo uma nota próxima de 100 nesse
caso usa a classificação textual como média, sujeita ao teto da fonte.

Cobertura não é confiança estatística, percentual de texto processado ou
percentual de fatos verificados. O peso efetivo de um único critério é 100%,
mas sua cobertura continua correspondendo ao peso previsto.

## Cartão de fatos verificáveis

O cartão permanece visível mesmo sem checagens utilizáveis. Ele apresenta:

- Disponibilidade, status, score, peso previsto, peso efetivo e contribuição.
- Afirmação avaliada e limites do escopo.
- Contagens de revisões recuperadas, correspondentes, usadas na nota e agências.
- Médias por agência e sinal de divergência quando disponíveis.
- Limite de paginação quando atingido.
- Afirmação checada, agência, veredito original, nota, data, link e motivo de exclusão por revisão.
- Motivo e código de indisponibilidade ou erro, além das consultas registradas.

O critério ausente na resposta produz um aviso de dados não recebidos, sem
desaparecer da interface ou inventar uma nota. Respostas com `source_credibility`
também são reconhecidas: `reviews_count` identifica o formato factual antigo;
`signals` identifica o critério histórico de metadados v4, exibido em cartão
separado com pesos e nota preservados. Dados ausentes aparecem como não informados.
Links de evidências são exibidos somente com HTTP/HTTPS, e
conteúdo recebido é escapado antes de sua inserção na página.

O cartão factual também distingue evidências favoráveis, contrárias, mistas ou
indisponíveis (`evidence_status`). São sínteses de checagens recuperadas, não
vereditos sobre a notícia inteira. Consultas parcialmente falhas mantêm os
resultados anteriores e exibem um aviso. A seção de afirmações complementares
expõe evidências e consultas separadas, sem contribuição à nota final.

## Cartão de estilo de escrita

O cartão apresenta score, pesos e contribuição, modelo, revisão, quantidade de
segmentos, classe e confiança agregadas. A seção expansível **“Resultados por
segmento”** informa caracteres, tokens incluindo tokens especiais, classe,
confiança e nota de cada janela. Segmentos são blocos do tokenizer, não frases.

Classe e confiança agregadas resumem as previsões dos segmentos. A confiança
do modelo não comprova veracidade. Consulte [Estilo de escrita](TipoDeEscrita.md).

## Credibilidade da fonte

`criteria.credibility` retorna o SCORE_FONTE. `criteria.credibility_evidence`
registra a origem e a versão da base de reconhecimento, política/hash, estado/hash
da blocklist e motivo do veto. Consulte [Atlas](Atlas.md) e a
[decisão de credibilidade](DecisaoCredibilidade.md).

## Saídas e precisão

`criteria.verifiable_facts` e `criteria.writing_style` contêm os resultados
atuais. `final` contém nota, cobertura, pesos e fórmula. `pipeline_version`
identifica regras, modelo e dependências. O texto integral extraído não é
retornado ou conservado em auditoria.

Scores de critérios aparecem com duas casas decimais; contribuições, com uma;
o número principal é arredondado para inteiro; pesos e confiança são apresentados
em percentuais inteiros. A resposta JSON conserva maior precisão. Uma nota
interna `0.9945` pode aparecer como score `0.99`, contribuição `99.5` com peso
de 100%, e índice principal `99`.

Registros históricos mantêm notas e versões originais. A adaptação de nomes de
campos para leitura não recalcula checagens já armazenadas.

## Diagnóstico

Chave configurada e checagens disponíveis são condições diferentes. Sem revisões
correspondentes e mapeáveis, o critério factual fica indisponível. Sem modelo
utilizável, o critério de escrita retorna `WRITING_MODEL_ERROR`.
Critérios indisponíveis são excluídos do cálculo, nunca substituídos por zero.

Erros de URL, bloqueio de destino, download ou extração interrompem a análise
antes dos critérios. Excesso de requisições gera `RATE_LIMITED` e HTTP 429.
A interface apresenta o código e a mensagem de erro retornados pela API.

## Referências do projeto

- [Google Fact Check Tools API](Manual_Google_Fact_Check_Tools_API.md)
- [Cálculo de fatos verificáveis](ChecagemDeFatos.md)
- [Estilo de escrita com BERTimbau](TipoDeEscrita.md)
