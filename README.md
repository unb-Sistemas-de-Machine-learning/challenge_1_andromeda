# Challenge 1 — Equipe Andrômeda

Documentação do **Challenge 1** da disciplina de **Sistemas de Machine Learning (2026/2)** da **Universidade de Brasília (UnB)**.

O projeto consiste no desenvolvimento de um sistema de Inteligência Artificial para auxiliar no **combate à desinformação**, especialmente entre pessoas da terceira idade.

## 1. Projeto

### 1.1. Ideia

O projeto **Antes de Compartilhar** tem como objetivo auxiliar pessoas que recebem notícias sobre política pelas redes sociais e aplicativos de mensagem a avaliar se determinado conteúdo é confiável antes de repassá-lo aos seus contatos.

A proposta consiste em um assistente com interface simples, pensado principalmente para pessoas que não possuem familiaridade com as ferramentas de checagem disponíveis atualmente.

O aplicativo permite informar o **título ou o link de uma notícia**, consultar reportagens candidatas, analisar o conteúdo e apresentar um **índice de confiabilidade**, acompanhado da composição da nota.

### 1.2. Objetivo

O sistema busca facilitar o processo de verificação de informações por meio da combinação de:

* checagem factual;
* análise da credibilidade da fonte;
* análise estatística do estilo de escrita;
* apresentação simplificada dos resultados.

O sistema não determina de forma absoluta se uma notícia é verdadeira ou falsa. O modelo de linguagem fornece um sinal estatístico que é combinado com outras informações para compor o índice apresentado ao usuário.

## 2. Funcionamento

O fluxo principal do aplicativo ocorre da seguinte forma:

1. A pessoa informa o **título de uma notícia** ou seu **link HTTPS**.
2. Quando é informado apenas um título, o aplicativo consulta a **GDELT** e apresenta reportagens candidatas para que a pessoa selecione o link correto.
3. O aplicativo acessa diretamente a reportagem por HTTP e realiza a extração do texto.
4. Conteúdos classificados como **opinião, coluna ou editorial** são excluídos da análise.
5. O aplicativo realiza parte do processamento localmente, incluindo:

   * matching de checagens;
   * consulta ao Atlas;
   * geração do resumo;
   * análise pelo modelo BERTimbau em ONNX.
6. O aplicativo consulta o backend do projeto para realizar a checagem factual por meio da **API do Google Fact Check**.
7. O sistema apresenta o **índice de confiabilidade** ao usuário.
8. Por meio do botão `*`, o usuário pode consultar a composição da nota.

O modelo local fornece apenas um **sinal estatístico**, não um veredito factual. Portanto, o índice apresentado **não representa a probabilidade de uma notícia ser verdadeira**.

## 3. Critérios de Avaliação

A composição do índice segue os pesos definidos na especificação `sdd_v1`:

| Critério               | Peso |
| ---------------------- | ---: |
| Checagem factual       |  65% |
| Credibilidade da fonte |  20% |
| Estilo de escrita      |  15% |

Quando algum critério não está disponível, ele é removido do denominador e os pesos dos critérios restantes são normalizados.

### 3.1. Checagem factual

A checagem factual representa o principal componente do índice, correspondendo a **65% da composição original**.

O aplicativo consulta o backend, que utiliza a **API do Google Fact Check** para realizar a verificação das alegações relacionadas ao conteúdo analisado.

### 3.2. Credibilidade da fonte

A credibilidade da fonte corresponde a **20% da composição original** e considera informações como:

* índice do Atlas;
* transparência editorial;
* idade do domínio, consultada via RDAP;
* domínio institucional;
* utilização de HTTPS.

Fontes com nota inferior a **20/100** limitam o índice final a **35/100**.

### 3.3. Estilo de escrita

A análise de estilo corresponde a **15% da composição original**.

O aplicativo utiliza o modelo **BERTimbau**, executado localmente em formato ONNX, para obter uma avaliação estatística dos trechos analisados.

A nota final do BERTimbau é calculada considerando os trechos analisados de acordo com seus respectivos comprimentos.

## 4. Tecnologias e Arquitetura

O aplicativo é desenvolvido de forma **nativa para Android**, utilizando **Kotlin**.

A interface utiliza uma `Activity` Android e o projeto gera um APK para instalação diretamente no dispositivo.

O projeto **não utiliza**:

* React;
* Capacitor;
* Vite;
* WebView;
* servidor em `localhost`.

### 4.1. Componentes

