"""Construit la version « page web » de l'appli : Firebase (comptes + base Firestore)
à la place du stockage de Claude.

Usage : python3 build/build_firebase.py --essai      -> écrit essai/index.html (version d'essai, voir plus bas)
        python3 build/build_firebase.py              -> écrit index.html (racine du dépôt, publié par GitHub Pages)
        python3 build/build_firebase.py [--essai] <sortie.html> [<source.html>]

Version d'essai (--essai) : publiée à côté de l'ancienne appli (adresse …/Budget/essai/).
Elle n'ouvre JAMAIS les données d'origine (racine de la base) : chacun y crée un
budget d'essai (foyer), où il peut importer une copie de secours de ses vraies données.

Ce que la version page web ajoute :
- connexion, création de compte, mot de passe oublié ;
- un « foyer » par budget (données sous foyers/<id>/…), partagé par invitation ;
- les données d'origine (à la racine de la base) restent à leur place et servent
  telles quelles aux deux comptes autorisés par les règles (rien n'est copié) ;
- page Réglages : compte, foyer, invitations, copie de secours, suppression du compte."""
import sys, os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESSAI = '--essai' in sys.argv
args = [a for a in sys.argv[1:] if a != '--essai']
src_path = args[1] if len(args) > 1 else os.path.join(ROOT, 'src', 'budget-clair.html')
out_path = args[0] if args else os.path.join(ROOT, 'essai' if ESSAI else '', 'index.html')
src = open(src_path, encoding='utf-8').read()
s = src

FIREBASE_CONFIG = """{
  apiKey: "AIzaSyDWRNKF0VKo6qzWlkVVtrXzHvEcJmQb218",
  authDomain: "budget-familial-713e2.firebaseapp.com",
  projectId: "budget-familial-713e2",
  storageBucket: "budget-familial-713e2.firebasestorage.app",
  messagingSenderId: "591945442194",
  appId: "1:591945442194:web:b51ee7e268607bba26d74b"
}"""
FB_VERSION = '10.14.1'

def rep(a, b, n=1):
    """Remplace a par b ; a doit apparaître exactement n fois dans la source."""
    global s
    c = s.count(a)
    assert c == n, (c, a[:90])
    s = s.replace(a, b)

# ---------- icône : fichier à côté de la page (plus fiable sur iPhone qu'une image intégrée)
a = s.index('<link rel="apple-touch-icon"')
b = s.index('>', a) + 1
s = s[:a] + '<link rel="apple-touch-icon" href="apple-touch-icon.png">\n<meta name="apple-mobile-web-app-status-bar-style" content="default">' + s[b:]
rep('<meta name="apple-mobile-web-app-title" content="Budget Clair">', '<meta name="apple-mobile-web-app-title" content="'+('Budget essai' if ESSAI else 'Budget')+'">')
if ESSAI: rep('<title>Budget</title>', '<title>Budget (essai)</title>')

# ---------- premier lancement d'un budget vide : importer une sauvegarde, ou partir de zéro
rep("""      '<div class="empty"><div class="em">💶</div><p><strong>Aucun budget initialisé.</strong></p>'+
      '<p style="font-size:12.5px;margin-top:4px;">On démarre avec un budget vide (tout à 0 €) : vous le remplirez ensuite.</p>'+
      '<button class="btn btn-primary" id="seedBtn" style="margin-top:14px;">Initialiser mon budget</button></div>';""",
"""      '<div class="card" style="max-width:520px;margin:30px auto;"><h3 style="font-size:19px;margin:0 0 6px;">Votre budget est prêt</h3>'+
      '<p class="hint-line" style="margin-top:0;">Commencez avec un budget vide (quelques postes à 0 €, à remplir), ou restaurez une copie de secours (.json) exportée depuis l\\'appli.</p>'+
      '<div class="tf-row" style="margin-top:14px;"><button class="btn btn-primary" id="seedBtn">Commencer un budget vide</button></div>'+
      '<p class="hint-line" style="margin-top:16px;">Vous avez une copie de secours ? <label class="link-btn" style="cursor:pointer;">Importer le fichier<input type="file" id="impFile" accept=".json,application/json" hidden></label></p>'+
      '<p class="hint-line" id="impMsg"></p></div>';""")
rep("""Le stockage n\\'est pas disponible dans cette vue.<br>Rouvrez la page depuis Claude.""",
    """Impossible de joindre la base de données.<br>Vérifiez votre connexion internet, puis rouvrez l\\'appli.""")

# ---------- démarrage : seulement une fois connecté et le budget trouvé
rep("""if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded', initDb); } else { initDb(); }""",
    """window.__startApp = initDb;""")

EXTRA_CSS = r"""
<style>
  .prof-btn{position:absolute; top:2px; right:0; width:36px; height:36px; border-radius:50%; border:1px solid var(--line); background:var(--card); color:var(--ink-2); display:inline-flex; align-items:center; justify-content:center; cursor:pointer; padding:0;}
  .prof-btn.on{color:var(--accent); border-color:var(--accent);}
  .prof-btn .i{width:20px; height:20px;}
  .auth-wrap{max-width:420px; margin:36px auto 0;}
  .auth-logo{width:52px; height:52px; border-radius:14px; background:var(--accent); color:#fff; font-size:28px; font-weight:750; display:flex; align-items:center; justify-content:center; margin:0 auto 12px;}
  .auth-wrap h1{font-size:22px; text-align:center; margin:0 0 4px;}
  .auth-wrap .sub{color:var(--ink-muted); text-align:center; font-size:13.5px; margin-bottom:18px;}
  .auth-form{display:flex; flex-direction:column; gap:10px;}
  .auth-form input{font-size:16px; padding:11px 12px;}
  .auth-msg{font-size:13px; text-align:center; min-height:18px; margin-top:10px; color:var(--critical);}
  .auth-msg.ok{color:var(--good);}
  .auth-alt{text-align:center; margin-top:14px; font-size:13.5px; color:var(--ink-2);}
  .auth-foot{text-align:center; font-size:11.5px; color:var(--ink-muted); margin-top:18px; line-height:1.5;}
  .rg-row{display:flex; justify-content:space-between; align-items:center; gap:10px; padding:9px 0; border-top:1px solid var(--line); font-size:14px;}
  .rg-row:first-of-type{border-top:0;}
  .rg-row span{color:var(--ink-2); min-width:0; overflow:hidden; text-overflow:ellipsis;}
  .rg-row em{font-style:normal; font-size:11.5px; color:var(--ink-muted); margin-left:6px;}
  .rg-msg{font-size:13px; margin-top:8px; line-height:1.5;}
  .rg-msg.ok{color:var(--good);} .rg-msg.ko{color:var(--critical);}
  .invit-box{background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:10px 12px; font-size:13px; line-height:1.5; white-space:pre-line; margin-top:8px;}
  .danger-zone{border-color:#f1c9c4;}
  .btn-danger{background:var(--critical); color:#fff;}
  .pf-wrap{position:absolute; top:4px; right:0; z-index:25; max-width:52%;}
  .pf-sel{display:inline-flex; align-items:center; gap:6px; max-width:100%; padding:7px 12px 7px 10px; border-radius:100px; background:var(--card); border:1px solid var(--line); color:var(--accent); box-shadow:var(--shadow); font:600 15px -apple-system, system-ui, sans-serif; cursor:pointer;}
  .pf-sel span{color:var(--ink); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
  .pf-sel .i{width:18px; height:18px; flex:0 0 auto;}
  .pf-sel::after{content:'▾'; color:var(--ink-muted); font-size:12px;}
  .pf-menu{position:absolute; right:0; top:calc(100% + 6px); width:260px; max-width:86vw; background:var(--card); border:1px solid var(--line); border-radius:16px; box-shadow:0 16px 40px rgba(0,0,0,.22); padding:8px; display:flex; flex-direction:column; gap:4px;}
  .pf-menu-t{font-size:12px; font-weight:700; color:var(--ink-muted); text-transform:uppercase; letter-spacing:.04em; padding:6px 8px 2px;}
  .pf-item{position:relative; display:block; width:100%; text-align:left; border:0; background:transparent; border-radius:10px; padding:9px 30px 9px 10px; font-family:inherit; color:var(--ink); cursor:pointer;}
  .pf-item b{display:block; font-size:15px;} .pf-item em{display:block; font-style:normal; font-size:12px; color:var(--ink-muted);}
  .pf-item.on{background:var(--accent-bg);} .pf-item i{position:absolute; right:10px; top:50%; transform:translateY(-50%); font-style:normal; color:var(--accent); font-weight:700;}
  .pf-menu-h{font-size:12.5px; color:var(--ink-2); margin:4px 8px; line-height:1.45;}
  .pf-new{border:0; border-radius:10px; background:var(--accent); color:var(--accent-ink, #fff); font:600 14px -apple-system, system-ui, sans-serif; padding:10px; margin-top:4px; cursor:pointer;}
  .pf-gerer{border:0; background:transparent; color:var(--accent); font:600 13px -apple-system, system-ui, sans-serif; padding:6px; cursor:pointer;}
  .hero{position:relative;}
  .essai-bandeau{position:sticky; top:0; z-index:30; background:#fdf3e1; color:#7a4a00; font-size:12.5px; font-weight:600; text-align:center; padding:6px 10px calc(6px); border-bottom:1px solid #f1dcb5;}
</style>
"""

