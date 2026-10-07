import { expect, test } from "@playwright/test";

const article = { title: "Governo anuncia nova medida para escolas públicas", publisher: "noticias.gov.br", url: "https://noticias.gov.br/escolas" };

test.beforeEach(async ({ page }) => {
  await page.route("**api.gdeltproject.org/**", (route) => route.fulfill({ json: { articles: [
    { title: "Editorial: o governo deveria agir agora", publisher: "example.com", url: "https://example.com/opiniao/editorial" },
    article,
  ] } }));
  await page.route("**/fact-check", (route) => route.fulfill({ json: { claims: [] } }));
  await page.route(article.url, (route) => route.fulfill({ contentType: "text/html", body: `<html><head><meta property="og:title" content="${article.title}"></head><body><article>${"Texto da reportagem. ".repeat(30)}</article></body></html>` }));
  await page.goto("/", { waitUntil: "domcontentloaded" });
});

test("busca por título, filtra editorial e mostra apenas a explicação pública", async ({ page }) => {
  await page.getByLabel("Título da notícia").fill(article.title);
  await page.getByRole("button", { name: "Buscar notícia" }).click();
  await expect(page.getByRole("heading", { name: "Escolha a reportagem" })).toBeVisible();
  await expect(page.getByText("Editorial: o governo deveria agir agora")).toHaveCount(0);
  await page.getByRole("button", { name: article.title }).click();
  await expect(page.getByText(/Não há checagem factual disponível/)).toBeVisible();
  await expect(page.getByText("Resultado de demonstração")).toHaveCount(0);
});

test("link de opinião não chega à API", async ({ page }) => {
  let called = false;
  await page.route("**/fact-check", (route) => { called = true; return route.abort(); });
  await page.getByRole("button", { name: "Tenho o link" }).click();
  await page.getByLabel("Link da reportagem").fill("https://example.com/opiniao/editorial");
  await page.getByRole("button", { name: "Analisar notícia" }).click();
  await expect(page.getByRole("alert")).toContainText("opinião");
  expect(called).toBe(false);
});

test("erro preserva a entrada para tentar novamente", async ({ page }) => {
  await page.route("**api.gdeltproject.org/**", (route) => route.fulfill({ status: 502, json: {} }));
  await page.getByLabel("Título da notícia").fill(article.title);
  await page.getByRole("button", { name: "Buscar notícia" }).click();
  await expect(page.getByRole("alert")).toContainText("buscar notícias");
  await expect(page.getByLabel("Título da notícia")).toHaveValue(article.title);
});
