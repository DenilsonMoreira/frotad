import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  timeout: 60000,
  expect: { timeout: 15000 },
  workers: 2,
  use: { baseURL: "http://127.0.0.1:3100" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { viewport: { width: 360, height: 800 } } },
  ],
  webServer: [
    {
      command: "node tests/api-fixture.mjs",
      url: "http://127.0.0.1:8101/health",
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3100",
      url: "http://127.0.0.1:3100",
      env: { API_URL: "http://127.0.0.1:8101" },
    },
  ],
});
