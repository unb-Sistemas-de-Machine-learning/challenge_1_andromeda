# Pesquisa e decisões — 2026-10-05

## Fontes consultadas

- [Documentação oficial](https://atlas.jor.br/api/documentacao-da-api/).
- [Regras de uso](https://atlas.jor.br/api/regras-de-uso-da-api-do-atlas-da-noticia/).
- [Metodologia](https://atlas.jor.br/metodologia/intro/).
- Código atual: criteria/source_credibility.py, credibility_io.py,
  api/dependencies.py e storage/audit_repository.py.

A API documenta token público em `/auth/dummy-jwt`, busca online por nome,
dados em `/data/analytic` e respectivas definições. O exemplo de `/media/online`
não fornece URL. `/media/verified` é um subconjunto com critérios de transparência;
não substitui automaticamente o universo de cadastros.

## Decisões

### Contrato remoto

**Decisão:** contrato interno independente; adaptador condicionado à validação de
endereço oficial e elegibilidade em respostas reais. Na implementação, o acesso
externo foi validado e a fixture real sanitizada da BBC foi registrada.
**Motivo:** impedir associação de domínio inventada.
**Alternativas:** usar nome ou link editorial incidental foi rejeitado. Caso o
contrato público não ofereça vínculo suficiente, usar exportação oficial ou
curadoria explícita, mantendo modo Atlas desativado até comprovação.

### Persistência

**Decisão:** sincronização explícita para SQLite, atualização atômica, consulta local.
**Motivo:** previsibilidade, sobrevivência a reinícios e menor carga externa.
**Alternativas:** consultar por notícia aumenta latência; cache só em memória é
insuficiente, pois get_analyzer recria o serviço em cada requisição.

### Semântica

**Decisão:** Atlas alimenta reconhecimento; verificação editorial remota não soma
pontos adicionais de transparência. Preservar 35 pontos da política atual.
**Motivo:** evitar dupla contagem e distinguir cadastro de veracidade.
**Alternativas:** exigir /media/verified mudaria a regra e excluiria cadastros
sem essa avaliação; fica fora da primeira integração.

### Cobertura

**Decisão:** positivo válido pode vir de uma fonte; negativo exige todas as fontes
habilitadas consultáveis no escopo. Erro parcial sem match é indisponível.
**Motivo:** não transformar falta de evidência em evidência negativa.
**Alternativa rejeitada:** lista vazia como fallback de falhas.

### Operação e minimização

**Decisão:** token público primeiro, conta apenas configurada; manter token no
backend. Salvar somente identificação e evidência necessária, sem e-mails.
**Motivo:** regras de uso recomendam cache e proíbem exibição pública de e-mails.
**Alternativa rejeitada:** persistir respostas integrais ou autenticar no navegador.

## Gate operacional, não suposição

Gate atendido em 2026-10-05: respostas públicas são arrays, `media_channels`
inclui `channel_id=1`, `channel.id=1`, `channel.name=Site` e `link` oficial.
`ativo=1` e `segmento=Online` delimitam a coleta. `/media/online` inclui todos os
6499 IDs da consulta filtrada, inclusive 708 com `eh_jornal=0`. A definição oficial
desse campo em /docs é “é um jornal”; não é certificado jornalístico genérico.
BBC BRASIL tem ID 14205 e canal encurtado cuja cadeia real termina em bbc.com.
A coleta de identidades é incompleta onde não há site utilizável: isso impede
inferências negativas abrangentes e não impede correspondências comprovadas.
