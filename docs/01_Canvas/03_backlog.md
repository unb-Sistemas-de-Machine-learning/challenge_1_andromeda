# Backlog

## 1. Requisitos do Sistema

<p align="center">Tabela 1 - Backlog de Requisitos</p>

<table>
  <thead>
    <tr>
      <th colspan="2">Épico</th>
      <th colspan="3">Requisito</th>
      <th rowspan="2">Status</th>
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
      <td rowspan="8">EP01</td>
      <td rowspan="8">Avaliação das Notícias</td>
      <td>EP01-RF01</td>
      <td>Consulta de Checagens Pré-Existentes</td>
      <td>O sistema deve consultar o Google Fact Check Tools API, via backend, para identificar checagens factuais publicadas por agências sobre uma afirmação equivalente ao título da reportagem.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP01-RF02</td>
      <td>Filtro de Correspondência de Afirmações</td>
      <td>O sistema deve comparar a afirmação checada com o título da reportagem, descartando divergências de número, localidade, polaridade, atribuição e negação.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP01-RF03</td>
      <td>Tabela de Vereditos</td>
      <td>O sistema deve converter o veredito textual da agência (`textualRating`) em um valor numérico de 0 a 1, usando uma tabela de vereditos reconhecidos.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP01-RF04</td>
      <td>Modelo de Análise de Escrita</td>
      <td>O sistema deve manter um modelo de linguagem em português (BERTimbau) exportado para ONNX, capaz de reconhecer padrões de escrita que fogem das boas práticas jornalísticas, como falas apelativas e indutivas.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP01-RF05</td>
      <td>Inferência Local do Modelo</td>
      <td>O sistema deve executar o modelo BERTimbau no próprio aparelho, sem envio do texto da reportagem a servidores externos, devolvendo um score de 0 a 1.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP01-RF06</td>
      <td>Triagem de Credibilidade da Fonte</td>
      <td>O sistema deve avaliar a credibilidade do veículo a partir de três sinais: presença do domínio no Atlas da Notícia, presença de metadados jornalísticos no HTML (autor, data, links institucionais) e caráter institucional ou governamental do domínio.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP01-RF07</td>
      <td>Cálculo da Nota Final</td>
      <td>O sistema deve combinar as três métricas em uma nota de 0 a 100, aplicando pesos (0,65 para checagens; 0,20 para fonte; 0,15 para escrita) e renormalizando quando alguma métrica estiver ausente.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP01-RF08</td>
      <td>Veto da Fonte</td>
      <td>O sistema deve limitar a nota final a 35 quando a pontuação da fonte for menor que 20, impedindo que uma fonte fraca receba classificação alta.</td>
      <td>Implementado</td>
    </tr>
    <!-- ÉPICO 02 -->
    <tr>
      <td rowspan="6">EP02</td>
      <td rowspan="6">Interação e Feedback</td>
      <td>EP02-RF01</td>
      <td>Entrada por Título</td>
      <td>O sistema deve aceitar um título de reportagem digitado pela pessoa e buscar reportagens correspondentes na GDELT.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP02-RF02</td>
      <td>Entrada por Link</td>
      <td>O sistema deve aceitar um link HTTPS de reportagem, validando o esquema antes de baixar o conteúdo.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP02-RF03</td>
      <td>Geração de Feedback por Frases Fixas</td>
      <td>O sistema deve montar o texto do feedback por meio de frases pré-definidas, sem geração livre por LLM, garantindo que nomes de fontes e links não sejam inventados.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP02-RF04</td>
      <td>Exibição de Evidências</td>
      <td>O sistema deve oferecer um botão de detalhes, exibido apenas quando houver ao menos uma checagem correspondente, pontuada negativamente e com link HTTP(S) válido.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP02-RF05</td>
      <td>Entrada por Imagens</td>
      <td>O sistema deve aceitar imagens e capturas de tela nos formatos PNG e JPEG como entrada de pesquisa.</td>
      <td>Planejado</td>
    </tr>
    <tr>
      <td>EP02-RF06</td>
      <td>Entrada por Voz</td>
      <td>O sistema deve aceitar gravações de áudio como entrada de pesquisa.</td>
      <td>Planejado</td>
    </tr>
    <!-- ÉPICO 03 -->
    <tr>
      <td rowspan="5">EP03</td>
      <td rowspan="5">Acessibilidade</td>
      <td>EP03-RF01</td>
      <td>Ajustes de Tipografia e Interface Visual</td>
      <td>O sistema deve apresentar um layout simples, com elementos visualmente claros e opções para utilização de fontes maiores.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP03-RF02</td>
      <td>Alvos de Toque Ampliados</td>
      <td>A interface deve possuir botões e áreas de interação significativamente maiores.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP03-RF03</td>
      <td>Distância Ampliada entre Alvos de Toque</td>
      <td>A interface deve possuir botões e áreas de interação com uma distância significativa entre si, de modo a evitar toques acidentais.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP03-RF04</td>
      <td>Ícones Acessíveis e Descritivos</td>
      <td>A interface deve utilizar ícones de fácil compreensão universal quando necessário.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP03-RF05</td>
      <td>Navegação Simplificada</td>
      <td>O sistema deve manter uma estrutura de navegação linear e previsível, evitando funcionalidades secundárias, menus ocultos e passos desnecessários.</td>
      <td>Implementado</td>
    </tr>
    <!-- ÉPICO 04 - NOVO -->
    <tr>
      <td rowspan="3">EP04</td>
      <td rowspan="3">Infraestrutura e Segurança</td>
      <td>EP04-RF01</td>
      <td>Backend Proxy de Checagem</td>
      <td>O sistema deve possuir um backend FastAPI independente que esconde a chave do Google, exige token Bearer do app e repassa o JSON de checagens sem transformá-lo.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP04-RF02</td>
      <td>Autenticação por Token</td>
      <td>O backend deve exigir um token Bearer em todas as requisições ao endpoint <code>/fact-check</code>, comparando-o com <code>secrets.compare_digest</code>.</td>
      <td>Implementado</td>
    </tr>
    <tr>
      <td>EP04-RF03</td>
      <td>Verificação de Saúde</td>
      <td>O backend deve expor um endpoint de saúde (<code>GET /</code>) que informe variáveis de ambiente ausentes sem expor seus valores.</td>
      <td>Implementado</td>
    </tr>
  </tbody>
