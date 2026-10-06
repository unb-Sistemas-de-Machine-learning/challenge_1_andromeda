// Etapa 1 do pipeline: interpreta o que o usuário colou e decide se é um
// link ou um texto. Nenhum conteúdo é acessado aqui; apenas a forma é validada.

export type ParsedInput =
  | { kind: "url"; url: URL; raw: string }
  | { kind: "text"; text: string; raw: string };

export type InputError = { kind: "invalid"; message: string };

export const MIN_TEXT_WORDS = 5;
export const MAX_TEXT_LENGTH = 20_000;

// Um único "token" sem espaços, com domínio e TLD, opcionalmente com
// protocolo http(s) e caminho. Ex.: "https://site.com/x", "site.com.br/x".
const URL_PATTERN =
  /^(?:https?:\/\/)?(?:[a-z0-9-]+\.)+[a-z]{2,}(?::\d{2,5})?(?:[/?#]\S*)?$/i;

// Protocolos explícitos diferentes de http(s) (javascript:, file:, ftp://…).
const OTHER_SCHEME = /^[a-z][a-z0-9+.-]*:(?!\d)/i;

export function parseInput(raw: string): ParsedInput | InputError {
  const value = raw.trim();
  if (!value) {
    return {
      kind: "invalid",
      message: "Cole o texto ou o link da notícia para continuar.",
    };
  }

  if (
    !/\s/.test(value) &&
    OTHER_SCHEME.test(value) &&
    !/^https?:/i.test(value)
  ) {
    return {
      kind: "invalid",
      message: "Use um link que comece com http:// ou https://.",
    };
  }

  if (URL_PATTERN.test(value)) {
    try {
      const withScheme = /^https?:\/\//i.test(value)
        ? value
        : `https://${value}`;
      return { kind: "url", url: new URL(withScheme), raw: value };
    } catch {
      return {
        kind: "invalid",
        message:
          "Esse link parece incompleto. Confira o endereço e tente de novo.",
      };
    }
  }

  if (value.length > MAX_TEXT_LENGTH) {
    return {
      kind: "invalid",
      message: `O texto é muito longo. Cole até ${MAX_TEXT_LENGTH.toLocaleString("pt-BR")} caracteres.`,
    };
  }
  if (value.split(/\s+/).length < MIN_TEXT_WORDS) {
    return {
      kind: "invalid",
      message: `O texto é muito curto. Cole a notícia completa ou pelo menos ${MIN_TEXT_WORDS} palavras.`,
    };
  }
  return { kind: "text", text: value, raw: value };
}
