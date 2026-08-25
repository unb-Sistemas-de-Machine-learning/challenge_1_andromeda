# Objetivos

## 1. Objetivo de negócio

**Problema:** Pessoas idosas têm grande dificuldade em identificar notícias falsas e desinformação (especialmente no contexto político brasileiro), o que as torna vulneráveis a manipulações e gera ansiedade e insegurança no uso da tecnologia.

**Objetivo do negócio:** Desenvolver um sistema simples, acolhedor e altamente intuitivo que permita a esse público a fácil verificação da veracidade e/ou confiabilidade de uma notícia, promovendo autonomia digital.

- O que muda: Redução do repasse de fake news em redes sociais e aumento da confiança do idoso ao consumir informações. Ele passa a ter uma ferramenta parceira que verifica suas dúvidas.
- Como medir:
    - Taxa de retenção/recorrência (quantas vezes o mesmo idoso volta para verificar novas notícias).
    - Volume de entradas processadas semanalmente.

## 2. Objetivo de ML

A partir dos dados de entrada, o modelo prevê:

- Categorias de classificação (Verdadeiro, Falso, Sensacionalista, Fora de contexto, etc.).
- Índices de confiabilidade.
- Parágrafo didático da análise.
- Fontes confiáveis utilizadas para embasar a resposta.

## 3. Escopo

Este projeto **TRATA** exclusivamente da verificação, classificação e contextualização didática de notícias e conteúdos de mídia (com foco no cenário político brasileiro) submetidos pelos usuários.

Esse projeto **NÃO TRATA** de moderação automática de redes sociais, rastreamento de dados pessoais, exclusão de conteúdos nos dispositivos dos usuários ou verificação de golpes financeiros diretos.


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
      <td><a href="https://github.com/Brenofrds">Breno Fernandes</a></td>
       <td><a href="https://github.com/bolzanMGB">Othavio Bolzan</a></td>
      <td>23/08/2026</td>
    </tr>
    <tr>
      <td>1.1</td>
      <td>Refinamento das métricas de negócio e modelo</td>
      <td><a href="https://github.com/bolzanMGB">Othavio Bolzan</a></td>
      <td> - </td>
      <td>26/08/2026</td>
    </tr>
  </tbody>
</table>