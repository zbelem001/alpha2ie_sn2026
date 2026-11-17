import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const spaces = ["auth", "citizen", "agent", "trust-center", "administration"];

// Chaque espace importe uniquement son métier et les briques communes.
const spaceBoundaries = spaces.map((space) => ({
  files: [`src/features/${space}/**/*.{ts,tsx}`, `src/app/(${space})/**/*.{ts,tsx}`],
  rules: {
    "no-restricted-imports": ["error", {
      patterns: [{
        group: spaces.filter((other) => other !== space).flatMap((other) => [
          `@/features/${other}`, `@/features/${other}/**`, `**/features/${other}/**`,
          `**/${other}/**`,
        ]),
        message: "Les espaces utilisateur sont indépendants. Déplacer le code réellement commun dans components/shared ou lib.",
      }, {
        group: ["@/app/**", "**/app/**"],
        message: "Les routes composent les fonctionnalités ; une fonctionnalité ne doit pas importer une route.",
      }],
    }],
  },
}));

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  ...spaceBoundaries,
  {
    files: ["src/components/**/*.{ts,tsx}", "src/lib/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": ["error", {
        patterns: [{
          group: ["@/features/**", "**/features/**", "@/app/**", "**/app/**"],
          message: "Les briques partagées ne doivent pas dépendre d'un espace utilisateur ou d'une route.",
        }],
      }],
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
