import { expect, test } from "@playwright/test";
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
