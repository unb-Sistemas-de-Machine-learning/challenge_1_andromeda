# Equipe Andromeda - Challenge 1

Esta é a documentação do **Challenge 1** da disciplina de **Sistemas de Machine Learning (2026.2)** da **Universidade de Brasília (UnB)**. Nosso projeto consiste no desenvolvimento de um sistema de Inteligência Artificial para o **Combate à Desinformação na Terceira Idade**.

## 1. Ideia inicial

Circulam pelas redes sociais e pelos aplicativos de mensagem muitas notícias sobre
política cuja veracidade é difícil de verificar. Quem recebe raramente tem tempo,
ou familiaridade com as ferramentas de checagem que já existem, para conferir antes
de repassar, seja de forma oral ou através do compartilhamento dentro de redes sociais.

Nossa ideia é auxiliar pessoas, especialmente aquelas da terceira idade, a avaliar se uma notícia é confiável por meio de um assistente com interface simples.


## Equipe
<div align="center">
   <table style="margin-left: auto; margin-right: auto;">
        <tr>
            <td align="center">
                <a href="https://github.com/DaviNegreiros">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/75706873?v=4" width="150px;"/>
                    <h5 class="text-center">Davi Negreiros <br>232013971</h5>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/Bertolazi">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/122479691?v=4" width="150px;"/>
                    <h5 class="text-center">Gabriel Bertolazi <br>202023663</h5>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/joaopedrodasilvarodrigues">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/100419740?v=4" width="150px;"/>
                    <h5 class="text-center">João Pedro da Silva Rodrigues <br>211031074</h5>
                </a>
            </td>
        </tr>
        <tr>
            <td align="center">
                <a href="https://github.com/bolzanMGB">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/149620306?v=4" width="150px;"/>
                    <h5 class="text-center">Othavio Bolzan <br>231039150</h5>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/Pietrocv">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/86116655?v=4" width="150px;"/>
                    <h5 class="text-center">Pietro Visentin <br>232014754</h5>
                </a>
            </td>
        </tr>
    </table>
</div>
# Challenge 1 Andromeda

## Implemented Feature: News Analysis System

The feature specification lives in `specs/001-news-analysis/` and defines an
auditable news-analysis pipeline with:

- URL safety and fetch limits
- Checagem de fatos verificáveis: published claim reviews, explicit selected-claim scope and publisher-balanced scores
- BERTimbau writing-style inference on CPU, with a pinned model revision,
  complete token-window processing, and character-weighted aggregation
- Credibilidade da fonte com índice local do Atlas da Notícia e evidências auditáveis
- SQLite audit trail without retaining full extracted article text
- explicit pipeline versioning, coverage, and non-verdict limitations

Validation targets are documented in `specs/001-news-analysis/quickstart.md`.

Consulte [Checagem de fatos verificáveis](ChecagemDeFatos.md) para a interpretação
dos vereditos, a escala local, as entradas e saídas e os limites da correspondência.

## Estilo de escrita

O critério usa exclusivamente o modelo
`vzani/portuguese-fake-news-classifier-bertimbau-combined`. Cada segmento contém
até 512 tokens, incluindo tokens especiais. Todo o texto extraído é processado
em janelas sem sobreposição. A nota é a média das saídas para a classe `True`,
ponderada pelos caracteres de cada segmento.

A interface apresenta modelo, revisão, segmentos analisados, classe e confiança
agregadas. Os resultados por segmento estão disponíveis na seção expansível
da interface, na API e na auditoria.
Confiança do classificador não comprova veracidade. Com apenas escrita disponível,
o peso efetivo é 100%, mas a cobertura dos critérios permanece 40%.

Consulte [Estilo de escrita com BERTimbau](TipoDeEscrita.md) para instalação,
segmentação, interpretação das saídas e tratamento de falhas.

## Interface e integração

O cartão de checagem factual permanece visível com ou sem evidências. Status,
motivos, consultas registradas, vereditos, links e exclusões mostram o que foi
possível avaliar. Com somente escrita disponível, o resumo indica “Somente
estilo de escrita”, sem apresentar a nota como confirmação factual.

- [Google Fact Check Tools API](Manual_Google_Fact_Check_Tools_API.md)
- [Interface, API e fluxo do sistema](InterfaceEAPI.md)
