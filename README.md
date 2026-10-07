# Antes de compartilhar — Equipe Andrômeda

Sistemas de Machine Learning — UnB/FCTE — 2026/02

## Ideia

Ajudar pessoas que recebem notícias sobre política pelas redes sociais e por aplicativos de mensagem a avaliar se aquele conteúdo é confiável antes de repassá-lo aos seus contatos.

A proposta é um assistente com interface simples, pensado para quem não tem familiaridade com as ferramentas de checagem que já existem hoje.

O aplicativo permite informar o título ou o link de uma notícia, consultar reportagens candidatas, analisar o conteúdo e apresentar um índice de confiabilidade acompanhado da composição da nota.

## Como funciona

1. A pessoa informa o título de uma notícia ou seu link HTTPS.
2. Para títulos, o aplicativo consulta a GDELT e apresenta reportagens candidatas para a pessoa escolher o link correto.
3. O aplicativo acessa a reportagem diretamente por HTTP, extrai o texto e exclui conteúdos de opinião, colunas e editoriais.
4. A análise é realizada no próprio aparelho, incluindo o matching de checagens, a consulta ao Atlas, o resumo e o modelo BERTimbau em ONNX.
5. O aplicativo consulta o backend do projeto para realizar a checagem factual por meio da API do Google Fact Check.
6. O resultado apresenta um índice de confiabilidade e permite consultar a composição da nota pelo botão `*`.

O modelo local fornece um sinal estatístico, não um veredito factual. O índice apresentado não representa a probabilidade de uma notícia ser verdadeira.

## Critérios de avaliação

A composição da nota segue os pesos definidos na `sdd_v1`:

* **Checagem factual:** 65%.
* **Credibilidade da fonte:** 20%.
* **Estilo de escrita:** 15%.

Quando algum critério está indisponível, ele é retirado do denominador e os pesos restantes são normalizados.

A credibilidade da fonte considera o Atlas, a transparência editorial, a idade do domínio consultada via RDAP, o domínio institucional e o uso de HTTPS. Fontes com nota inferior a 20/100 limitam o índice final a 35/100.

A nota do BERTimbau combina os trechos analisados de acordo com seus comprimentos.

## Tecnologias e arquitetura

O aplicativo é nativo para Android, desenvolvido em Kotlin. A interface utiliza uma `Activity` Android, e o projeto gera um APK para instalação no aparelho.

A aplicação não utiliza React, Capacitor, Vite, WebView ou servidor em `localhost`.

A arquitetura distribui o processamento entre o aplicativo e o backend:

* **Android/Kotlin:** interface, extração de texto, análise local e apresentação dos resultados.
* **GDELT:** busca de reportagens a partir de títulos.
* **Atlas:** índice local de fontes, atualizado pela API pública.
* **BERTimbau ONNX:** análise estatística do estilo de escrita.
* **Render:** backend responsável pela rota `POST /fact-check`.
* **Google Fact Check:** serviço de checagem factual acessado pelo backend.

A busca de reportagens e a leitura do conteúdo acessam a GDELT e o veículo diretamente, sem passar pelo Render.

## Dados e funcionamento offline

O modelo ONNX e uma cópia inicial do Atlas ficam em `android/app/src/main/assets/`.

O índice atualizado do Atlas é armazenado na área privada do aplicativo e substituído somente após uma coleta válida. As atualizações são realizadas diretamente pela API pública do Atlas, utilizando o JWT público `dummy`, sem credenciais pessoais e sem passar pelo Render.

A atualização ocorre, no máximo, uma vez por dia quando bem-sucedida. Se houver falha, a última cópia válida pode ser utilizada por até 7 dias, incluindo a cópia inicial fornecida no APK. Após esse período, o aplicativo informa que o Atlas está indisponível. Falhas de atualização aguardam uma hora antes de uma nova tentativa.

O aplicativo não depende de um servidor local para funcionar. Entretanto, consultas externas, como a busca de reportagens, a atualização do Atlas e a checagem factual, dependem de conexão com a internet.

A extração do texto pode falhar em páginas que exigem JavaScript, login ou que bloqueiam clientes automatizados.

## Configuração

Defina a variável `FACTCHECK_PROXY_TOKEN` em um dos seguintes locais:

* No ambiente do sistema.
* Em `~/.gradle/gradle.properties`, utilizando `factcheckProxyToken=...`.
* Em um arquivo `.env` local na raiz do repositório.

O valor deve ser igual ao `FACTCHECK_PROXY_TOKEN` configurado no Render.

O endereço padrão do backend é `https://challenge-1-andromeda-00o6.onrender.com`. Para alterá-lo, utilize `FACTCHECK_BACKEND_URL`.

A chave `GOOGLE_FACT_CHECK_API_KEY` permanece exclusivamente no backend, na branch `servidor_backend`, hospedado no Render.

O token de comunicação com o backend é incorporado ao APK e pode ser extraído por quem instalar o aplicativo. Ele não deve ser tratado como um segredo. A chave do Google, por outro lado, não é distribuída no aplicativo.

## Gerar APK

Para compilar o aplicativo, instale:

* Android SDK, API 36 e Build Tools.
* JDK 17.
* Git LFS, para obter os pesos reais do modelo ONNX.

Após clonar o repositório, execute `git lfs pull` para baixar os arquivos do modelo.

No Windows, execute:

```powershell
cd android
.\gradlew.bat assembleDebug
```

No macOS ou Linux, execute:

```sh
cd android
./gradlew assembleDebug
```

O APK gerado estará em:

`android/app/build/outputs/apk/debug/app-debug.apk`

O build falha com uma mensagem clara caso o token de comunicação com o backend não esteja configurado. Não utilize `pnpm build`, pois esta branch não possui um projeto web.

## Documentação

A documentação do projeto é publicada em:

https://unb-sistemas-de-machine-learning.github.io/challenge_1_andromeda/

## Equipe

<div align="center">
    <table style="margin-left: auto; margin-right: auto;">
        <tr>
            <td align="center">
                <a href="https://github.com/DaviNegreiros">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/75706873?v=4" width="150px"/>
                    <h5 class="text-center">Davi Negreiros <br/>232013971</h5>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/Bertolazi">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/122479691?v=4" width="150px"/>
                    <h5 class="text-center">Gabriel Bertolazi <br/>202023663</h5>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/joaopedrodasilvarodrigues">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/100419740?v=4" width="150px"/>
                    <h5 class="text-center">João Pedro da Silva Rodrigues <br/>211031074</h5>
                </a>
            </td>
        </tr>
        <tr>
            <td align="center">
                <a href="https://github.com/bolzanMGB">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/149620306?v=4" width="150px"/>
                    <h5 class="text-center">Othavio Bolzan <br/>231039150</h5>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/Pietrocv">
                    <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/86116655?v=4" width="150px"/>
                    <h5 class="text-center">Pietro Visentin <br/>232014754</h5>
                </a>
            </td>
        </tr>
    </table>
</div>

## Disciplina

Sistemas de Machine Learning — UnB/FCTE — Profs. Isaque Alves e Guilherme Fernandes — 2026/2
