import { expect, test } from "@playwright/test";
import { DOCUMENT_TYPES, cleanReferences, profileDocumentTypes } from "@/lib/document-references";

test("un compte rattaché à un acte ne voit ni la référence de l'acte ni la déclaration de perte", () => {
  const keys = profileDocumentTypes("ACTE:OUAGA:2004:01234").map((doc) => doc.key);
  expect(keys).toEqual(["cnib", "nationality", "criminal", "payment"]);
});

test("un compte sans acte rattaché voit toutes les références", () => {
  expect(profileDocumentTypes("CITIZEN:ABC").length).toBe(DOCUMENT_TYPES.length);
  expect(profileDocumentTypes(null).length).toBe(DOCUMENT_TYPES.length);
});

test("une référence masquée mais enregistrée n'est pas effacée à l'enregistrement", () => {
  const saved = { birth: "ACTE-DEMO-OUAGA-2004-01234", cnib: "" };
  expect(cleanReferences([...DOCUMENT_TYPES], saved, false)).toEqual({ birth: "ACTE-DEMO-OUAGA-2004-01234" });
});
