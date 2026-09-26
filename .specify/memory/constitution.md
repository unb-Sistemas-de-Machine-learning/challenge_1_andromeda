<!--
Sync Impact Report
Version change: N/A -> 1.0.0
Modified principles: N/A -> C01 Transparencia, C02 Rastreabilidade, C03 Nao inferencia indevida, C04 Ausencia de evidencia, C05 Independencia, C06 Explicabilidade, C07 Integridade, C08 Versionamento, C09 Cobertura, C10 Limitacao
Added sections: Core Principles, Restricoes de Analise, Fluxo de Desenvolvimento, Governance
Removed sections: None
Follow-up TODOs: None
-->

# Challenge 1 Andromeda Constitution

## Core Principles

### C01. Transparencia
Toda pontuacao produzida pelo sistema DEVE possuir uma origem identificavel e
uma regra de calculo documentada. A documentacao DEVE permitir reconstruir como
o valor foi obtido a partir dos dados disponiveis, dos criterios executados e da
versao da pipeline utilizada. A racionalidade deste principio e impedir que um
resultado numerico pareca mais objetivo do que o processo que o gerou.

### C02. Rastreabilidade
Toda analise DEVE registrar os dados, modelos, versoes e resultados utilizados.
O registro DEVE incluir entradas relevantes, criterios executados, componentes da
pipeline, pesos, regras e saidas intermediarias quando existirem. A racionalidade
deste principio e permitir auditoria, reproducao e comparacao entre execucoes.

### C03. Nao Inferencia Indevida
O sistema NAO DEVE apresentar uma predicao de modelo como certeza sobre a
veracidade da noticia. Qualquer predicao, escore ou classificacao DEVE ser
rotulada como estimativa limitada ao metodo, aos dados e aos criterios
disponiveis. A racionalidade deste principio e evitar que suporte computacional
seja confundido com verificacao factual definitiva.

### C04. Ausencia de Evidencia
Dados indisponiveis NAO DEVEM ser interpretados automaticamente como evidencia
negativa. Quando uma fonte, criterio ou dado nao estiver disponivel, a analise
DEVE registrar a indisponibilidade e excluir esse criterio do calculo ou aplicar
uma regra documentada de tratamento de ausencia. A racionalidade deste principio
e impedir penalizacoes indevidas causadas por lacunas de coleta.

### C05. Independencia
Cada criterio DEVE ser calculado independentemente dos demais antes da agregacao.
Dependencias entre criterios DEVEM ser declaradas explicitamente e justificadas
como parte da regra de calculo. A racionalidade deste principio e preservar a
interpretabilidade dos criterios e evitar dupla contagem de um mesmo sinal.

### C06. Explicabilidade
O resultado final DEVE permitir identificar a contribuicao de cada criterio
disponivel. A apresentacao da analise DEVE separar criterio, valor, regra,
origem e impacto na agregacao. A racionalidade deste principio e permitir que
usuarios e revisores entendam quais evidencias influenciaram o indice final.

### C07. Integridade
O sistema NAO DEVE inventar fontes, evidencias, avaliacoes ou resultados.
Qualquer informacao ausente, incerta, nao consultada ou com falha de processamento
DEVE ser declarada como tal. A racionalidade deste principio e proteger a
confiabilidade do sistema e evitar fabricacao de suporte analitico.

### C08. Versionamento
Alteracoes em modelos, pesos, regras ou dependencias DEVEM gerar uma nova versao
identificavel da pipeline. Cada resultado armazenado ou apresentado DEVE apontar
para a versao da pipeline que o produziu. A racionalidade deste principio e
garantir que resultados antigos possam ser interpretados corretamente mesmo apos
mudancas metodologicas.

### C09. Cobertura
O sistema DEVE informar quais criterios foram efetivamente executados na analise.
A cobertura DEVE diferenciar criterios executados, criterios indisponiveis,
criterios ignorados por regra e criterios com erro. A racionalidade deste
principio e tornar explicito o alcance real de cada resultado.

### C10. Limitacao
O indice final NAO DEVE ser interpretado como probabilidade de a noticia ser
verdadeira ou falsa. O indice DEVE ser apresentado como uma medida operacional
dos criterios executados e das regras documentadas da pipeline. A racionalidade
deste principio e evitar conclusoes epistemicas mais fortes que as evidencias e
o metodo permitem.

## Restricoes de Analise

O sistema existe para apoiar avaliacao de confiabilidade de noticias, nao para
substituir verificacao jornalistica, decisao humana ou checagem factual completa.
Toda interface, relatorio, documentacao e avaliacao do projeto DEVE respeitar as
limitacoes dos criterios disponiveis, dos dados coletados e dos modelos usados.

Qualquer componente de machine learning DEVE ser tratado como uma fonte limitada
de sinal, sujeita a erro, vies, mudanca de distribuicao e dependencia dos dados
de treinamento. Nenhum componente DEVE ocultar suas fontes, regras, parametros
ou versoes quando essas informacoes forem necessarias para explicar o resultado.

## Fluxo de Desenvolvimento

Toda nova funcionalidade que altere coleta de dados, criterios, modelos, pesos,
regras de agregacao, apresentacao do indice ou persistencia de resultados DEVE
explicitar seu impacto sobre transparencia, rastreabilidade, explicabilidade,
cobertura e versionamento.

Mudancas na pipeline analitica DEVEM incluir validacao minima que demonstre:
origem dos dados usados, criterios executados, tratamento de ausencia de
evidencia, resultado por criterio, resultado agregado e versao da pipeline. Uma
mudanca que reduza rastreabilidade, invente informacao, confunda predicao com
certeza ou oculte cobertura NAO DEVE ser aceita.

## Governance

Esta constituicao governa decisoes de especificacao, planejamento,
implementacao, avaliacao e apresentacao de resultados do projeto. Em caso de
conflito, esta constituicao prevalece sobre praticas locais, conveniencia de
implementacao ou simplificacoes de interface.

Emendas DEVEM ser registradas neste arquivo com justificativa, impacto esperado
e incremento de versao semantica. A versao MAJOR muda quando principios de
governanca sao removidos ou redefinidos de forma incompativel; a versao MINOR
muda quando principios ou secoes sao adicionados ou materialmente expandidos; a
versao PATCH muda para clarificacoes, correcao de texto ou ajustes sem mudanca
semantica.

Antes de aceitar mudancas que afetem a pipeline de analise, a revisao DEVE
verificar conformidade com todos os principios aplicaveis. Qualquer excecao DEVE
ser documentada com escopo, motivo, risco e plano de correcao.

**Version**: 1.0.0 | **Ratified**: 2026-09-26 | **Last Amended**: 2026-09-26
