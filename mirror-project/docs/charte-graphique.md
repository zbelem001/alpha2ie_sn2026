# Charte graphique des interfaces

Règles visuelles communes à l'espace usager (`espace-usager/`) et au guichet agent (`guichet-agent/`). Elles reprennent l'esprit et les règles de `DESIGN.md` (document de design fourni, écrit pour un autre produit) avec les couleurs des armoiries du Burkina Faso. Les valeurs viennent du code : variables `:root` de `src/app/globals.css`, identiques dans les deux applications. Pour changer une couleur, la changer dans les deux fichiers.

**Esprit :** des cartes blanches givrées posées sur un fond dégradé chaud, une navigation et des boutons en pilules, beaucoup d'air. Le vert sombre des armoiries structure l'interface, l'or du mil signale l'action phare de l'écran, le rouge de l'écu est réservé aux erreurs et au bandeau d'annonces. Thème clair uniquement.

## Couleurs

### Origine

Relevées dans `public/Coat_of_arms_of_Burkina_Faso_(2025-present) (1).svg` (armoiries révisées en 2025) :

- écu aux couleurs du drapeau : rouge `#ef2b2d`, vert `#009e49`, étoile `#fcd116` ;
- or du mil `#e7bc03`, ombré de `#987c02` ;
- verts sombres des ornements, de `#183624` à `#3d895b` ;
- argent des étalons : blancs et gris.

La Constitution nomme les couleurs du drapeau (rouge, vert, jaune-or) sans en fixer la nuance.

### Marque

| Rôle | Variable | Couleur | Utilisation |
|---|---|---|---|
| Vert sombre (primaire) | `--vert-faso` | `#183624` | Boutons principaux, onglet actif, blocs pleins, anneau de focus. Blanc dessus : 13,2:1 |
| Vert sombre, survol | `--vert-faso-survol` | `#245236` | Survol des boutons principaux. Blanc dessus : 9,0:1 |
| Vert des armoiries | `--vert-armoiries` | `#316d49` | Icônes, liens, étiquettes, succès. 6,2:1 sur blanc |
| Or (accent) | `--or` | `#e7bc03` | Action phare : « Lancer la démarche », « Répondre », « Nouveau dossier ». Texte **vert sombre** dessus (7,3:1), jamais blanc |
| Or, survol | `--or-survol` | `#d6ad00` | Vert sombre dessus : 6,2:1 |
| Jaune-or de l'étoile | `--or-etoile` | `#fcd116` | Étiquettes sur le bloc vert du guichet (9,0:1), focus du lien d'évitement |
| Or doux | `--or-doux` | `#fbf0c4` | Fond des badges « en attente » |
| Surlignage | `--surlignage` | `#fdf7e3` | Encadrés d'information (aide) |
| Rouge | `--rouge` | `#b3141c` | Erreurs, refus, bandeau d'annonces. 6,9:1 sur blanc |
| Vert et rouge du drapeau | `--vert-drapeau`, `--rouge-drapeau` | `#009e49`, `#ef2b2d` | Pastilles des badges seulement : trop clairs pour du texte (3,5:1 et 4,2:1 sur blanc) |

### Neutres

| Rôle | Couleur |
|---|---|
| Texte principal | `#1a1a1a` |
| Texte secondaire | `#5a6a60` : 5,7:1 sur blanc, 4,7:1 au pire sur le fond de page |
| Fond de page (couleur de repli) | `#edefe9` |
| Cartes | blanc, ou blanc à 72 % givré (voir « Surfaces ») |
| Fonds discrets | `#f3f2ec`, `#f0f0e9` |
| Séparateurs | `#e3e3db` |
| Contour des champs | `#7f8c83` : 3,5:1 sur blanc, 3,3:1 sur la zone dorée du fond |
| Texte sur le vert sombre | `#f7f6f1`, secondaire `#c5d5ca` (8,6:1) |

### États

| État | Badge (fond / texte) | Pastille |
|---|---|---|
| Succès : « Oui », « Vérifications terminées » | `#e1f0e6` / `#245236` | `#009e49` |
| Erreur, refus, signalement du citoyen | `#fce8e8` / `#a3131a` | `#ef2b2d` |
| En attente, à examiner | `#fbf0c4` / `#6e5600` | `#987c02` |

Un état n'est jamais signalé par la couleur seule : chaque badge porte son libellé.

## Fond de page

Un gris vert en haut à gauche qui se fond en crème dorée en bas à droite, avec la lueur de l'or du mil :

```css
background:
  radial-gradient(60rem 40rem at 100% 100%, #f8e8b0 0%, transparent 70%),
  radial-gradient(50rem 30rem at 80% 0%, #f2f1e2 0%, transparent 60%),
  linear-gradient(135deg, #e3eae4 0%, #eeefe9 55%, #f6ecd0 100%);
```

## Typographie

| Usage | Police |
|---|---|
| Tout le texte, titres compris | **Outfit** |
| Références de dossier, heures, identifiants | **Geist Mono** |

