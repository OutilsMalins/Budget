"""Construit la version « page web » de l'appli : Firebase (connexion + base Firestore)
à la place du stockage de Claude.
Usage : python3 build/build_firebase.py            -> écrit index.html (à la racine du dépôt, publié par GitHub Pages)
        python3 build/build_firebase.py <sortie.html> [<source.html>]"""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'src', 'budget-clair.html')
out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'index.html')
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
    global s
    c = s.count(a)
    assert c == n, (c, a[:90])
    s = s.replace(a, b)

# ---------- icône : fichier à côté de la page (plus fiable sur iPhone qu'une image intégrée)
a = s.index('<link rel="apple-touch-icon"')
b = s.index('>', a) + 1
s = s[:a] + '<link rel="apple-touch-icon" href="apple-touch-icon.png">\n<meta name="apple-mobile-web-app-status-bar-style" content="default">' + s[b:]
rep('<meta name="apple-mobile-web-app-title" content="Budget Clair">', '<meta name="apple-mobile-web-app-title" content="Budget">')

# ---------- premier lancement : importer la sauvegarde venue de Claude
rep("""      '<div class="empty"><div class="em">💶</div><p><strong>Aucun budget initialisé.</strong></p>'+
      '<p style="font-size:12.5px;margin-top:4px;">On démarre avec un budget vide (tout à 0 €) : vous le remplirez ensuite.</p>'+
      '<button class="btn btn-primary" id="seedBtn" style="margin-top:14px;">Initialiser mon budget</button></div>';""",
"""      '<div class="card" style="max-width:520px;margin:30px auto;text-align:center;"><div style="font-size:30px;">📦</div><h3 style="justify-content:center;margin:6px 0 8px;">Bienvenue dans votre budget</h3>'+
      '<p class="hint-line" style="margin-top:0;">Pour retrouver toutes vos données, importez le fichier de sauvegarde (.json) que Claude vous a envoyé. À faire une seule fois, sur un seul téléphone : l\\'autre le verra tout seul.</p>'+
      '<label class="btn btn-primary" style="display:inline-block;margin-top:12px;cursor:pointer;">📥 Importer ma sauvegarde<input type="file" id="impFile" accept=".json,application/json" hidden></label>'+
      '<p class="hint-line" id="impMsg"></p>'+
      '<p class="hint-line" style="margin-top:18px;">Pas de sauvegarde ? <button type="button" class="link-btn" id="seedBtn">Commencer un budget vide</button></p></div>';""")
rep("""Le stockage n\\'est pas disponible dans cette vue.<br>Rouvrez la page depuis Claude.""",
    """Impossible de joindre la base de données.<br>Vérifiez votre connexion internet, puis rouvrez l\\'appli.""")

# ---------- carte « Compte » dans le Bilan : qui est connecté, sauvegarde, déconnexion
rep("""plier('hist', renderHistoryCard());""",
    """plier('hist', renderHistoryCard()) + compteFbCard();""")
rep("""/* ---------- où va l'argent""", r"""function compteFbCard(){
  var u = window.__fbUser;
  return '<div class="card"><h3>👤 Compte</h3>'+
    '<p class="pareto-sub">Connecté : <b>'+escHtml(u && u.email || '')+'</b>. Vos données sont dans votre base Firebase, accessibles seulement à vos deux comptes.</p>'+
    '<p class="pareto-sub">📄 Vos bilans lisibles (PDF) se téléchargent plus haut, dans « Bilans de fin de mois ». La copie de secours ci-dessous sert seulement à restaurer l\'appli en cas de problème.</p>'+
    '<div class="tf-row" style="margin-top:10px;"><button class="btn btn-ghost" id="fbExport">🛟 Copie de secours</button><button class="btn btn-ghost" id="fbLogout">Se déconnecter</button></div>'+
    '<p class="hint-line" id="fbExportMsg"></p></div>';
}
/* ---------- où va l'argent""")

# ---------- démarrage : seulement une fois connecté
rep("""if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded', initDb); } else { initDb(); }""",
    """window.__startApp = initDb;""")

