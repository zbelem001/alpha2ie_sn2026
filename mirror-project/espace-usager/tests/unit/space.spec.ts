import { expect, test } from "@playwright/test";
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
