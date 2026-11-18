import { expect, test, type Page } from "@playwright/test";

// Prérequis : miroir démarré (docker compose up -d dans mirror-project/), compte d'Awa rattaché
// à son acte (téléphone 70 00 00 01) et une consultation signalée par Awa : les tests de bout en
// bout de l'espace usager s'en chargent (npm run test:e2e dans espace-usager/, avant ceux-ci).
const AWA_REFERENCES = {
  "Référence de l’acte de naissance": "ACTE-DEMO-OUAGA-2004-01234",
  "Numéro du certificat de nationalité": "NAT-DEMO-OUAGA-2004-01234",
  "Numéro du casier judiciaire": "CASIER-DEMO-OUAGA-2004-01234",
};

async function login(page: Page, username: string, password: string) {
  await page.goto("/");
  await page.getByLabel("Identifiant").fill(username);
  await page.getByLabel("Mot de passe").fill(password);
  await page.getByRole("button", { name: "SE CONNECTER" }).click();
}

test("sans session, le guichet renvoie vers la connexion", async ({ page }) => {
  await page.goto("/guichet");
  await expect(page).toHaveURL(/\/$/);
});

test("un compte citoyen n'entre pas au guichet", async ({ page }) => {
  await login(page, "citoyen-demo", "CitoyenDemo-2026!");
  await expect(page.getByRole("alert").filter({ hasText: "Ce compte n’a pas accès à cet espace" })).toBeVisible();
});

test("dossier au guichet : sans pièce, accord par code, vérifications", async ({ page }) => {
  await login(page, "agent-demo", "AgentDemo-2026!");
  await expect(page).toHaveURL(/\/guichet$/);
  await page.getByRole("button", { name: "Nouveau dossier" }).click();
  await page.getByLabel("Démarche").selectOption("concours_direct_preverification");
  await page.getByLabel("Nom du citoyen (facultatif)").fill("Awa KABORE");
  await page.getByLabel("Téléphone pour l’accord").fill("70000001");
  await page.getByText("Sur place, avec un code reçu par SMS").click();
  for (const [label, value] of Object.entries(AWA_REFERENCES)) await page.getByLabel(label).fill(value);
  await page.getByRole("button", { name: "Ouvrir le dossier" }).click();

  await page.getByRole("button", { name: "Envoyer le code d’accord" }).click();
  await page.getByText("SMS de démonstration").click();
  const code = await page.locator("[data-demo-code]").getAttribute("data-demo-code");
  expect(code).toMatch(/^\d{6}$/);
  await page.getByLabel("Code communiqué par le citoyen").fill(code!);
  await page.getByRole("button", { name: "Valider le code" }).click();
  await expect(page.getByText("Accord reçu au guichet")).toBeVisible({ timeout: 15_000 });

  await page.getByRole("button", { name: "Lancer les vérifications" }).click();
  await expect(page.getByText("Vérifications terminées.")).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("ul li span[class*='checkResult']").filter({ hasText: "Oui" })).toHaveCount(3);

  const reference = (await page.getByText(/^Dossier DOS-/).first().innerText()).split(" ")[1];
  await page.getByRole("button", { name: "Retour aux dossiers" }).click();
  await page.getByLabel("Rechercher une demande").fill(reference);
  await expect(page.getByRole("button", { name: `Ouvrir le dossier ${reference}` })).toBeVisible();
  await expect(page.getByText("1 demande", { exact: true })).toBeVisible();
});

test("le guichet voit le signalement du citoyen dans la liste et dans le dossier", async ({ page }) => {
  await login(page, "agent-demo", "AgentDemo-2026!");
  await expect(page).toHaveURL(/\/guichet$/);
  const reported = page.locator("tbody tr").filter({ has: page.locator("span", { hasText: /^Signalement$/ }) }).first();
  await expect(reported).toBeVisible({ timeout: 20_000 });
  await reported.getByRole("button", { name: /^Ouvrir le dossier / }).click();
  const reports = page.getByRole("region", { name: "Signalements du citoyen" });
  await expect(reports).toContainText("le citoyen ne reconnaît pas la consultation");
  await expect(reports).toContainText("À examiner avant toute décision.");
});
