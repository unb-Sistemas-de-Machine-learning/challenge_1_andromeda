# Escopo: integração Atlas da Notícia

Data: 2026-10-05. Implementado e validado com contrato real e testes offline.
Escopo atualizado pelo usuário: remover completamente o critério de alegações não implementado.

## Objetivo

Reconhecer o domínio final da notícia por associação verificável a cadastro Atlas,
com lista local complementar e resultado transparente no módulo Credibilidade.

## Requisitos e aceitação

- FR01: contrato remoto validado por fixtures reais sanitizadas antes de ativar.
- FR02: 35 pontos somente para domínio ligado a cadastro ativo/elegível ou lista curada.
- FR03: nome, e-mail e links incidentais não comprovam endereço oficial.
- FR04: índice persistente e atualização atômica; zero chamadas Atlas por notícia.
- FR05: separar correspondência, ausência consultável, indisponibilidade e ambiguidade.
- FR06: auditar fonte, IDs, endereço de evidência, versão e instante da base consultada.
- FR07: erro, coleta parcial ou falta de permissão não equivalem a lista vazia.
- FR08: preservar pesos, idade, veto e blocklist; evitar dupla contagem editorial.
- FR09: análises históricas continuam legíveis sem recálculo.
- FR10: entregar CLI sync/status, diagnóstico, testes offline e smoke test explícito.
- FR11: remover módulo reservado de alegações, contrato e cartão do frontend; preservar leitura histórica sem expor o campo removido.

## Cenários

1. Correspondência confirmada recebe 35 pontos e evidência.
2. Nome parecido sem domínio comprovado não recebe reconhecimento.
3. Falha remota mantém snapshot válido; sem base válida o critério é indisponível.
4. Atualização parcial mantém snapshot anterior; reinício não elimina a base.
5. Blocklist prevalece sobre reconhecimento positivo.
6. BBC é caso exploratório: não prometer presença ou reconhecimento sem verificação.

## Fora do escopo

Escrever na API Atlas, criar blocklist por ausência no Atlas, alterar Google Fact
Check/BERTimbau ou implementar alegações automáticas e agendamento de infraestrutura.
