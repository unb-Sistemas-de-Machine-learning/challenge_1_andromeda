# Modelo de dados proposto

## atlas_snapshots

`id` UUID, `created_at`, `completed_at`, `expires_at` em UTC; `state`
(building/active/superseded/rejected), `schema_version`, `mapping_version`,
`content_hash`, `endpoint`, `scope`, `complete`, `received_count`,
`accepted_count`, `excluded_count` e `exclusion_reasons` agregados.
Snapshot elegível precisa ter coleta completa e conteúdo validado. Retenção
preserva versões referenciadas por auditorias; sem exclusão automática no MVP.

## atlas_domain_links

Chave composta `(snapshot_id, atlas_id, domain, official_url)`; nome do veículo,
domínio ASCII canônico, host original, URL oficial, estado ativo e evidência de
elegibilidade. Índice `(snapshot_id, domain)` para leitura. Relação N:N entre
domínios e veículos; multiplicidade legítima não soma pontos.
Datas de atualização remotas só são registradas se fornecidas.

## atlas_sync_state

Registro único: active_snapshot_id, last_attempt_at, last_success_at,
last_error_code sanitizado, lease_owner e lease_expires_at. Promoção do ponteiro
e mudança de estados em uma transação. Snapshot anterior permanece em caso de erro.

## RecognitionResult (interno)

`status`: matched/not_found/unavailable/ambiguous; `domain`, `checked_at`,
`providers`, `evidence`, `reason_code`. Para cada provedor: habilitação, cobertura,
snapshot/hash, data e estado de frescor. Evidência inclui fonte Atlas/local, ID
quando aplicável, URL oficial e método de correspondência.

## Persistência na análise

Campo opcional `criteria.credibility_evidence`, com cópia autocontida da decisão e
evidências. `criteria.credibility` conserva o resultado SCORE_FONTE existente.
Persistência usa payload_json; modelos e contrato recebem campo opcional para
compatibilidade. Nunca usar `criteria.source_credibility`, chave histórica de
checagem factual. Lista local também tem hash e domínio utilizado registrados.

## Validações e transições

- Building -> active somente após validação; active anterior -> superseded.
- Building -> rejected em falha; active anterior inalterado.
- Domínio vem de URL oficial, nunca de e-mail/nome; hosts compartilhados sem
  associação por tenant comprovada não recebem reconhecimento automático.
- Snapshot acima da idade máxima não sustenta decisão; indisponibilidade é explícita.
- Nenhum token, contato, texto integral de notícia ou corpo remoto bruto é armazenado.
