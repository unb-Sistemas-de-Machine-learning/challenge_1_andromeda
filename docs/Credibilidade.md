# Credibilidade da fonte (SCORE_FONTE)

A integração Atlas é descrita em [Integração Atlas](Atlas.md).

O módulo independente `news_analysis.criteria.source_credibility` expõe
`calcular_score_fonte(url) -> dict`, com as chaves solicitadas no prompt:
`url_original`, `url_final`, `dominio`, `score_fonte`, `confianca_fonte`,
`criterios`, `flags`, `veto_dominio_suspeito` e `erros`.

```python
from news_analysis.criteria.source_credibility import calcular_score_fonte
resultado = calcular_score_fonte('https://example.com/noticia')
```

## Configuração e bases locais

Instale com `pip install -r requirements.txt` ou `uv sync --extra dev`.
Pesos, faixas (em dias), TLDs, timeout, TTLs, limites e caminhos ficam em
`credibility_config.py`. O módulo usa Python 3.10+; o serviço mantém Python 3.11+.
Para uma configuração própria:

```python
from pathlib import Path
from news_analysis.criteria.credibility_config import CredibilityConfig
from news_analysis.criteria.source_credibility import SourceCredibility

scorer = SourceCredibility(CredibilityConfig(
    recognized_path=Path('dados/veiculos.json'),
    blocklist_path=Path('dados/desinformacao.csv'),
))
resultado = scorer.calculate('https://example.com/noticia')
```

JSON: lista de strings de domínios. CSV: coluna `dominio`. Subdomínios são
convertidos para o domínio registrável. As listas devem ser curadas pelo operador;
nenhum veículo foi inventado ou rotulado neste repositório. O Atlas usa um índice
SQLite sincronizado conforme [Atlas](Atlas.md). Arquivo local configurado ausente
ou inválido gera indisponibilidade dessa fonte; arquivo não configurado a desabilita.
Uma lista vazia válida indica ausência de correspondências naquela base.

No serviço, configure `.env` ou variáveis de ambiente:

```text
NEWS_ANALYSIS_RECOGNIZED_DOMAINS=dados/veiculos.json
NEWS_ANALYSIS_MISINFORMATION_DOMAINS=dados/desinformacao.csv
```

## Regras e integração

Reconhecimento: 40; transparência: autor 12, data 6, link Sobre/Contato 12;
idade: 25; HTTPS validado: 5. Esses quatro critérios somam 100 pontos. Um domínio
institucional confirmado acrescenta 30 pontos de bônus, limitados pela nota máxima
de 100; domínio não institucional não perde pontos. Idade usa intervalos
semiabertos de 30, 183, 730 e 1826 dias. Sem reconhecimento ou 18 pontos
editoriais, idade fica limitada a 13. Domínio com menos de 30 dias gera flag.

A nota é a soma dos pontos confirmados na base fixa de 100, mais o bônus quando
aplicável, com teto de 100. Sinais indisponíveis não recebem pontos e permanecem
identificados como indisponíveis, sem serem apresentados como evidência negativa.
Confiança mede a cobertura dos quatro sinais principais: baixa abaixo de 50%, média de 50% até menos de 80%,
alta a partir de 80%. Se nenhum critério puder ser avaliado, retorna
`score_fonte: null`, confiança baixa e veto falso. Indisponibilidade não é evidência
negativa. Uma nota disponível menor que 20 aciona o veto; uma correspondência
comprovada na blocklist prevalece, produzindo zero e veto mesmo se a página falhar.

A API e a auditoria incluem `criteria.credibility`, e a tela mostra explicações,
flags e falhas. A fonte tem peso previsto de 20% na média; checagem factual tem
65% e escrita tem 15%. Um critério indisponível sai da média e os pesos restantes
são renormalizados. O motor aplica `min(nota, 35)` quando há veto. As contribuições
representam a média anterior ao teto, explicitado na fórmula.
`final.score_before_veto` registra essa média; `final.source_veto_applied` informa
se o teto foi aplicado a uma nota existente. A nota final só é nula quando os três
critérios estão indisponíveis, mesmo quando houver veto da fonte.

`criteria.credibility_evidence` registra a política efetiva e seu hash, estado e
hash dos bytes consultados da blocklist, domínios correspondentes e motivo do veto
(`blocklist_match`, `score_below_threshold`, `source_unavailable` ou
`score_above_threshold`). A versão da pipeline inclui o hash da política, sem
credenciais nem caminhos locais. Hashes de bases identificam os dados utilizados;
não são substitutos para conservar as versões das listas curadas.

Consulte a [decisão de reconciliação do merge](DecisaoCredibilidade.md) para a
compatibilidade com análises históricas que usavam a média 50/30/20.

## Exemplos reproduzíveis

Execute `python examples/credibilidade.py`. O exemplo usa somente dados simulados,
sem rede, e imprime o JSON completo de três URLs fictícias. Todos têm autor,
data, contato, HTTPS e 3000 dias de idade:

| URL fictícia | Base local simulada | Score | Veto |
|---|---|---|---|
| https://jornal.example.com/noticia | Reconhecido | 100 | false |
| https://portal.example.net/noticia | Não reconhecido | 60 | false |
| https://boato.example.org/noticia | Blocklist | 0 | true |

Todos têm confiança alta e nenhum erro. No terceiro, a flag é
`dominio_em_lista_desinformacao`. Asserções no exemplo validam as notas esperadas.

## Limitações

- A cobertura depende do índice Atlas e das listas locais; falhas e lacunas são explícitas.
- Idade usa RDAP: para `.br`, o [servidor do Registro.br registrado na IANA](https://www.iana.org/domains/root/db/br.html);
  nos demais, o [bootstrap RDAP.org](https://about.rdap.org/). Dados ocultos,
  rate limits e falhas tornam idade indisponível. Não há fallback WHOIS de porta 43.
- A análise opcional de troca de dono via Wayback não foi implementada.
- Metadados e links podem ser falsificados. A página de contato é identificada
  por link do mesmo domínio, sem comprovar seu conteúdo ou a identidade do autor.
- O cache de idade dura 24 horas por domínio; HTML dura 5 minutos por URL,
  evitando aplicar autoria/data de uma notícia a outra. Cache é local ao processo
  e limitado a 512 entradas; falhas não são armazenadas. Listas são relidas.
- Falha ao resolver a página impede atribuir metadados ao destino com segurança;
  os critérios afetados ficam indisponíveis. Rede usa timeout de 6 segundos por
  operação, até 5 redirecionamentos e limite de 5 MB por resposta.
- A Public Suffix List vem com `tldextract`; atualize a dependência para atualizar
  essa base. Os sinais não são prova da veracidade de uma notícia.
