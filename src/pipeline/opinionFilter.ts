// Etapa 2 do pipeline: heurística por Regex que separa notícias de artigos de
// opinião. O escopo do sistema é checar fatos noticiados; opinião não tem
// "veracidade" a ser avaliada e não deve seguir para a ML.
//
// Funcionamento: cada padrão encontrado soma pontos. A partir de
// OPINION_THRESHOLD o conteúdo é tratado como opinião. Sinais fortes (rótulos
// explícitos, seções de opinião na URL) atingem o limite sozinhos; sinais
// fracos só bloqueiam quando aparecem juntos.

import type { ParsedInput } from "./input";

export type Signal = { id: string; description: string; weight: number };
export type ContentClassification = {
  type: "news" | "opinion";
  score: number;
  signals: Signal[];
};

export const OPINION_THRESHOLD = 3;

type Rule = Signal & { pattern: RegExp };

// Os padrões são escritos sem acentos e em minúsculas porque o texto é
// normalizado antes da comparação (ver normalize).
const TEXT_RULES: Rule[] = [
  {
    id: "rotulo-opiniao",
    description: "Identificado como artigo de opinião, editorial ou coluna",
    weight: 3,
    pattern:
      /^\s*(?:artigo de opiniao|opiniao|editorial|coluna|cronica|ponto de vista|carta do leitor)\s*(?:[:|\-–—]|$)|\bartigo de opiniao\b/m,
  },
  {
    id: "aviso-autoria",
    description: "Aviso de que o texto reflete a opinião do autor",
    weight: 3,
    pattern:
      /\b(?:nao )?reflete(?:m)? (?:necessariamente )?(?:a )?(?:opiniao|posicao|linha editorial)\b|\b(?:e|sao) de (?:inteira |exclusiva )?responsabilidade (?:exclusiva )?d[oa]s? (?:autor|autora|colunista)/,
  },
  {
    id: "declaracao-de-opiniao",
    description: "Declaração explícita de opinião do autor",
    weight: 3,
    pattern:
      /\b(?:na|em) minha (?:opiniao|visao|avaliacao)\b|\b(?:a|ao) meu ver\b|\bno meu (?:entender|entendimento|modo de ver)\b|\bdo meu ponto de vista\b/,
  },
  {
    id: "primeira-pessoa-opinativa",
    description: "Expressões de opinião em primeira pessoa",
    weight: 2,
    pattern:
      /\b(?:eu )?(?:acho|acredito|penso|defendo|considero) que\b|\bsou (?:totalmente |plenamente )?(?:a favor|contra)\b|\bme parece (?:que|claro|evidente)\b/,
  },
  {
    id: "juizo-de-valor",
    description: "Juízos de valor fortes",
    weight: 1,
    pattern:
      /\be (?:simplesmente |absolutamente |totalmente )?(?:inaceitavel|inadmissivel|vergonhoso|absurdo|lamentavel|ridiculo|revoltante|uma vergonha)\b/,
  },
  {
    id: "prescricao",
    description: "Recomendações sobre o que deveria ser feito",
    weight: 1,
    pattern:
      /\b(?:deveria|deveriam|deveriamos|precisamos|temos que)\b|\be (?:preciso|urgente|necessario) que\b/,
  },
  {
    id: "retorica",
    description: "Marcadores retóricos típicos de opinião",
    weight: 1,
    pattern:
      /\b(?:obviamente|evidentemente|sem duvida(?: alguma)?|convenhamos|fica claro que)\b/,
  },
];

// Seções de portais que publicam opinião (ex.: /opiniao/, /colunas/, blog.).
const URL_RULES: Rule[] = [
  {
    id: "url-secao-opiniao",
    description: "O link aponta para uma seção de opinião, coluna ou blog",
    weight: 3,
    pattern:
      /(?:^|[./])(?:opiniao|opinion|opinioes|editoria(?:l|is)|colunas?|colunistas?|blogs?|cronicas?|ponto-de-vista|tendencias-e-debates)(?:[./?#-]|$)/,
  },
];

// Remove acentos e padroniza caixa para que "Opinião" e "opiniao" casem.
export function normalize(value: string): string {
  return value.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

// Notícias costumam citar falas opinativas entre aspas ("Eu acho que...",
// disse o prefeito). Essas falas são de terceiros e não tornam o texto uma
// opinião, então são removidas antes da análise.
export function stripQuotes(value: string): string {
  return value.replace(/"[^"]*"|“[^”]*”|«[^»]*»/g, " ");
}

function safeDecode(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function collect(rules: Rule[], subject: string): Signal[] {
  return rules
    .filter((rule) => rule.pattern.test(subject))
    .map(({ id, description, weight }) => ({ id, description, weight }));
}

export function classifyContent(input: ParsedInput): ContentClassification {
  const signals =
    input.kind === "url"
      ? collect(
          URL_RULES,
          normalize(`${input.url.hostname}${safeDecode(input.url.pathname)}`),
        )
      : collect(TEXT_RULES, normalize(stripQuotes(input.text)));

  const score = signals.reduce((sum, signal) => sum + signal.weight, 0);
  return {
    type: score >= OPINION_THRESHOLD ? "opinion" : "news",
    score,
    signals,
  };
}
