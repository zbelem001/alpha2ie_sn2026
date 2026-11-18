import type { Metadata, Viewport } from "next";
import { Geist_Mono, Outfit } from "next/font/google";
import "./globals.css";

// Outfit pour tout le texte, Geist Mono pour les références et les heures (docs/charte-graphique.md).
// Téléchargées à la construction et servies par l'application : le navigateur n'appelle pas Google.
const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Guichet agent | Dites-le-nous une fois",
    template: "%s | Dites-le-nous une fois",
  },
  description: "Guichet des administrations : ouvrir un dossier, recueillir l’accord du citoyen, vérifier sans pièce.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#183624",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="fr"
      className={`${outfit.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <a className="skip-link" href="#contenu">Aller au contenu</a>
        {children}
      </body>
    </html>
  );
}