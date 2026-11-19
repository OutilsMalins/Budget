/* Tests des règles Firestore (firestore.rules) avec l'émulateur Firebase.
   Usage : cd tests && npm install && npm run test:rules
   Les deux adresses « données d'origine » sont remplacées par des adresses de test. */
const fs = require('fs'), path = require('path');
const { initializeTestEnvironment, assertSucceeds, assertFails } = require('@firebase/rules-unit-testing');

const ORIG1 = 'ancien1@test.fr', ORIG2 = 'ancien2@test.fr';
const rules = fs.readFileSync(path.join(__dirname, '..', 'firestore.rules'), 'utf8')
  .replace('adresse-1@exemple.fr', ORIG1).replace('adresse-2@exemple.fr', ORIG2);

let n = 0, ko = 0;
async function cas(nom, fn) {
  n++;
  try { await fn(); console.log('ok   ', nom); }
  catch (e) { ko++; console.log('ÉCHEC', nom, '-', e.message.split('\n')[0]); }
}

(async () => {
  const env = await initializeTestEnvironment({ projectId: 'demo-budget', firestore: { rules } });
  const db = (uid, email, verifie) => env.authenticatedContext(uid, { email, email_verified: !!verifie }).firestore();
  const anonyme = env.unauthenticatedContext().firestore();

  /* données de départ, écrites sans règles */
  await env.withSecurityRulesDisabled(async ctx => {
    const f = ctx.firestore();
    await f.doc('config/main').set({ monthLabel: 'Ancien', revenus: [] });
    await f.doc('depenses/a1').set({ mois: '2026-11', montant: 10 });
    await f.doc('foyers/F1').set({ nom: 'Foyer de Alice', owner: 'alice', membres: ['alice'], emails: ['alice@test.fr'], creeLe: 'x' });
    await f.doc('foyers/F1/config/main').set({ monthLabel: 'Novembre' });
    await f.doc('foyers/F1/depenses/d1').set({ mois: '2026-11', montant: 12 });
    await f.doc('foyers/F2').set({ nom: 'Foyer de Bob', owner: 'bob', membres: ['bob'], emails: ['bob@test.fr'], creeLe: 'x' });
  });
  const ancien = db('o1', ORIG1), ancien2 = db('o2', ORIG2.toUpperCase());
  const alice = db('alice', 'alice@test.fr', true), bob = db('bob', 'bob@test.fr', true);
  const carole = db('carole', 'carole@test.fr', true), caroleNonVerif = db('carole', 'carole@test.fr', false);
  const intrus = db('mallory', 'mallory@test.fr', true);

  console.log('--- données d\'origine (à la racine)');
  await cas('les deux comptes d\'origine lisent leur budget', async () => { await assertSucceeds(ancien.doc('config/main').get()); await assertSucceeds(ancien2.doc('config/main').get()); });
  await cas('…et peuvent écrire', () => assertSucceeds(ancien.doc('depenses/a2').set({ mois: '2026-11', montant: 5 })));
  await cas('…et lister les dépenses', () => assertSucceeds(ancien.collection('depenses').where('mois', '==', '2026-11').get()));
  await cas('un nouvel utilisateur ne lit PAS les données d\'origine', () => assertFails(alice.doc('config/main').get()));
  await cas('un nouvel utilisateur ne liste PAS les dépenses d\'origine', () => assertFails(alice.collection('depenses').get()));
  await cas('un visiteur non connecté ne lit rien', () => assertFails(anonyme.doc('config/main').get()));
  await cas('les comptes d\'origine ne lisent PAS les foyers des autres', () => assertFails(ancien.doc('foyers/F1/config/main').get()));

  console.log('--- foyers');
  await cas('Alice lit son budget', () => assertSucceeds(alice.doc('foyers/F1/config/main').get()));
  await cas('Alice écrit dans son budget', () => assertSucceeds(alice.doc('foyers/F1/depenses/d2').set({ mois: '2026-11', montant: 3 })));
  await cas('Alice retrouve ses foyers (requête)', () => assertSucceeds(alice.collection('foyers').where('membres', 'array-contains', 'alice').get()));
  await cas('Bob ne lit PAS le budget d\'Alice', () => assertFails(bob.doc('foyers/F1/config/main').get()));
  await cas('Bob ne lit PAS la fiche du foyer d\'Alice', () => assertFails(bob.doc('foyers/F1').get()));
  await cas('Bob n\'écrit PAS dans le budget d\'Alice', () => assertFails(bob.doc('foyers/F1/depenses/x').set({ montant: 1 })));
  await cas('Bob ne liste PAS tous les foyers', () => assertFails(bob.collection('foyers').get()));
  await cas('Bob ne s\'ajoute PAS au foyer d\'Alice sans invitation', () => assertFails(bob.doc('foyers/F1').update({ membres: ['alice', 'bob'], emails: ['alice@test.fr', 'bob@test.fr'] })));
  await cas('créer son propre foyer', () => assertSucceeds(carole.doc('foyers/F3').set({ nom: 'Mon budget', owner: 'carole', membres: ['carole'], emails: ['carole@test.fr'], creeLe: 'x' })));
  await cas('PAS de foyer créé au nom d\'un autre', () => assertFails(intrus.doc('foyers/F4').set({ nom: 'x', owner: 'alice', membres: ['alice'], emails: ['alice@test.fr'], creeLe: 'x' })));
  await cas('PAS de foyer créé avec un autre membre dedans', () => assertFails(intrus.doc('foyers/F5').set({ nom: 'x', owner: 'mallory', membres: ['mallory', 'alice'], emails: ['mallory@test.fr'], creeLe: 'x' })));
  await cas('un membre renomme son foyer', () => assertSucceeds(alice.doc('foyers/F1').update({ nom: 'Budget de la maison' })));
  await cas('PAS changer le propriétaire', () => assertFails(alice.doc('foyers/F1').update({ owner: 'bob' })));

  console.log('--- invitations');
  await cas('un intrus n\'invite PAS dans le foyer d\'Alice', () => assertFails(intrus.doc('invitations/mallory@test.fr').set({ foyer: 'F1', nomFoyer: 'x', de: 'mallory@test.fr', le: 'x' })));
  await cas('Alice invite Carole', () => assertSucceeds(alice.doc('invitations/carole@test.fr').set({ foyer: 'F1', nomFoyer: 'Budget', de: 'alice@test.fr', le: 'x' })));
  await cas('Carole voit son invitation', () => assertSucceeds(carole.doc('invitations/carole@test.fr').get()));
  await cas('Alice liste les invitations de son foyer', () => assertSucceeds(alice.collection('invitations').where('foyer', '==', 'F1').get()));
  await cas('Bob ne liste PAS les invitations du foyer d\'Alice', () => assertFails(bob.collection('invitations').where('foyer', '==', 'F1').get()));
  await cas('Bob n\'écrase PAS l\'invitation de Carole', () => assertFails(bob.doc('invitations/carole@test.fr').set({ foyer: 'F2', nomFoyer: 'x', de: 'bob@test.fr', le: 'x' })));
  await cas('Bob ne voit PAS l\'invitation de Carole', () => assertFails(bob.doc('invitations/carole@test.fr').get()));
  await cas('Bob ne rejoint PAS avec l\'invitation de Carole', () => assertFails(bob.doc('foyers/F1').update({ membres: ['alice', 'bob'], emails: ['alice@test.fr', 'bob@test.fr'] })));
  await cas('Carole sans adresse vérifiée ne rejoint PAS', () => assertFails(caroleNonVerif.doc('foyers/F1').update({ membres: ['alice', 'carole'], emails: ['alice@test.fr', 'carole@test.fr'] })));
  await cas('Carole ne rejoint PAS en retirant Alice', () => assertFails(carole.doc('foyers/F1').update({ membres: ['carole'], emails: ['carole@test.fr'] })));
  await cas('Carole (vérifiée) rejoint le foyer', () => assertSucceeds(carole.doc('foyers/F1').update({ membres: ['alice', 'carole'], emails: ['alice@test.fr', 'carole@test.fr'] })));
  await cas('Carole lit alors le budget partagé', () => assertSucceeds(carole.doc('foyers/F1/config/main').get()));
  await cas('Carole choisit ce foyer', () => assertSucceeds(carole.doc('users/carole').set({ foyer: 'F1' })));
  await cas('PAS choisir un foyer dont on n\'est pas membre', () => assertFails(bob.doc('users/bob').set({ foyer: 'F1' })));
  await cas('Carole supprime son invitation', () => assertSucceeds(carole.doc('invitations/carole@test.fr').delete()));
  await cas('Carole ne retire PAS Alice', () => assertFails(carole.doc('foyers/F1').update({ membres: ['carole'], emails: ['carole@test.fr'] })));
  await cas('Carole quitte le foyer', () => assertSucceeds(carole.doc('foyers/F1').update({ membres: ['alice'], emails: ['alice@test.fr'] })));
  await cas('Carole ne lit plus le budget', () => assertFails(carole.doc('foyers/F1/config/main').get()));

  console.log('--- suppression');
  await cas('Bob ne supprime PAS le foyer d\'Alice', () => assertFails(bob.doc('foyers/F1').delete()));
  await cas('Alice (seule) supprime ses données puis son foyer', async () => {
    await assertSucceeds(alice.doc('foyers/F1/depenses/d1').delete());
    await assertSucceeds(alice.doc('foyers/F1').delete());
  });

  await env.cleanup();
  console.log('\n' + (n - ko) + ' / ' + n + ' cas réussis');
  process.exit(ko ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
