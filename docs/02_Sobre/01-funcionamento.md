# Visão Geral

Dado um título ou um link de reportagem, o app devolve:

- Uma classificação de confiabilidade: alta, média, baixa ou baixíssima.
- Um texto explicativo montado por frases fixas em Kotlin.
- Opcionalmente, um botão de detalhes que abre um modal com checagens factuais correspondentes.

---

## 1. Componentes do Sistema

O sistema é dividido em três componentes principais, cada um com uma responsabilidade bem definida:

<p align="center">Tabela 1 - Componentes do sistema</p>

| Número | Componente | Função |
|---|---|---|
| 01 | App Android | Interface com a pessoa, orquestração do pipeline, inferência do BERTimbau no aparelho e aplicação das regras que geram o feedback. |
| 02 | Backend de checagem | Proxy FastAPI no Render que esconde a chave do Google, exige token Bearer e repassa o JSON de checagens sem transformá-lo. |
| 03 | Serviços externos | GDELT: Busca por título. <br> Google Fact Check: Checagens factuais. <br> Atlas da Notícia: Domínios de veículos. <br> Git LFS: Armazenamento do modelo `.onnx`. |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

---

## 2. Fluxo de Funcionamento

<p align="center">Tabela 2 - Etapas detalhadas do fluxo</p>

| Número | Etapa | O que acontece |
|---|---|---|
| 01 | Entrada | A pessoa informa um título ou um link. Para link, valida-se HTTPS. Para título, consulta-se a GDELT e a pessoa escolhe uma reportagem. |
| 02 | Download e extração | A página é baixada e o **Jsoup** extrai informações do HTML. |
| 03 | Filtro de opinião | Se a reportagem parece opinião ou editorial, a avaliação é interrompida. |
| 04 | Aplicação de Métricas | **1. Checagens factuais;** <br> **2. Credibilidade da Fonte;** <br> **3. Tipo de Escrita.** |
| 05 | Cálculo dos scores | Cada métrica possui um peso. É gerado um score de 0 a 1 para cada métrica. Scores ausentes saem da conta e os pesos são renormalizados. |
| 06 | Geração do texto | O texto não é gerado por LLM: é montado por **frases fixas** escolhidas por condições (faixa, checagens, critérios disponíveis, Atlas, institucional, escrita) e unidas com espaço. |
| 07 | Nível de confiabilidade | A nota final (0–100) define a faixa: **alta** (> 85), **média** (> 70), **baixa** (> 40) ou **baixíssima** (≤ 40). |
| 08 | Exibição | A tela mostra a explicação. O botão de detalhes só aparece se houver evidência (ver seção 8). |

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

<p align="center"><b>Figura 1 - Fluxo de funcionamento do app</b></p>

<p align="center">
  <img src="/02_Sobre/fluxo.png" alt="Fluxo de funcionamento do app">
</p>

<p align="center">Fonte: Autoria de <a href="https://github.com/DaviNegreiros">Davi Negreiros</a> e <a href="https://github.com/bolzanMGB">Othavio Araújo Bolzan</a></p>

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
