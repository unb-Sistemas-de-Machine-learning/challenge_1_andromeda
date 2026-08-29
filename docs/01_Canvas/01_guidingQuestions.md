# Guiding Questions

## 1. Dados

<p align="center">Tabela 1 - Guiding Questions de Dados</p>

|  | Pergunta | Atividade | Recurso | Responsável | Prazo |
| :--- | :--- | :--- | :--- | :--- | :---: |
| DGQ1 | Quais são os critérios que permitem a identificação de uma fake news? | Identificar esses critérios baseado em artigos científicos existentes relacionados ao tema. | Bases de dados e mecanismos de pesquisa científica para levantamento de artigos relacionados ao tema (ex.: Google Scholar, IEEE Xplore e SciELO).  | <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> | |
| DGQ2 | Quais datasets entregam os dados necessários para que um modelo seja capaz de atender os critérios presentes em DGQ1? | Levantar datasets relacionados à detecção de fake news e analisar seus atributos, verificando quais fornecem as informações necessárias para a aplicação dos critérios identificados em DGQ1. | Repositórios e plataformas de datasets para aprendizado de máquina (ex.: Kaggle, Hugging Face Datasets e UCI Machine Learning Repository) | | |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>


## 2. Usuário


<p align="center">Tabela 2 - Guiding Questions de Usuário</p>

|  | Pergunta | Atividade | Recurso | Responsável | Prazo |
| :--- | :--- | :--- | :--- | :--- | :---: |
| UGQ1 | Quais adaptações de acessibilidade a interface deve possuir para facilitar a leitura e a navegação dos idosos? | Desenvolver diretrizes de design inclusivo focadas na terceira idade (tipografia ampliada, alto contraste de cores, botões grandes e navegação simplificada). | Diretrizes de acessibilidade (WCAG), ferramentas de prototipagem (Figma) e testes com usuários idosos. | | |
| UGQ2 | Quais as melhores formas de entrada de conteúdo que o sistema deve ter tendo em vista idosos como usuários? | Mapear como os idosos costumam receber notícias e implementar múltiplos métodos práticos de envio na interface (texto colado, links, áudio do WhatsApp, prints de tela, etc). | Ferramentas de escrita, transcrição de áudio e leitura de imagens. | | |
| UGQ3 | Quais formas de saída de conteúdo seriam melhores para idosos e como promover o engajamento com essa resposta? | Desenvolver formatos de veredito claros e amigáveis (alertas visuais intuitivos, síntese de voz para leitura em áudio e explicações didáticas). | Ferramentas de Text-to-Speech e diretrizes de comunicação clara (Plain Language). | | |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

## 3. Modelo


<p align="center">Tabela 3 - Guiding Questions de Modelo</p>

|  | Pergunta | Atividade | Recurso | Responsável | Prazo |
| :--- | :--- | :--- | :--- | :--- | :---: |
| MQD1 | Qual arquitetura de modelo e estratégia lógica utilizar para simular o processo de fact-checking jornalístico na detecção de desinformação política brasileira? | Desenvolver Chain-of-Thought ou Fine-Tuning para simular etapas: extração de afirmações centrais, busca de evidências e verificação cruzada com jargões políticos nacionais. | APIs de LLMs ou modelos open-source em português e guidelines de fact-checking. | | |
| MQD2 | Como lidar algoritmicamente com fontes de dados que se contradizem durante o cruzamento de informações? | Implementar uma base de dados de conhecimentos incontestáveis. | Algoritmos de resolução de conflitos, identificação de contradições e base de dados geral para conhecimentos de altíssima confiabilidade. | | |
| MQD3 | Quais categorias de classificação (além de verdadeiro/falso) o sistema deve utilizar na saída? | Definir a taxonomia de vereditos e scores de confiança da IA, utilizando categorias como: Verdadeira/Falsa, Paródia, Sensacionalista, Fora do contexto, Desinformação, Malinformação, Misinformation e Propaganda. | Padrões internacionais de taxonomia de desinformação (ex: First Draft News) e testes de compreensão com o público-alvo. | | |
| MQD4 | Quais métricas utilizar para medir cada uma dessas categorias de classificação? | Aplicar matriz de confusão multiclasse, calcular métricas de acurácia, eficácia e F1-Score separadas por categoria e realizar validações periódicas com especialistas (human-in-the-loop) a partir de dados rotulados. | Métricas de avaliação de Machine Learning, conjunto de teste rotulado por jornalistas e relatórios de erro. | | |
| MQD5 | Como lidar com a classificação de Verdadeiro/Falso tendo em vistas as diversas categorias (como no caso de sensacionalista e fora de contexto)? | Estabelecer uma matriz de decisão onde um fato tecnicamente real, mas distorcido ou exagerado, receba o rótulo principal de "Fora do Contexto" ou "Sensacionalista" em vez de um binário simplista. | Diretrizes de análise de discurso, regras de desambiguação textual e curadoria de datasets complexos. | | |
| MQD6 | Como estruturar a saída do sistema considerando as classificações e a necessidade de contextualizar e explicar o veredito, especialmente em casos de conteúdo sensacionalista? | Projetar a resposta da IA para exibir um card de veredito claro, acompanhado obrigatoriamente de um parágrafo descritivo e didático, contextualizando a origem do fato e desconstruindo o apelo emocional. | Diretrizes de comunicação acessível (Plain Language) e protótipos de interface para exibição de texto explicativo. | | |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>


