# Antes de compartilhar

Aplicativo Android em Capacitor para localizar uma notícia pelo título ou analisar um link. O fluxo atual filtra URLs de opinião antes de mostrar o resultado e consulta o proxy de Fact Check no Render. A chave da API do Google fica no servidor.

## Fluxo atual

1. `src/App.tsx` recebe título ou URL e aplica `src/pipeline/opinionFilter.ts`.
2. `src/pipeline/localAnalysis.ts` busca candidatos na GDELT quando há título, abre a página escolhida e extrai texto no WebView.
3. O app consulta `public/data/atlas-domains.json`, chama `POST /fact-check` pelo cliente `src/pipeline/factCheckClient.ts` e tenta classificar a escrita com `src/pipeline/bertimbau.ts` e os arquivos de `public/models/writing_bertimbau/`.
4. O app monta uma explicação curta na tela.

O código atual ainda não reproduz integralmente a lógica de `sdd_v1`: não executa matching local das alegações, a agregação ponderada nem o resumo original. A busca e a extração por `fetch` no WebView também dependem de CORS dos serviços e veículos consultados. O carregamento dinâmico do runtime BERTimbau precisa ser validado no APK: hoje uma falha é convertida silenciosamente em resultado parcial. Esses pontos impedem considerar o fluxo Android validado de ponta a ponta.

## Configuração e build

```env
VITE_FACTCHECK_API_URL=https://challenge-1-andromeda-00o6.onrender.com
VITE_FACTCHECK_PROXY_TOKEN=valor_compartilhado_com_o_proxy
```

`VITE_FACTCHECK_PROXY_TOKEN` entra no APK e não deve ser tratado como segredo do Google. O servidor da branch `servidor_backend` mantém `GOOGLE_FACT_CHECK_API_KEY` e atende `POST /fact-check`.

```sh
pnpm install
pnpm build
pnpm test
pnpm exec cap sync android
pnpm exec cap open android
```

## Arquivos da branch

- `src/App.tsx` e `src/pipeline/`: interface e análise executada pelo app.
- `public/data/` e `public/models/`: Atlas exportado e modelo embarcado. O arquivo ONNX é versionado com Git LFS porque excede 100 MiB.
- `android/` e `capacitor.config.ts`: projeto Android Capacitor.
- `scripts/export_atlas.py`: exportação do snapshot local do Atlas; requer a base SQLite em `.data/`.
- `tests/app-flow.spec.ts` e `scripts/test-server.mjs`: verificação do fluxo da interface.

O código Python de `sdd_v1` e o proxy permanecem nas respectivas branches, fora desta branch do app.
