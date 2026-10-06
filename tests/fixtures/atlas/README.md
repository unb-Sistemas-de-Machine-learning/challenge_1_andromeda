# Amostra real sanitizada do Atlas

bbc_real.json foi obtido em 2026-10-05 de
`GET https://api.atlas.jor.br/api/v1/data/analytic?nome_veiculo[lk]=BBC`.
Somente identificação, flags e canal Site são mantidos; contatos, endereço,
anotações e demais relações foram removidos. Token nunca foi salvo.

O canal Site é ID 1, nome Site; o registro ativo é Online. O link é encurtado,
portanto a fixture sozinha não prova `bbc.com`: o teste simula explicitamente a
cadeia observada e a execução real a resolve novamente.

O contrato retorna array JSON, sem envelope de paginação, com media_channels
relacionados. A consulta completa observada de ativo=1/segmento=Online continha
6499 registros. A lista /media/online continha todos esses IDs, incluindo registros
com eh_jornal=0; por isso esse campo não é filtro de elegibilidade genérica.

Mudança de envelope, campos essenciais ou definições bloqueia a publicação.
