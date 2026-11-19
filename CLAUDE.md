# Budget Clair — récap pour Claude Code

Appli de budget d'un couple (Tani et Lauryne), utilisée sur iPhone. Elle remplace leur ancien fichier Excel.
Tout est en **un seul fichier HTML** (HTML + CSS + JavaScript, sans framework, sans étape de compilation).
Toute l'interface est **en français**.

## Règles à respecter (demandées par l'utilisateur)

- **Être objectif et réaliste. Ne rien inventer.** Pas de montants ni de classements inventés, et pas de « conseils » présentés comme des certitudes. Si on ne sait pas, on le dit.
- **Dire honnêtement les limites.** Pas de synchronisation bancaire. On ne peut pas tester sur un vrai iPhone. On ne voit pas les écrans Firebase ou GitHub de l'utilisateur.
- **Ne pas retirer** sans qu'il le demande :
  - le tri et les filtres de l'onglet Budget ;
  - les « options avancées » de l'onglet Mois ;
  - le Pareto (il a dit « on verra plus tard »).
- **L'utilisateur n'est pas développeur.** Expliquer simplement, étape par étape, en français.
- **Toute modification de l'appli doit aller dans les DEUX versions** (voir Déploiement) :
  1. modifier `src/budget-clair.html` ;
  2. reconstruire `index.html` avec le script ;
  3. l'utilisateur envoie le fichier sur GitHub.
- Les données sont personnelles et financières. Ne jamais les mettre dans le code, dans le dépôt ou dans un service externe.

## Fichiers

```
src/budget-clair.html     SOURCE UNIQUE de l'appli (version « artefact Claude », sans <html>/<head>/<body>)
build/build_firebase.py   fabrique la version page web (Firebase) à partir de la source
index.html            version page web générée (ne pas modifier à la main)
apple-touch-icon.png  icône iPhone (180×180, € blanc sur bleu)
tests/stub-claude.js      fausse base de données pour tester la source dans un navigateur
tests/smoke.js            test Playwright : 3 onglets, erreurs JS, boucle de rendu, captures
tests/fakefb.js           faux Firebase (connexion + Firestore) pour tester index.html
autres/Mon budget ….html  version « ami » autonome (stockage local), ANCIENNE (n'a pas les derniers ajouts)
```

Commandes :

```bash
python3 build/build_firebase.py          # src/budget-clair.html -> index.html
node tests/smoke.js                      # nécessite : npm i -D playwright && npx playwright install chromium
node tests/smoke.js sauvegarde.json      # avec une « copie de secours » exportée par l'appli
```

Vérification rapide de la syntaxe : extraire les blocs `<script>` dans un fichier `.js`, puis `node --check`.

## Déploiement : deux versions

### 1. Page web, la version principale

- **Hébergement :** GitHub Pages, dépôt `Budget`, adresse `https://<nom-utilisateur>.github.io/Budget/`. L'utilisateur a changé son nom GitHub : demandez-lui l'adresse exacte.
- **Mise à jour :** l'utilisateur dépose `index.html` (et l'icône si elle change) sur GitHub depuis Safari ou un ordinateur. L'appli GitHub pour iPhone ne permet sans doute pas de déposer un fichier.
- **Données :** Firebase, projet `budget-familial-713e2`.
  - connexion par e-mail et mot de passe (Firebase Auth) ;
  - données dans Firestore ;
  - SDK « compat » 10.14.1 chargé depuis gstatic ;
  - formule gratuite (Spark).
  - La config Firebase est dans `build_firebase.py`. La clé `apiKey` n'est pas un secret : la sécurité repose sur les règles Firestore.
- **Règles Firestore :** elles limitent lecture et écriture aux **deux e-mails** du couple. Elles se règlent dans la console Firebase (Firestore → Règles) et ne sont pas dans ce dossier.
- Sur iPhone, la page est ajoutée à l'écran d'accueil (« Ouvrir comme app web »).

### 2. Artefact Claude, la version d'origine

- Lien : `https://claude.ai/artifact/V8pQczQxX2ZbgSUkhbD7Sz`
- Capacités : `db` (base partagée) et `downloads`, contrat 0.2.52.
- Elle a été publiée depuis Claude (Cowork). Claude Code ne peut sans doute pas la republier : signalez-le à l'utilisateur si une modification doit y aller aussi.