SHIM = r"""
<script src="https://www.gstatic.com/firebasejs/%(v)s/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/%(v)s/firebase-auth-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/%(v)s/firebase-firestore-compat.js"></script>
<script>
/* ===== Firebase : comptes + base de données, à la place du stockage de Claude ===== */
(function(){
var CONFIG = %(cfg)s;
/* version d'essai : jamais les données d'origine, seulement des budgets d'essai (foyers) */
var ESSAI = %(essai)s;
var ok = !!window.firebase;
var fdb = null, auth = null;
if(ok){
  firebase.initializeApp(CONFIG);
  auth = firebase.auth();
  auth.languageCode = 'fr';
  fdb = firebase.firestore();
  if(window.__BC_EMU){ auth.useEmulator('http://127.0.0.1:9099', {disableWarnings:true}); fdb.useEmulator('127.0.0.1', 8080); }
  try{ fdb.settings({ignoreUndefinedProperties:true, merge:true}); }catch(e){}
  if(!window.__BC_EMU){ try{ fdb.enablePersistence({synchronizeTabs:true}).catch(function(){}); }catch(e){} }
}
var COLLS = ['config','depenses','versements','transferts','mois'];
/* où sont les données du budget : '' = données d'origine (racine), sinon 'foyers/<id>/' */
var CTX = {mode:null, base:'', foyerId:null, foyer:null, invitation:null};
var USER = null;
var dbw = {
  doc: function(p){ return fdb.doc(CTX.base + p); },
  collection: function(c){ return fdb.collection(CTX.base + c); }
};

function download(name, data, type){
  var ext = String(name||'').split('.').pop().toLowerCase();
  var mime = type || ({pdf:'application/pdf', json:'application/json'}[ext]) || 'text/html';
  var blob = new Blob([data], {type: mime});
  function viaLien(){
    var url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url; a.download = name; document.body.appendChild(a); a.click();
    setTimeout(function(){ URL.revokeObjectURL(url); a.remove(); }, 1500);
  }
  /* iPhone / iPad : la feuille de partage propose « Enregistrer dans Fichiers » */
  var ios = /iP(hone|ad|od)/.test(navigator.userAgent) || (navigator.platform==='MacIntel' && navigator.maxTouchPoints>1);
  try{
    var f = new File([blob], name, {type: mime});
    if(ios && navigator.canShare && navigator.canShare({files:[f]})){
      return navigator.share({files:[f], title:name}).catch(function(e){ if(!e || e.name!=='AbortError') viaLien(); });
    }
  }catch(e){}
  viaLien();
}
window.claude = { use: function(name){
  if(name==='db') return fdb ? Promise.resolve(dbw) : Promise.reject(new Error('firebase indisponible'));
  if(name==='downloads') return Promise.resolve({ save: function(r){ download(r.filename, r.data); return Promise.resolve({status:'saved'}); } });
  return Promise.reject(new Error('indisponible'));
} };

function esc(t){ return String(t==null?'':t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function appEl(){ return document.getElementById('app'); }
function $(id){ return document.getElementById(id); }
function emailDe(u){ return String((u && u.email) || '').toLowerCase(); }
function maintenant(){ return new Date().toISOString(); }
var MSG = {
  'auth/invalid-credential':'E-mail ou mot de passe incorrect.',
  'auth/invalid-login-credentials':'E-mail ou mot de passe incorrect.',
  'auth/wrong-password':'Mot de passe incorrect.',
  'auth/user-not-found':'Aucun compte avec cet e-mail.',
  'auth/invalid-email':'Cet e-mail n\'est pas valide.',
  'auth/email-already-in-use':'Un compte existe déjà avec cet e-mail : connectez-vous.',
  'auth/weak-password':'Mot de passe trop court : 8 caractères au moins.',
  'auth/too-many-requests':'Trop d\'essais. Patientez quelques minutes.',
  'auth/network-request-failed':'Pas de connexion internet.',
  'auth/user-disabled':'Ce compte est désactivé.',
  'auth/requires-recent-login':'Pour cette action, reconnectez-vous d\'abord.',
  'auth/operation-not-allowed':'La création de compte n\'est pas activée dans Firebase (Authentication → Sign-in method → E-mail/Mot de passe).',
  'permission-denied':'Accès refusé par les règles de sécurité.'
};
function msgErr(err){ var c = err && err.code; return MSG[c] || MSG[String(c).replace(/^firestore\//,'')] || ('Erreur ('+(c || (err && err.message) || 'inconnue')+').'); }

/* ================= écran de connexion / création de compte ================= */
var vueAuth = 'login';
function showLogin(msg, okMsg){
  var cre = vueAuth==='signup';
  appEl().innerHTML =
    '<div class="auth-wrap"><div class="card" style="padding:24px 20px;">'+
    '<div class="auth-logo">€</div><h1>Budget</h1><div class="sub">'+(cre ? 'Créez votre compte : votre budget sera privé.' : 'Connectez-vous pour retrouver votre budget.')+'</div>'+
    '<form id="loginForm" class="auth-form">'+
    '<input class="text-input" id="lgEmail" type="email" autocomplete="username" placeholder="E-mail" required>'+
    '<input class="text-input" id="lgPass" type="password" autocomplete="'+(cre?'new-password':'current-password')+'" placeholder="Mot de passe'+(cre?' (8 caractères au moins)':'')+'" required>'+
    (cre ? '<input class="text-input" id="lgPass2" type="password" autocomplete="new-password" placeholder="Retapez le mot de passe" required>' : '')+
    '<button class="btn btn-primary" type="submit" id="lgBtn">'+(cre?'Créer mon compte':'Se connecter')+'</button></form>'+
    '<div class="auth-msg'+(okMsg?' ok':'')+'" id="lgMsg">'+esc(okMsg||msg||'')+'</div>'+
    (cre ? '' : '<div class="auth-alt"><button type="button" class="link-btn" id="lgReset">Mot de passe oublié ?</button></div>')+
    '<div class="auth-alt">'+(cre ? 'Déjà un compte ? <button type="button" class="link-btn" id="lgSwitch">Se connecter</button>' : 'Pas encore de compte ? <button type="button" class="link-btn" id="lgSwitch">Créer un compte</button>')+'</div>'+
    (cre ? '<div class="auth-foot">Vos données de budget sont enregistrées dans une base Firebase (Google), accessibles seulement aux membres de votre foyer. L\'appli n\'est reliée à aucune banque.</div>' : '')+
    '</div></div>';
  $('lgSwitch').onclick = function(){ vueAuth = cre ? 'login' : 'signup'; showLogin(); };
  $('loginForm').onsubmit = function(ev){
    ev.preventDefault();
    var em = $('lgEmail').value.trim(), pw = $('lgPass').value, m = $('lgMsg'), btn = $('lgBtn');
    m.className = 'auth-msg'; m.textContent = '';
    if(cre){
      if(pw.length < 8){ m.textContent = MSG['auth/weak-password']; return; }
      if(pw !== $('lgPass2').value){ m.textContent = 'Les deux mots de passe sont différents.'; return; }
    }
    btn.disabled = true; btn.textContent = cre ? 'Création…' : 'Connexion…';
    var p = cre ? auth.createUserWithEmailAndPassword(em, pw).then(function(c){ return c.user.sendEmailVerification().catch(function(){}); })
                : auth.signInWithEmailAndPassword(em, pw);
    p.catch(function(err){ btn.disabled = false; btn.textContent = cre ? 'Créer mon compte' : 'Se connecter'; m.textContent = msgErr(err); });
  };
  var rs = $('lgReset');
  if(rs) rs.onclick = function(){
    var em = $('lgEmail').value.trim(), m = $('lgMsg');
    if(!em){ m.className = 'auth-msg'; m.textContent = 'Tapez d\'abord votre e-mail ci-dessus.'; return; }
    auth.sendPasswordResetEmail(em).then(function(){ m.className = 'auth-msg ok'; m.textContent = 'Si un compte existe, un e-mail pour changer le mot de passe vient d\'être envoyé.'; })
      .catch(function(err){ m.className = 'auth-msg'; m.textContent = msgErr(err); });
  };
}

/* ================= quel budget ouvrir ? ================= */
function memoKey(u){ return (ESSAI ? 'bc_ctx_essai_' : 'bc_ctx_')+u.uid; }
function memoCtx(u, c){ try{ if(c) localStorage.setItem(memoKey(u), JSON.stringify(c)); else return JSON.parse(localStorage.getItem(memoKey(u))||'null'); }catch(e){ return null; } }
function lireFoyer(fid){
  return fdb.doc('foyers/'+fid).get().then(function(d){ return d.exists ? {id:d.id, data:d.data()} : null; }).catch(function(){ return null; });
}
function chercherFoyer(u){
  return fdb.doc('users/'+u.uid).get().then(function(s){ var f = s.exists && s.data().foyer; return f ? lireFoyer(f) : null; }).catch(function(){ return null; })
    .then(function(f){
      if(f) return f;
      return fdb.collection('foyers').where('membres','array-contains',u.uid).limit(10).get().then(function(qs){
        if(qs.empty) return null;
        var d = qs.docs.slice().sort(function(a,b){ return String(a.data().creeLe||'').localeCompare(String(b.data().creeLe||'')); })[0];
        return {id:d.id, data:d.data()};
      });
    });
}
function lireInvitation(u){
  var em = emailDe(u); if(!em) return Promise.resolve(null);
  return fdb.doc('invitations/'+em).get().then(function(d){ return d.exists ? d.data() : null; }).catch(function(){ return null; });
}
/* portefeuille choisi sur ce téléphone : 'ancien' (données d'origine) ou l'id d'un foyer */
function choixKey(u){ return (ESSAI ? 'bc_pf_essai_' : 'bc_pf_')+u.uid; }
function memoChoix(u, id){ try{ if(id===undefined) return localStorage.getItem(choixKey(u)); localStorage.setItem(choixKey(u), id); }catch(e){ return null; } }
function listerPortefeuilles(u){
  var L = [];
  var pAncien = ESSAI ? Promise.resolve(false) : fdb.doc('config/main').get().then(function(){ return true; }, function(err){ if(err && err.code==='permission-denied') return false; throw err; });
  return pAncien.then(function(ancien){
    if(ancien) L.push({id:'ancien', nom:'Nous', base:''});
    return fdb.collection('foyers').where('membres','array-contains',u.uid).limit(20).get();
  }).then(function(qs){
    qs.docs.slice().sort(function(a,b){ return String(a.data().creeLe||'').localeCompare(String(b.data().creeLe||'')); })
      .forEach(function(d){ L.push({id:d.id, nom:d.data().nom||'Portefeuille', base:'foyers/'+d.id+'/', membres:(d.data().membres||[]).length}); });
    return L;
  });
}
function resoudre(u){
  return listerPortefeuilles(u).then(function(L){
    CTX.liste = L;
    if(!L.length) return {mode:'aucun'};
    var choix = memoChoix(u), P = L.find(function(x){ return x.id===choix; });
    if(P) return P;
    return fdb.doc('users/'+u.uid).get().then(function(s2){ var f = s2.exists && s2.data().foyer; return L.find(function(x){ return x.id===f; }) || L[0]; }, function(){ return L[0]; });
  }).then(function(P){
    if(P.mode==='aucun') return P;
    return P.id==='ancien' ? {mode:'ancien', base:'', pfId:'ancien'} : {mode:'foyer', base:P.base, foyerId:P.id, pfId:P.id};
  }, function(err){
    var m = memoCtx(u); if(m) return m;   /* hors ligne : dernier choix connu */
    throw err;
  });
}
function changerPortefeuille(id){
  memoChoix(USER, id);
  var p = (id!=='ancien') ? fdb.doc('users/'+USER.uid).set({foyer:id}).catch(function(){}) : Promise.resolve();
  p.then(function(){ location.reload(); });
}
/* comptes des autres portefeuilles : pour les virements de l'un à l'autre */
function chargerAutres(){
  var A = (CTX.liste||[]).filter(function(x){ return x.id!==CTX.pfId; });
  Promise.all(A.map(function(P){
    return fdb.doc(P.base+'config/main').get().then(function(d){
      var c = d.exists ? (d.data().comptes || [{id:'compte', label:'Compte principal', devise:'EUR', kind:'courant'}, {id:'especes', label:'Espèces', devise:'EUR', kind:'especes'}]) : [];
      return {pf:P.id, nom:P.nom, comptes:c};
    }).catch(function(){ return null; });
  })).then(function(R){ CTX.autres = R.filter(Boolean); if(window.requestRender) requestRender(); });
}
function ecrireAutre(pfId, obj, id){
  var P = (CTX.liste||[]).find(function(x){ return x.id===pfId; });
  if(!P) return;
  fdb.doc(P.base+'config/main').get().then(function(d){
    var mois = (d.exists && d.data().moisCle) || new Date().toISOString().slice(0,7);
    obj.mois = mois;
    return fdb.doc(P.base+'transferts/'+id).set(obj);
  }).catch(function(err){ toast('Le virement n\'a pas pu être noté dans « '+esc(P.nom)+' » ('+esc(msgErr(err))+').', 'bad'); });
}
var started = false, foyerUnsub = null;
function suivreFoyer(){
  if(foyerUnsub){ foyerUnsub(); foyerUnsub = null; }
  if(CTX.mode!=='foyer') return;
  foyerUnsub = fdb.doc('foyers/'+CTX.foyerId).onSnapshot(function(d){
    CTX.foyer = d.exists ? d.data() : null;
    var P = (CTX.liste||[]).find(function(x){ return x.id===CTX.foyerId; }); if(P && CTX.foyer) P.nom = CTX.foyer.nom || P.nom;
    if(!d.exists || (CTX.foyer.membres||[]).indexOf(USER.uid)<0){ location.reload(); return; }
    if(window.requestRender) requestRender();
  }, function(){ location.reload(); });
}
function lancer(c){
  CTX.mode = c.mode; CTX.base = c.base || ''; CTX.foyerId = c.foyerId || null; CTX.pfId = c.pfId || c.foyerId || (c.mode==='ancien' ? 'ancien' : null);
  if(!CTX.liste) CTX.liste = CTX.pfId ? [{id:CTX.pfId, nom:(c.mode==='ancien'?'Nous':'Moi'), base:CTX.base}] : [];
  memoCtx(USER, {mode:c.mode, base:CTX.base, foyerId:CTX.foyerId, pfId:CTX.pfId});
  if(CTX.pfId) memoChoix(USER, CTX.pfId);
  chargerAutres();
  started = true;
  suivreFoyer();
  lireInvitation(USER).then(function(inv){ CTX.invitation = (inv && inv.foyer!==CTX.foyerId) ? inv : null; if(CTX.invitation && window.requestRender) requestRender(); });
  window.__startApp();
  /* outils PDF chargés d'avance : l'export devient instantané (utile pour le partage sur iPhone) */
  setTimeout(function(){ try{ if(window.chargerPdfLibs) chargerPdfLibs().catch(function(){}); }catch(e){} }, 2500);
}
function chargement(txt){ appEl().innerHTML = '<div class="empty"><p>'+esc(txt||'Chargement de votre budget…')+'</p></div>'; }

/* ---------- créer son foyer / rejoindre un foyer ---------- */
function creerFoyer(nom){
  var ref = fdb.collection('foyers').doc();
  return ref.set({nom:String(nom||'Moi').trim().slice(0,60) || 'Moi', owner:USER.uid, membres:[USER.uid], emails:[emailDe(USER)], creeLe:maintenant()})
    .then(function(){ return fdb.doc('users/'+USER.uid).set({foyer:ref.id}); })
    .then(function(){ memoChoix(USER, ref.id); return {mode:'foyer', base:'foyers/'+ref.id+'/', foyerId:ref.id, pfId:ref.id}; });
}
function rejoindre(inv){
  var em = emailDe(USER);
  return USER.reload().then(function(){ return USER.getIdToken(true); }).then(function(){
    if(!auth.currentUser.emailVerified) throw {code:'non-verifie'};
    return fdb.doc('foyers/'+inv.foyer).update({
      membres: firebase.firestore.FieldValue.arrayUnion(USER.uid),
      emails: firebase.firestore.FieldValue.arrayUnion(em)
    });
  }).then(function(){ return fdb.doc('users/'+USER.uid).set({foyer:inv.foyer}); })
    .then(function(){ return fdb.doc('invitations/'+em).delete().catch(function(){}); })
    .then(function(){ memoChoix(USER, inv.foyer); memoCtx(USER, {mode:'foyer', base:'foyers/'+inv.foyer+'/', foyerId:inv.foyer, pfId:inv.foyer}); });
}
function msgRejoindre(err){
  if(err && err.code==='non-verifie') return 'Confirmez d\'abord votre adresse : ouvrez l\'e-mail de vérification envoyé à '+emailDe(USER)+' (pensez aux indésirables), puis touchez à nouveau « Rejoindre ».';
  return msgErr(err);
}
function invitationHtml(inv, id){
  return '<div class="card" style="border-color:var(--accent);"><h3>Invitation reçue</h3>'+
    '<p style="margin:0 0 10px;font-size:14px;">'+esc(inv.de||'Quelqu\'un')+' vous invite à partager le budget « <b>'+esc(inv.nomFoyer||'Budget')+'</b> ».</p>'+
    (USER.emailVerified ? '' : '<p class="hint-line" style="margin-top:0;">Avant de rejoindre, confirmez votre adresse avec l\'e-mail de vérification reçu. <button type="button" class="link-btn" id="'+id+'Verif">Renvoyer l\'e-mail</button></p>')+
    '<div class="tf-row"><button class="btn btn-primary" id="'+id+'Ok">Rejoindre</button><button class="btn btn-ghost" id="'+id+'No">Refuser</button></div>'+
    '<div class="rg-msg" id="'+id+'Msg"></div></div>';
}
function brancherInvitation(inv, id, apres){
  var okB = $(id+'Ok'), no = $(id+'No'), v = $(id+'Verif'), m = $(id+'Msg');
  if(okB) okB.onclick = function(){
    okB.disabled = true; m.className = 'rg-msg'; m.textContent = 'Un instant…';
    rejoindre(inv).then(function(){ location.reload(); }).catch(function(err){ okB.disabled = false; m.className = 'rg-msg ko'; m.textContent = msgRejoindre(err); });
  };
  if(no) no.onclick = function(){ fdb.doc('invitations/'+emailDe(USER)).delete().catch(function(){}).then(apres); };
  if(v) v.onclick = function(){ USER.sendEmailVerification().then(function(){ m.className = 'rg-msg ok'; m.textContent = 'E-mail envoyé à '+emailDe(USER)+'.'; }).catch(function(err){ m.className = 'rg-msg ko'; m.textContent = msgErr(err); }); };
}
function showBienvenue(){
  chargement('Un instant…');
  lireInvitation(USER).then(function(inv){
    appEl().innerHTML = '<div class="auth-wrap">'+
      '<div class="auth-logo">€</div><h1>Bienvenue</h1><div class="sub">Connecté : '+esc(emailDe(USER))+'</div>'+
      (inv ? invitationHtml(inv, 'bvInv') : '')+
      '<div class="card"><h3>'+(inv ? 'Ou commencer votre propre portefeuille' : 'Créer votre portefeuille')+'</h3>'+
      '<p class="hint-line" style="margin-top:0;">Un portefeuille « Moi », privé. Vous pourrez ensuite en créer un autre à partager (« Nous ») depuis les Réglages.</p>'+
      '<div class="tf-row" style="margin-top:12px;"><button class="btn '+(inv?'btn-ghost':'btn-primary')+'" id="bvCreer">Créer mon portefeuille</button></div>'+
      (ESSAI ? '<p class="hint-line"><b>Version d\'essai :</b> ce budget est séparé de votre vrai budget, qui n\'est pas touché. Pour essayer avec vos chiffres : dans l\'ancienne appli, onglet Bilan → « Copie de secours », puis ici « Créer mon budget » → « Importer le fichier ».</p>' : '')+
      '<p class="hint-line">Quelqu\'un doit vous inviter dans son budget ? Demandez-lui de vous inviter avec l\'adresse <b>'+esc(emailDe(USER))+'</b>, puis <button type="button" class="link-btn" id="bvRe">actualisez</button>.</p>'+
      '<div class="rg-msg" id="bvMsg"></div></div>'+
      '<div class="auth-alt"><button type="button" class="link-btn" id="bvOut">Se déconnecter</button></div></div>';
    if(inv) brancherInvitation(inv, 'bvInv', showBienvenue);
    $('bvCreer').onclick = function(){
      var b = $('bvCreer'); b.disabled = true; b.textContent = 'Création…';
      creerFoyer('Moi').then(lancer).catch(function(err){ b.disabled = false; b.textContent = 'Créer mon portefeuille'; $('bvMsg').className = 'rg-msg ko'; $('bvMsg').textContent = msgErr(err); });
    };
    $('bvRe').onclick = showBienvenue;
    $('bvOut').onclick = function(){ auth.signOut(); };
  });
}

function boot(){
  if(!ok){ appEl().innerHTML = '<div class="empty"><p>Impossible de charger Firebase.<br>Vérifiez votre connexion internet, puis rouvrez l\'appli.</p></div>'; return; }
  auth.onAuthStateChanged(function(u){
    USER = u;
    window.__fbUser = u;
    if(!u){ if(started){ location.reload(); return; } showLogin(); return; }
    if(started) return;
    chargement();
    resoudre(u).then(function(c){
      if(c.mode==='aucun') showBienvenue(); else lancer(c);
    }).catch(function(err){
      appEl().innerHTML = '<div class="empty"><p>'+esc(msgErr(err))+'<br>Vérifiez votre connexion, puis rouvrez l\'appli.</p></div>';
    });
  });
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', boot); else boot();

/* ================= copie de secours : export / import ================= */
function exporter(btnMsg){
  if(btnMsg) btnMsg.textContent = 'Préparation…';
  var docs = {};
  return Promise.all(COLLS.map(function(c){ return dbw.collection(c).get().then(function(qs){ qs.docs.forEach(function(d){ docs[c+'/'+d.id] = d.data(); }); }); }))
    .then(function(){
      var d = new Date(), nom = 'Budget - sauvegarde '+d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')+'.json';
      download(nom, JSON.stringify({app:'budget-clair', exportedAt:d.toISOString(), docs:docs}), 'application/json');
      if(btnMsg) btnMsg.textContent = '';
    }).catch(function(){ if(btnMsg) btnMsg.textContent = 'Sauvegarde impossible (connexion ?).'; });
}
document.addEventListener('change', function(ev){
  if(!ev.target || ev.target.id!=='impFile' || !ev.target.files || !ev.target.files[0]) return;
  var msg = $('impMsg');
  var r = new FileReader();
  r.onload = function(){
    var o;
    try{ o = JSON.parse(r.result); }catch(e){ o = null; }
    if(!o || !o.docs || !o.docs['config/main']){ msg.style.color = 'var(--critical)'; msg.textContent = 'Ce fichier n\'est pas une sauvegarde de l\'appli. Rien n\'a été modifié.'; return; }
    var paths = Object.keys(o.docs).filter(function(p){ return /^[A-Za-z0-9_-]+\/[A-Za-z0-9_.~:@+-]+$/.test(p) && COLLS.indexOf(p.split('/')[0])>-1; });
    msg.style.color = ''; msg.textContent = 'Import en cours… (' + paths.length + ' éléments)';
    var chunks = [];
    for(var i=0; i<paths.length; i+=400) chunks.push(paths.slice(i, i+400));
    var p = Promise.resolve();
    chunks.forEach(function(ch){
      p = p.then(function(){ var b = fdb.batch(); ch.forEach(function(path){ b.set(dbw.doc(path), o.docs[path]); }); return b.commit(); });
    });
    p.then(function(){ msg.style.color = 'var(--good)'; msg.textContent = paths.length + ' éléments importés.'; setTimeout(function(){ location.reload(); }, 800); })
     .catch(function(err){ msg.style.color = 'var(--critical)'; msg.textContent = 'L\'import a échoué (' + (err && err.code || 'erreur') + '). Réessayez.'; });
  };
  r.readAsText(ev.target.files[0]);
});

/* le menu des portefeuilles se ferme quand on touche ailleurs */
document.addEventListener('click', function(ev){
  if(!RG.pfMenu) return;
  var t = ev.target; if(t && t.closest && t.closest('.pf-wrap')) return;
  RG.pfMenu = false; if(window.render) render();
}, true);
/* ================= page Réglages (bouton en haut à droite) ================= */
var RG = {invite:'', inviteMsg:'', inviteTxt:'', suppr:false, supprMsg:'', armRetrait:null, invites:null};
var ICON_WALLET = '<svg class="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 7h15a3 3 0 0 1 3 3v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 7l12-3v3"/><circle cx="16.5" cy="13.5" r="1.2"/></svg>';
var ICON_USER = '<svg class="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>';
function estProprio(){ return CTX.mode==='foyer' && CTX.foyer && CTX.foyer.owner===USER.uid; }
function lienAppli(){ return location.origin + location.pathname; }
function texteInvitation(em){
  return 'Bonjour ! Je t\'invite à partager notre budget dans l\'appli Budget.\n'+
    '1. Ouvre ce lien : '+lienAppli()+'\n'+
    '2. Touche « Créer un compte » et utilise cette adresse : '+em+'\n'+
    '3. Confirme ton adresse avec l\'e-mail de vérification reçu (regarde aussi dans les indésirables)\n'+
    '4. Reviens dans l\'appli et touche « Rejoindre ».';
}
function chargerInvites(){
  if(CTX.mode!=='foyer') return;
  fdb.collection('invitations').where('foyer','==',CTX.foyerId).get().then(function(qs){
    RG.invites = qs.docs.map(function(d){ return {email:d.id, data:d.data()}; });
    if(window.requestRender) requestRender();
  }).catch(function(){ RG.invites = []; });
}
window.BC_HOOKS = {
  heroBtn: function(){
    var L = CTX.liste || []; if(!CTX.pfId) return '';
    var P0 = L.find(function(x){ return x.id===CTX.pfId; });
    var h = '<div class="pf-wrap"><button type="button" class="pf-sel" id="pfBtn" aria-expanded="'+(RG.pfMenu?'true':'false')+'">'+ICON_WALLET+'<span>'+esc(P0 ? P0.nom : 'Portefeuille')+'</span></button>';
    if(RG.pfMenu){
      h += '<div class="pf-menu" role="menu"><div class="pf-menu-t">Mes portefeuilles</div>';
      L.forEach(function(P){
        var actuel = P.id===CTX.pfId;
        h += '<button type="button" class="pf-item'+(actuel?' on':'')+'" data-pfid="'+esc(P.id)+'"'+(actuel?'':' data-pfopen="'+esc(P.id)+'"')+'><b>'+esc(P.nom)+'</b><em>'+(P.id==='ancien'?'budget d\'origine':(P.membres>1?P.membres+' membres':'vous seul'))+'</em>'+(actuel?'<i>✓</i>':'')+'</button>';
      });
      if(L.length<2) h += '<p class="pf-menu-h">Un portefeuille = des comptes et un budget à part. Par exemple « Moi » pour vous, et « Nous » à partager.</p>';
      h += '<button type="button" class="pf-new" id="pfMenuNew">＋ Créer un portefeuille</button>'+
           '<button type="button" class="pf-gerer" id="pfMenuGerer">Renommer, inviter…</button></div>';
    }
    return h + '</div>';
  },
  autresComptes: function(){ return CTX.autres || []; },
  pfActuel: function(){ var P = (CTX.liste||[]).find(function(x){ return x.id===CTX.pfId; }); return {id:CTX.pfId, nom: P ? P.nom : ''}; },
  ecrireAutre: ecrireAutre,

  pageHaut: function(){
    var h = '';
    if(CTX.invitation) h += invitationHtml(CTX.invitation, 'rgInv');
    /* portefeuilles */
    var L = CTX.liste || [];
    h += '<div class="card" id="pfCard"><h3>Portefeuilles</h3>';
    h += '<p class="hint-line" style="margin-top:0;">Chaque portefeuille a ses comptes et son budget. Par exemple « Moi » (à vous seul) et « Nous » (partagé). Les membres d\'un portefeuille ne voient pas les autres.</p>';
    L.forEach(function(P){
      var actuel = P.id===CTX.pfId;
      h += '<div class="rg-row"><span><b style="color:var(--ink);">'+esc(P.nom)+'</b>'+(actuel?'<em>ouvert</em>':'')+(P.id==='ancien'?'<em>budget d\'origine</em>':(P.membres>1?'<em>'+P.membres+' membres</em>':'<em>vous seul</em>'))+'</span>'+
        (actuel ? '' : '<button class="btn-mini btn-ok" data-pfopen="'+esc(P.id)+'">Ouvrir</button>')+'</div>';
    });
    if(RG.pfNouveau){
      h += '<div class="tf-row" style="margin-top:10px;"><input class="text-input" id="pfNom" maxlength="60" placeholder="Nom (ex. Moi, Nous)" value="'+esc(RG.pfNom||'')+'"><button class="btn btn-primary btn-sm" id="pfCreer" style="flex:0 0 auto;">Créer</button></div>'+
        '<div class="tf-row" style="margin-top:6px;"><button class="btn-mini" data-pfnom="Moi">Moi</button><button class="btn-mini" data-pfnom="Nous">Nous</button><button class="btn-mini" id="pfAnnuler">Annuler</button></div>'+
        '<div class="rg-msg" id="pfMsg"></div>';
    } else h += '<button class="add-row-btn" id="pfAjout">+ Nouveau portefeuille</button>';
    h += '</div>';
    return h;
  },
  page: function(){
    var h = '';
    /* compte */
    h += '<div class="card"><h3>Mon compte</h3>';
    h += '<div class="rg-row"><span>'+esc(emailDe(USER))+(USER.emailVerified ? '' : '<em>adresse non vérifiée</em>')+'</span><button class="btn-mini" id="rgOut">Se déconnecter</button></div>';
    if(!USER.emailVerified && CTX.mode!=='ancien') h += '<p class="hint-line" style="margin-top:4px;">Confirmez votre adresse : c\'est nécessaire pour rejoindre un budget partagé. <button type="button" class="link-btn" id="rgVerif">Renvoyer l\'e-mail</button></p>';
    h += '<div class="rg-row"><span>Mot de passe</span><button class="btn-mini" id="rgPass">Recevoir un lien pour le changer</button></div>';
    h += '<div class="rg-msg" id="rgCptMsg"></div></div>';
    /* foyer */
    if(CTX.mode==='ancien'){
      h += '<div class="card"><h3>Ce portefeuille : Nous</h3><p class="hint-line" style="margin-top:0;">Budget d\'origine, partagé entre les deux adresses autorisées dans les règles de sécurité Firebase. Ces données n\'ont pas été déplacées.</p></div>';
    } else if(CTX.foyer){
      var F = CTX.foyer, proprio = estProprio();
      h += '<div class="card"><h3>Ce portefeuille et ses membres</h3>';
      h += '<label class="pl-det" style="border:0;padding:0;background:none;margin:0 0 6px;"><label><span>Nom</span><input class="text-input" id="rgNom" value="'+esc(F.nom||'')+'" maxlength="60"></label></label>';
      h += '<div style="font-size:12px;font-weight:600;color:var(--ink-muted);margin:10px 0 2px;">Membres</div>';
      (F.emails||[]).forEach(function(em){
        var moi = em===emailDe(USER), estProp = false;
        /* l'e-mail du propriétaire est le premier enregistré */
        if((F.emails||[])[0]===em) estProp = true;
        h += '<div class="rg-row"><span>'+esc(em)+(moi?'<em>vous</em>':'')+(estProp?'<em>créateur</em>':'')+'</span>'+
          (proprio && !moi ? (RG.armRetrait===em ? '<span><button class="btn-mini danger" data-rgretok="'+esc(em)+'">Retirer</button> <button class="btn-mini" id="rgRetNo">Non</button></span>' : '<button class="btn-mini" data-rgret="'+esc(em)+'">Retirer</button>') : '')+'</div>';
      });
      if(RG.invites && RG.invites.length){
        h += '<div style="font-size:12px;font-weight:600;color:var(--ink-muted);margin:10px 0 2px;">Invitations en attente</div>';
        RG.invites.forEach(function(x){ h += '<div class="rg-row"><span>'+esc(x.email)+'</span><button class="btn-mini" data-rginvdel="'+esc(x.email)+'">Annuler</button></div>'; });
      }
      if((F.membres||[]).length < 6){
        h += '<div style="font-size:12px;font-weight:600;color:var(--ink-muted);margin:14px 0 6px;">Inviter quelqu\'un (il ou elle verra et modifiera ce budget)</div>';
        h += '<div class="tf-row"><input class="text-input" id="rgInvEmail" type="email" placeholder="Son adresse e-mail" value="'+esc(RG.invite)+'"><button class="btn btn-primary btn-sm" id="rgInvOk" style="flex:0 0 auto;">Inviter</button></div>';
        if(RG.inviteMsg) h += '<div class="rg-msg">'+RG.inviteMsg+'</div>';
        if(RG.inviteTxt) h += '<div class="invit-box">'+esc(RG.inviteTxt)+'</div><div class="tf-row" style="margin-top:8px;"><button class="btn-mini" id="rgInvShare">Envoyer ce message…</button><button class="btn-mini" id="rgInvCopy">Copier</button></div>';
        h += '<p class="hint-line">L\'appli n\'envoie pas d\'e-mail d\'invitation : transmettez le message (SMS, WhatsApp, e-mail…).</p>';
      }
      if(!proprio) h += '<div class="tf-row" style="margin-top:10px;"><button class="btn-mini" id="rgQuit">Quitter ce budget</button></div>';
      h += '<div class="rg-msg" id="rgFoyerMsg"></div></div>';
    }
    /* sauvegarde */
    h += '<div class="card"><h3>Copie de secours</h3><p class="hint-line" style="margin-top:0;">Un fichier (.json) avec toutes les données du budget, à garder dans vos Fichiers. Les bilans lisibles (PDF) se téléchargent dans l\'onglet Bilan.</p>'+
      '<div class="tf-row" style="margin-top:10px;"><button class="btn btn-ghost" id="fbExport">Télécharger la copie de secours</button></div><div class="rg-msg" id="fbExportMsg"></div></div>';
    /* suppression du compte */
    if(CTX.mode==='foyer'){
      var seul = CTX.foyer && (CTX.foyer.membres||[]).length===1;
      h += '<div class="card danger-zone"><h3>Supprimer mon compte</h3>';
      if(estProprio() && !seul){
        h += '<p class="hint-line" style="margin-top:0;">Vous avez créé ce budget et il a d\'autres membres : retirez-les d\'abord, ou demandez-leur de partir.</p>';
      } else if(!RG.suppr){
        h += '<p class="hint-line" style="margin-top:0;">'+(seul ? 'Supprime définitivement votre compte et tout votre budget (dépenses, comptes, historique). Pensez à télécharger une copie de secours avant.' : 'Supprime votre compte. Le budget partagé reste aux autres membres.')+'</p>'+
          '<div class="tf-row" style="margin-top:10px;"><button class="btn-mini" id="rgSuppr">Supprimer mon compte…</button></div>';
      } else {
        h += '<p style="font-size:13.5px;margin:0 0 8px;">Tapez votre mot de passe pour confirmer. <b>C\'est définitif.</b></p>'+
          '<div class="tf-row"><input class="text-input" id="rgSupprPw" type="password" autocomplete="current-password" placeholder="Mot de passe"><button class="btn btn-danger btn-sm" id="rgSupprOk" style="flex:0 0 auto;">Supprimer</button></div>'+
          '<div class="tf-row" style="margin-top:8px;"><button class="btn-mini" id="rgSupprNo">Annuler</button></div>';
      }
      h += '<div class="rg-msg ko" id="rgSupprMsg">'+esc(RG.supprMsg)+'</div></div>';
    }
    return h;
  },
  wire: function(){
    var pb2 = $('pfBtn'); if(pb2) pb2.onclick = function(ev){ ev.stopPropagation(); RG.pfMenu = !RG.pfMenu; render(); };
    var mn = $('pfMenuNew'); if(mn) mn.onclick = function(){ RG.pfMenu = false; state.tab = 'reglages'; RG.pfNouveau = true; render(); window.scrollTo(0,0); var n = $('pfNom'); if(n) n.focus(); };
    var mg = $('pfMenuGerer'); if(mg) mg.onclick = function(){ RG.pfMenu = false; state.tab = 'reglages'; render(); window.scrollTo(0,0); };
    Array.prototype.forEach.call(document.querySelectorAll('[data-pfopen]'), function(b){ b.onclick = function(){ chargement('Ouverture du portefeuille…'); changerPortefeuille(b.getAttribute('data-pfopen')); }; });
    var pa = $('pfAjout'); if(pa) pa.onclick = function(){ RG.pfNouveau = true; render(); var n = $('pfNom'); if(n) n.focus(); };
    var pn = $('pfAnnuler'); if(pn) pn.onclick = function(){ RG.pfNouveau = false; render(); };
    var pnom = $('pfNom'); if(pnom) pnom.oninput = function(){ RG.pfNom = pnom.value; };
    Array.prototype.forEach.call(document.querySelectorAll('[data-pfnom]'), function(b){ b.onclick = function(){ RG.pfNom = b.getAttribute('data-pfnom'); var n = $('pfNom'); if(n) n.value = RG.pfNom; }; });
    var pc = $('pfCreer');
    if(pc) pc.onclick = function(){
      var nom = String(RG.pfNom||'').trim();
      if(!nom){ var n = $('pfNom'); if(n){ n.classList.add('field-error'); n.focus(); } return; }
      pc.disabled = true;
      creerFoyer(nom).then(function(){ location.reload(); }).catch(function(e){ pc.disabled = false; var m = $('pfMsg'); if(m){ m.className = 'rg-msg ko'; m.textContent = msgErr(e); } });
    };
    var pb = $('profBtn');
    if(pb) pb.onclick = function(){
      if(state.tab==='reglages'){ state.tab = 'saisie'; }
      else { state.tab = 'reglages'; RG.invites = null; chargerInvites(); }
      render(); window.scrollTo(0,0);
    };
    if(state.tab!=='reglages') return;
    if(CTX.mode==='foyer' && RG.invites===null){ RG.invites = []; chargerInvites(); }
    if(CTX.invitation) brancherInvitation(CTX.invitation, 'rgInv', function(){ CTX.invitation = null; render(); });
    function msg(id, t, k){ var m = $(id); if(m){ m.className = 'rg-msg '+(k||''); m.textContent = t; } }
    var o = $('rgOut'); if(o) o.onclick = function(){ auth.signOut(); };
    var v = $('rgVerif'); if(v) v.onclick = function(){ USER.sendEmailVerification().then(function(){ msg('rgCptMsg', 'E-mail de vérification envoyé à '+emailDe(USER)+'.', 'ok'); }).catch(function(e){ msg('rgCptMsg', msgErr(e), 'ko'); }); };
    var pw = $('rgPass'); if(pw) pw.onclick = function(){ auth.sendPasswordResetEmail(emailDe(USER)).then(function(){ msg('rgCptMsg', 'Lien envoyé à '+emailDe(USER)+'.', 'ok'); }).catch(function(e){ msg('rgCptMsg', msgErr(e), 'ko'); }); };
    var ex = $('fbExport'); if(ex) ex.onclick = function(){ exporter($('fbExportMsg')); };
    var nom = $('rgNom');
    if(nom) nom.onchange = function(){
      var n = nom.value.trim().slice(0,60) || 'Mon budget';
      fdb.doc('foyers/'+CTX.foyerId).update({nom:n}).then(function(){ msg('rgFoyerMsg', 'Nom enregistré.', 'ok'); }).catch(function(e){ msg('rgFoyerMsg', msgErr(e), 'ko'); });
    };
    var ie = $('rgInvEmail'); if(ie) ie.oninput = function(){ RG.invite = ie.value; };
    var io = $('rgInvOk');
    if(io) io.onclick = function(){
      var em = String(RG.invite||'').trim().toLowerCase();
      if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)){ RG.inviteMsg = '<span style="color:var(--critical);">Adresse e-mail invalide.</span>'; RG.inviteTxt = ''; render(); return; }
      if((CTX.foyer.emails||[]).indexOf(em)>-1){ RG.inviteMsg = 'Cette personne fait déjà partie du budget.'; RG.inviteTxt = ''; render(); return; }
      io.disabled = true;
      fdb.doc('invitations/'+em).set({foyer:CTX.foyerId, nomFoyer:CTX.foyer.nom||'Budget', de:emailDe(USER), le:maintenant()}).then(function(){
        RG.inviteMsg = '<span style="color:var(--good);">Invitation enregistrée pour '+esc(em)+'.</span> Envoyez-lui ce message :';
        RG.inviteTxt = texteInvitation(em); RG.invite = '';
        chargerInvites(); render();
      }).catch(function(e){ io.disabled = false; RG.inviteMsg = '<span style="color:var(--critical);">'+esc(e && e.code==='permission-denied' ? 'Cette adresse a déjà une invitation d\'un autre budget.' : msgErr(e))+'</span>'; render(); });
    };
    var sh = $('rgInvShare');
    if(sh) sh.onclick = function(){
      if(navigator.share) navigator.share({text: RG.inviteTxt}).catch(function(){});
      else location.href = 'mailto:?subject='+encodeURIComponent('Invitation : budget partagé')+'&body='+encodeURIComponent(RG.inviteTxt);
    };
    var cp = $('rgInvCopy');
    if(cp) cp.onclick = function(){ try{ navigator.clipboard.writeText(RG.inviteTxt).then(function(){ toast('Message copié', 'good'); }); }catch(e){} };
    Array.prototype.forEach.call(document.querySelectorAll('[data-rginvdel]'), function(b){
      b.onclick = function(){ fdb.doc('invitations/'+b.getAttribute('data-rginvdel')).delete().then(chargerInvites).catch(function(e){ msg('rgFoyerMsg', msgErr(e), 'ko'); }); };
    });
    Array.prototype.forEach.call(document.querySelectorAll('[data-rgret]'), function(b){ b.onclick = function(){ RG.armRetrait = b.getAttribute('data-rgret'); render(); }; });
    var rn = $('rgRetNo'); if(rn) rn.onclick = function(){ RG.armRetrait = null; render(); };
    Array.prototype.forEach.call(document.querySelectorAll('[data-rgretok]'), function(b){
      b.onclick = function(){
        var em = b.getAttribute('data-rgretok'), F = CTX.foyer, i = (F.emails||[]).indexOf(em);
        /* membres et e-mails sont rangés dans le même ordre */
        var uid = i>-1 ? (F.membres||[])[i] : null;
        if(!uid){ msg('rgFoyerMsg', 'Membre introuvable.', 'ko'); return; }
        fdb.doc('foyers/'+CTX.foyerId).update({
          membres: firebase.firestore.FieldValue.arrayRemove(uid),
          emails: firebase.firestore.FieldValue.arrayRemove(em)
        }).then(function(){ RG.armRetrait = null; }).catch(function(e){ msg('rgFoyerMsg', msgErr(e), 'ko'); });
      };
    });
    var q = $('rgQuit');
    if(q) q.onclick = function(){
      if(!confirm('Quitter ce budget ? Vous ne le verrez plus (les autres membres le gardent).')) return;
      quitterFoyer().then(function(){ localStorage.removeItem(memoKey(USER)); location.reload(); }).catch(function(e){ msg('rgFoyerMsg', msgErr(e), 'ko'); });
    };
    var sp = $('rgSuppr'); if(sp) sp.onclick = function(){ RG.suppr = true; RG.supprMsg = ''; render(); };
    var sn = $('rgSupprNo'); if(sn) sn.onclick = function(){ RG.suppr = false; RG.supprMsg = ''; render(); };
    var so = $('rgSupprOk');
    if(so) so.onclick = function(){
      var pwd = ($('rgSupprPw')||{}).value || '';
      if(!pwd){ msg('rgSupprMsg', 'Tapez votre mot de passe.', 'ko'); return; }
      so.disabled = true; msg('rgSupprMsg', 'Suppression…', '');
      var cred = firebase.auth.EmailAuthProvider.credential(USER.email, pwd);
      USER.reauthenticateWithCredential(cred).then(supprimerTout).then(function(){
        try{ localStorage.removeItem(memoKey(USER)); }catch(e){}
        return USER.delete();
      }).then(function(){ location.reload(); }).catch(function(e){ so.disabled = false; RG.supprMsg = msgErr(e); msg('rgSupprMsg', RG.supprMsg, 'ko'); });
    };
  }
};
function quitterFoyer(){
  var em = emailDe(USER);
  return fdb.doc('foyers/'+CTX.foyerId).update({
    membres: firebase.firestore.FieldValue.arrayRemove(USER.uid),
    emails: firebase.firestore.FieldValue.arrayRemove(em)
  }).then(function(){ return fdb.doc('users/'+USER.uid).delete().catch(function(){}); });
}
/* compte supprimé : seul membre -> tout le budget part avec ; sinon on quitte le budget */
function supprimerTout(){
  var seul = CTX.foyer && (CTX.foyer.membres||[]).length===1;
  if(!seul) return quitterFoyer();
  var refs = [];
  return Promise.all(COLLS.map(function(c){ return dbw.collection(c).get().then(function(qs){ qs.docs.forEach(function(d){ refs.push(d.ref); }); }); }))
    .then(function(){ return fdb.collection('invitations').where('foyer','==',CTX.foyerId).get().then(function(qs){ qs.docs.forEach(function(d){ refs.push(d.ref); }); }).catch(function(){}); })
    .then(function(){
      var p = Promise.resolve();
      for(var i=0; i<refs.length; i+=400){ (function(ch){ p = p.then(function(){ var b = fdb.batch(); ch.forEach(function(r){ b.delete(r); }); return b.commit(); }); })(refs.slice(i, i+400)); }
      return p;
    })
    .then(function(){ return fdb.doc('foyers/'+CTX.foyerId).delete(); })
    .then(function(){ return fdb.doc('users/'+USER.uid).delete().catch(function(){}); });
}
})();
</script>
""" % {'v': FB_VERSION, 'cfg': FIREBASE_CONFIG, 'essai': 'true' if ESSAI else 'false'}

head_end = s.index('</style>') + len('</style>')
body_start = s.index('<script>')
doc = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       + s[:head_end] + EXTRA_CSS + '\n</head>\n<body>'
       + ('<div class="essai-bandeau">Version d\'essai · votre vrai budget n\'est pas touché</div>' if ESSAI else '')
       + s[head_end:body_start] + SHIM + s[body_start:] + '\n</body>\n</html>\n')
os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
open(out_path, 'w', encoding='utf-8').write(doc)
if ESSAI and not args:   # l'icône à côté de la page d'essai
    shutil.copyfile(os.path.join(ROOT, 'apple-touch-icon.png'), os.path.join(ROOT, 'essai', 'apple-touch-icon.png'))
print('ok', len(doc))
