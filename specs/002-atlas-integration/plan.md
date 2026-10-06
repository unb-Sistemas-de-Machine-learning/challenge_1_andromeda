# Plano de implementação: API Atlas da Notícia

**Data:** 2026-10-05 | **Branch atual:** `sdd_v1`
**Feature:** `002-atlas-integration` | **Escopo:** [spec.md](spec.md)
**Status:** implementado; contrato real validado e índice sincronizado em 2026-10-05.
**Escopo adicional autorizado:** remoção do critério de alegações não implementado, incluindo frontend e contrato.

## Resumo

Criar cliente Atlas e sincronização explícita para um índice SQLite. Credibilidade
consulta o índice e a lista complementar local, sem chamada Atlas por notícia.
Reconhecimento permanece valendo até 35 pontos; cadastro não será apresentado como
certificação da veracidade. Pesos, transparência da página, regra de idade e veto
existentes permanecem. Blocklist continua independente.

## Contexto técnico

- Python 3.11+, FastAPI, httpx, Pydantic, tldextract e SQLite já utilizados.
- Serviço web com interface embutida, execução Windows/Linux; pytest/respx.
- Sem Redis, fila ou framework de agendamento.
- Meta proposta: consulta local em até 50 ms p95 com 50 mil vínculos, medida
  separadamente dos demais critérios; não é desempenho já observado.
- Política inicial configurável: atualização após 24 h, validade máxima de 7 dias;
  timeout HTTP de 20 s/operação em lote, até 2 novas tentativas, orçamento de 120 s por sync.
- Coleta serial; respeitar Retry-After. Se a espera exceder orçamento, encerrar.
- Limites: 32 MiB/resposta e 100 mil registros; excedentes geram erro.
  Ajustado após observar 21.168.083 bytes na consulta real sem seleção. Não truncar silenciosamente.

## Constitution Check

| Princípios | Atendimento antes e após o desenho |
|---|---|
| C01/C02/C06 | Origem, vínculo e versão da base gravados com cada análise |
| C03/C10 | Cadastro não significa comprovação factual |
| C04/C09 | Ausência, indisponibilidade e ambiguidade têm estados distintos |
| C05 | Atlas alimenta apenas reconhecimento, evitando dupla contagem editorial |
| C07 | Nenhum campo ou endpoint de domínio presumido; validar antes de ativar |
| C08 | Nova versão da regra; hashes da base e da lista local na auditoria |

Gates atendidos, sem exceções. Token público, array sem paginação, canal Site,
elegibilidade online ativa e cadeia oficial da BBC foram verificados na etapa 1.
O escopo de elegibilidade é cadastro Online ativo, não certificação de qualidade.

## Estrutura proposta

```text
API Atlas -> AtlasClient -> AtlasSync -> snapshot SQLite
                                            |
URL final -> domínio -> RecognitionProvider + lista local -> reconhecimento
                                            |
                                      evidência -> auditoria/UI

src/news_analysis/
  criteria/atlas_client.py          novo: transporte, autenticação, adaptação
  criteria/recognition.py           novo: contrato e composição de fontes
  criteria/source_credibility.py    substituir leitura direta do reconhecimento
  criteria/credibility_config.py    política centralizada
  criteria/credibility_io.py        preservar carregador local
  storage/atlas_repository.py       novo: snapshots e consulta
  storage/schema.py                migração aditiva
  atlas_sync.py                    novo: CLI sync/status
  config.py                        opções de ambiente
  api/dependencies.py              provedor compartilhado
  api/app.py                       evidência e estado na interface/config
  pipeline/models.py               evidências opcionais no envelope
  pipeline/analyzer.py             injeção e captura da evidência
  pipeline/version.py              versão das regras
```

## Etapas, entregas e dependências

### 1. Validar o contrato remoto

Conferir uma amostra real pequena: autenticação, envelope, completude/paginação,
flags de elegibilidade, canais e endereço oficial. Registrar fixtures sanitizadas
com data e mapeamento remoto -> interno. BBC é caso exploratório, sem presumir presença.
Não interpretar `eh_jornal` como elegibilidade genérica sem validar a semântica:
o campo pode representar segmento impresso.

**Gate:** sem vínculo oficial cadastro/site e elegibilidade demonstráveis, manter
Atlas desativado e documentar necessidade de exportação oficial ou curadoria dos
vínculos. Não reconhecer por nome, e-mail ou URL incidental de transparência.
**Entrega:** fixtures e contrato comprovado. Transporte e armazenamento podem ser
trabalhados com fixtures; adaptador e ativação dependem desta etapa.

### 2. Construir AtlasClient

