/* Test de bout en bout de la page web (index.html) avec l'émulateur Firebase
   (comptes + base) et un vrai navigateur.
   Usage : cd tests && npm install && npm run test:web
   Scénario : Alice crée son compte et son budget, invite Carole ; Carole confirme
   son adresse et rejoint ; Bob ne voit rien ; un compte « d'origine » retrouve les
   données d'origine (racine), qui ne sont ni copiées ni déplacées. */
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const { initializeTestEnvironment } = require('@firebase/rules-unit-testing');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const PROJET = 'demo-budget';
const ORIG = 'ancien1@test.fr';
let n = 0, ko = 0;
function verif(nom, cond, detail){ n++; if(!cond) ko++; console.log((cond ? 'ok   ' : 'ÉCHEC') + ' ' + nom + (cond || detail == null ? '' : ' — ' + detail)); }
const attendre = ms => new Promise(r => setTimeout(r, ms));
async function jusqua(fn, ms){ const t = Date.now(); while(Date.now() - t < (ms || 15000)){ try{ if(await fn()) return true; }catch(e){} await attendre(200); } return false; }

(async () => {
  /* page fabriquée par le script, pointée vers le projet de démo de l'émulateur */
  const out = path.join(__dirname, 'out'); fs.mkdirSync(out, {recursive: true});
  execFileSync('python3', [path.join(ROOT, 'build', 'build_firebase.py'), path.join(out, 'index.html')]);
  let html = fs.readFileSync(path.join(out, 'index.html'), 'utf8').replace(/budget-familial-713e2/g, PROJET);
  html = html.replace('<head>', '<head><script>window.__BC_EMU = true;</script>');
  execFileSync('python3', [path.join(ROOT, 'build', 'build_firebase.py'), '--essai', path.join(out, 'essai.html')]);
  const htmlEssai = fs.readFileSync(path.join(out, 'essai.html'), 'utf8').replace(/budget-familial-713e2/g, PROJET)
    .replace('<head>', '<head><script>window.__BC_EMU = true;</script>');
  const rules = fs.readFileSync(path.join(ROOT, 'firestore.rules'), 'utf8').replace('adresse-1@exemple.fr', ORIG);

  /* règles + données d'origine dans l'émulateur */
  const env = await initializeTestEnvironment({ projectId: PROJET, firestore: { rules, host: '127.0.0.1', port: 8080 } });
  await env.clearFirestore();
  await env.withSecurityRulesDisabled(async ctx => {
    const f = ctx.firestore();
    await f.doc('config/main').set({ monthLabel: 'Budget d\'origine', moisCle: new Date().toISOString().slice(0, 7), revenus: [], lignes: [{id: 'l1', label: 'Courses', type: 'variable', budget: 300, reel: 0}], report: {compte: 1234, especes: 0} });
  });
  await fetch('http://127.0.0.1:9099/emulator/v1/projects/' + PROJET + '/accounts', {method: 'DELETE'});
  await fetch('http://127.0.0.1:9099/identitytoolkit.googleapis.com/v1/accounts:signUp?key=x', {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({email: ORIG, password: 'motdepasse1', returnSecureToken: true})});

  /* petit serveur : la page + les fichiers Firebase locaux (pas d'accès à gstatic ici) */
  const NM = path.join(__dirname, 'node_modules', 'firebase');
  const srv = http.createServer((req, res) => {
    if(req.url.startsWith('/essai/')){ res.writeHead(200, {'content-type': 'text/html; charset=utf-8'}); return res.end(htmlEssai); }
    if(req.url === '/' || req.url.startsWith('/index.html')){ res.writeHead(200, {'content-type': 'text/html; charset=utf-8'}); return res.end(html); }
    res.writeHead(404); res.end();
  }).listen(5077);
  const browser = await chromium.launch();
  async function nouvellePage(chemin){
    const ctx = await browser.newContext({viewport: {width: 390, height: 844}});
    const p = await ctx.newPage();
    p.errs = []; p.on('pageerror', e => p.errs.push(e.message));
    await p.route(/gstatic\.com\/firebasejs\/.*\/(firebase-[a-z]+-compat\.js)/, (route) => {
      const f = route.request().url().match(/(firebase-[a-z]+-compat\.js)/)[1];
      route.fulfill({status: 200, contentType: 'text/javascript', body: fs.readFileSync(path.join(NM, f))});
    });
    await p.route(/cdn\.jsdelivr\.net/, r => r.abort());
    await p.goto('http://127.0.0.1:5077' + (chemin || '/'));
    return p;
  }
  async function creerCompte(p, email){
    await p.waitForSelector('#lgSwitch'); await p.click('#lgSwitch');
    await p.fill('#lgEmail', email); await p.fill('#lgPass', 'motdepasse1'); await p.fill('#lgPass2', 'motdepasse1');
    await p.click('#lgBtn');
  }
  async function verifierEmail(email){
    const r = await (await fetch('http://127.0.0.1:9099/emulator/v1/projects/' + PROJET + '/oobCodes')).json();
    const c = r.oobCodes.filter(x => x.email === email && x.requestType === 'VERIFY_EMAIL').pop();
    if(c) await fetch(c.oobLink);
    return !!c;
  }

  /* --- Alice : nouveau compte, nouveau budget --- */
  const A = await nouvellePage();
  await creerCompte(A, 'alice@test.fr');
  verif('Alice : écran de bienvenue', await jusqua(() => A.$('#bvCreer')));
  await A.click('#bvCreer');
  verif('Alice : budget créé, écran « Votre budget est prêt »', await jusqua(() => A.$('#seedBtn')));
  await A.click('#seedBtn');
  verif('Alice : l\'appli s\'ouvre', await jusqua(() => A.$('[data-tab="comptes"]')), A.errs.join(' | ') + ' / ' + (await A.textContent('body')).slice(0,200));
  await A.click('[data-tab="ajout"]'); await A.waitForSelector('#qaLabel');
  await A.fill('#qaLabel', 'Boulangerie'); await A.fill('#qaMontant', '4,20'); await A.click('#qaAdd');
  const fid = await A.evaluate(() => JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('bc_ctx_')))).foyerId);
  let docs = {};
  await env.withSecurityRulesDisabled(async ctx => { const qs = await ctx.firestore().collection('foyers/' + fid + '/depenses').get(); qs.forEach(d => docs[d.id] = d.data()); });
  verif('Alice : dépense enregistrée dans SON foyer', await jusqua(async () => { let ok = false; await env.withSecurityRulesDisabled(async ctx => { const qs = await ctx.firestore().collection('foyers/' + fid + '/depenses').get(); ok = qs.docs.some(d => d.data().label === 'Boulangerie'); }); return ok; }));
  let racine = null;
  await env.withSecurityRulesDisabled(async ctx => { racine = (await ctx.firestore().doc('config/main').get()).data(); });
  verif('données d\'origine intactes', racine && racine.monthLabel === 'Budget d\'origine' && racine.report.compte === 1234);

  /* --- Alice invite Carole --- */
  await A.click('[data-tab="reglages"]'); await A.waitForSelector('#rgInvEmail');
  await A.fill('#rgInvEmail', 'Carole@Test.fr'); await A.click('#rgInvOk');
  verif('Alice : message d\'invitation prêt', await jusqua(async () => (await A.textContent('body')).includes('carole@test.fr') && !!(await A.$('.invit-box'))));
  await A.screenshot({path: path.join(out, 'web-reglages.png'), fullPage: true});

  /* --- Carole : compte, invitation, vérification, rejoindre --- */
  const C = await nouvellePage();
  await creerCompte(C, 'carole@test.fr');
  verif('Carole : voit l\'invitation', await jusqua(() => C.$('#bvInvOk')));
  await C.click('#bvInvOk');
  verif('Carole : refus tant que l\'adresse n\'est pas confirmée', await jusqua(async () => (await C.textContent('#bvInvMsg')).includes('Confirmez')));
  verif('Carole : e-mail de vérification envoyé', await verifierEmail('carole@test.fr'));
  await C.click('#bvInvOk');
  verif('Carole : rejoint et voit la dépense d\'Alice', await jusqua(async () => { const b = await C.$('[data-tab="ajout"]'); if(!b) return false; await C.evaluate(() => { state.tab = 'ajout'; state.sec = Object.assign(state.sec||{}, {deplist: true}); render(); }); return (await C.textContent('body')).includes('Boulangerie'); }, 15000));
  await C.click('[data-tab="reglages"]');
  verif('Carole : 2 membres affichés', await jusqua(async () => { const t = await C.textContent('body'); return t.includes('alice@test.fr') && t.includes('carole@test.fr'); }));

  /* --- Alice : un 2e portefeuille « Nous », et un virement de « Moi » vers « Nous » --- */
  await A.click('[data-tab="reglages"]'); await A.waitForSelector('#pfAjout');
  await A.click('#pfAjout'); await A.click('[data-pfnom="Nous"]'); await A.click('#pfCreer');
  verif('Alice : portefeuille « Nous » créé (nouveau budget vide)', await jusqua(() => A.$('#seedBtn'), 12000));
  await A.click('#seedBtn');
  await A.waitForSelector('#pfBtn'); await A.click('#pfBtn');
  verif('Alice : menu avec « Moi » et « Nous »', await jusqua(async () => { const o = await A.$$eval('.pf-item b', x => x.map(y => y.textContent)); return o.includes('Moi') && o.includes('Nous'); }, 15000));
  const nousId = await A.evaluate(() => document.querySelector('.pf-item.on').getAttribute('data-pfid'));
  const moiId = await A.evaluate(() => [...document.querySelectorAll('.pf-item')].find(o => o.querySelector('b').textContent === 'Moi').getAttribute('data-pfid'));
  await A.click('.pf-item[data-pfid="' + moiId + '"]');
  verif('Alice : retour dans « Moi » (la dépense Boulangerie est là)', await jusqua(async () => { if(!(await A.$('#pfBtn'))) return false; if(!(await A.textContent('#pfBtn')).includes('Moi')) return false; return await A.evaluate(() => (state.data.achats||[]).some(a => a.label === 'Boulangerie')); }, 15000));
  await A.click('[data-tab="ajout"]'); await A.click('[data-addmode="virement"]');
  verif('Alice : comptes de « Nous » proposés dans le virement', await jusqua(async () => (await A.$$eval('#virVers option', x => x.map(y => y.value))).includes('pf:' + nousId + ':compte')));
  await A.selectOption('#virDe', 'compte'); await A.selectOption('#virVers', 'pf:' + nousId + ':compte');
  await A.fill('#virMontant', '25'); await A.click('#virOk');
  let ici = null, labas = null;
  verif('virement noté dans « Moi » (sortie) et dans « Nous » (entrée)', await jusqua(async () => {
    await env.withSecurityRulesDisabled(async ctx => { const f = ctx.firestore();
      const a1 = await f.collection('foyers/' + moiId + '/transferts').get(); ici = a1.docs.map(d => ({id: d.id, ...d.data()})).find(x => x.vers === 'ext');
      const b1 = await f.collection('foyers/' + nousId + '/transferts').get(); labas = b1.docs.map(d => ({id: d.id, ...d.data()})).find(x => x.de === 'ext'); });
    return ici && labas && ici.id === labas.id && ici.montant === 25 && labas.montantVers === 25 && labas.vers === 'compte' && labas.ext.nom === 'Moi';
  }, 10000));

  await A.click('[data-tab="saisie"]'); await attendre(500);
  await A.click('#pfBtn'); await attendre(400);
  await A.screenshot({path: path.join(out, 'web-portefeuille.png')});
  await A.click('#pfBtn'); await attendre(300);
  await A.click('[data-tab="reglages"]'); await attendre(500);
  await A.screenshot({path: path.join(out, 'web-portefeuilles-reglages.png')});
  /* --- Bob : rien à voir --- */
  const B = await nouvellePage();
  await creerCompte(B, 'bob@test.fr');
  verif('Bob : écran de bienvenue sans invitation', await jusqua(async () => !!(await B.$('#bvCreer')) && !(await B.$('#bvInvOk'))));
  /* Bob importe une copie de secours au format de l'ancienne appli */
  const mois = new Date().toISOString().slice(0, 7);
  const copie = {app: 'budget-clair', docs: {
    'config/main': {monthLabel: 'Importé', moisCle: mois, report: {compte: 500, especes: 20}, revenus: [{id: 'r1', label: 'Salaire', mode: 'compte', budget: 1000, reel: 1000, recu: true}],
      lignes: [{id: 'l1', label: 'Courses', type: 'variable', paiement: 'carte', budget: 300, reel: 0}], epargnes: []},
    'depenses/a1': {mois, date: mois + '-02', label: 'Leclerc', posteId: 'l1', montant: 50, paiement: 'carte'},
    'transferts/t1': {mois, date: mois + '-03', sens: 'retrait', montant: 30}}};
  fs.writeFileSync(path.join(out, 'copie.json'), JSON.stringify(copie));
  await B.click('#bvCreer');
  await B.waitForSelector('#impFile', {state: 'attached'});
  await B.setInputFiles('#impFile', path.join(out, 'copie.json'));
  verif('Bob : copie de secours importée', await jusqua(async () => (await B.textContent('#monthTitle').catch(() => '')) === 'Importé', 12000));
  await B.click('[data-tab="comptes"]');
  verif('Bob : soldes repris de la copie (compte 1 420 €, espèces 50 €)', await jusqua(async () => { const t = (await B.textContent('body')).replace(/\s/g, ''); return t.includes('1420,00€') && t.includes('50,00€'); }));

  /* --- compte d'origine : retrouve les données d'origine --- */
  const O = await nouvellePage();
  await O.waitForSelector('#lgEmail');
  await O.fill('#lgEmail', ORIG); await O.fill('#lgPass', 'motdepasse1'); await O.click('#lgBtn');
  verif('compte d\'origine : budget d\'origine ouvert', await jusqua(async () => (await O.textContent('#monthTitle').catch(() => '')) === 'Budget d\'origine'));
  await O.click('[data-tab="comptes"]');
  verif('compte d\'origine : solde du compte repris (1 234 €)', await jusqua(async () => (await O.textContent('body')).replace(/\s/g, '').includes('1234,00€')));
  await O.click('[data-tab="reglages"]');
  verif('compte d\'origine : pas d\'invitation possible', await jusqua(async () => (await O.textContent('body')).includes('Budget d\'origine') && !(await O.$('#rgInvEmail'))));

  /* --- version d'essai : le compte d'origine n'y voit PAS les données d'origine --- */
  const E = await nouvellePage('/essai/');
  await E.waitForSelector('#lgEmail');
  await E.fill('#lgEmail', ORIG); await E.fill('#lgPass', 'motdepasse1'); await E.click('#lgBtn');
  verif('essai : bandeau « version d\'essai »', await jusqua(async () => (await E.textContent('body')).includes('Version d\'essai')));
  verif('essai : compte d\'origine → budget d\'essai à créer (données d\'origine pas ouvertes)', await jusqua(() => E.$('#bvCreer')));
  await E.click('#bvCreer');
  verif('essai : budget d\'essai créé', await jusqua(() => E.$('#seedBtn')));
  await E.click('#seedBtn');
  verif('essai : l\'appli s\'ouvre sur le budget d\'essai', await jusqua(async () => !!(await E.$('[data-tab="comptes"]')) && (await E.textContent('#monthTitle')) !== 'Budget d\'origine'));
  await E.click('[data-tab="ajout"]'); await E.waitForSelector('#qaLabel');
  await E.fill('#qaLabel', 'Essai'); await E.fill('#qaMontant', '99'); await E.click('#qaAdd');
  await attendre(800);
  let racine2 = null, depRacine = 0;
  await env.withSecurityRulesDisabled(async ctx => { const f = ctx.firestore(); racine2 = (await f.doc('config/main').get()).data(); depRacine = (await f.collection('depenses').get()).size; });
  verif('essai : données d\'origine toujours intactes', racine2.monthLabel === 'Budget d\'origine' && racine2.report.compte === 1234 && !racine2.comptes && depRacine === 0);

  /* --- bascule : la vraie appli, pour le compte d'origine qui a aussi un portefeuille d'essai --- */
  const V = await nouvellePage();
  await V.waitForSelector('#lgEmail');
  await V.fill('#lgEmail', ORIG); await V.fill('#lgPass', 'motdepasse1'); await V.click('#lgBtn');
  verif('bascule : s\'ouvre sur le budget d\'origine (« Nous »), pas sur le portefeuille d\'essai', await jusqua(async () => (await V.textContent('#monthTitle').catch(() => '')) === 'Budget d\'origine'));
  await V.click('#pfBtn');
  const noms = await V.$$eval('.pf-item b', x => x.map(y => y.textContent));
  verif('bascule : le menu montre « Nous » et le portefeuille d\'essai', noms.includes('Nous') && noms.length === 2, noms.join(', '));
  const essaiId = await V.evaluate(() => [...document.querySelectorAll('.pf-item')].find(o => o.querySelector('b').textContent !== 'Nous').getAttribute('data-pfid'));
  await V.click('.pf-item[data-pfid="' + essaiId + '"]');
  verif('bascule : ouvrir le portefeuille d\'essai', await jusqua(async () => (await V.$('#pfBtn')) && !(await V.textContent('#pfBtn')).includes('Nous')));
  await V.click('[data-tab="reglages"]'); await V.waitForSelector('#pfSuppr'); await V.click('#pfSuppr'); await V.waitForSelector('#pfSupprOk'); await attendre(400);
  await V.click('#pfSupprOk');
  /* la page a pu se redessiner au moment du toucher : on réessaie une fois si le bouton est toujours là */
  await attendre(1500); if(await V.$('#pfSupprOk:not([disabled])')) await V.click('#pfSupprOk');
  const okSuppr = await jusqua(async () => (await V.textContent('#monthTitle').catch(() => '')) === 'Budget d\'origine' && (await V.textContent('#pfBtn')).includes('Nous'), 20000);
  verif('bascule : portefeuille d\'essai supprimé, retour sur « Nous »', okSuppr, V.errs.join(' | ') + ' / msg: ' + (await V.textContent('#rgFoyerMsg').catch(() => '?')) + ' / titre: ' + (await V.textContent('#monthTitle').catch(() => '?')) + ' / pf: ' + (await V.textContent('#pfBtn').catch(() => '?')));
  let resteEssai = true, racine3 = null;
  await env.withSecurityRulesDisabled(async ctx => { const f = ctx.firestore(); resteEssai = (await f.doc('foyers/' + essaiId).get()).exists; racine3 = (await f.doc('config/main').get()).data(); });
  verif('bascule : le portefeuille d\'essai a bien disparu, les données d\'origine sont intactes', !resteEssai && racine3.report.compte === 1234);

  for(const [nom, p] of [['Alice', A], ['Carole', C], ['Bob', B], ['Origine', O], ['Essai', E], ['Bascule', V]]) verif('aucune erreur JS (' + nom + ')', !p.errs.length, p.errs.join(' | '));
  await browser.close(); srv.close(); await env.cleanup();
  console.log('\n' + (n - ko) + ' / ' + n + ' vérifications réussies');
  process.exit(ko ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
