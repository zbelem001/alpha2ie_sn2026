import { defineConfig } from "@playwright/test";

// Deux familles de tests (npm run test:unit, npm run test:e2e) :
// - unit : logique TypeScript, sans navigateur (accord, routes relayées) ;
// - e2e  : parcours dans Chrome, contre le miroir démarré (docker compose up -d dans mirror-project/).
export default defineConfig({
  testDir: "tests",
  timeout: 60_000,
  reporter: [["list"]],
  projects: [
    { name: "unit", testMatch: /unit\/.*\.spec\.ts/ },
    {
      name: "e2e",
      testMatch: /e2e\/.*\.spec\.ts/,
      use: {
        baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3002",
        // Chrome installé sur la machine ; sinon : npx playwright install chromium et PLAYWRIGHT_CHANNEL=chromium.
        channel: process.env.PLAYWRIGHT_CHANNEL ?? "chrome",
        locale: "fr-FR",
        viewport: { width: 1280, height: 900 },
      },
    },
  ],
});
