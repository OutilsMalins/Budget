(function(){
function clone(o){ return JSON.parse(JSON.stringify(o)); }
var KEY='fakefb'; var S; try{ S=JSON.parse(localStorage.getItem(KEY)||'null'); }catch(e){} if(!S) S={docs:{}, user:null};
if(window.__seed && !S.seeded){ S.docs=clone(window.__seed); S.seeded=true; }
function save(){ localStorage.setItem(KEY, JSON.stringify(S)); }
window.__fb = S;
var docSubs={}, qSubs=[];
function denied(){ return !S.user || (window.__allowed && window.__allowed.indexOf(S.user.email)<0); }
function snapOf(path){ var v=S.docs[path]; var d=v?clone(v):undefined; return {exists:!!v, id:path.split('/').pop(), data:function(){return d;}}; }
function runQuery(q){ var pre=q.coll+'/'; var list=Object.keys(S.docs).filter(function(p){ return p.indexOf(pre)===0 && p.slice(pre.length).indexOf('/')<0; }).filter(function(p){ return q.where.every(function(w){ return S.docs[p][w[0]]===w[2]; }); });
  if(q.order){ var f=q.order[0],dir=q.order[1]==='desc'?-1:1; list.sort(function(a,b){ var x=S.docs[a][f],y=S.docs[b][f]; return (x>y?1:x<y?-1:0)*dir; }); }
  list=list.map(snapOf); return {docs:list,size:list.length,empty:!list.length}; }
function fire(path){ setTimeout(function(){ (docSubs[path]||[]).forEach(function(cb){ cb(snapOf(path)); }); qSubs.forEach(function(s){ if(!s.dead && path.indexOf(s.q.coll+'/')===0) s.cb(runQuery(s.q)); }); },5); }
function err(){ var e=new Error('denied'); e.code='permission-denied'; return e; }
function write(path, fn){ if(denied()) return Promise.reject(err()); fn(); save(); fire(path); return Promise.resolve(); }
function docRef(path){ return { id:path.split('/').pop(), path:path,
  get:function(){ return denied()?Promise.reject(err()):Promise.resolve(snapOf(path)); },
  set:function(d){ return write(path,function(){ S.docs[path]=clone(d); }); },
  update:function(d){ return write(path,function(){ S.docs[path]=Object.assign(S.docs[path]||{}, clone(d)); }); },
  delete:function(){ return write(path,function(){ delete S.docs[path]; }); },
  onSnapshot:function(cb,eb){ if(denied()){ setTimeout(function(){ eb&&eb(err()); },5); return function(){}; } (docSubs[path]=docSubs[path]||[]).push(cb); setTimeout(function(){ cb(snapOf(path)); },5); return function(){}; } }; }
function query(coll, where, order){ var q={coll:coll, where:where||[], order:order}; var api={ where:function(f,op,v){ return query(coll,q.where.concat([[f,op,v]]),order); }, orderBy:function(f,d){ return query(coll,q.where,[f,d]); }, limit:function(){ return api; },
  doc:function(id){ return docRef(coll+'/'+(id||Math.random().toString(36).slice(2))); },
  get:function(){ return denied()?Promise.reject(err()):Promise.resolve(runQuery(q)); },
  onSnapshot:function(cb,eb){ if(denied()){ setTimeout(function(){ eb&&eb(err()); },5); return function(){}; } var s={q:q,cb:cb}; qSubs.push(s); setTimeout(function(){ cb(runQuery(q)); },5); return function(){ s.dead=true; }; } }; return api; }
var authCbs=[];
var fs={ settings:function(){}, enablePersistence:function(){ return Promise.resolve(); }, doc:docRef, collection:function(c){ return query(c); },
  batch:function(){ var ops=[]; return { set:function(ref,d){ ops.push([ref.path,d]); }, commit:function(){ if(denied()) return Promise.reject(err()); ops.forEach(function(o){ S.docs[o[0]]=clone(o[1]); }); save(); ops.forEach(function(o){ fire(o[0]); }); return Promise.resolve(); } }; } };
var au={ onAuthStateChanged:function(cb){ authCbs.push(cb); setTimeout(function(){ cb(S.user); },10); },
  signInWithEmailAndPassword:function(e,p){ if(p!=='secret') { var x=new Error('x'); x.code='auth/invalid-credential'; return Promise.reject(x); } S.user={email:e}; save(); authCbs.forEach(function(cb){ cb(S.user); }); return Promise.resolve({user:S.user}); },
  signOut:function(){ S.user=null; save(); authCbs.forEach(function(cb){ cb(null); }); return Promise.resolve(); },
  sendPasswordResetEmail:function(){ return Promise.resolve(); } };
window.firebase={ initializeApp:function(){}, auth:function(){ return au; }, firestore:function(){ return fs; } };
})();
