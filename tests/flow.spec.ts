import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
});

test("empty input shows recovery and keeps keyboard focus", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "Verificar notícia", exact: true })
    .click();
  await expect(page.getByRole("alert")).toHaveText(
    "Cole o texto ou o link da notícia para continuar.",
  );
  await expect(
    page.getByLabel("Cole aqui o texto ou o link da notícia"),
  ).toBeFocused();
});

for (const scenario of [
  {
    button: "Informação sustentada",
    title: "O material do exemplo sustenta essa informação.",
    source: "Aviso de consulta pública sobre o orçamento",
  },
  {
    button: "Informação sem contexto",
    title: "Falta contexto: a proposta ainda não foi aprovada.",
    source: "Registro da reunião sobre transporte aos domingos",
  },
  {
    button: "Evidências insuficientes",
    title: "Não há evidências suficientes para concluir.",
    source: null,
  },
]) {
  test(`complete flow: ${scenario.button}`, async ({ page }) => {
    await page
      .getByRole("button", { name: scenario.button, exact: true })
      .click();
    await expect(page.getByRole("textbox")).toHaveValue(/EXEMPLO FICTÍCIO/);
    await page
      .getByRole("button", { name: "Verificar notícia", exact: true })
      .click();
    await expect(page.getByRole("status")).toContainText(
      "Estamos buscando informações sobre essa notícia.",
    );
    await expect(page.getByText(scenario.title, { exact: true })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "O que encontramos", exact: true }),
    ).toBeFocused();
    await expect(
      page.getByText("Demonstração — análise simulada", { exact: true }),
    ).toBeVisible();
    if (scenario.source) {
      const popupPromise = page.waitForEvent("popup");
      await page
        .getByRole("link", { name: new RegExp(scenario.source) })
        .click();
      const popup = await popupPromise;
      await expect(
        popup.getByRole("heading", { name: scenario.source }),
      ).toBeVisible();
      await expect(
        popup.getByText("Demonstração — documento fictício", { exact: true }),
      ).toBeVisible();
      await popup.close();
    } else {
      await expect(
        page.getByText(/A ausência de evidências não significa/),
      ).toBeVisible();
    }
    await page.getByRole("button", { name: "Verificar outra notícia" }).click();
    await expect(page.getByRole("textbox")).toHaveValue("");
    await expect(page.getByRole("textbox")).toBeFocused();
  });
}

test("failure preserves input and retry succeeds", async ({ page }) => {
  await page
    .getByRole("button", { name: "Ver um exemplo", exact: true })
    .click();
  const original = await page.getByRole("textbox").inputValue();
  await page
    .getByText("Testar uma falha de verificação", { exact: true })
    .click();
  await page.getByLabel("Simular falha no próximo envio").check();
  await page
    .getByRole("button", { name: "Verificar notícia", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Seu texto foi mantido. Tente novamente.",
  );
  await expect(page.getByRole("textbox")).toHaveValue(original);
  await page
    .getByRole("button", { name: "Tentar novamente", exact: true })
    .click();
  await expect(
    page.getByText("O material do exemplo sustenta essa informação.", {
      exact: true,
    }),
  ).toBeVisible();
});

test("arbitrary links get no invented verification", async ({ page }) => {
  await page.getByRole("textbox").fill("https://example.com/noticia");
  await page
    .getByRole("button", { name: "Verificar notícia", exact: true })
    .click();
  await expect(
    page.getByText("Não há evidências suficientes para concluir.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("https://example.com/noticia", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Não houve pesquisa na internet/)).toBeVisible();
});

test("opinion text is blocked before analysis and input is kept", async ({
  page,
}) => {
  const opinion =
    "Na minha opinião, a nova lei é um erro e vai prejudicar a cidade.";
  await page.getByRole("textbox").fill(opinion);
  await page
    .getByRole("button", { name: "Verificar notícia", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Isso parece um artigo de opinião." }),
  ).toBeFocused();
  await expect(
    page.getByText("Declaração explícita de opinião do autor"),
  ).toBeVisible();
  await expect(page.getByText("O que encontramos")).toHaveCount(0);
  await expect(page.getByRole("textbox")).toHaveValue(opinion);
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);

  // Ao editar o conteúdo, o aviso some.
  await page.getByRole("textbox").fill("https://example.com/noticia");
  await expect(
    page.getByRole("heading", { name: "Isso parece um artigo de opinião." }),
  ).toHaveCount(0);
});

test("links to opinion sections are blocked", async ({ page }) => {
  await page
    .getByRole("textbox")
    .fill("https://www.estadao.com.br/opiniao/editorial-qualquer/");
  await page
    .getByRole("button", { name: "Verificar notícia", exact: true })
    .click();
  await expect(
    page.getByText("O link aponta para uma seção de opinião, coluna ou blog"),
  ).toBeVisible();
});

test("too short text shows a validation message", async ({ page }) => {
  await page.getByRole("textbox").fill("Prefeito renunciou ontem");
  await page
    .getByRole("button", { name: "Verificar notícia", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("O texto é muito curto.");
  await expect(page.getByRole("textbox")).toBeFocused();
});

test("keyboard access and enlarged text reflow", async ({ page }) => {
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Ir para o conteúdo" }),
  ).toBeFocused();
  await page.setViewportSize({ width: 320, height: 780 });
  await page.addStyleTag({
    content:
      "html { font-size: 40px !important } body * { font-size: max(1em, 20px) }",
  });
  await expect(page.getByRole("textbox")).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflow).toBe(false);
});

test("input and result meet automated WCAG AA checks", async ({ page }) => {
  const audit = () =>
    new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
  expect((await audit()).violations).toEqual([]);
  await page
    .getByRole("button", { name: "Ver um exemplo", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Verificar notícia", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "O que encontramos", exact: true }),
  ).toBeVisible();
  expect((await audit()).violations).toEqual([]);
});