### Ce que fait `build_firebase.py`

Il prend la source et remplace des morceaux de texte précis. Chaque `rep(a, b)` **vérifie que `a` apparaît exactement une fois**. Si vous modifiez la source à ces endroits, le script s'arrête et il faut mettre à jour la chaîne dans le script. C'est déjà arrivé avec `pageBilan`. Il fait les changements suivants :

- **Fichier complet :** il ajoute `<!doctype html>` et des balises `<head>` et `<body>` complètes.
- **Icône :** il lie `apple-touch-icon.png` au lieu d'une image intégrée.
- **Remplace `window.claude.use('db')` par Firestore :**
  - `ignoreUndefinedProperties` et persistance hors ligne activés ;
  - mêmes appels que dans l'appli : `doc`, `collection`, `where`, `orderBy`, `limit`, `get`, `onSnapshot`, `set`, `update`, `delete`.
- **Remplace `downloads.save`** par un téléchargement de fichier. Sur iOS, il utilise `navigator.share` avec un fichier.
- **Ajoute un écran de connexion,** avec un message clair si le compte n'est pas autorisé.
- **Premier lancement :** propose « Importer une sauvegarde ». Le JSON a la forme `{app:'budget-clair', docs:{"chemin": données}}` et l'import se fait par lots de 400.
- **Budget vide :** remplace les données de départ venues d'Excel par un budget vide.
- **Ajoute une carte « Compte » à la fin du Bilan (`compteFbCard`) :** qui est connecté, « 🛟 Copie de secours » (export JSON) et « Se déconnecter ».

## Architecture de `src/budget-clair.html`

- **Style du code :** JavaScript « ES5 » (`var`, `function`, chaînes concaténées). Garder ce style.
- **Rendu :** `render()` reconstruit tout `#app` en `innerHTML`, puis `wireEvents()` rebranche les gestionnaires avec `querySelectorAll('[data-…]')`.
- **Re-rendus repoussés :** `requestRender()` attend si un champ a le focus ou si un doigt est posé sur l'écran (`needsRender`, `flushDeferredRender`). `rerenderKeepFocus()` re-rend en gardant le champ actif.
- **État :** l'objet global `state`. Il contient :
  - les données (`data`, `history`) ;
  - le choix de l'onglet (`tab` : `saisie` | `budget` | `bilan`) ;
  - les sections dépliées (`sec`, gardé dans `localStorage` sous `bc_sec`) ;
  - l'aide ouverte (`aide`) ;
  - les analyses en cours (`anaSel`, `anaLoad`, `anaLock`, `coachEtape`), etc.
- **Petits outils d'affichage :**
  - `sec(id, ouvertParDéfaut, titre, contenu)` : section repliable (`<details>`) ;
  - `plier(id, carteHtml, droite)` : rend une carte entière repliable. Il gère aussi les cartes à bandeau `card-head`, comme « Où va l'argent » ;
  - `seg(clé, options, valeur)` : boutons à bascule ;
  - `aideBtn(k)` et `aideTxt(k, html)` : icône ⓘ qui déplie une explication.
- **Enregistrement :**
  - `persist(immédiat, champs)` enregistre `config/main` ; `flushConfig` regroupe les écritures ;
  - `CollSync` synchronise une collection pour le mois en cours (`deps`, `vers`, `trans`).
- **⚠️ Comportement de la base :** `update()` **fusionne les objets imbriqués mais remplace les tableaux**. Pour « vider » une valeur dans un objet imbriqué (par exemple `prochain[mois].lignes[id]`), il faut écrire `null`, pas supprimer la clé.

### Données

