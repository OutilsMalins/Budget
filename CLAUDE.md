# Budget Clair — récap pour Claude Code

Appli de budget d'un couple (Tani et Lauryne), utilisée sur iPhone. Elle remplace leur ancien fichier Excel.
Depuis le 19/11/2026, la version page web est **ouverte à tous** : chacun crée son compte et a son propre budget (« foyer »), partageable par invitation.
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
- Les données sont personnelles et financières. Ne jamais les mettre dans le code, dans le dépôt ou dans un service externe. **Le dépôt est public** : pas de montants réels, pas d'adresses e-mail (les règles Firestore du dépôt gardent des adresses factices).
- **Ne jamais modifier l'appli factures (`OutilsMalins/factures`) ni la relier à l'appli budget** (demande explicite de l'utilisateur). Les deux applis restent totalement indépendantes.
- **Ne jamais perdre les données de l'utilisateur.** Toute évolution du format doit rester compatible avec les données existantes (voir « Comptes » : les anciens champs sont toujours lus).

## Fichiers

```
src/budget-clair.html     SOURCE UNIQUE de l'appli (version « artefact Claude », sans <html>/<head>/<body>)
build/build_firebase.py   fabrique la version page web (Firebase, comptes, foyers) à partir de la source
index.html                ANCIENNE appli en ligne (version d'avant le 19/11/2026), gardée telle quelle pendant l'essai
essai/index.html          NOUVELLE version, en essai (…/Budget/essai/) — générée par le script, ne pas modifier à la main
apple-touch-icon.png      icône iPhone (180×180, € blanc sur bleu)
firestore.rules           COPIE DE RÉFÉRENCE des règles Firestore (adresses factices : voir Déploiement)
tests/stub-claude.js      fausse base de données pour tester la source dans un navigateur
tests/smoke.js            test Playwright : 4 onglets, erreurs JS, boucle de rendu, captures
tests/comptes.js          comptes multiples : anciennes données = mêmes soldes, CHF, virements, clôture
tests/rules.test.js       règles Firestore dans l'émulateur (40 cas)
tests/web.test.js         page web + émulateur : inscription, foyer, invitation, import, données d'origine, version d'essai (27 vérifications)
```
La version « ami » (`autres/`, stockage local) n'est plus dans le dépôt : la page web ouverte à tous la remplace.

Commandes :

```bash
python3 build/build_firebase.py --essai  # src/budget-clair.html -> essai/index.html (pendant la période d'essai)
python3 build/build_firebase.py          # -> index.html : SEULEMENT le jour où l'utilisateur valide la bascule
node tests/smoke.js                      # Playwright (déjà installé dans l'environnement cloud)
node tests/comptes.js
node tests/smoke.js sauvegarde.json      # avec une « copie de secours » exportée par l'appli
cd tests && npm install                  # une fois : émulateur Firebase (Java requis) + SDK
npm run test:rules                       # règles Firestore
npm run test:web                         # page web complète (Firebase local servi depuis node_modules)
```

Vérification rapide de la syntaxe : extraire les blocs `<script>` dans un fichier `.js`, puis `node --check`.

## Déploiement : deux versions

### 0. Période d'essai (depuis le 20/11/2026)

- L'utilisateur garde l'**ancienne appli** à son adresse habituelle (`index.html` à la racine, inchangé) et essaie la **nouvelle** à `…/Budget/essai/`.
- La version d'essai (`--essai`) **n'ouvre jamais les données d'origine** : chacun y crée un budget d'essai (foyer) et peut y importer une copie de secours exportée depuis l'ancienne appli. Bandeau « Version d'essai » en haut. Mémoire locale séparée (`bc_ctx_essai_<uid>`).
- Ne pas faire tourner la nouvelle version sur les données d'origine en même temps que l'ancienne : l'ancienne ne connaît pas les comptes multiples (virements entre comptes comptés comme retraits d'espèces, report d'un seul compte à la clôture).
- **Bascule** (quand l'utilisateur le demande) : `python3 build/build_firebase.py` → `index.html`, puis supprimer `essai/` ou le garder pour les prochains essais.
- Les règles Firestore doivent déjà autoriser les foyers pour que l'essai fonctionne (voir plus bas).

### 1. Page web, la version principale

- **Hébergement :** GitHub Pages, dépôt `Budget`, adresse `https://<nom-utilisateur>.github.io/Budget/`. L'utilisateur a changé son nom GitHub : demandez-lui l'adresse exacte.
- **Mise à jour :** l'utilisateur dépose `index.html` (et l'icône si elle change) sur GitHub depuis Safari ou un ordinateur. L'appli GitHub pour iPhone ne permet sans doute pas de déposer un fichier.
- **Données :** Firebase, projet `budget-familial-713e2`.
  - connexion par e-mail et mot de passe (Firebase Auth) ;
  - données dans Firestore ;
  - SDK « compat » 10.14.1 chargé depuis gstatic ;
  - formule gratuite (Spark).
  - La config Firebase est dans `build_firebase.py`. La clé `apiKey` n'est pas un secret : la sécurité repose sur les règles Firestore.
- **Règles Firestore :** copie de référence dans `firestore.rules`. Les règles actives se collent dans la console Firebase (Firestore → Règles → Publier), **en remplaçant les deux adresses factices par les vrais e-mails du couple** (à demander à l'utilisateur, ne jamais les écrire dans le dépôt).
  - données d'origine (racine : `config`, `depenses`, `versements`, `transferts`, `mois`) : seulement ces deux e-mails ;
  - `foyers/{id}` + sous-collections : seulement les membres ; `invitations/{email}` ; `users/{uid}` (foyer choisi).
- **Création de compte :** Firebase Auth e-mail/mot de passe (inscription ouverte). Vérification de l'adresse obligatoire pour rejoindre un foyer par invitation.
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
- **Écran de connexion / création de compte / mot de passe oublié.**
- **Choix du budget (`resoudre`) :** si le compte peut lire `config/main` à la racine → mode « ancien » (données d'origine, préfixe vide). Sinon → foyer (`users/{uid}.foyer`, ou requête `membres array-contains uid`) → préfixe `foyers/<id>/`. Aucun foyer → écran de bienvenue (créer son budget, ou rejoindre via une invitation). Le choix est mémorisé (`localStorage bc_ctx_<uid>`) pour l'ouverture hors ligne.
- **`dbw`** : enveloppe `doc()` / `collection()` qui ajoute le préfixe. L'appli n'utilise que ces deux appels.
- **Premier lancement d'un budget vide :** « Commencer un budget vide » ou importer une copie de secours (`{app:'budget-clair', docs:{"chemin": données}}`, lots de 400).
- **Page Réglages** (`BC_HOOKS` : bouton rond en haut à droite) : compte, vérification d'adresse, foyer (nom, membres, invitations avec message à transmettre, quitter), copie de secours, suppression du compte (mot de passe redemandé ; seul membre → tout le budget est effacé).
- `window.__BC_EMU = true` (tests seulement) branche l'émulateur Firebase.

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

### Comptes et devises (19/11/2026)

- **`config.comptes`** : `[{id, label, banque, devise: EUR|CHF|USD|GBP, kind: courant|especes, archive}]`. Les ids **`compte`** (compte principal, toujours EUR, non supprimable) et **`especes`** sont ceux de l'ancienne version : `report {compte, especes}`, `paiement: carte|especes`, `mode` des revenus et `source` des versements restent valables tels quels.
- **Compte de chaque opération** : `cptDep(a)` (`a.compte`, sinon `paiement`), `cptRev(r)` (`r.mode` = id du compte), `cptFixe(l)` (`l.compte`), `cptVers(v)` (`v.source`), `tfDe/tfVers(x)` (`x.de/x.vers`, sinon l'ancien `x.sens` retrait/dépôt).
- **Devises** : le budget reste en euros. Une opération sur un compte en devise garde les deux montants : `montant` (EUR) + `devise` + `montantDevise`. Revenus et prélèvements en devise : `budgetDevise` / `reelDevise`, les euros suivent le taux (`syncEur`). Virement entre devises : `montant` (devise de départ) + `montantVers` (devise d'arrivée, modifiable : c'est ce que la banque annonce).
- **Taux** : `config.taux[dev] = {v (1 dev = v €), date, source: 'BCE'|'manuel', manuel}`. `majTaux()` interroge api.frankfurter.dev puis api.frankfurter.app (taux de référence BCE). **Pas testé depuis l'environnement cloud (hôte bloqué)** : la saisie manuelle sert de secours.
- **Soldes** : `soldesComptes()` → par compte : début (`report[id]`) + revenus − prélèvements − dépenses − épargne + virements reçus − envoyés. `totals().totalComptes` = total en euros. Clôture : `report[id]` = solde de chaque compte ; archive `totals.soldes`, `totals.totalComptes`, `snapshot.comptes`.
- **Virement** (`virementCard`, `state.vir`) : compte → compte (`transferts`), compte → placement (versement), placement → compte (versement négatif, ancien « puiser »).

### Les 4 onglets (+ Réglages en version page web)

- **Mois (`pageSaisie`)**, quatre cartes :
  - **`compteCard`** : total disponible sur tous les comptes + un bouton par compte, bouton « Virement », deux fins de mois estimées (« si plus aucune dépense » et « en dépensant tout le prévu », tous comptes), « cette semaine », les retards, « Puiser dans l'épargne » (prépare un virement). Le retrait/dépôt d'espèces et le détail du calcul sont passés dans l'onglet Comptes (virement, et détail par compte).
  - **`renderAchatsCard`** : saisie rapide d'une dépense (Dépense ou Remboursement, Besoin ou Envie, poste proposé automatiquement par `suggestionPoste`, favoris, répartition sur plusieurs postes). La liste des dépenses est repliable et a une recherche, y compris dans tous les mois.
  - **`aCocherCard`** : revenus reçus et prélèvements, cochés automatiquement à leur date par `autoPrelevements`.
  - **`versementsCard`** : l'épargne du mois.
- **Budget (`pageBudget`)** : cartes repliables (Revenus, Postes avec tri et filtres, Épargne, Investissements avec types et objectif), plus le « Prévisionnel du mois prochain » (`prochainCard`).
- **Comptes (`pageComptes`)** : virement, liste des comptes (détail, solde du 1er du mois, « solde aujourd'hui » qui recale le report, masquer), virements du mois, taux de change.
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
- **Style (19/11/2026)** : thème sobre (tokens `:root`, bloc « Style pro » en fin de `<style>`, qui prime sur les règles plus haut). Icônes SVG (`ICON`, `svgI`) dans la barre d'onglets et les boutons ; plus d'émojis décoratifs dans les titres (ceux des noms de postes et des bilans restent : ce sont des données).
- **Ordre `membres` / `emails` d'un foyer** : même ordre (création, `arrayUnion`, `arrayRemove`) ; « Retirer un membre » s'en sert pour retrouver l'uid.

## Décisions et demandes en attente

- **Refusé par l'utilisateur :** les courbes mois par mois (idée 6), retirer le tri et les filtres, retirer les options avancées.
- **Plus tard :** un résumé en haut de l'onglet Mois (idée 3), l'import CSV de la banque (idée 12), le sort du Pareto.
- **Fait le 19/11/2026 :** plusieurs comptes bancaires + virements + CHF ; nouveau style ; ouverture à tous (comptes, foyers, invitations). La version « ami » n'a plus de raison d'être.
- **Reste à faire pour une ouverture publique :** mentions légales et politique de confidentialité (RGPD) — pas rédigées, à faire relire ; suppression automatique des comptes inactifs (non faite) ; surveiller les quotas Spark.
- **Pas testé sur un vrai iPhone** ni avec le vrai projet Firebase (tests faits avec l'émulateur).
- **Peut-être un jour :** une version payante pour d'autres personnes. Il faudrait alors :
  - (fait) plusieurs comptes, données par foyer, règles propres à chaque foyer ;
  - **un autre hébergeur**, car GitHub Pages interdit les sites qui vendent un logiciel en ligne ;
  - **la formule payante Firebase (Blaze)** ;
  - **un système de paiement** ;
  - **les démarches légales** : RGPD, mentions légales et conditions de vente, statut de micro-entreprise.

  Conseil donné : d'abord faire tester gratuitement à 5 à 10 personnes.
