import { defineConfig, devices } from "@playwright/test";
const channel = process.env.PLAYWRIGHT_CHANNEL === "msedge" ? "msedge" : undefined;
export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  use: { baseURL: "http://127.0.0.1:5174" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], channel } },
    {
      name: "mobile",
      use: { ...devices["iPhone 13"], defaultBrowserType: "chromium", channel },
    },
  ],
  webServer: {
    command: "node ./scripts/test-server.mjs",
    url: "http://127.0.0.1:5174",
    reuseExistingServer: false,
  },
});
