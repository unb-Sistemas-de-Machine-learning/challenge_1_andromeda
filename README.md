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

Os 16 testes cobrem os três resultados, abertura das fontes, campo vazio, carregamento, falha com conteúdo preservado, recuperação, entrada arbitrária e refluxo em tela de 320 px com texto ampliado. Incluem auditorias automatizadas com axe para WCAG A/AA nas telas de entrada e resultado. São executados em Chromium com tamanhos de desktop e celular; não substituem testes manuais com leitores de tela ou outros navegadores.

## Fluxo demonstrativo

- “Ver um exemplo” preenche o cenário sustentado. Os três botões abaixo permitem escolher os demais cenários.
- Somente a correspondência exata com os exemplos fictícios seleciona os resultados preparados. Outros textos e links recebem o cenário de evidências insuficientes, explicitamente simulado.
- Links enviados não são acessados e não há consulta à internet. As fontes são documentos locais fictícios, abertos em outra aba para preservar o resultado.
- “Testar uma falha de verificação” permite provocar um erro recuperável. A opção é desativada depois da falha para que “Tentar novamente” funcione.
- A espera de 1,4 segundo demonstra o estado de carregamento; não representa pesquisa real.

## Estrutura

- `src/App.tsx`: interface, navegação entre estados, foco e mensagens acessíveis.
- `src/components.tsx`: aviso de demonstração e lista de fontes reutilizáveis.
- `src/analysis.ts`: contrato `Analysis`, exemplos e função assíncrona `analyzeNews`, separada da apresentação. A integração futura pode substituir essa função mantendo o contrato.
- `src/styles.css`: aparência responsiva, foco visível e adaptação para telas pequenas.
- `public/fontes/`: material fictício consultável.
- `tests/flow.spec.ts`: testes de ponta a ponta.

Os textos enviados ficam apenas no estado em memória da aplicação atual, sem implementação de persistência. Isso não constitui uma promessa de privacidade ou segurança. A fonte DM Sans é carregada do Google Fonts com fallback para Arial/sans-serif. Todos os cenários e a instituição Vila Serena foram criados para a demonstração e não atribuem declarações a pessoas reais.
