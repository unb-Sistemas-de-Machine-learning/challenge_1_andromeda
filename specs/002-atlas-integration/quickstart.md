# Roteiro de validação após implementação

Os comandos atlas_sync e os testes estão implementados. Preparação: Python do projeto, dependências `uv sync --extra dev`,
SQLite gravável, adaptador remoto aprovado na etapa 1 e ambiente de teste isolado.

## Offline

1. Executar `uv run pytest` com fixtures remotas sanitizadas, sem rede.
2. Cobrir autenticação/erros, IDN/subdomínio/imitador, aliases, domínio compartilhado,
   registro inativo, conflito, normalização e composição Atlas/local.
3. Testar candidato incompleto, rollback transacional, concorrência e lease expirado.
4. Simular duas análises, reiniciar serviço e confirmar persistência do reconhecimento.
5. Trocar snapshot, verificar nova leitura e auditoria antiga inalterada.
6. Aplicar blocklist ao domínio reconhecido: SCORE_FONTE zero e veto preservados.
7. Medir consulta local p95 com 50 mil vínculos; não incluir rede/modelos no benchmark.

## Smoke test explícito com rede

No PowerShell, após implementação:

```powershell
$env:NEWS_ANALYSIS_ATLAS_ENABLED = 'true'
$env:NEWS_ANALYSIS_ATLAS_AUTH_MODE = 'dummy'
uv run python -m news_analysis.atlas_sync sync --dry-run
uv run python -m news_analysis.atlas_sync sync
uv run python -m news_analysis.atlas_sync status
```

Não promover se contrato/volume/completude falharem. Confirmar quantidade de vínculos,
exclusões, snapshot/hash e horário. Não afirmar que dry-run sozinho prova o vínculo
BBC: conferir a URL oficial e ID real no registro sanitizado.

## Ponta a ponta

Iniciar API, analisar notícia de domínio comprovado e consultar GET /analyses/{id}.
Esperar 35 no reconhecimento, origem/data visíveis e evidência persistida. Monitorar
cliente Atlas injetado: nenhuma chamada durante análise. Com erro de sync, versão
válida anterior continua utilizável; após expiração e sem match local, reconhecimento
fica indisponível e normalizado fora do denominador. Ausência não gera blocklist.

## Recuperação

Corrigir acesso/esquema, executar sync novamente e confirmar nova versão ativa.
Para desativar, configurar ATLAS_ENABLED=false com o prefixo documentado e reiniciar
configuração do serviço; lista local continua funcionando. Preservar snapshots
referenciados e análises antigas. Não publicar e-mails, senhas ou JWTs no relatório.