Token público onde permitido; modo de conta apenas se explicitamente configurado.
Reutilizar token até expiração, renovar uma vez em 401, não repetir 403. Tratar
429/5xx/transporte com tentativas e orçamento limitados. Validar esquema e tamanho.
Não encaminhar Authorization a outra origem em redirects. Logs sem segredos,
contatos ou corpo bruto. Token e credenciais ficam exclusivamente no backend.

**Aceite:** expiração, 401/403/429/5xx, timeout, JSON inválido, esquema alterado,
resposta excessiva e redirect para origem diferente cobertos em testes.

### 3. Sincronizar snapshots SQLite

Usar SQLite existente com tabelas separadas. Normalizar URLs HTTP/HTTPS oficiais
com IDNA/PSL; rejeitar credenciais, IPs, canais sociais e hosts de plataformas
compartilhadas sem identidade de tenant comprovada. No MVP, excluir plataformas
compartilhadas do índice automático. Cada alias exige evidência: não inferir
`bbc.com` a partir de `bbc.co.uk`. Guardar todos os cadastros elegíveis de um domínio;
multiplicidade não aumenta pontos e conflitos reais geram ambiguidade.

Construir versão candidata, validar e promover numa transação. Esquema incompatível,
coleta parcial ou conjunto vazio inesperado não substituem versão ativa. Registrar
exclusões sem endereço oficial; cobertura incompleta impede inferir ausência ampla.
Leitores observam uma única versão. Lease no SQLite evita sync concorrente entre
processos e permite recuperação após expiração. Preservar versões referenciadas.

**Aceite:** interrupção, reinício, concorrência, cadastros removidos/inativos,
duplicatas e atualização incompleta mantêm consistência. Depende da etapa 2.

### 4. Integrar RecognitionProvider

Retorno: `matched`, `not_found`, `unavailable` ou `ambiguous`, mais evidências.
Correspondência válida Atlas OU local concede 35, apenas uma vez. Ausência só
produz zero quando todas as fontes habilitadas forem consultáveis e completas
para o escopo declarado. Sem match e alguma fonte falhou/é incompleta: indisponível.
Fonte não configurada é desabilitada; arquivo configurado ilegível é falha.
Ambiguidade não gera ponto automático; curadoria local pode resolver identidade
com origem explícita. Não transformar ausência no Atlas em blocklist.

Snapshot de 24 h a 7 dias é utilizável com aviso; mais antigo é indisponível.
Consultar com provedor compartilhado via dependencies: hoje cada request recria
NewsAnalyzer e SourceCredibility, perdendo caches em memória. Detectar snapshot
novo sem exigir reinício do serviço. Preservar a função pública
`calcular_score_fonte(url) -> dict` e suas chaves.

**Aceite:** matriz de estados, duas requisições reutilizando provedor, atualização
visível após sync e blocklist prevalecendo. Depende da etapa 3.

### 5. Integrar auditoria, UI e versão

Manter explicação em `criterios[].detalhe`. Evidência estruturada em campo opcional
`criteria.credibility_evidence` do envelope, mantendo o JSON independente do módulo.
Resultado interno deve devolver score e evidência juntos, sem `last_result` mutável
compartilhado. Registrar snapshot/hash, URL, IDs, regra e hash da lista local.
Não reutilizar `criteria.source_credibility`, reservado à migração de registros legados.
Não recalcular análises antigas. Mostrar fonte, data e aviso de base antiga na UI;
/config mostra estado sem segredos. Atualizar versão, contrato OpenAPI e documentação.

**Aceite:** persistência preserva evidência após novo snapshot; respostas antigas
renderizam; HTML é escapado; nenhum contato/token aparece. Depende da etapa 4.

### 6. Validar e ativar

Executar suíte offline, ponta a ponta com fixtures e benchmark. Smoke test remoto
explícito registra resultado e data. Habilitar somente após primeira sincronização
validada. Medir vínculos utilizáveis e exclusões. CLI poderá ser chamada por
agendador do ambiente, mas nenhuma automação é criada neste planejamento.
Rollback: desabilitar Atlas e manter provedor local, preservando histórico.

**Pronto quando:** requisitos da spec passam, nenhuma chamada Atlas ocorre na
análise de notícia, score/normalização/veto permanecem compatíveis, evidências são
auditáveis e a documentação cobre operação e recuperação.

## Artefatos de desenho

[Pesquisa](research.md) · [Modelo de dados](data-model.md) ·
[Contratos](contracts/atlas-integration.md) · [Validação](quickstart.md).

## Complexidade

Sem exceções constitucionais. Reutilizar dependências, SQLite e injeção existentes.
A execução e validação estão registradas em [tasks.md](tasks.md) e [implementation-results.md](implementation-results.md).
