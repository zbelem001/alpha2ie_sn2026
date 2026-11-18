import { expect, test } from "@playwright/test";
import { SPACE } from "@/lib/space";

test("la console admet uniquement les administrateurs locaux", () => {
  expect(SPACE.roles).toEqual(["local-admin"]);
  expect(SPACE.home["local-admin"]).toBe("/administration");
});
test("la console ne relaie que son API et le guichet partagé", () => {
  for (const route of ["admin/config", "admin/agents", "admin/audit", "cases", "procedures"]) expect(SPACE.backendRoutes.test(route)).toBe(true);
  for (const route of ["citizen/identifiers", "auth/phone/register", "adminx/config"]) expect(SPACE.backendRoutes.test(route)).toBe(false);
});
