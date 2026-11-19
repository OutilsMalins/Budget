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
async function jusqua(fn, ms){ const t = Date.now(); while(Date.now() - t < (ms || 8000)){ try{ if(await fn()) return true; }catch(e){} await attendre(200); } return false; }

(async () => {
  /* page fabriquée par le script, pointée vers le projet de démo de l'émulateur */
  const out = path.join(__dirname, 'out'); fs.mkdirSync(out, {recursive: true});
  execFileSync('python3', [path.join(ROOT, 'build', 'build_firebase.py'), path.join(out, 'index.html')]);
  let html = fs.readFileSync(path.join(out, 'index.html'), 'utf8').replace(/budget-familial-713e2/g, PROJET);
  html = html.replace('<head>', '<head><script>window.__BC_EMU = true;</script>');
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
    if(req.url === '/' || req.url.startsWith('/index.html')){ res.writeHead(200, {'content-type': 'text/html; charset=utf-8'}); return res.end(html); }
    res.writeHead(404); res.end();
  }).listen(5077);
  const browser = await chromium.launch();
  async function nouvellePage(){
    const ctx = await browser.newContext({viewport: {width: 390, height: 844}});
    const p = await ctx.newPage();
    p.errs = []; p.on('pageerror', e => p.errs.push(e.message));
    await p.route(/gstatic\.com\/firebasejs\/.*\/(firebase-[a-z]+-compat\.js)/, (route) => {
      const f = route.request().url().match(/(firebase-[a-z]+-compat\.js)/)[1];
      route.fulfill({status: 200, contentType: 'text/javascript', body: fs.readFileSync(path.join(NM, f))});
    });
    await p.route(/cdn\.jsdelivr\.net/, r => r.abort());
    await p.goto('http://127.0.0.1:5077/');
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
  verif('Alice : l\'appli s\'ouvre', await jusqua(() => A.$('[data-tab="comptes"]')));
  await A.fill('#qaLabel', 'Boulangerie'); await A.fill('#qaMontant', '4,20'); await A.click('#qaAdd');
  const fid = await A.evaluate(() => JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('bc_ctx_')))).foyerId);
  let docs = {};
  await env.withSecurityRulesDisabled(async ctx => { const qs = await ctx.firestore().collection('foyers/' + fid + '/depenses').get(); qs.forEach(d => docs[d.id] = d.data()); });
  verif('Alice : dépense enregistrée dans SON foyer', await jusqua(async () => { let ok = false; await env.withSecurityRulesDisabled(async ctx => { const qs = await ctx.firestore().collection('foyers/' + fid + '/depenses').get(); ok = qs.docs.some(d => d.data().label === 'Boulangerie'); }); return ok; }));
  let racine = null;
  await env.withSecurityRulesDisabled(async ctx => { racine = (await ctx.firestore().doc('config/main').get()).data(); });
  verif('données d\'origine intactes', racine && racine.monthLabel === 'Budget d\'origine' && racine.report.compte === 1234);

  /* --- Alice invite Carole --- */
  await A.click('#profBtn'); await A.waitForSelector('#rgInvEmail');
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
  verif('Carole : rejoint et voit la dépense d\'Alice', await jusqua(async () => { const b = await C.$('[data-tab="saisie"]'); if(!b) return false; await C.evaluate(() => { state.sec = Object.assign(state.sec||{}, {deplist: true}); render(); }); return (await C.textContent('body')).includes('Boulangerie'); }, 15000));
  await C.click('#profBtn');
  verif('Carole : 2 membres affichés', await jusqua(async () => { const t = await C.textContent('body'); return t.includes('alice@test.fr') && t.includes('carole@test.fr'); }));

  /* --- Bob : rien à voir --- */
  const B = await nouvellePage();
  await creerCompte(B, 'bob@test.fr');
  verif('Bob : écran de bienvenue sans invitation', await jusqua(async () => !!(await B.$('#bvCreer')) && !(await B.$('#bvInvOk'))));

  /* --- compte d'origine : retrouve les données d'origine --- */
  const O = await nouvellePage();
  await O.waitForSelector('#lgEmail');
  await O.fill('#lgEmail', ORIG); await O.fill('#lgPass', 'motdepasse1'); await O.click('#lgBtn');
  verif('compte d\'origine : budget d\'origine ouvert', await jusqua(async () => (await O.inputValue('#monthInput').catch(() => '')) === 'Budget d\'origine'));
  await O.click('[data-tab="comptes"]');
  verif('compte d\'origine : solde du compte repris (1 234 €)', await jusqua(async () => (await O.textContent('body')).replace(/\s/g, '').includes('1234,00€')));
  await O.click('#profBtn');
  verif('compte d\'origine : pas d\'invitation possible', await jusqua(async () => (await O.textContent('body')).includes('Budget d\'origine') && !(await O.$('#rgInvEmail'))));

  for(const [nom, p] of [['Alice', A], ['Carole', C], ['Bob', B], ['Origine', O]]) verif('aucune erreur JS (' + nom + ')', !p.errs.length, p.errs.join(' | '));
  await browser.close(); srv.close(); await env.cleanup();
  console.log('\n' + (n - ko) + ' / ' + n + ' vérifications réussies');
  process.exit(ko ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