## 4. Produção


<p align="center">Tabela 4 - Guiding Questions de Produção</p>

|  | Pergunta | Atividade | Recurso | Responsável | Prazo |
| :--- | :--- | :--- | :--- | :--- | :---: |
| PGQ1 | Como gerenciar o desenvolvimento do projeto, considerando a adoção de uma metodologia ágil e a organização das atividades da equipe?| Escolher uma metodologia ágil, organizar sprints, entregas incrementais e divisão de tarefas da equipe. | Ferramentas de gestão de projetos (Trello, Jira ou GitHub Projects). | | |
| PGQ2 | Qual será a stack tecnológica usada no projeto? | Definir as linguagens, frameworks e ferramentas de hospedagem do projeto. | Python, Streamlit/FastAPI, MkDocs e plataformas de nuvem (AWS, Heroku, etc.). | | |
| PGQ3 | Onde e como documentar o projeto? | Definir o framework ou ferramenta que será utilizada para documentação. | MkDocs com o tema Material e repositório Git. | | |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>


## 5. Ética 


<p align="center">Tabela 5 - Guiding Questions de Ética</p>

|  | Pergunta | Atividade | Recurso | Responsável | Prazo |
| :--- | :--- | :--- | :--- | :--- | :---: |
| EGQ1 | Como garantir clareza dos dados-fonte? | Exibir de forma clara para o usuário de onde a IA tirou a resposta e quais fontes foram consultadas. | Design de interface voltado à explicabilidade (Explainable AI) e links diretos para as fontes. | | |
| EGQ2 | Como diminuir ao máximo o enviesamento tendo em vista as diversas fontes utilizadas? | Desenvolver uma estratégia para que a IA analise os fatos com base em evidências objetivas e incontestáveis, de forma semântica. Além da busca por formas de identificação de fake news que não levem em consideração o conteúdo da notícia. | Datasets de conhecimentos objetivos e incontestáveis, modelos de análise semântica, diretrizes de neutralidade algorítmica e modelos de análise de padrões de escrita relacionados a fake news. | | |

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
       <td><a href="https://github.com/DaviNegreiros">Davi Negreiros<a></td>
      <td>23/08/2026</td>
    </tr>
    <tr>
      <td>1.1</td>
      <td>Refinamento das métricas de negócio e modelo</td>
      <td><a href="https://github.com/bolzanMGB">Othavio Bolzan</a></td>
      <td><a href="https://github.com/DaviNegreiros">Davi Negreiros</a></td>
      <td>25/08/2026</td>
    </tr>
    <tr>
      <td>1.2</td>
      <td>Aplicação das correções necessárias encontradas na revisão de 1.1</td>
      <td><a href="https://github.com/DaviNegreiros">Davi Negreiros<a></td>
      <td> - </td>
      <td>26/08/2026</td>
    </tr>
  </tbody>
</table>