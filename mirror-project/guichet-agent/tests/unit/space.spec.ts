import { expect, test } from "@playwright/test";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/server/session-cookies";
import { SPACE } from "@/lib/space";

test("le guichet admet uniquement les agents", () => {
  expect(SPACE.roles).toEqual(["agent"]);
  expect(SPACE.home.agent).toBe("/guichet");
});

test("le relais ne transmet que les routes de l'agent", () => {
  for (const route of ["procedures", "cases", "cases/123", "cases/123/checks", "cases/123/consent/otp", "cases/123/journal"]) {
    expect(SPACE.backendRoutes.test(route), route).toBe(true);
  }
  for (const route of ["citizen/identity-link", "citizen/cases", "notifications", "admin/config", "adminx/config", "auth/registration/otp", ""]) {
    expect(SPACE.backendRoutes.test(route), route).toBe(false);
  }
});

test("les cookies de session sont propres à cette application", () => {
  // Mêmes noms dans les deux applications : une connexion à l'une effaçait la session de l'autre.
  expect([ACCESS_COOKIE, REFRESH_COOKIE]).toEqual(["dlnuf_guichet_access", "dlnuf_guichet_refresh"]);
  expect(`${ACCESS_COOKIE}${REFRESH_COOKIE}`).not.toContain("usager");
});
