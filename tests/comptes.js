/* Test des comptes multiples (version Claude + fausse base) :
   1. d'anciennes données (carte / espèces, retrait d'espèces) donnent les MÊMES soldes qu'avant ;
   2. compte en francs suisses, dépense en CHF, virement EUR -> CHF, virement vers un livret ;
   3. clôture : chaque compte reporte son solde.
   Usage : node tests/comptes.js */
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..');
const mois = new Date().toISOString().slice(0, 7);
const seed = {
  'config/main': {
    monthLabel: 'Test', moisCle: mois,
    report: {compte: 1000, especes: 50},
    revenus: [{id: 'r1', label: 'Salaire', source: 'salaire', mode: 'compte', budget: 2000, reel: 2000, recu: true},
              {id: 'r2', label: 'Vente', source: 'autre', mode: 'especes', budget: 30, reel: 30, recu: true}],
    lignes: [{id: 'l1', label: 'Loyer', type: 'fixe', paiement: 'carte', budget: 800, reel: 800, paye: true},
             {id: 'l2', label: 'Courses', type: 'variable', paiement: 'carte', budget: 400, reel: 0},
             {id: 'l3', label: 'Épargne', type: 'epargne', paiement: 'carte', budget: 100, reel: 0}],
    epargnes: [{id: 'e1', kind: 'livretA', label: 'Livret A', debut: 500}]
  },
  'depenses/a1': {mois, date: mois + '-02', label: 'Leclerc', posteId: 'l2', montant: 60, paiement: 'carte'},
  'depenses/a2': {mois, date: mois + '-03', label: 'Marché', posteId: 'l2', montant: 20, paiement: 'especes'},
  'versements/v1': {mois, date: mois + '-04', epId: 'e1', montant: 100, source: 'compte'},
  'transferts/t1': {mois, date: mois + '-05', sens: 'retrait', montant: 40}
};
/* formule de l'ancienne version */
const ancienCompte = 1000 + 2000 - (800 + 60 + 100) - 40;   // 2000
const ancienEspeces = 50 + 30 - 20 + 40;                    // 100
let ok = true;
function verif(nom, a, b){ const bon = Math.abs(a - b) < 0.005; if(!bon) ok = false; console.log((bon ? 'ok   ' : 'ÉCHEC') + ' ' + nom + ' : ' + a + (bon ? '' : ' (attendu ' + b + ')')); }
(async () => {
  const src = fs.readFileSync(path.join(ROOT, 'src', 'budget-clair.html'), 'utf8');
  const stub = fs.readFileSync(path.join(__dirname, 'stub-claude.js'), 'utf8');
  const out = path.join(__dirname, 'out'); fs.mkdirSync(out, {recursive: true});
  const page = path.join(out, 'comptes.html');
  fs.writeFileSync(page, '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><script>' + stub + '</script>' + src + '</body></html>');
  const browser = await chromium.launch();
  const p = await browser.newPage({viewport: {width: 390, height: 844}});
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.addInitScript(s => { window.__initStore = s; localStorage.clear(); }, seed);
  await p.goto('file://' + page); await p.waitForTimeout(1200);
  const soldes = () => p.evaluate(() => { const S = soldesComptes(); const o = {}; Object.keys(S).forEach(k => o[k] = Math.round(S[k].solde * 100) / 100); return o; });
  let S = await soldes();
  verif('ancien compte chèque', S.compte, ancienCompte);
  verif('anciennes espèces', S.especes, ancienEspeces);

  /* compte suisse, taux saisi à la main */
  await p.click('[data-tab="comptes"]'); await p.waitForTimeout(300);
  await p.click('#addCptBtn'); await p.waitForTimeout(300);
  const cid = await p.evaluate(() => state.cptOpen);
  await p.fill('[data-clabel="' + cid + '"]', 'Compte suisse'); await p.waitForTimeout(100);
  await p.selectOption('[data-cdev="' + cid + '"]', 'CHF'); await p.waitForTimeout(400);
  await p.fill('[data-taux="CHF"]', '1,05'); await p.dispatchEvent('[data-taux="CHF"]', 'change'); await p.waitForTimeout(300);
  /* virement 210 € -> compte suisse : 200 CHF annoncés par la banque */
await p.click('[data-tab="ajout"]'); await p.waitForTimeout(200); await p.click('[data-addmode="virement"]'); await p.waitForTimeout(300);
  await p.selectOption('#virDe', 'compte'); await p.waitForTimeout(150);
  await p.selectOption('#virVers', cid); await p.waitForTimeout(150);
  await p.fill('#virMontant', '210'); await p.waitForTimeout(150);
  verif('montant proposé à l\'arrivée (CHF)', +(await p.inputValue('#virRecu')).replace(',', '.'), 200);
  await p.fill('#virRecu', '198'); await p.waitForTimeout(150);
  await p.click('#virOk'); await p.waitForTimeout(400);
  /* virement compte -> livret A */
  await p.selectOption('#virDe', 'compte'); await p.waitForTimeout(150);
  await p.selectOption('#virVers', 'ep:e1'); await p.waitForTimeout(150);
  await p.fill('#virMontant', '50'); await p.click('#virOk'); await p.waitForTimeout(400);
  /* dépense de 30 CHF payée avec le compte suisse */
  await p.click('[data-addmode="carte"]'); await p.waitForTimeout(300);
  await p.selectOption('#qaCompte', cid); await p.waitForTimeout(300);
  await p.fill('#qaLabel', 'Migros'); await p.fill('#qaMontant', '30');
  await p.selectOption('#qaPoste', 'l2'); await p.waitForTimeout(150);
  await p.click('#qaAdd'); await p.waitForTimeout(500);
  S = await soldes();
  verif('compte chèque après virements', S.compte, ancienCompte - 210 - 50);
  verif('compte suisse (CHF)', S[cid], 198 - 30);
  verif('espèces inchangées', S.especes, ancienEspeces);
  const dep = await p.evaluate(() => state.data.achats.find(a => a.label === 'Migros'));
  verif('dépense Migros en euros (30 × 1,05)', dep.montant, 31.5);
  verif('livret A', await p.evaluate(() => epFin(state.data.epargnes[0])), 500 + 100 + 50);
  const total = await p.evaluate(() => Math.round(totals().totalComptes * 100) / 100);
  verif('total en euros', total, (ancienCompte - 260) + ancienEspeces + 168 * 1.05);
  await p.screenshot({path: path.join(out, 'comptes-test.png'), fullPage: true});

  /* clôture : report compte par compte */
  await p.click('[data-tab="bilan"]'); await p.waitForTimeout(300);
  await p.click('#closeMonthBtn'); await p.waitForTimeout(300);
  await p.click('#confirmCloseBtn'); await p.waitForTimeout(800);
  const rep = await p.evaluate(() => state.data.report);
  verif('report compte chèque', rep.compte, ancienCompte - 260);
  verif('report compte suisse', rep[cid], 168);
  verif('report espèces', rep.especes, ancienEspeces);
  S = await soldes();
  verif('nouveau mois : solde compte suisse', S[cid], 168);
  const arch = await p.evaluate(() => window.__store.docs['mois/' + Object.keys(window.__store.docs).find(k => k.startsWith('mois/')).slice(5)]);
  verif('archive : solde suisse', arch.totals.soldes[cid], 168);
  console.log('erreurs JS :', errors.length ? errors : 'aucune');
  await browser.close();
  process.exit(errors.length || !ok ? 1 : 0);
})();
