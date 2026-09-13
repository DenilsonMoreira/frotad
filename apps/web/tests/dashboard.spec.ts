import { expect, test } from "@playwright/test";

test("connects, filters, handles stale data and disconnects without overflow", async ({
  page,
}, testInfo) => {
  const metrics = {
    day: "2026-09-12",
    trips: 4,
    volume_m3: "32",
    diesel_liters: "78",
    liters_per_m3: "2.4375",
    missing_measurements: 0,
  };
  const payload = {
    company: "Empresa de teste",
    timezone: "America/Fortaleza",
    server_time: "2026-09-12T13:00:00Z",
    metrics,
    trend: [metrics],
    active_vehicles: 1,
    active_cycles: 1,
    waiting: 1,
    waiting_status: "WAITING_AT_SITE",
    target_liters_per_m3: "2.5",
    active: [
      {
        period_id: "period-1",
        submission_id: "cycle-123",
        vehicle: "FD-107",
        driver: "Marcos Lima",
        status_key: "WAITING_AT_SITE",
        status_label: "Aguardando na obra",
        started_at: "2026-09-12T12:18:00Z",
        elapsed_seconds: 2520,
      },
    ],
  };
  let fail = false;
  await page.route("**/api/backend/dashboard*", (route) =>
    route.fulfill({
      status: fail ? 503 : 200,
      contentType: "application/json",
      body: JSON.stringify(payload),
    }),
  );
  await page.goto("/login");
  await page.getByLabel("E-mail", { exact: true }).fill("owner@example.test");
  await page
    .getByLabel("Senha", { exact: true })
    .fill("Frase de teste segura 123");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByRole("heading", { name: "FD-107" })).toBeVisible();
  await expect(page.getByText("0h 42min")).toBeVisible();
  await expect(
    page.locator(".metric").filter({ hasText: "Consumo por volume" }),
  ).toContainText("2,44");
  await expect(page.locator("body")).not.toContainText("browser-test-token");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("dashboard.png"),
    fullPage: true,
  });
  await page.getByLabel("Buscar na operação").fill("inexistente");
  await expect(
    page.getByText("Nenhuma operação corresponde aos filtros."),
  ).toBeVisible();
  await page.getByLabel("Buscar na operação").fill("");
  fail = true;
  await page.getByRole("button", { name: "Atualizar", exact: true }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "última atualização",
  );
  await expect(page.getByRole("heading", { name: "FD-107" })).toBeVisible();
  await page.getByRole("button", { name: "Desconectar" }).click();
  await expect(
    page.getByRole("heading", { name: "Acesse sua conta" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "FD-107" })).toHaveCount(0);
});