| Componente        | Responsabilidade                                                          |
| ----------------- | ------------------------------------------------------------------------- |
| Android/Kotlin    | Interface, extração de texto, análise local e apresentação dos resultados |
| GDELT             | Busca de reportagens a partir de títulos                                  |
| Atlas             | Índice local de fontes                                                    |
| BERTimbau ONNX    | Análise estatística do estilo de escrita                                  |
| Render            | Backend responsável pela rota `POST /fact-check`                          |
| Google Fact Check | Serviço de checagem factual utilizado pelo backend                        |

### 4.2. Distribuição do processamento

O processamento é distribuído entre o aplicativo Android e o backend.

**Aplicativo Android:**

* interface;
* busca de reportagens;
* extração de texto;
* consulta e atualização do Atlas;
* matching de checagens;
* resumo;
* execução do BERTimbau;
* cálculo e apresentação dos resultados.

**Backend:**

* disponibilização da rota `POST /fact-check`;
* comunicação com a API do Google Fact Check;
* gerenciamento da chave da API do Google.

A busca de reportagens e a leitura do conteúdo são realizadas diretamente pela aplicação, sem passar pelo Render.

## 5. Dados e Funcionamento Offline

O modelo ONNX e uma cópia inicial do Atlas estão armazenados em:

```text
android/app/src/main/assets/
```

O Atlas atualizado é armazenado na área privada do aplicativo e somente substitui a versão anterior após uma coleta válida.

As atualizações são realizadas diretamente pela API pública do Atlas utilizando o JWT público `dummy`, sem credenciais pessoais e sem passar pelo Render.

### 5.1. Política de atualização do Atlas

A atualização do Atlas ocorre, no máximo, uma vez por dia quando realizada com sucesso.

Em caso de falha:

* a última cópia válida pode ser utilizada por até **7 dias**;
* a cópia inicial fornecida no APK também pode ser utilizada durante esse período;
* após esse período, o aplicativo informa que o Atlas está indisponível;
* novas tentativas após uma falha aguardam **uma hora**.

### 5.2. Dependência de Internet

O aplicativo não depende de um servidor local para funcionar.

Entretanto, algumas funcionalidades dependem de conexão com a internet, incluindo:

* busca de reportagens;
* atualização do Atlas;
* checagem factual.

A extração do texto pode falhar em páginas que:

* exigem JavaScript;
* exigem autenticação;
* bloqueiam clientes automatizados;
* utilizam mecanismos que impedem o acesso automatizado ao conteúdo.

## 6. Configuração

A variável `FACTCHECK_PROXY_TOKEN` deve ser configurada em um dos seguintes locais:

* variável de ambiente do sistema;
* `~/.gradle/gradle.properties`, utilizando `factcheckProxyToken=...`;
* arquivo `.env` local na raiz do repositório.

O valor deve ser igual ao `FACTCHECK_PROXY_TOKEN` configurado no Render.

O endereço padrão do backend é:

```text
https://challenge-1-andromeda-00o6.onrender.com
```

Para alterá-lo, utilize a variável:

```text
FACTCHECK_BACKEND_URL
```

A chave `GOOGLE_FACT_CHECK_API_KEY` permanece exclusivamente no backend, na branch `servidor_backend`, hospedada no Render.

O token utilizado para comunicação com o backend é incorporado ao APK e pode ser extraído por qualquer pessoa que instale o aplicativo. Portanto, esse token **não deve ser tratado como um segredo**.

A chave da API do Google, por outro lado, **não é distribuída no aplicativo**.

## 7. Compilação do APK

### 7.1. Requisitos

Para compilar o aplicativo, são necessários:

* Android SDK;
* Android API 36;
* Android Build Tools;
* JDK 17;
* Git LFS.

O Git LFS é necessário para obter os pesos reais do modelo ONNX.

Após clonar o repositório, execute:

```sh
git lfs pull
```

### 7.2. Windows

No Windows, execute:

```powershell
cd android
.\gradlew.bat assembleDebug
```

### 7.3. macOS e Linux

No macOS ou Linux, execute:

```sh
cd android
./gradlew assembleDebug
```

O APK será gerado em:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

O processo de build apresenta uma mensagem de erro caso o token de comunicação com o backend não esteja configurado.

Não utilize:

```sh
pnpm build
```

Essa branch não possui um projeto web.

## 8. Documentação

A documentação completa do projeto está disponível em:

[https://unb-sistemas-de-machine-learning.github.io/challenge_1_andromeda/](https://unb-sistemas-de-machine-learning.github.io/challenge_1_andromeda/)

## 9. Equipe

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

