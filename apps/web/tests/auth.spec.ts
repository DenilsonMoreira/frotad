import { expect, test } from "@playwright/test";
const password = "Frase de teste segura 123";

test("login stores only HttpOnly session, survives reload and logs out", async ({
  page,
  context,
}, testInfo) => {
  await page.goto("/login");
  await page.screenshot({
    path: testInfo.outputPath("login.png"),
    fullPage: true,
  });
  await page.getByLabel("E-mail", { exact: true }).fill("owner@example.test");
  await page.getByLabel("Senha", { exact: true }).fill("wrong");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "E-mail ou senha inválidos",
  );
  await page.screenshot({ path: testInfo.outputPath("login.png"), fullPage: true });
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Controle da operação" }),
  ).toBeVisible();
  const cookie = (await context.cookies()).find(
    (cookie) => cookie.name === "frotad_session",
  );
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.sameSite).toBe("Strict");
  expect(await page.evaluate(() => document.cookie)).not.toContain(
    "frotad_session",
  );
  await page.reload();
  await expect(
    page.getByText("Nenhum período ativo.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Usuários da empresa" }).click();
  await expect(
    page.getByRole("heading", { name: "Usuários da empresa" }),
  ).toBeVisible();
  await page.getByLabel("Nome", { exact: true }).fill("Pessoa teste");
  await page.getByLabel("E-mail", { exact: true }).fill("person@example.test");
  await page.getByLabel("Senha inicial").fill(password);
  await page.getByLabel("Perfil").selectOption("DRIVER");
  await page.getByRole("button", { name: "Cadastrar usuário" }).click();
  await expect(page.getByRole("status")).toContainText("Usuário cadastrado");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("users.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Acesse sua conta" }),
  ).toBeVisible();
  expect(
    (await context.cookies()).some(
      (cookie) => cookie.name === "frotad_session",
    ),
  ).toBe(false);
});

test("system administrator creates a company and company administrator", async ({
  page,
}, testInfo) => {
  await page.goto("/login");
  await page.getByLabel("E-mail", { exact: true }).fill("system@example.test");
  await page.screenshot({ path: testInfo.outputPath("login.png"), fullPage: true });
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Empresas da plataforma" }),
  ).toBeVisible();
  await page
    .getByLabel("Nome da empresa", { exact: true })
    .fill("Concreto teste");
  await page.getByLabel("Identificador da empresa").fill("concreto-teste");
  await page
    .getByLabel("Nome do administrador responsável")
    .fill("Admin concreto");
  await page
    .getByLabel("E-mail do administrador")
    .fill("concreto@example.test");
  await page
    .getByLabel("Senha do administrador")
    .fill(password);
  await page.getByLabel("Confirmar senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Cadastrar empresa" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Empresa e administrador cadastrados",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("system.png"),
    fullPage: true,
  });
});

test("public registration, denied system area and CSRF protection", async ({
  page,
  request,
}) => {
  const denied = await request.post("/api/backend/auth/login", {
    headers: { origin: "https://foreign.example" },
    data: { email: "owner@example.test", password },
  });
  expect(denied.status()).toBe(403);
  await page.goto("/cadastro");
  await page
    .getByLabel("Nome da empresa", { exact: true })
    .fill("Empresa nova");
  await page.getByLabel("Identificador da empresa").fill("empresa-nova");
  await page.getByLabel("Nome do administrador responsável").fill("Admin novo");
  await page.getByLabel("E-mail do administrador").fill("new@example.test");
  await page
    .getByLabel("Senha do administrador")
    .fill(password);
  await page.getByLabel("Confirmar senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Cadastrar empresa" }).click();
  await expect(
    page.getByRole("heading", { name: "Controle da operação" }),
  ).toBeVisible();
  await page.goto("/admin");
  await expect(
    page.getByRole("heading", { name: "Acesso restrito" }),
  ).toBeVisible();
});

test("company administrator builds, reorders and publishes a form", async ({
  page,
}, testInfo) => {
  await page.goto("/login");
  await page.getByLabel("E-mail", { exact: true }).fill("forms@example.test");
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await page.getByRole("link", { name: "Formulários" }).click();
  await expect(
    page.getByRole("heading", { name: "Formulários", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Código").fill("FORM_TESTE");
  await page.getByLabel("Nome", { exact: true }).fill("Formulário de teste");
  await page.getByRole("button", { name: "Criar rascunho" }).click();
  await expect(page.getByText("Rascunho em edição")).toBeVisible();

  await page.getByLabel("Chave técnica").fill("wait");
  await page.getByLabel("Rótulo").fill("Aguardando na obra");
  await page.getByLabel("Tipo").selectOption("PERIOD");
  await page.getByLabel("Chave do status").fill("WAITING_AT_SITE");
  await page.getByLabel("Nome do status").fill("Aguardando na obra");
  await page.getByRole("button", { name: "Adicionar campo" }).click();
  await expect(page.getByText("wait · Período/status")).toBeVisible();

  await page.getByLabel("Chave técnica").fill("volume_m3");
  await page.getByLabel("Rótulo").fill("Volume entregue");
  await page.getByLabel("Tipo").selectOption("DECIMAL");
  await page.getByRole("button", { name: "Adicionar campo" }).click();
  await page
    .getByRole("button", { name: "Mover Volume entregue para cima" })
    .click();
  await expect(page.locator(".field-item").first()).toContainText(
    "Volume entregue",
  );

  page.on("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Publicar versão" }).click();
  await expect(page.getByText("Versão publicada")).toBeVisible();
  await expect(page.getByText("Imutável")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("form-builder.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Criar nova versão editável" })
    .click();
  await expect(page.getByText("Rascunho em edição")).toBeVisible();
});
