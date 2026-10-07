# Antes de compartilhar — Android

Aplicativo **nativo em Kotlin**. A interface é uma `Activity` Android; o projeto não usa React, Capacitor, Vite, WebView nem servidor em `localhost`. O build produz um APK, não um site.

## Fluxo

1. A pessoa informa o título de uma notícia ou seu link HTTPS.
2. Para título, o app consulta a GDELT diretamente e mostra reportagens candidatas. A pessoa escolhe o link correto.
3. O app baixa a reportagem por HTTP nativo, extrai o texto e exclui opinião, coluna e editorial.
4. Atlas, matching de checagens, resumo e BERTimbau ONNX são processados no aparelho. O modelo e o snapshot do Atlas estão em `android/app/src/main/assets/`.
5. A única chamada ao **nosso** backend é `POST /fact-check` no Render. O servidor da branch `servidor_backend` mantém `GOOGLE_FACT_CHECK_API_KEY`.

A busca pelo título e a leitura da reportagem acessam GDELT e o veículo diretamente; não passam pelo Render. O modelo local fornece um sinal estatístico, não um veredito factual. A extração pode falhar em páginas que exigem JavaScript, login ou bloqueiam clientes automatizados.

## Configuração

Defina `FACTCHECK_PROXY_TOKEN` no ambiente, em `~/.gradle/gradle.properties` como `factcheckProxyToken=...`, ou em um `.env` local na raiz do repositório. Esse valor deve ser igual ao `FACTCHECK_PROXY_TOKEN` no Render. O endereço padrão é `https://challenge-1-andromeda-00o6.onrender.com`; `FACTCHECK_BACKEND_URL` permite alterá-lo.

O token de comunicação é incorporado ao APK e pode ser extraído por quem instalar o aplicativo. A chave do Google permanece exclusivamente no Render.

## Gerar APK

Instale Android SDK (API 36 e Build Tools), JDK 17 e Gradle Wrapper. No Windows:

```powershell
cd android
.\gradlew.bat assembleDebug
```

Em macOS ou Linux:

```sh
cd android
./gradlew assembleDebug
```

APK gerado: `android/app/build/outputs/apk/debug/app-debug.apk`. O arquivo ONNX usa Git LFS; execute `git lfs pull` após clonar para obter os pesos reais antes de compilar.

O build falha com mensagem clara se o token não estiver configurado. Não use `pnpm build`: esta branch não possui um projeto web.
