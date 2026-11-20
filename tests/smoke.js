/* Test rapide : ouvre l'appli (version Claude) avec la fausse base, initialise un budget,
   parcourt les 3 onglets en taille iPhone, vérifie qu'il n'y a pas d'erreur JS et pas de
   boucle de rendu, et fait des captures dans tests/out/.
   Usage : npm i -D playwright && npx playwright install chromium && node tests/smoke.js
   Option : node tests/smoke.js chemin/sauvegarde.json  (copie de secours exportée par l'appli) */
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..');
(async () => {
  const src = fs.readFileSync(path.join(ROOT, 'src', 'budget-clair.html'), 'utf8');
  const stub = fs.readFileSync(path.join(__dirname, 'stub-claude.js'), 'utf8');
  const out = path.join(__dirname, 'out'); fs.mkdirSync(out, {recursive: true});
  const page = path.join(out, 'test.html');
  fs.writeFileSync(page, '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><script>' + stub + '</script>' + src + '</body></html>');
  const seed = process.argv[2] ? JSON.parse(fs.readFileSync(process.argv[2], 'utf8')).docs : {};

  const browser = await chromium.launch();
  const p = await browser.newPage({viewport: {width: 390, height: 844}});
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.addInitScript(s => { window.__initStore = s; }, seed);
  await p.goto('file://' + page); await p.waitForTimeout(1200);
  if (await p.$('#seedBtn')) { await p.click('#seedBtn'); await p.waitForTimeout(800); }
  for (const tab of ['saisie', 'comptes', 'epargne', 'budget', 'bilan', 'reglages']) {
    await p.click('[data-tab="' + tab + '"]'); await p.waitForTimeout(500);
    const renders = await p.evaluate(() => new Promise(r => { let c = 0; const o = new MutationObserver(() => c++);
      o.observe(document.getElementById('app'), {childList: true}); setTimeout(() => { o.disconnect(); r(c); }, 1500); }));
    await p.screenshot({path: path.join(out, tab + '.png'), fullPage: true});
    console.log(tab.padEnd(7), 'rendus pendant 1,5 s sans rien toucher :', renders, renders ? '⚠️ boucle ?' : 'ok');
  }
  console.log('erreurs JS :', errors.length ? errors : 'aucune');
  await browser.close();
  process.exit(errors.length ? 1 : 0);
})();
