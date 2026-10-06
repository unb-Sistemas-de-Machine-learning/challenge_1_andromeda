# Antes de compartilhar

Protótipo responsivo de um fluxo guiado para avaliar informações antes de compartilhar. React, TypeScript e Vite. Sem cadastro, backend ou verificação real.

## Executar

```sh
npm install
npm run dev
```

## Validar

```sh
npm run build
npx playwright install chromium
npm test
```

Os testes cobrem o filtro de entrada e de opinião (`tests/pipeline.spec.ts`) e os três resultados, abertura das fontes, campo vazio, carregamento, falha com conteúdo preservado, recuperação, entrada arbitrária e refluxo em tela de 320 px com texto ampliado. Incluem auditorias automatizadas com axe para WCAG A/AA nas telas de entrada e resultado. São executados em Chromium com tamanhos de desktop e celular; não substituem testes manuais com leitores de tela ou outros navegadores.

## Fluxo demonstrativo

- “Ver um exemplo” preenche o cenário sustentado. Os três botões abaixo permitem escolher os demais cenários.
- Somente a correspondência exata com os exemplos fictícios seleciona os resultados preparados. Outros textos e links recebem o cenário de evidências insuficientes, explicitamente simulado.
- Links enviados não são acessados e não há consulta à internet. As fontes são documentos locais fictícios, abertos em outra aba para preservar o resultado.
- “Testar uma falha de verificação” permite provocar um erro recuperável. A opção é desativada depois da falha para que “Tentar novamente” funcione.
- A espera de 1,4 segundo demonstra o estado de carregamento; não representa pesquisa real.

## Pipeline de entrada → filtro → ML

1. **Entrada** (`src/pipeline/input.ts`): `parseInput` identifica se o conteúdo é um link (com ou sem `https://`) ou um texto. Rejeita entrada vazia, textos com menos de 5 palavras ou mais de 20 mil caracteres e protocolos que não sejam http(s).
2. **Filtro de opinião** (`src/pipeline/opinionFilter.ts`): `classifyContent` aplica Regex sobre o texto normalizado (sem acentos, minúsculo e sem trechos entre aspas, que são falas de terceiros) ou sobre o domínio e o caminho do link. Cada sinal soma pontos e, a partir de 3, o conteúdo é tratado como opinião e bloqueado com a lista de motivos.
   - Bloqueiam sozinhos: rótulos como “Opinião:”, “Editorial” ou “Artigo de opinião”, avisos de responsabilidade do autor, “na minha opinião” / “a meu ver” e links para `/opiniao/`, `/colunas/` ou `blog`.
   - Precisam de reforço: “acho que” / “acredito que” (2 pontos), juízos de valor, prescrições como “deveria” e marcadores retóricos (1 ponto cada).
3. **ML** (`src/pipeline/mlClient.ts`): `sendToMl` faz `POST` com `{ "type": "text" | "url", "content": string }` para `VITE_ML_API_URL` (tempo limite de 30 s) e espera um JSON no formato `Analysis`. Quando o formato real for definido, o único ponto a ajustar é `toAnalysis`. Sem a variável, a simulação local continua sendo usada.

`src/pipeline/index.ts` (`screenInput`) junta as etapas 1 e 2. A interface só chama `sendToMl` quando o resultado é `accepted`.

Para apontar para o serviço real, crie `.env.local`:

```sh
VITE_ML_API_URL=http://localhost:8000/predict
```

Limitações: a heurística é baseada em palavras e pode errar, tanto deixando passar opiniões escritas em tom neutro quanto bloqueando notícias atípicas. Para links, apenas o endereço é analisado, pois o conteúdo da página não é baixado no navegador.

## Estrutura

- `src/App.tsx`: interface, navegação entre estados, foco e mensagens acessíveis.
- `src/components.tsx`: aviso de demonstração e lista de fontes reutilizáveis.
- `src/analysis.ts`: contrato `Analysis`, exemplos e a simulação `analyzeNews`, usada quando não há serviço de ML configurado.
- `src/pipeline/`: camada entre a interface e a ML (ver abaixo).
- `src/styles.css`: aparência responsiva, foco visível e adaptação para telas pequenas.
- `public/fontes/`: material fictício consultável.
- `tests/flow.spec.ts`: testes de ponta a ponta.

Os textos enviados ficam apenas no estado em memória da aplicação atual, sem implementação de persistência. Isso não constitui uma promessa de privacidade ou segurança. A fonte DM Sans é carregada do Google Fonts com fallback para Arial/sans-serif. Todos os cenários e a instituição Vila Serena foram criados para a demonstração e não atribuem declarações a pessoas reais.