- **`config/main`** contient les champs de `CONFIG_FIELDS` : `monthLabel`, `moisCle` (ex. `2026-11`), `revenus`, `lignes`, `epargnes`, `report`, `favoris`, `prochain`, `types`.
  - **`lignes`** (les postes) : `{id, label, type: fixe|variable|epargne|invest, budget, reel, paye, dispensable (true = « envie »), jour (jour du prélèvement), autoMois, autoCoche}`
  - **`revenus`** : `{id, label, budget, reel, recu, source, mode: compte|especes}`
  - **`epargnes`** (les placements) : `{id, kind, label, plateforme (« Où ? »), debut, investi, finOverride, valeurDate, verseAuMoment, histo:[{mois, valeur, investi}], objectif}`
  - **`types`** : types de placement personnalisés (ex. LJMO).
  - **`prochain`** : `{"AAAA-MM": {lignes:{id:montant}, revenus:{id:montant}, coach:{idPiste:{delta, le}}}}`. C'est le prévisionnel du mois suivant, appliqué à la clôture.
  - **`report`** : `{compte, especes}`, les soldes reportés du mois précédent.
- **`depenses/{id}`** : `{mois, date, label, posteId, montant, paiement: carte|especes, nature: besoin|envie (facultatif), splitOf}`. Un montant négatif est un remboursement.
- **`versements/{id}`** : `{mois, date, epId, montant, source, sens}`. Un montant négatif est un retrait pour « puiser dans l'épargne ».
- **`transferts/{id}`** : retraits et dépôts d'espèces entre le compte et le porte-monnaie.
- **`mois/{AAAA-MM}`** : le mois archivé à la clôture : `{id, label, closedAt, totals:{…}, bilan:[{ic, txt}], snapshot:{revenus, lignes, epargnes, achats, versements, transferts, report}}`.
- **Calculs principaux :**
  - `totals()` calcule tous les totaux du mois en cours (prévus `…B` et réels `…R`, soldes compte et espèces) ;
  - `reelOf(ligne)` donne le réel d'un poste ;
  - `natureDe(dépense)` dit besoin ou envie : le choix fait sur la dépense passe avant celui du poste.

### Les 3 onglets

- **Mois (`pageSaisie`)**, quatre cartes :
  - **`compteCard`** : solde du compte et des espèces, avec deux fins de mois estimées (« si plus aucune dépense » et « en dépensant tout le prévu »). Elle affiche aussi « cette semaine », les retards et l'aide pour puiser dans l'épargne.
  - **`renderAchatsCard`** : saisie rapide d'une dépense (Dépense ou Remboursement, Besoin ou Envie, poste proposé automatiquement par `suggestionPoste`, favoris, répartition sur plusieurs postes). La liste des dépenses est repliable et a une recherche, y compris dans tous les mois.
  - **`aCocherCard`** : revenus reçus et prélèvements, cochés automatiquement à leur date par `autoPrelevements`.
  - **`versementsCard`** : l'épargne du mois.
- **Budget (`pageBudget`)** : cartes repliables (Revenus, Postes avec tri et filtres, Épargne, Investissements avec types et objectif), plus le « Prévisionnel du mois prochain » (`prochainCard`).
- **Bilan (`pageBilan`)** :
  - bandeau PDF après une clôture ;
  - carte **« 🔍 Analyser mon budget »** ;
  - cartes repliables : Bilan du mois, Où va l'argent (règle 50/30/20, Prévu ou Réel, colonne Cible), Pareto, Historique ;
  - bouton « 📦 Clôturer » (`closePanel` puis `doCloseMonth`) ;
  - téléchargement du PDF de chaque mois.

### Analyses (`coachCard`)

Quatre boutons. Chacun affiche un petit chargement mis en scène (environ 2,5 s, le calcul est instantané), puis le résultat :

| id | Bouton | Fonction | Disponible après |
|---|---|---|---|
| `eco` | 💰 Mes pistes d'économies | `anaEco` + `coachAnalyse` | 1 mois complet |
| `point` | 🚦 Point du mois | `anaPoint` | toujours |
| `hab` | 🏪 Mes habitudes | `anaHabitudes` | 1 mois complet |
| `real` | 📅 Budget réaliste | `anaReel` + `anaReelCalc` | 3 mois complets |

