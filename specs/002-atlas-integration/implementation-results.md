# Resultado da implementação — 2026-10-05

## Entregas

Cliente Atlas com token público/conta, renovação limitada, retries, orçamento e
validação de esquema. Adaptador de cadastro Online ativo e canal Site comprovado.
Resolução de encurtadores fora do fluxo de análise, sem JWT e com validação de destinos.
Snapshots SQLite com lease entre processos, promoção atômica e histórico.
CLI sync/status, reconhecimento Atlas/local, evidência autocontida e cache compartilhado.
API, auditoria e interface expõem origem e estado da base.

Critério reservado de alegações removido: fábrica, modelo, enum, assembly,
cartão frontend, schemas, testes específicos e documentação. Projeção de registros
históricos omite o campo antigo, sem recalcular nota nem modificar payload armazenado.

## Validação

- Suíte completa: **123 testes passaram**, com um aviso de depreciação do TestClient
  em dependência de terceiros. Sem downloads de modelos ou chamadas Atlas nos testes.
- Contrato remoto e amostra BBC confirmados; fixture sanitizada armazenada.
- Sync real: 6499 registros recebidos, 4796 com site utilizável, 1703 excluídos.
- 4451 domínios distintos no índice; múltiplos veículos/domínios não duplicam pontos.
- Snapshot: `7b9a7505-4d6b-4221-84e7-4551900f7bc6`.
- BBC BRASIL ID 14205: Site oficial encurtado -> bbcbrasil.com -> bbc.com/portuguese.
  Reconhecimento local de bbc.com confirmado, com evidências do snapshot.
- Benchmark isolado, 50 mil vínculos simulados e 200 consultas: p95 **4,883 ms**,
  meta <50 ms. Não é benchmark do pipeline/modelos nem promessa de desempenho em produção.
- `.env` local habilitado após sucesso do sync; arquivo e SQLite permanecem ignorados no Git.

## Ajustes justificados ao plano

O endpoint completo ultrapassou 20 MiB e o timeout inicial de 6 segundos.
Consulta Atlas em lote agora permite 32 MiB e timeout de 20 segundos, mantendo
orçamento total de 120 segundos e limites do módulo de página/RDAP independentes.
`eh_jornal` não é filtro genérico de elegibilidade: a definição oficial indica
“é um jornal”. Escopo registrado é cadastro Online ativo.

Recebimento do array é completo, mas cobertura de identidades é incompleta por
cadastros sem site utilizável. Correspondências comprovadas concedem os 35 pontos;
domínio ausente não recebe negativo abrangente enquanto essa lacuna existir.
Falhas preservam snapshot anterior. Nenhum contato/token é persistido.

## Operação

Reiniciar o servidor para carregar código/configuração novos. Sincronizações
posteriores são vistas sem reinício. Renovar o índice via comando documentado;
não há agendamento automático. Consulte [operação](../../docs/Atlas.md),
[smoke test](smoke-result.json) e [benchmark](benchmark-result.txt).
