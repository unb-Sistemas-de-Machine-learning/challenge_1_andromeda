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
  institution: "Câmara de Vila Serena · instituição fictícia",
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
    title: "O material do exemplo sustenta essa informação.",
    explanation: [
      "No cenário fictício, o aviso informa que a consulta sobre o orçamento está aberta até 30 de novembro de 2026. Isso corresponde à afirmação analisada.",
      "Este resultado se limita a essa afirmação. Não avalia todas as informações que uma notícia poderia conter.",
    ],
    sources: [consultation],
    next: "Leia o aviso e compare a data e o assunto com a mensagem recebida. Em uma notícia real, confira também a origem antes de compartilhar.",
  },
  context: {
    outcome: "context",
    title: "Falta contexto: a proposta ainda não foi aprovada.",
    explanation: [
      "No cenário fictício, o registro informa que a proposta foi apresentada para discussão. A votação ainda não aconteceu.",
      "Apresentar uma proposta é diferente de aprová-la. O material contradiz a afirmação de que a medida já foi aprovada, sem avaliar a notícia inteira.",
    ],
    sources: [minutes],
    next: "Evite compartilhar a mensagem como uma decisão já tomada. Confira o registro e procure uma atualização sobre a votação.",
  },
  insufficient: {
    outcome: "insufficient",
    title: "Não há evidências suficientes para concluir.",
    explanation: [
      "O acervo fictício deste protótipo não contém materiais que permitam confirmar ou contradizer essa afirmação.",
      "A ausência de evidências não significa que a informação seja falsa. Para avaliar uma notícia real, seria preciso pesquisar fontes relevantes e atualizadas.",
    ],
    sources: [],
    next: "Aguarde mais informações antes de compartilhar. Procure a publicação original e uma fonte responsável pelo assunto.",
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
