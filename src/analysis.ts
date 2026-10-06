export type Outcome = "supported" | "context" | "insufficient";
export type Source = {
  title: string;
  institution: string;
  date: string;
  href: string;
};
export type Analysis = {
  outcome: Outcome;
  claim: string;
  title: string;
  explanation: string[];
  sources: Source[];
  next: string;
};

export const examples: Record<Outcome, string> = {
  supported:
    "EXEMPLO FICTÍCIO: A Câmara de Vila Serena abriu uma consulta pública sobre o orçamento municipal até 30 de novembro de 2026.",
  context:
    "EXEMPLO FICTÍCIO: A Câmara de Vila Serena já aprovou a proposta de transporte gratuito aos domingos.",
  insufficient:
    "EXEMPLO FICTÍCIO: Uma mensagem diz que Vila Serena vai mudar todos os locais de votação no próximo mês.",
};

const consultation: Source = {
  title: "Aviso de consulta pública sobre o orçamento",
  institution: "Câmara de Vila Serena (fictícia)",
  date: "1 de outubro de 2026",
  href: "/fontes/consulta.html",
};
const minutes: Source = {
  title: "Registro da reunião sobre transporte aos domingos",
  institution: "Câmara de Vila Serena · instituição fictícia",
  date: "2 de outubro de 2026",
  href: "/fontes/reuniao.html",
};

const results: Record<Outcome, Omit<Analysis, "claim">> = {
  supported: {
    outcome: "supported",
    title: "O material do exemplo confirma essa informação.",
    explanation: [
      "O aviso diz que a consulta está aberta até 30 de novembro de 2026, como a mensagem afirma.",
    ],
    sources: [consultation],
    next: "Leia o aviso e compare a data com a mensagem antes de compartilhar.",
  },
  context: {
    outcome: "context",
    title: "A proposta ainda não foi aprovada.",
    explanation: [
      "O registro diz que ela foi apresentada para discussão. Ainda não houve votação.",
    ],
    sources: [minutes],
    next: "Não compartilhe como se fosse uma decisão já tomada.",
  },
  insufficient: {
    outcome: "insufficient",
    title: "Não achamos provas para confirmar ou negar.",
    explanation: [
      "Isso não quer dizer que seja falso. Só não temos como saber com este material.",
    ],
    sources: [],
    next: "Espere mais informações e procure a publicação original.",
  },
};

// Interface independente da UI: substituir esta função por uma chamada à API.
// Nenhum link é acessado e nenhum texto é verificado de fato.
export async function analyzeNews(
  input: string,
  options: { simulateFailure?: boolean } = {},
): Promise<Analysis> {
  await new Promise((resolve) => setTimeout(resolve, 1400));
  if (options.simulateFailure) throw new Error("Simulated unavailable service");
  const outcome =
    (Object.keys(examples) as Outcome[]).find(
      (key) => examples[key] === input.trim(),
    ) ?? "insufficient";
  return { ...results[outcome], claim: input.trim() };
}