/* Faux « window.claude » pour tester src/budget-clair.html hors de Claude.
   Base en mémoire, mêmes appels que l'appli : doc/collection/where/orderBy/limit/get/onSnapshot,
   set/update/delete. update() fusionne les objets imbriqués et remplace les tableaux
   (comme la vraie base des artefacts). Données de départ : window.__initStore = {"chemin/doc": {...}}. */
(function(){
  function clone(o){ return o === undefined ? undefined : JSON.parse(JSON.stringify(o)); }
  var S = window.__store = { docs: clone(window.__initStore || {}) };
  var docSubs = {}, qSubs = [];
  function snapOf(path){ var v = S.docs[path], d = clone(v); return {exists: !!v, id: path.split('/').pop(), data: function(){ return d; }}; }
  function runQuery(q){
    var pre = q.coll + '/';
    var list = Object.keys(S.docs).filter(function(p){ return p.indexOf(pre) === 0 && p.slice(pre.length).indexOf('/') < 0; })
      .filter(function(p){ return q.where.every(function(w){ return S.docs[p][w[0]] === w[2]; }); });
    if(q.order){ var f = q.order[0], dir = q.order[1] === 'desc' ? -1 : 1;
      list.sort(function(a, b){ var x = S.docs[a][f], y = S.docs[b][f]; return (x > y ? 1 : x < y ? -1 : 0) * dir; }); }
    if(q.lim) list = list.slice(0, q.lim);
    list = list.map(snapOf);
    return {docs: list, size: list.length, empty: !list.length, forEach: function(cb){ list.forEach(cb); }};
  }
  function fire(path){
    setTimeout(function(){
      (docSubs[path] || []).forEach(function(cb){ cb(snapOf(path)); });
      qSubs.forEach(function(s){ if(!s.dead && path.indexOf(s.q.coll + '/') === 0) s.cb(runQuery(s.q)); });
    }, 20);
  }
  function merge(dst, src){
    Object.keys(src).forEach(function(k){
      var v = src[k];
      if(v && typeof v === 'object' && !Array.isArray(v) && dst[k] && typeof dst[k] === 'object' && !Array.isArray(dst[k])) merge(dst[k], v);
      else dst[k] = clone(v);
    });
    return dst;
  }
  function write(path, fn){ return new Promise(function(res){ setTimeout(function(){ fn(); fire(path); res(); }, 30); }); }
  function docRef(path){
    return { id: path.split('/').pop(), path: path,
      get: function(){ return Promise.resolve(snapOf(path)); },
      set: function(d){ return write(path, function(){ S.docs[path] = clone(d); }); },
      update: function(d){ return write(path, function(){ S.docs[path] = merge(S.docs[path] || {}, d); }); },
      delete: function(){ return write(path, function(){ delete S.docs[path]; }); },
      onSnapshot: function(cb){ (docSubs[path] = docSubs[path] || []).push(cb); setTimeout(function(){ cb(snapOf(path)); }, 10); return function(){}; }
    };
  }
  function query(coll, where, order, lim){
    var q = {coll: coll, where: where || [], order: order, lim: lim};
    return {
      where: function(f, op, v){ return query(coll, q.where.concat([[f, op, v]]), q.order, q.lim); },
      orderBy: function(f, dir){ return query(coll, q.where, [f, dir], q.lim); },
      limit: function(n){ return query(coll, q.where, q.order, n); },
      doc: function(id){ return docRef(coll + '/' + id); },
      get: function(){ return Promise.resolve(runQuery(q)); },
      onSnapshot: function(cb){ var s = {q: q, cb: cb}; qSubs.push(s); setTimeout(function(){ cb(runQuery(q)); }, 10); return function(){ s.dead = true; }; }
    };
  }
  var db = { doc: docRef, collection: function(c){ return query(c); } };
  var downloads = { save: function(o){ window.__lastDownload = o; return Promise.resolve({status: 'saved'}); } };
  window.claude = { use: function(name){
    if(name === 'db') return Promise.resolve(db);
    if(name === 'downloads') return Promise.resolve(downloads);
    return Promise.reject(new Error('unsupported'));
  } };
})();
