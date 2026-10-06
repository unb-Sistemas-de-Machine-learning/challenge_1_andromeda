import { test, expect } from "@playwright/test";
import { examples } from "../src/analysis";
import { parseInput, type ParsedInput } from "../src/pipeline/input";
import { classifyContent } from "../src/pipeline/opinionFilter";

// Regras puras: não dependem do navegador, rodam só uma vez.
test.beforeEach(({}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop");
});

function classify(raw: string) {
  const parsed = parseInput(raw);
  if (parsed.kind === "invalid") throw new Error(parsed.message);
  return classifyContent(parsed as ParsedInput);
}

test.describe("parseInput", () => {
  test("detects links with and without protocol", () => {
    expect(
      parseInput("https://g1.globo.com/politica/noticia.ghtml"),
    ).toMatchObject({
      kind: "url",
    });
    const bare = parseInput("www.exemplo.com.br/noticia");
    expect(bare.kind).toBe("url");
    if (bare.kind === "url")
      expect(bare.url.href).toBe("https://www.exemplo.com.br/noticia");
  });

  test("treats sentences as text", () => {
    expect(parseInput(examples.supported).kind).toBe("text");
  });

  test("rejects empty, short and unsafe input", () => {
    expect(parseInput("   ").kind).toBe("invalid");
    expect(parseInput("Prefeito renunciou ontem").kind).toBe("invalid");
    expect(parseInput("javascript:alert(1)").kind).toBe("invalid");
    expect(parseInput("ftp://exemplo.com/arquivo").kind).toBe("invalid");
  });
});

test.describe("classifyContent", () => {
  for (const [name, text] of Object.entries(examples)) {
    test(`demo example "${name}" is news`, () => {
      expect(classify(text).type).toBe("news");
    });
  }

  for (const text of [
    "A prefeitura anunciou nesta segunda-feira que as aulas da rede municipal começam em 3 de fevereiro, segundo nota oficial.",
    'O prefeito disse que "na minha opinião, é inaceitável o que aconteceu" e afirmou que vai recorrer da decisão.',
    "Coluna de fumaça foi vista no centro da cidade na manhã desta terça-feira, segundo os bombeiros.",
    "O governo deveria apresentar o relatório até sexta-feira, conforme determinou o tribunal.",
  ]) {
    test(`news: ${text.slice(0, 40)}…`, () => {
      expect(classify(text).type).toBe("news");
    });
  }

  for (const text of [
    "OPINIÃO\nO transporte público da cidade precisa de mais investimento.",
    "Artigo de opinião: por que a reforma tributária vai falhar no longo prazo.",
    "Na minha opinião, a nova lei é um erro e vai prejudicar os mais pobres.",
    "Eu acho que o governo errou. É simplesmente inaceitável que nada tenha sido feito.",
    "A reforma foi aprovada ontem. Este artigo não reflete necessariamente a opinião do jornal.",
  ]) {
    test(`opinion: ${text.slice(0, 40).replace(/\n/g, " ")}…`, () => {
      const result = classify(text);
      expect(result.type).toBe("opinion");
      expect(result.signals.length).toBeGreaterThan(0);
    });
  }

  for (const url of [
    "https://www.estadao.com.br/opiniao/editorial-sobre-a-reforma/",
    "https://www1.folha.uol.com.br/colunas/fulano/2026/10/texto.shtml",
    "https://g1.globo.com/politica/blog/nome-do-blog/post/2026/10/06/x.ghtml",
    "https://exemplo.com/opini%C3%A3o/texto",
  ]) {
    test(`opinion link: ${url}`, () => {
      expect(classify(url).type).toBe("opinion");
    });
  }

  for (const url of [
    "https://g1.globo.com/politica/noticia/2026/10/06/camara-aprova-projeto.ghtml",
    "https://example.com/noticia",
    "https://exemplo.com/%E0%A4%A",
  ]) {
    test(`news link: ${url}`, () => {
      expect(classify(url).type).toBe("news");
    });
  }
});
