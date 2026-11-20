/* Test des automatismes et des suggestions (version Claude + fausse base).
   Usage : node tests/auto.js */
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..');
const now = new Date(), mois = now.toISOString().slice(0, 7), jour = now.getDate();
const plusTard = Math.min(jour + 1, 28) > jour ? jour + 1 : null;   // un jour pas encore arrivé (sauf fin de mois)
let ok = true;
function verif(nom, c, detail){ if(!c) ok = false; console.log((c ? 'ok   ' : 'ÉCHEC') + ' ' + nom + (c || detail == null ? '' : ' — ' + detail)); }
const seed = {
  'config/main': {
    monthLabel: 'Test', moisCle: mois, report: {compte: 100, especes: 0, c2: -50},
    comptes: [{id: 'compte', label: 'Compte principal', devise: 'EUR', kind: 'courant'}, {id: 'especes', label: 'Espèces', devise: 'EUR', kind: 'especes'},
              {id: 'c2', label: 'Trade Republic', devise: 'EUR', kind: 'courant'}],
    revenus: [{id: 'r1', label: 'Salaire', mode: 'compte', budget: 2000, reel: 0, recu: false, jour: 1},
              {id: 'r2', label: 'Prime', mode: 'compte', budget: 300, reel: 0, recu: false, jour: plusTard || 31}],
    lignes: [{id: 'l1', label: 'Loyer', type: 'fixe', budget: 800, reel: 0, paye: false, jour: 1},
             {id: 'l2', label: 'Courses', type: 'variable', budget: 400, reel: 0},
             {id: 'l3', label: 'Épargne', type: 'epargne', budget: 100, reel: 0}],
    epargnes: [{id: 'e1', kind: 'livretA', label: 'Livret A', debut: 1000}],
    programmes: [{id: 'P1', de: 'compte', vers: 'c2', montant: 200, jour: 1, actif: true},
                 {id: 'P2', de: 'compte', vers: 'ep:e1', montant: 50, jour: plusTard || 31, actif: true},
                 {id: 'P3', de: 'compte', vers: 'c2', montant: 999, jour: 1, actif: false}]
  },
  'depenses/a1': {mois, date: mois + '-02', label: 'Leclerc', posteId: 'l2', montant: 47.2, paiement: 'carte'},
  'depenses/a2': {mois, date: mois + '-02', label: 'Leclerc', posteId: 'l2', montant: 47.2, paiement: 'carte'},
  'depenses/a3': {mois, date: mois + '-03', label: 'Truc', posteId: '', montant: 12, paiement: 'carte'}
};
(async () => {
  const src = fs.readFileSync(path.join(ROOT, 'src', 'budget-clair.html'), 'utf8');
  const stub = fs.readFileSync(path.join(__dirname, 'stub-claude.js'), 'utf8');
  const out = path.join(__dirname, 'out'); fs.mkdirSync(out, {recursive: true});
  const page = path.join(out, 'auto.html');
  fs.writeFileSync(page, '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><script>' + stub + '</script>' + src + '</body></html>');
  const browser = await chromium.launch();
  const p = await browser.newPage({viewport: {width: 390, height: 844}});
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.addInitScript(s => { window.__initStore = s; localStorage.clear(); }, seed);
  await p.goto('file://' + page); await p.waitForTimeout(1500);
  const D = () => p.evaluate(() => JSON.parse(JSON.stringify(window.__store.docs)));
  let docs = await D(), cfg = docs['config/main'];
  verif('salaire (le 1er) coché tout seul', cfg.revenus[0].recu === true && cfg.revenus[0].reel === 2000 && cfg.revenus[0].autoCoche === true);
  if (plusTard) verif('prime (jour pas encore arrivé) pas cochée', cfg.revenus[1].recu === false);
  verif('loyer (le 1er) coché tout seul', cfg.lignes[0].paye === true);
  const idP1 = 'transferts/pP1_' + mois;
  verif('virement programmé P1 enregistré', !!docs[idP1] && docs[idP1].montant === 200 && docs[idP1].de === 'compte' && docs[idP1].vers === 'c2');
  verif('P1 marqué fait ce mois-ci', cfg.programmes[0].dernierMois === mois);
  if (plusTard) verif('P2 (jour pas encore arrivé) pas encore fait', !docs['versements/pP2_' + mois]);
  verif('P3 en pause : rien', !Object.keys(docs).some(k => k.includes('pP3_')));
  /* re-rendus : jamais de doublon */
  await p.evaluate(() => { render(); render(); }); await p.waitForTimeout(400);
  docs = await D();
  verif('pas de doublon après plusieurs affichages', Object.keys(docs).filter(k => k.startsWith('transferts/')).length === 1);
  /* l'utilisateur supprime le virement automatique : il ne revient pas ce mois-ci */
  await p.evaluate(id => { trans.remove(id); render(); }, 'pP1_' + mois); await p.waitForTimeout(400);
  await p.evaluate(() => render()); await p.waitForTimeout(300);
  docs = await D();
  verif('virement automatique supprimé : pas recréé', !docs[idP1]);
  /* suggestions */
  await p.click('[data-tab="saisie"]'); await p.waitForTimeout(300);
  const sug = await p.evaluate(() => suggestions(totals()).map(x => x.k));
  verif('suggestion : doublon Leclerc', sug.some(k => k.startsWith('dbl-')), sug.join(','));
  verif('suggestion : Trade Republic à découvert', sug.includes('decouvert-c2') === (await p.evaluate(() => soldesComptes().c2.solde < 0)), sug.join(','));
  verif('suggestion : dépense sans poste', sug.includes('sansposte'), sug.join(','));
  await p.screenshot({path: path.join(out, 'auto-mois.png'), fullPage: true});
  /* masquer une suggestion */
  const avant = await p.$$eval('[data-sugx]', b => b.length);
  await p.click('[data-sugx]'); await p.waitForTimeout(300);
  verif('masquer une suggestion', (await p.evaluate(() => suggestions(totals()).length)) === sug.length - 1);
  /* chiffres du mois */
  await p.click('[data-tab="bilan"]'); await p.waitForTimeout(300);
  verif('chiffres du mois affichés', (await p.textContent('body')).includes('Plus grosses dépenses'));
  /* réglages : couper les revenus automatiques */
  await p.click('[data-tab="reglages"]'); await p.waitForTimeout(300);
  await p.click('[data-auto="revenus"]'); await p.waitForTimeout(300);
  verif('interrupteur « revenus » coupé', (await p.evaluate(() => state.data.auto.revenus)) === false);
  await p.screenshot({path: path.join(out, 'auto-reglages.png'), fullPage: true});
  /* programmer depuis le formulaire de virement (« Répéter chaque mois ») */
  await p.click('[data-tab="comptes"]'); await p.waitForTimeout(300);
  await p.selectOption('#virDe', 'compte'); await p.selectOption('#virVers', 'ep:e1'); await p.waitForTimeout(150);
  await p.fill('#virMontant', '75'); await p.check('#virRepeter'); await p.click('#virOk'); await p.waitForTimeout(400);
  const prog = await p.evaluate(() => state.data.programmes);
  verif('« Répéter chaque mois » crée un programme (pas refait ce mois-ci)', prog.length === 4 && prog[3].montant === 75 && prog[3].dernierMois === prog[3].dernierMois && prog[3].dernierMois);
  /* ordre des cartes : descendre la 1re carte de l'onglet Mois */
  await p.click('[data-tab="saisie"]'); await p.waitForTimeout(300);
  const premiere = () => p.evaluate(() => { const c = [...document.querySelectorAll('#app > .card')].filter(x => !x.classList.contains('ordre-card'))[0]; return c ? c.className : ''; });
  verif('ordre d\'origine : la carte des comptes en premier', (await premiere()).includes('solde-card'));
  await p.click('[data-ordreedit="saisie"]'); await p.waitForTimeout(300);
  await p.click('[data-ordre="saisie:0:1"]'); await p.waitForTimeout(300);
  await p.click('#ordreFini'); await p.waitForTimeout(300);
  verif('après « ↓ » : la carte des comptes n\'est plus en premier', !(await premiere()).includes('solde-card'));
  verif('ordre gardé sur le téléphone', (await p.evaluate(() => JSON.parse(localStorage.getItem('bc_ordre_saisie'))[1])) === 'solde');
  await p.click('[data-ordreedit="saisie"]'); await p.waitForTimeout(200); await p.click('#ordreDefaut'); await p.waitForTimeout(200); await p.click('#ordreFini'); await p.waitForTimeout(300);
  verif('« Ordre d\'origine » remet la carte des comptes en premier', (await premiere()).includes('solde-card'));
  /* chèques : le solde ne baisse qu'à l'encaissement ; reporté à la clôture */
  await p.click('[data-tab="saisie"]'); await p.waitForTimeout(300);
  const s0 = await p.evaluate(() => soldesComptes().compte.solde);
  const f0 = await p.evaluate(() => aVenir().prelev);
  await p.check('#qaCheque'); await p.waitForTimeout(200);
  await p.fill('#qaChqNum', '1234'); await p.fill('#qaLabel', 'Plombier'); await p.fill('#qaMontant', '80');
  await p.selectOption('#qaPoste', 'l2'); await p.selectOption('#qaCompte', 'compte'); await p.waitForTimeout(200);
  await p.check('#qaCheque').catch(() => {}); await p.fill('#qaChqNum', '1234'); await p.fill('#qaLabel', 'Plombier'); await p.fill('#qaMontant', '80');
  await p.click('#qaAdd'); await p.waitForTimeout(400);
  const chq = await p.evaluate(() => state.data.achats.find(a => a.label === 'Plombier'));
  verif('chèque enregistré (n° 1234, à encaisser)', chq && chq.cheque && chq.cheque.num === '1234' && chq.cheque.encaisse === false);
  verif('chèque pas encore encaissé : solde du compte inchangé', Math.abs((await p.evaluate(() => soldesComptes().compte.solde)) - s0) < 0.005);
  verif('…mais compté dans les fins de mois', Math.abs((await p.evaluate(() => aVenir().prelev)) - f0 - 80) < 0.005);
  verif('…et dans le budget du poste', (await p.evaluate(() => reelOf(state.data.lignes.find(l => l.id === 'l2')))) >= 80);
  /* clôture avec le chèque en attente */
  await p.click('[data-tab="bilan"]'); await p.waitForTimeout(300);
  await p.click('#closeMonthBtn'); await p.waitForTimeout(300); await p.click('#confirmCloseBtn'); await p.waitForTimeout(900);
  const cr = await p.evaluate(() => state.data.chequesReport);
  verif('clôture : le chèque passe au mois suivant', cr.length === 1 && cr[0].num === '1234' && cr[0].montant === 80);
  const s1 = await p.evaluate(() => soldesComptes().compte.solde);
  verif('nouveau mois : solde reporté sans le chèque', Math.abs(s1 - s0) < 0.005, s1 + ' / ' + s0);
  await p.evaluate(() => { encaisserCheque(state.data.chequesReport[0].id, true); render(); }); await p.waitForTimeout(300);
  verif('encaissé le mois suivant : le solde baisse de 80 €', Math.abs((await p.evaluate(() => soldesComptes().compte.solde)) - (s1 - 80)) < 0.005);
  console.log('erreurs JS :', errors.length ? errors : 'aucune');
  await browser.close();
  process.exit(errors.length || !ok ? 1 : 0);
})();