</table>

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

---

## Referências

> Gomez-Hernandez et al. (2023) — "Design Guidelines of Mobile Apps for Older Adults: Systematic Review and Thematic Analysis"

> Amouzadeh et al. (2025) — "Optimizing mobile app design for older adults: systematic review of age-friendly design".

---

## 4. Histórico de Versão

<p align="center">Tabela 3 - Histórico de versão do backlog</p>

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
      <td> - </td>
      <td>26/08/2026</td>
    </tr>
    <tr>
      <td>1.1</td>
      <td>Análise inicial dos requisitos e critérios</td>
      <td><a href="https://github.com/bolzanMGB">Othavio Bolzan</a> e <a href="https://github.com/DaviNegreiros">Davi Negreiros</a></td>
      <td>- </td>
      <td>29/08/2026</td>
    </tr>
    <tr>
      <td>1.1</td>
      <td>Reorganização dos requisitos de acessibilidade.</td>
      <td><a href="https://github.com/bolzanMGB">Othavio Bolzan</a> e <a href="https://github.com/DaviNegreiros">Davi Negreiros</a></td>
      <td>- </td>
      <td>29/08/2026</td>
    </tr>
    <tr>
      <td>2.0</td>
      <td>Revisão do backlog com base no funcionamento real do sistema: descrições alinhadas ao código, inclusão do épico de infraestrutura, status de implementação e separação dos requisitos planejados.</td>
      <td><a href="https://github.com/bolzanMGB">Othavio Bolzan</a> e <a href="https://github.com/DaviNegreiros">Davi Negreiros</a></td>
      <td>- </td>
      <td>07/10/2026</td>
    </tr>
  </tbody>
</table>

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>


- Criar uma **Tabela 4 - Matriz de rastreabilidade** ligando cada requisito aos tópicos da documentação técnica.