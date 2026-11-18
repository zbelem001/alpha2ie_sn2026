import { expect, test, type Page } from "@playwright/test";

// Prérequis : miroir démarré (docker compose up -d dans mirror-project/). Compte de démonstration
// d'Awa ; s'il n'est pas encore rattaché à son acte, le test le rattache avec la preuve.
const AWA = {
  username: "citoyen-demo", password: "CitoyenDemo-2026!", act: "ACTE:OUAGA:2004:01234",
  lastName: "KABORE", firstNames: "Awa", birthDate: "2004-03-12", mother: "COMPAORE Salimata",
};

test.describe.configure({ mode: "serial" });

async function login(page: Page, username = AWA.username, password = AWA.password) {
  await page.goto("/");
  await page.getByLabel("Identifiant").fill(username);
  await page.getByLabel("Mot de passe").fill(password);
  await page.getByRole("button", { name: "SE CONNECTER" }).click();
}

async function openSpace(page: Page) {
  await login(page);
  await expect(page).toHaveURL(/\/usager$/);
  const linkForm = page.getByRole("heading", { name: "Rattacher mon compte" });
  const start = page.getByRole("heading", { name: "Faire une démarche" });
  await expect(linkForm.or(start)).toBeVisible({ timeout: 20_000 });
  if (await linkForm.isVisible()) {
    await page.getByLabel("Référence de l’acte de naissance").fill(AWA.act);
    await page.getByLabel("Nom", { exact: true }).fill(AWA.lastName);
    await page.getByLabel("Prénoms").fill(AWA.firstNames);
    await page.getByLabel("Date de naissance").fill(AWA.birthDate);
    await page.getByLabel("Nom et prénom de votre mère").fill(AWA.mother);
    await page.getByLabel("Je confirme qu’il s’agit de mon propre acte de naissance.").check();
    await page.getByRole("button", { name: "Rattacher mon compte" }).click();
    await expect(start).toBeVisible({ timeout: 20_000 });
  }
}

test("sans session, l'espace renvoie vers la connexion", async ({ page }) => {
  await page.goto("/usager");
  await expect(page).toHaveURL(/\/$/);
});

test("un mauvais mot de passe est refusé", async ({ page }) => {
  await login(page, AWA.username, "mauvais-mot-de-passe");
  await expect(page.getByRole("alert").filter({ hasText: "Identifiant ou mot de passe incorrect" })).toBeVisible();
});

test("un compte agent n'entre pas dans l'espace usager", async ({ page }) => {
  await login(page, "agent-demo", "AgentDemo-2026!");
  await expect(page.getByRole("alert").filter({ hasText: "Ce compte n’a pas accès à cet espace" })).toBeVisible();
});

test("démarche faite par le citoyen seul, sans pièce, puis consultations retrouvées", async ({ page }) => {
  await openSpace(page);
  await page.getByLabel("Pré-vérification partielle d’une candidature à un concours direct").check();
  await expect(page.getByRole("heading", { name: "Informations vérifiées" })).toBeVisible();
  await page.getByLabel("J’autorise ces vérifications pour cette démarche.").check();
  await page.getByRole("button", { name: "Lancer la démarche" }).click();
  await expect(page.getByText("est faite : le résultat est dans « Mes démarches »")).toBeVisible({ timeout: 30_000 });

  const entry = page.locator("section[aria-labelledby='cases-title'] ol > li").first();
  await expect(entry).toContainText("Vérifications terminées");
  await entry.locator("summary").click();
  await expect(entry.locator("dd").filter({ hasText: /^Oui/ })).toHaveCount(3);

  const consultations = page.locator("section[aria-labelledby='journal-title'] ol > li");
  await expect(consultations.first()).toContainText("Pré-vérification partielle d’une candidature à un concours direct");
  await consultations.first().locator("summary").click();
  await expect(consultations.first()).toContainText("Votre accord sur le portail");
});

test("le citoyen signale une consultation qu'il ne reconnaît pas", async ({ page }) => {
  await openSpace(page);
  const consultation = page.locator("section[aria-labelledby='journal-title'] ol > li").first();
  await consultation.locator("summary").click();
  await consultation.getByRole("button", { name: "Je ne reconnais pas cette consultation" }).click();
  await expect(consultation).toContainText("Votre signalement sera inscrit au journal de la démarche");
  await consultation.getByRole("button", { name: "Confirmer" }).click();
  await expect(consultation.getByRole("status").filter({ hasText: "Consultation signalée le" })).toBeVisible({ timeout: 15_000 });
  await page.reload();
  const again = page.locator("section[aria-labelledby='journal-title'] ol > li").first();
  await again.locator("summary").click();
  await expect(again.getByRole("status").filter({ hasText: "Consultation signalée le" })).toBeVisible({ timeout: 20_000 });
  await expect(again.getByRole("button", { name: "Une information est fausse : demander une correction" })).toBeVisible();
});

test("le citoyen retire son accord", async ({ page }) => {
  await openSpace(page);
  const entry = page.locator("section[aria-labelledby='cases-title'] ol > li").first();
  await entry.locator("summary").click();
  await entry.getByRole("button", { name: "Retirer mon accord" }).click();
  await entry.getByRole("button", { name: "Confirmer le retrait" }).click();
  await expect(page.getByText("Votre accord est retiré")).toBeVisible({ timeout: 15_000 });
  await expect(entry.locator("p").filter({ hasText: "Votre accord" })).toContainText("Vous avez retiré votre accord");
});

test("le profil ne propose que les références utiles, toutes facultatives", async ({ page }) => {
  await openSpace(page);
  await page.getByRole("link", { name: "Mon profil" }).click();
  await expect(page.getByText("tous les champs ci-dessous sont facultatifs")).toBeVisible();
  await expect(page.getByText("Numéro de CNIB")).toBeVisible();
  // Compte rattaché à l'acte : ni la référence de l'acte (doublon), ni la déclaration de perte (aucune démarche).
  await expect(page.getByText("Référence de l’acte de naissance")).toHaveCount(0);
  await expect(page.getByText("Numéro de déclaration de perte")).toHaveCount(0);
});

test("la déconnexion ferme la session", async ({ page }) => {
  await openSpace(page);
  await page.getByRole("button", { name: "Quitter et revenir à la connexion" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/usager");
  await expect(page).toHaveURL(/\/$/);
});
