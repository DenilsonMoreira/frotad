import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  use: { baseURL: "http://127.0.0.1:3100" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { viewport: { width: 360, height: 800 } } },
  ],
  webServer: {
    command: "npm run dev -- --hostname 127.0.0.1 --port 3100",
    url: "http://127.0.0.1:3100",
    reuseExistingServer: !process.env.CI,
  },
});
