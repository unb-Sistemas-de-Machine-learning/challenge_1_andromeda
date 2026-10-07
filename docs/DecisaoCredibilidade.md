# Reconciliação de Atlas e credibilidade

Decisão de 2026-10-06, implementada a partir de `analysis-rules-v6-source-abstention-history`.

> Esta decisão registra a política anterior. A política atual usa 65% para
> checagem factual, 20% para credibilidade da fonte e 15% para estilo de escrita,
> com renormalização dos critérios disponíveis e veto da fonte preservado.

O commit `dedfb5c` (Docs Atlas) introduziu implementação, API, persistência e
documentação da integração Atlas. O merge `e8cfb1d` (merge fake) registrou
`ba9d9ff` como segundo pai, mas preservou integralmente a árvore de `dedfb5c`.
As mudanças da outra linha de desenvolvimento não foram integradas.

## Política adotada para novas análises

- A média usa fatos verificáveis (60%) e escrita (40%), com renormalização quando
  um deles estiver indisponível. Nenhum disponível significa nota final nula.
- SCORE_FONTE é independente e não recebe peso adicional na média.
- Fonte com nota disponível menor que 20 ou domínio comprovado na blocklist
  limita a nota final existente a 35. Fonte totalmente indisponível não aciona veto.
- Cobertura final mede somente a execução de fatos e escrita (100/60/40/0).
  A confiança da fonte mede separadamente a cobertura de seus próprios sinais.
- Contribuições e `score_before_veto` descrevem a média antes do teto;
  `score` contém o resultado após o teto e `source_veto_applied` registra a aplicação.

Essa política preserva a integração Atlas e formaliza sua combinação com a média.
O modelo alternativo de metadados com pesos 50/30/20 não é usado para novas análises.
As dependências de documentação continuam em `requirements-docs.txt`, utilizado
pelo workflow de publicação; a aplicação usa `pyproject.toml`/`requirements.txt`.

## Compatibilidade histórica

Há dois significados históricos para `source_credibility`:

1. Formatos antigos de checagem factual possuem `reviews_count` e não possuem
   `signals`. Sem `verifiable_facts` existente, são projetados para essa chave.
2. A versão v4 de metadados possui `signals` e coexiste com `verifiable_facts`.
   É preservada em `criteria.source_credibility`, exclusivamente para leitura
   histórica, com pesos, contribuições, fórmula, nota e versão originais.

Nenhum registro armazenado é reescrito ou recalculado. A interface distingue o
cartão histórico de metadados da checagem factual. Campos novos de auditoria não
são inventados para registros antigos que não os possuam.

## Rastreabilidade e validação

Novas análises registram a política efetiva e seu hash, evidências Atlas/lista
local, hash e estado da blocklist e motivo estruturado do veto. Credenciais e
caminhos locais não entram no hash de política nem nas evidências.

Os testes de regressão abrangem leitura v4 pela API sem alterações no banco,
compatibilidade factual antiga, falha total da fonte sem veto, blocklist mesmo
com falha de rede, atualização de bases, versionamento da política e interface.
