# Integração Atlas da Notícia

A Credibilidade da fonte pode reconhecer veículos cadastrados no Atlas usando
um índice persistente de domínios. O índice é sincronizado automaticamente na
primeira análise válida de cada dia (horário de São Paulo). As análises seguintes
no mesmo dia consultam o SQLite e as listas locais configuradas sem repetir a
sincronização. O comando manual continua disponível para diagnóstico.

## Ativar e sincronizar

No `.env` da raiz, configure:

```text
NEWS_ANALYSIS_ATLAS_ENABLED=true
NEWS_ANALYSIS_ATLAS_AUTH_MODE=dummy
```

Esse modo utiliza o token público documentado, sem cadastro pessoal. Para uma
conta autorizada, use `account` e configure `NEWS_ANALYSIS_ATLAS_EMAIL` e
`NEWS_ANALYSIS_ATLAS_PASSWORD` no backend. Não publique essas credenciais.

```powershell
uv run python -m news_analysis.atlas_sync sync --dry-run
uv run python -m news_analysis.atlas_sync sync
uv run python -m news_analysis.atlas_sync status
uv run uvicorn news_analysis.api.app:app --reload
```

`--dry-run` valida sem promover a base. `status` lê apenas o estado local.
O SQLite é o mesmo definido em `NEWS_ANALYSIS_DB_PATH`. Reinicie o serviço após
mudar configuração; sincronizações posteriores ficam visíveis sem reinício.
Retornos CLI: 0 sucesso; 1 falha de sync; 2 configuração inválida; 3 sync concorrente.

## Correspondência com domínio

O contrato foi validado em 2026-10-05 com os endpoints públicos do Atlas. A coleta
usa `/data/analytic/definitions` e `/data/analytic`, filtrando `ativo=1` e
`segmento=Online`. Seleciona identificação, nome, segmento e estado; o endpoint
também fornece `media_channels`. Apenas canal de ID 1 e nome `Site` é usado como
endereço oficial. `eh_jornal` significa “é um jornal”; não é usado como avaliação
genérica de qualidade ou veracidade.

Normalização usa `tldextract` e IDNA. Nomes parecidos, e-mails, redes sociais e
links editoriais incidentais não reconhecem um domínio. Plataformas compartilhadas
são excluídas do reconhecimento automático. Cada alias exige URL oficial ou
redirecionamento observado a partir dela. A análise usa o domínio final da notícia.

Encurtadores conhecidos são resolvidos somente durante sync, com cliente sem JWT,
verificação de cada destino, limite de saltos e leitura apenas dos headers. O
resultado inclui a cadeia. O domínio do encurtador não recebe reconhecimento.

Na amostra real, BBC BRASIL, ID 14205, fornece um canal Site encurtado:
`t.co` → `bbcbrasil.com` → `bbc.com/portuguese`. A cadeia comprovada permite
reconhecimento de `bbc.com`. Isso depende da evidência da base sincronizada,
e não de um nome ou exceção fixa no código. A fixture sanitizada está em
`tests/fixtures/atlas/bbc_real.json`.

## Score e disponibilidade

Correspondência Atlas ou lista local concede 35 pontos uma única vez. Os demais
sinais e a regra de combinação da idade são mantidos. A blocklist permanece
independente e prioritária. Ausência no Atlas nunca gera blocklist.

Sem match, um negativo só é permitido quando todas as fontes habilitadas são
consultáveis e completas para o escopo declarado. Cadastros sem site ou links
não resolvidos tornam a cobertura de identidades incompleta: matches comprovados
continuam válidos, mas ausência não pode ser considerada negativa abrangente.
Arquivo local não configurado desabilita essa fonte; arquivo configurado inválido
é falha. Nenhuma fonte habilitada resulta em reconhecimento indisponível.

`criteria.credibility` conserva o formato SCORE_FONTE. O campo opcional
`criteria.credibility_evidence` registra fontes consultadas, evidência, IDs,
hashes, versão, data e frescor do índice. A interface mostra essa origem em
“Origem do reconhecimento da fonte”. Cadastro não certifica a veracidade.

## Limites e recuperação

Política central em `credibility_config.py`: renovação recomendada em 24 h,
validade máxima de 7 dias. Entre esses limites, usa cópia local com aviso. Uma
base expirada não concede pontos. Se a atualização diária falhar, a análise
continua usando a última base válida; o erro fica registrado no estado do Atlas.
Uma nova análise tenta sincronizar novamente. A primeira análise do dia pode
demorar enquanto a atualização ocorre.

Timeout de 20 s/operação na consulta Atlas em lote; orçamento de 120 s/sync; até duas novas tentativas;
resposta limitada a 32 MiB e 100 mil registros. Retry-After é respeitado; esperas
acima de 30 s encerram o comando para retomada posterior. O limite de resposta
foi ajustado após medir 21.168.083 bytes na consulta sem seleção de campos.
Até 20 links encurtados são resolvidos por execução; demais são excluídos com
contagem e cobertura incompleta. Sites normais não são baixados durante sync.

Uma lease SQLite evita concorrência entre processos; atualização é transacional.
Falha, esquema incompatível, vazio inesperado ou queda de registros acima de 50%
mantêm a versão anterior. Erro seguro fica disponível em `status`. Corrija a
causa e execute sync novamente. As versões anteriores e evidências das análises
são preservadas. Desative por `NEWS_ANALYSIS_ATLAS_ENABLED=false` para usar só
a lista local.

Tokens, contatos e respostas integrais não são persistidos. Os e-mails não são
exibidos. Crédito e links: [documentação](https://atlas.jor.br/api/documentacao-da-api/),
[definições dos campos](https://api.atlas.jor.br/docs),
[metodologia](https://atlas.jor.br/metodologia/intro/) e
[regras de uso](https://atlas.jor.br/api/regras-de-uso-da-api-do-atlas-da-noticia/).
