# Contratos propostos

Interfaces implementadas em 2026-10-05.

## CLI

`python -m news_analysis.atlas_sync sync [--dry-run]`

Coleta e valida; dry-run não promove snapshot. Saída JSON: status, snapshot_id
(se criado), fetched_at, received_count, accepted_count, excluded_count,
error_code. Exit 0 sucesso; 1 falha; 2 configuração inválida; 3 execução concorrente.
Falha preserva versão ativa. Não emitir contatos ou respostas brutas.

`python -m news_analysis.atlas_sync status`

Exibe habilitação, versão ativa, última tentativa/sucesso, idade, validade e erro
sanitizado. Não chama o Atlas. Não expor endpoint público de sincronização.

## Configuração proposta

`NEWS_ANALYSIS_ATLAS_ENABLED=false` por padrão até configuração;
`NEWS_ANALYSIS_ATLAS_AUTH_MODE=dummy|account`; conta usa
`NEWS_ANALYSIS_ATLAS_EMAIL` e `NEWS_ANALYSIS_ATLAS_PASSWORD` apenas no backend.
Timeout, tentativas, limites e validade ficam em credibility_config.py; Settings
somente converte opções de ambiente para a configuração central. SQLite reutiliza
NEWS_ANALYSIS_DB_PATH. Base remota fixa em HTTPS; sem URL remota arbitrária do usuário.

## Contrato interno

`RecognitionProvider.lookup(domain: str) -> RecognitionResult` não acessa rede.
`AtlasClient` entrega registros normalizados segundo adaptador validado na etapa 1.
`SourceCredibility` recebe provedor por injeção. Operação interna retorna score e
evidências juntos. `calcular_score_fonte(url)` mantém somente as chaves públicas
originais e usa detalhe para a explicação textual.

## API/interface

POST /analyses e GET /analyses/{id} continuam com semântica atual; novo campo
opcional `criteria.credibility_evidence`. Registros anteriores podem omiti-lo.
GET /config pode adicionar `atlas_enabled`, `atlas_status`, `atlas_last_success_at`.
Não expor segredos. Texto UI: cadastro identificado, fonte local, não localizado
nas bases consultáveis, consulta indisponível ou vínculo ambíguo, conforme estado.
Escape de HTML e links com esquema HTTP/HTTPS validado.

## Matriz de decisão

| Atlas | Local habilitada | Resultado |
|---|---|---|
| Match válido | Qualquer | matched, 35 |
| Falha/expirado | Match curado | matched, 35, origem local e falha registrada |
| Completo, sem match | Completa, sem match | not_found, 0 |
| Falha/parcial | Sem match | unavailable, excluído do cálculo |
| Desabilitado | Completa, sem match | not_found, 0 |
| Sem fontes habilitadas | — | unavailable |
| Vínculo conflitante | Sem curadoria que resolva | ambiguous, indisponível |

Falha de fonte configurada não equivale a fonte desabilitada. Ausência só afirma
resultado no escopo consultado. Blocklist continua prevalecendo sobre qualquer match.