Les deux viennent de `next/font/google` : elles sont téléchargées à la construction et servies par l'application. Le navigateur n'appelle pas Google.

- Titres de page **fins** (300), 2,25 à 3 rem, interlignage 1,1, approche −0,02 em.
- Titres de carte : 1,375 à 1,75 rem, graisse 400.
- Libellés et boutons : graisse 500.
- Étiquettes de section en majuscules espacées (0,08 em), 0,75 rem, gris secondaire.
- Chiffres alignés (`tabular-nums`) dans les tableaux et les dates ; titres en `text-wrap: balance`.

## Formes

| Élément | Arrondi |
|---|---|
| Rayon de base (encadrés, cartes de choix) | 1 rem |
| Cartes givrées, blocs pleins | 1,75 rem |
| Boutons, champs, navigation, badges | pilule |

## Surfaces

La carte givrée est la surface principale :

```css
background: rgb(255 255 255 / 0.72);
backdrop-filter: blur(18px);
border: 1px solid rgb(255 255 255 / 0.8);
border-radius: 1.75rem;
box-shadow: 0 1px 2px rgb(20 22 26 / 0.04), 0 8px 24px -12px rgb(20 22 26 / 0.08);
```

**Bloc vert plein** pour le contenu mis en avant : le dossier suivi au guichet.

**Écran de connexion :** la carte du formulaire est centrée dans la page, sur un fond d'armoiries en motif : les armoiries réduites (`public/armoiries-motif.webp`, 4,8 Ko, tirée de l'image `armoiries-1.png` fournie, fond rendu transparent), 52 × 64 px dans une case de 104 × 112 px, répétées en grille sur toute la page, à 8 % d'opacité. Le motif est décoratif et hors du flux : la pilule du logo annonce déjà les armoiries. Les angles y sont moins arrondis qu'ailleurs : carte 14 px ; champs, bouton et messages 10 px (`--rayon-connexion`).

## Composants

- **Boutons :** pilules de 48 px, réduites à 97 % à la pression.

  | Variante | Classe | Rendu |
  |---|---|---|
  | Principal | `.primary` | vert sombre, texte blanc |
  | Accent (une action phare par écran) | `.accent` | or, texte vert sombre |
  | Contour | `.secondary` | blanc à 80 %, contour clair |
  | Discret | `.reportButton`, `.textButton` | transparent et souligné, fond atténué au survol |

- **Champs :** pilules de 48 px, fond blanc à 80 %, contour `#7f8c83`, contour vert sombre et anneau léger au focus.
- **Choix :** chaque bouton radio est une carte de choix, au contour vert sombre une fois choisie.
- **En-tête :** les armoiries et le nom du service dans une pilule à gauche ; dans l'espace usager, la navigation (« Mes consultations », « Mon profil ») dans une pilule blanche translucide, onglet actif en vert sombre ; actions en pilules à droite, rondes sur téléphone.
- **Badges d'état :** pilules de 0,75 rem avec une pastille de couleur.
- **Bandeau d'annonces :** rouge `#b3141c`, texte blanc ; pause possible, immobile si l'appareil demande moins d'animations.

## Mise en page

- Largeur maximale : 90 rem.
- Marges latérales : 16 px sur téléphone, 32 px à partir de 640 px.
- Sous 900 px, la navigation de l'espace usager passe sur sa propre ligne. Aucune page ne déborde en largeur (vérifié à 390 et 1 366 px).

## Mouvement

- Courbe commune : `cubic-bezier(0.23, 1, 0.32, 1)` (sortie douce).
- Durées : 160 ms pour les boutons et les survols, 520 ms pour l'apparition de la carte de connexion.
- Si l'appareil demande moins d'animations (`prefers-reduced-motion`), tout est désactivé.

## Accessibilité

- Contrastes du tableau ci-dessus, calculés à la main : axe-core ne mesure pas un texte posé sur une surface givrée ou un dégradé, il le marque « à vérifier ». Audit axe-core WCAG 2.1 A et AA sans violation sur tous les écrans des deux interfaces, à 1 280 et 390 px (18/11/2026).
- Focus toujours visible : contour vert sombre de 2 px ; contour or sur le lien d'évitement.
- Lien « Aller au contenu » en tête de chaque page (cible `#contenu`).
- Cibles tactiles de 40 px au moins.

## Écarts avec DESIGN.md

- **Champs :** contour `#7f8c83` au lieu d'une bordure blanche, pour que le champ reste repérable sur une carte blanche (3:1 exigé par WCAG 1.4.11).
- **Vert et rouge du drapeau :** trop clairs pour du texte, ils ne servent qu'aux pastilles ; les textes utilisent leurs versions foncées.
- **Écran de connexion :** champs et bouton à angles de 10 px au lieu de pilules, carte à 14 px, à la demande de l'équipe (18/11).
- **Pas de notifications flottantes (Sonner) ni de hachures :** les confirmations s'affichent dans la page, et les interfaces n'ont pas de graphiques.
