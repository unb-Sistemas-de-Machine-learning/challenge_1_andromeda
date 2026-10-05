#  Backlog


## 1. Requisitos do Sistema

<p align="center">Tabela 1 - Backlog de Requisitos </p>

|  ID Épico | Nome Épico |  ID Requisito | Nome Requisito |Descrição Requisito | 
| :--- | :--- | :--- | :--- | :---: |
| EP01  | Avaliação das Notícias| RF01 | Detecção de Falsidades Factuais | O sistema deve ser capaz de identificar a presença de falsidades factuais na notícia através do cruzamento da própria notícia com uma base de dados com conhecimentos incontestáveis. |
|  | | RF02 | Modelo de Estilo de Escrita | O sistema deve carregar e reutilizar o modelo `vzani/portuguese-fake-news-classifier-bertimbau-combined`, com revisão fixa e registro da versão usada. |
|  | | RF03 | Análise de Estilo de Escrita | O sistema deve executar exclusivamente a inferência do BERTimbau em segmentos de até 512 tokens, processar todo o texto extraído e agregar as notas orientadas à classe `True` pelos caracteres de cada segmento, sem apresentar a previsão como veredito factual. |
|  | | RF04 | Checagem de Fatos Verificáveis | O sistema deve consultar checagens publicadas para uma afirmação selecionada, usando a Google Fact Check Tools API, sem atribuir reputação à fonte. |
|  | | RF05 | Correspondência da Afirmação | O sistema deve comparar a afirmação selecionada com `Claim.text`, rejeitar diferenças numéricas e de negação e preservar as revisões excluídas com seus motivos. |
|  | | RF06 | Normalização dos Vereditos | O sistema deve mapear somente rótulos completos conhecidos para a escala local de 0 a 1, conservando o veredito original e sem nota para rótulos desconhecidos. |
|  | | RF07 | Agregação de Checagens | O sistema deve excluir duplicatas, calcular médias por agência e combinar essas médias com pesos iguais, exibindo divergências, limites da busca e escopo da afirmação. |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

## 2. Critérios do Sistema

### 2.1 Para Avaliar a Veracidade da Notícia

<p align="center">Tabela 2 - Critérios para Avaliação de Veracidade </p>

|  ID Critérios | Descrição Critério |  
| :--- |  :---: |
| CRT01  | Checagem de fatos verificáveis: afirmação selecionada e checagens publicadas, peso previsto 60%. |
| CRT02  | Estilo de escrita com BERTimbau, peso previsto 40%. |
| CRT03  | Verificação de alegações com evidências e XLM-RoBERTa, planejada e fora da nota atual. |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>


## Histórico de Versão
<table classa= "full-width-table">
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
      <td>Criação inicial da documentação </td>
      <td><a href="https://github.com/bolzanMGB">Othavio Bolzan</a></td>
       <td> - </td>
      <td>26/08/2026</td>
    </tr>
    <tr>
      <td>1.1</td>
      <td> Análise inicial dos requisitos e critérios</td>
      <td><a href="https://github.com/bolzanMGB">Othavio Bolzan</a> e <a href="https://github.com/DaviNegreiros">Davi Negreiros</a></td>
      <td>- </td>
      <td>29/08/2026</td>
    </tr>
  </tbody>
</table>
