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
- Google Fact Check Tools criterion
- Portuguese writing-style classifier criterion
- reserved factual-claims criterion marked `NOT_IMPLEMENTED`
- SQLite audit trail without retaining full extracted article text
- explicit pipeline versioning, coverage, and non-verdict limitations

Validation targets are documented in `specs/001-news-analysis/quickstart.md`.
