// nexus-rea — runtime inventory of a React app, one evaluate call, MAIN world, after the hook shim pre-load.
// Returns JSON: hook state (shim present, roots, commits), script/chunk URLs, the app's data-* vocabulary, localStorage keys,
// uppercase panel titles, short uppercase buttons (command bars), and the top prop-key SIGNATURES over the fiber tree —
// minified component names are useless, prop signatures are not. Bounded: at most `limit` fibers (default 6000).
// Usage: evaluate(`(${INVENTORY})({ limit: 6000, chunks: true })`) — or paste the body into the nexus-browser MCP `evaluate`
// tool (mainWorld:true on the sandbox backend; the default backend has one world).
(function (args) {
  args = args || {}; var limit = args.limit || 6000; var out = {};
  var h = window.__REACT_DEVTOOLS_GLOBAL_HOOK__;
  out.hook = { present: !!h, shim: !!(h && h.__nexusShim), renderers: h && h.renderers ? h.renderers.size : 0,
               roots: h && h._nexusRoots ? h._nexusRoots.size : 0, commits: h ? (h._nexusCommits || 0) : 0 };
  out.scripts = [].slice.call(document.scripts).map(function (s) { return s.src; }).filter(Boolean).slice(0, 40);
  if (args.chunks !== false && window.performance && performance.getEntriesByType) {
    out.chunks = performance.getEntriesByType('resource').map(function (e) { return e.name; })
      .filter(function (u) { return /\.(m?js)(\?|$)/.test(u); }).filter(function (v, i, a) { return a.indexOf(v) === i; }).slice(0, 200);
  }
  out.dataAttrs = {};
  var all = [].slice.call(document.querySelectorAll('*'));
  all.forEach(function (el) { for (var i = 0; i < el.attributes.length; i++) { var a = el.attributes[i].name; if (a.indexOf('data-') === 0) out.dataAttrs[a] = (out.dataAttrs[a] || 0) + 1; } });
  try { out.localStorageKeys = Object.keys(localStorage).slice(0, 60); } catch (e) { out.localStorageKeys = []; }
  out.panelTitles = all.filter(function (el) {
    var t = el.textContent && el.textContent.trim(); if (!t || el.children.length > 4 || t.length < 2 || t.length > 40) return false;
    if (!/^[A-Z][A-Z0-9 &/\-]{2,}$/.test(t)) return false; var cs = getComputedStyle(el); return parseInt(cs.fontWeight, 10) >= 500;
  }).map(function (el) { return el.textContent.trim(); }).filter(function (v, i, a) { return a.indexOf(v) === i; }).slice(0, 60);
  out.commandBar = [].slice.call(document.querySelectorAll('button')).map(function (b) { return (b.textContent || '').trim(); })
    .filter(function (t) { return /^[A-Z]{1,5}$/.test(t); }).filter(function (v, i, a) { return a.indexOf(v) === i; }).slice(0, 40);
  var sig = {}, n = 0;
  try {
    var roots = h && h._nexusRoots ? Array.from(h._nexusRoots) : [];
    if (!roots.length) { // fallback: any __reactContainer$ root on the DOM
      all.some(function (el) { for (var k in el) { if (k.indexOf('__reactContainer$') === 0 && el[k]) { roots.push({ current: el[k] }); return true; } } return false; });
    }
    var st = roots.map(function (r) { return r.current; }).filter(Boolean);
    while (st.length && n < limit) {
      var f = st.pop(); if (!f) continue; n++;
      if (typeof f.type === 'function' && f.memoizedProps) {
        var ks = Object.keys(f.memoizedProps).filter(function (k) { return k !== 'children'; }).sort().join(',');
        if (ks) sig[ks] = (sig[ks] || 0) + 1;
      }
      if (f.child) st.push(f.child); if (f.sibling) st.push(f.sibling);
    }
    out.fibersVisited = n;
    out.topPropSignatures = Object.keys(sig).map(function (k) { return [k, sig[k]]; }).sort(function (a, b) { return b[1] - a[1]; }).slice(0, args.top || 40);
  } catch (e) { out.fiberErr = String(e); }
  return JSON.stringify(out);
})