- **Mois complet** (`moisComplet`) : un mois clôturé qui a au moins 10 dépenses rangées dans un poste. Le compte se fait avec `nbMoisComplets()`, et les analyses bloquées affichent 🔒 avec une barre de progression.
- **`coachAnalyse(m?)`** :
  - Sans argument, il analyse le mois en cours (avec boutons). Avec un mois archivé, il sert pour le PDF.
  - Il se base sur au plus les 3 derniers mois complets.
  - Il calcule l'épargne prévue par rapport au repère de 20 % des revenus, puis des pistes chiffrées : argent prévu sans destination, abonnements (fixes « envie »), habitudes repérées dans le nom des dépenses (`THEMES` : jeux d'argent, achats en ligne, restos et bars, cafés, tabac), puis les autres envies poste par poste.
  - Il ajoute une partie « À surveiller » (rythme, gros achats, prévu trop bas, retrait d'épargne) et le temps pour atteindre les objectifs de placement.
- **Ce qu'il respecte :**
  - un poste dont les dépenses du mois ont toutes été marquées « besoin » n'est pas proposé comme envie à réduire ;
  - le Budget réaliste ne baisse jamais un besoin sur un seul mois, ni sous ce qui est déjà dépensé ce mois-ci ;
  - il ne propose jamais d'augmenter une envie ;
  - un poste qui ne vaut que par une grosse dépense ponctuelle reste tel quel.
- **« Mettre dans le budget de <mois> » (`coachAppliquer`) :** modifie seulement `prochain[mois suivant]`. Il enregistre les **écarts** (`delta`) dans `prochain[mois].coach[id]`, et `coachAnnuler` les retire. Ainsi chaque piste s'annule seule, même si plusieurs touchent la ligne Épargne.
- Les pistes sont aussi ajoutées au PDF du mois (section « Pistes pour épargner plus »).

### PDF

- **Bibliothèques :** jsPDF 2.5.2 et jspdf-autotable 3.8.4, depuis cdn.jsdelivr.net, chargées seulement au premier export (`chargerPdfLibs`).
- **Nettoyage du texte (`pdfTxt`) :** il retire les émojis et les caractères que les polices PDF de base ne savent pas afficher, et remplace − ≤ ≥ →.
- **Construction :** `donneesMois(m)` prépare les données et `bilanPdf(mois)` produit le fichier.
- **Contenu :** les chiffres du mois, le bilan, les pistes, les revenus, le détail par catégorie et le tableau 50/30/20. Le détail dépense par dépense **a été retiré à la demande de l'utilisateur**.

## Pièges connus

- **iPhone et zoom :** tout champ avec un texte de moins de 16 px fait zoomer Safari. Une règle CSS force 16 px sur mobile.
- **Réécriture de la page pendant un dépliage :** si la page est reconstruite pendant qu'on déplie une section, il faut re-rendre seulement si l'état a changé. Sinon, la page boucle sans fin. À vérifier : **0 rendu en 1,5 s sans rien toucher** (c'est ce que mesure `tests/smoke.js`).
- **Pareto dans une section fermée :** sa largeur vaut 0, donc on le redessine à l'ouverture (`b-pareto`).
- **Ancien tableau qui débordait :** une règle globale `table{min-width:720px}` existe. Mettre `min-width:0` sur les nouveaux tableaux.
- **Mise en page :** tester à 390 px de large (iPhone).

## Décisions et demandes en attente

- **Refusé par l'utilisateur :** les courbes mois par mois (idée 6), retirer le tri et les filtres, retirer les options avancées.
- **Plus tard :** un résumé en haut de l'onglet Mois (idée 3), l'import CSV de la banque (idée 12), le sort du Pareto.
- **Proposé, pas encore fait :** mettre à jour la version « ami » (`autres/`) avec les derniers ajouts.
- **Peut-être un jour :** une version payante pour d'autres personnes. Il faudrait alors :
  - **plusieurs comptes**, avec les données sous `users/{uid}/…` et des règles Firestore propres à chaque utilisateur ;
  - **un autre hébergeur**, car GitHub Pages interdit les sites qui vendent un logiciel en ligne ;
  - **la formule payante Firebase (Blaze)** ;
  - **un système de paiement** ;
  - **les démarches légales** : RGPD, mentions légales et conditions de vente, statut de micro-entreprise.

  Conseil donné : d'abord faire tester gratuitement à 5 à 10 personnes.
