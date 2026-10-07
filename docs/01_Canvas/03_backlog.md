# Backlog

## 1. Requisitos do Sistema

<p align="center">Tabela 1 - Backlog de Requisitos </p>

<table>
  <thead>
    <tr>
      <th colspan="2">Épico</th>
      <th colspan="3">Requisito</th>
    </tr>
    <tr>
      <th>ID</th>
      <th>Nome</th>
      <th>ID</th>
      <th>Nome</th>
      <th>Descrição</th>
    </tr>
  </thead>
  <tbody>
    <!-- ÉPICO 01 -->
    <tr>
      <td rowspan="7">EP01</td>
      <td rowspan="7">Avaliação das Notícias</td>
      <td>EP01-RF01</td>
      <td>Detecção de Falsidades Factuais</td>
      <td>O sistema deve ser capaz de identificar a presença de falsidades factuais na notícia através do cruzamento da própria notícia com uma base de dados com conhecimentos incontestáveis.</td>
    </tr>
    <tr>
      <td>EP01-RF02</td>
      <td>Base de Dados de Padrões de Escrita</td>
      <td>O sistema deve registrar e manter atualizados padrões linguísticos e estruturais comuns em notícias falsas e sensacionalistas.</td>
    </tr>
    <tr>
      <td>EP01-RF03</td>
      <td>Análise de Padrões de Escrita</td>
      <td>O sistema deve comparar o texto da notícia com os padrões de escrita definidos no RF02 para detectar indícios de viés falso ou sensacionalista.</td>
    </tr>
    <tr>
      <td>EP01-RF04</td>
      <td>Triagem de Credibilidade da Fonte</td>
      <td>O sistema deve executar um procedimento de triagem para avaliar a credibilidade do portal ou autor de origem da notícia.</td>
    </tr>
    <tr>
      <td>EP01-RF05</td>
      <td>Verificação de Histórico da Fonte</td>
      <td>A triagem de credibilidade (RF04) deve abranger a checagem do histórico de publicações anteriores do veículo em busca de reincidência em desinformação.</td>
    </tr>
    <tr>
      <td>EP01-RF06</td>
      <td>Verificação de Reputação da Fonte</td>
      <td>A triagem de credibilidade (RF04) deve abranger a validação externa da reputação do veículo perante agências de checagem, selos de qualidade e certificações institucionais (como a IFCN).</td>
    </tr>
    <tr>
      <td>EP01-RF07</td>
      <td>Verificação da Relação entre Fontes</td>
      <td>A triagem de credibilidade (RF04) deve confrontar a notícia analisada com os registros de outras fontes de dados sobre o mesmo acontecimento, avaliando o grau de concordância entre as informações.</td>
    </tr>
    <!-- ÉPICO 02 - Interação -->
    <tr>
      <td rowspan="3">EP02</td>
      <td rowspan="3">Interação</td>
      <td>EP02-RF01</td>
      <td>Entrada por Texto</td>
      <td>O sistema deve aceitar texto inserido pelo usuário via digitação ou copy/paste.</td>
    </tr>
    <tr>
      <td>EP02-RF02</td>
      <td>Entrada por Imagens</td>
      <td>O sistema deve aceitar imagens e capturas de tela inseridas pelo usuário nos formatos PNG e JPEG.</td>
    </tr>
    <tr>
      <td>EP02-RF03</td>
      <td>Entrada de Voz</td>
      <td>O sistema deve aceitar gravações de áudio como entrada de pesquisa.</td>
    </tr>
    <!-- ÉPICO 03 - Acessibilidade -->
    <tr>
      <td rowspan="5">EP03</td>
      <td rowspan="5">Acessibilidade</td>
      <td>EP03-RF01</td>
      <td>Ajustes de Tipografia e Interface Visual</td>
      <td>O sistema deve apresentar um layout simples, com elementos visualmente claros e opções para utilização de fontes maiores.</td>
    </tr>
    <tr>
      <td>EP03-RF02</td>
      <td>Alvos de Toque Ampliados</td>
      <td>A interface deve possuir botões e áreas de interação significativamente maiores.</td>
    </tr>
    <tr>
      <td>EP03-RF03</td>
      <td>Distância Ampliada entre Alvos de Toque</td>
      <td>A interface deve possuir botões e áreas de interação com uma distância significante grande entre si, de modo a evitar toques acidentais.</td>
    </tr>
    <tr>
      <td>EP03-RF04</td>
      <td>Ícones Acessíveis e Descritivos</td>
      <td>A interface deve utilizar ícones de fácil compreensão universal quando necessário.</td>
    </tr>
    <tr>
      <td>EP03-RF05</td>
      <td>Navegação Simplificada</td>
      <td>O sistema deve manter uma estrutura de navegação linear e previsível, evitando funcionalidades secundárias, menus ocultos e passos desnecessários.</td>
    </tr>
  </tbody>
</table>

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

## 2. Critérios do Sistema

### 2.1 Para Avaliar a Veracidade da Notícia

<p align="center">Tabela 2 - Critérios para Avaliação de Veracidade </p>

| ID Critérios |         Descrição Critério         |
| :----------- | :--------------------------------: |
| CRT01        |        Falsidades Factuais         |
| CRT02        | Padrões de Escrita Sensacionalista |
| CRT03        |         Histórico da Fonte         |
| CRT04        |         Reputação da Fonte         |
| CRT05        |        Relação entre Fontes        |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

<!-- ### 2.2 Para Escolha de Fonte

<p align="center">Tabela 2 - Critérios para Avaliação de Veracidade </p>

| ID Critérios |         Descrição Critério         |
| :----------- | :--------------------------------: |
| CRT01        |        Falsidades Factuais         |
| CRT02        | Padrões de Escrita Sensacionalista |
| CRT03        |         Histórico da Fonte         |
| CRT04        |         Reputação da Fonte         |
| CRT05        |        Relação entre Fontes        |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p> -->

## Referências

Referências: Gomez-Hernandez et al. (2023) — “Design Guidelines of Mobile Apps for Older Adults: Systematic Review and Thematic Analysis” e  Amouzadeh et al. (2025) — “Optimizing mobile app design for older adults: systematic review of age-friendly design”.

## Histórico de Versão

<table class= "full-width-table">
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
      <tr>
      <td>1.1</td>
      <td> Reorganização dos requisitos de acessibilidade.</td>
      <td><a href="https://github.com/bolzanMGB">Othavio Bolzan</a> e <a href="https://github.com/DaviNegreiros">Davi Negreiros</a></td>
      <td>- </td>
      <td>29/08/2026</td>
    </tr>
  </tbody>
</table>