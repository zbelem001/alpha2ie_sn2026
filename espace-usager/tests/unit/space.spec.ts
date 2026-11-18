import { expect, test } from "@playwright/test";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/server/session-cookies";
import { SPACE } from "@/lib/space";

test("l'espace usager n'admet que le rôle citoyen", () => {
  expect(SPACE.roles).toEqual(["citizen"]);
  expect(SPACE.home.citizen).toBe("/usager");
});

test("le relais ne transmet que les routes du citoyen", () => {
  for (const route of ["cases", "cases/123/journal", "cases/123/consent", "citizen/identity-link", "citizen/cases", "notifications", "procedures"]) {
    expect(SPACE.backendRoutes.test(route), route).toBe(true);
  }
  for (const route of ["admin/config", "admin/agents", "auth/registration/otp", "casesx", ""]) {
    expect(SPACE.backendRoutes.test(route), route).toBe(false);
  }
});

test("les cookies de session sont propres à cette application", () => {
  // Mêmes noms dans les deux applications : une connexion à l'une effaçait la session de l'autre.
  expect([ACCESS_COOKIE, REFRESH_COOKIE]).toEqual(["dlnuf_usager_access", "dlnuf_usager_refresh"]);
  expect(`${ACCESS_COOKIE}${REFRESH_COOKIE}`).not.toContain("guichet");
});