SHIM = r"""
<script src="https://www.gstatic.com/firebasejs/%(v)s/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/%(v)s/firebase-auth-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/%(v)s/firebase-firestore-compat.js"></script>
<script>
/* ===== Firebase : connexion + base de données, à la place du stockage de Claude ===== */
(function(){
var CONFIG = %(cfg)s;
var ok = !!window.firebase;
var fdb = null, auth = null;
if(ok){
  firebase.initializeApp(CONFIG);
  auth = firebase.auth();
  fdb = firebase.firestore();
  try{ fdb.settings({ignoreUndefinedProperties:true, merge:true}); }catch(e){}
  try{ fdb.enablePersistence({synchronizeTabs:true}).catch(function(){}); }catch(e){}
}
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
  if(name==='db') return fdb ? Promise.resolve(fdb) : Promise.reject(new Error('firebase indisponible'));
  if(name==='downloads') return Promise.resolve({ save: function(r){ download(r.filename, r.data); return Promise.resolve({status:'saved'}); } });
  return Promise.reject(new Error('indisponible'));
} };

function esc(t){ return String(t==null?'':t).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
function appEl(){ return document.getElementById('app'); }
var MSG = {
  'auth/invalid-credential':'E-mail ou mot de passe incorrect.',
  'auth/invalid-login-credentials':'E-mail ou mot de passe incorrect.',
  'auth/wrong-password':'E-mail ou mot de passe incorrect.',
  'auth/user-not-found':'Aucun compte avec cet e-mail.',
  'auth/invalid-email':'Cet e-mail n\'est pas valide.',
  'auth/too-many-requests':'Trop d\'essais. Patientez quelques minutes.',
  'auth/network-request-failed':'Pas de connexion internet.',
  'auth/user-disabled':'Ce compte est désactivé.'
};
function showLogin(msg){
  appEl().innerHTML =
    '<div class="card" style="max-width:420px;margin:40px auto;">'+
    '<div style="font-size:30px;text-align:center;">💶</div><h3 style="justify-content:center;margin:6px 0 4px;font-size:18px;">Budget</h3>'+
    '<p class="hint-line" style="text-align:center;margin:0 0 14px;">Connectez-vous avec le compte créé dans Firebase.</p>'+
    '<form id="loginForm" style="display:flex;flex-direction:column;gap:10px;">'+
    '<input class="text-input" id="lgEmail" type="email" autocomplete="username" placeholder="E-mail" required style="font-size:16px;">'+
    '<input class="text-input" id="lgPass" type="password" autocomplete="current-password" placeholder="Mot de passe" required style="font-size:16px;">'+
    '<button class="btn btn-primary" type="submit" id="lgBtn">Se connecter</button></form>'+
    '<p class="hint-line" id="lgMsg" style="color:var(--critical);text-align:center;">'+esc(msg||'')+'</p>'+
    '<p class="hint-line" style="text-align:center;"><button type="button" class="link-btn" id="lgReset">Mot de passe oublié ?</button></p></div>';
  var f = document.getElementById('loginForm');
  f.onsubmit = function(ev){
    ev.preventDefault();
    var btn = document.getElementById('lgBtn'); btn.disabled = true; btn.textContent = 'Connexion…';
    auth.signInWithEmailAndPassword(document.getElementById('lgEmail').value.trim(), document.getElementById('lgPass').value)
      .catch(function(err){ btn.disabled = false; btn.textContent = 'Se connecter'; document.getElementById('lgMsg').textContent = MSG[err && err.code] || ('Connexion impossible ('+(err && err.code || 'erreur')+').'); });
  };
  document.getElementById('lgReset').onclick = function(){
    var em = document.getElementById('lgEmail').value.trim(), m = document.getElementById('lgMsg');
    if(!em){ m.textContent = 'Tapez d\'abord votre e-mail ci-dessus.'; return; }
    auth.sendPasswordResetEmail(em).then(function(){ m.style.color = 'var(--good)'; m.textContent = 'Un e-mail pour changer le mot de passe vient d\'être envoyé.'; })
      .catch(function(err){ m.textContent = MSG[err && err.code] || 'Envoi impossible.'; });
  };
}
var started = false;
function boot(){
  if(!ok){ appEl().innerHTML = '<div class="empty"><div class="em">⚠️</div><p>Impossible de charger Firebase.<br>Vérifiez votre connexion internet, puis rouvrez l\'appli.</p></div>'; return; }
  auth.onAuthStateChanged(function(u){
    window.__fbUser = u;
    if(!u){ if(started){ location.reload(); return; } showLogin(); return; }
    if(started) return;
    appEl().innerHTML = '<div class="empty"><div class="em">💶</div><p>Chargement de votre budget…</p></div>';
    /* vérifie l'accès (règles Firestore) avant de lancer l'appli */
    fdb.doc('config/main').get().then(function(){
      started = true; window.__startApp();
      /* outils PDF chargés d'avance : l'export devient instantané (utile pour le partage sur iPhone) */
      setTimeout(function(){ try{ if(window.chargerPdfLibs) chargerPdfLibs().catch(function(){}); }catch(e){} }, 2500);
    }).catch(function(err){
      if(err && err.code==='permission-denied'){
        auth.signOut();
        showLogin('Ce compte n\'a pas accès aux données. Vérifiez que son e-mail est bien écrit dans les règles de Firestore.');
      } else { started = true; window.__startApp(); }
    });
  });
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', boot); else boot();

/* ----- import de la sauvegarde (premier lancement) ----- */
document.addEventListener('change', function(ev){
  if(!ev.target || ev.target.id!=='impFile' || !ev.target.files || !ev.target.files[0]) return;
  var msg = document.getElementById('impMsg');
  var r = new FileReader();
  r.onload = function(){
    var o;
    try{ o = JSON.parse(r.result); }catch(e){ o = null; }
    if(!o || !o.docs || !o.docs['config/main']){ msg.style.color = 'var(--critical)'; msg.textContent = 'Ce fichier n\'est pas une sauvegarde de l\'appli. Rien n\'a été modifié.'; return; }
    var paths = Object.keys(o.docs).filter(function(p){ return /^[A-Za-z0-9_-]+\/[A-Za-z0-9_.~:@+-]+$/.test(p); });
    msg.style.color = ''; msg.textContent = 'Import en cours… (' + paths.length + ' éléments)';
    var chunks = [];
    for(var i=0; i<paths.length; i+=400) chunks.push(paths.slice(i, i+400));
    var p = Promise.resolve();
    chunks.forEach(function(ch){
      p = p.then(function(){ var b = fdb.batch(); ch.forEach(function(path){ b.set(fdb.doc(path), o.docs[path]); }); return b.commit(); });
    });
    p.then(function(){ msg.style.color = 'var(--good)'; msg.textContent = '✅ ' + paths.length + ' éléments importés.'; setTimeout(function(){ location.reload(); }, 800); })
     .catch(function(err){ msg.style.color = 'var(--critical)'; msg.textContent = 'L\'import a échoué (' + (err && err.code || 'erreur') + '). Réessayez.'; });
  };
  r.readAsText(ev.target.files[0]);
});

/* ----- carte Compte : sauvegarde + déconnexion ----- */
document.addEventListener('click', function(ev){
  var t = ev.target && ev.target.closest ? ev.target : null; if(!t) return;
  if(t.closest('#fbLogout')){ auth.signOut(); return; }
  if(t.closest('#fbExport')){
    var m = document.getElementById('fbExportMsg'); if(m) m.textContent = 'Préparation…';
    var colls = ['config','depenses','versements','transferts','mois'], docs = {};
    Promise.all(colls.map(function(c){ return fdb.collection(c).get().then(function(qs){ qs.docs.forEach(function(d){ docs[c+'/'+d.id] = d.data(); }); }); }))
      .then(function(){
        var d = new Date(), nom = 'Budget - sauvegarde '+d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')+'.json';
        download(nom, JSON.stringify({app:'budget-clair', exportedAt:d.toISOString(), docs:docs}), 'application/json');
        if(m) m.textContent = '';
      }).catch(function(){ if(m) m.textContent = 'Sauvegarde impossible (connexion ?).'; });
  }
});
})();
</script>
""" % {'v': FB_VERSION, 'cfg': FIREBASE_CONFIG}

head_end = s.index('</style>') + len('</style>')
body_start = s.index('<script>')
doc = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       + s[:head_end] + '\n</head>\n<body>' + s[head_end:body_start] + SHIM + s[body_start:] + '\n</body>\n</html>\n')
open(out_path, 'w', encoding='utf-8').write(doc)
print('ok', len(doc))
