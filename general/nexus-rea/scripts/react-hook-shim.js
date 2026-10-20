// nexus-rea — React DevTools hook SHIM. Load BEFORE the page's scripts (Playwright add_init_script /
// puppeteer evaluateOnNewDocument / a CDP Page.addScriptToEvaluateOnNewDocument). React 16-19 registers its renderer
// through window.__REACT_DEVTOOLS_GLOBAL_HOOK__ and reports every commit; the shim records renderers (Map), every
// committed FiberRoot (hook._nexusRoots, a Set) and a commit counter (hook._nexusCommits). A real DevTools hook wins.
// Source of truth: nexus-terminal/modules/nexus-sense/tools/injectable/react-hook-shim.injectable.ts (same bytes).
(function () {
  try {
    if (typeof window === 'undefined') return;
    if (window.__REACT_DEVTOOLS_GLOBAL_HOOK__) return; // real DevTools (or an earlier shim) wins
    var renderers = new Map();
    var roots = new Set();
    var listeners = {};
    var nextId = 0;
    function emit(event, data) {
      var fns = listeners[event];
      if (!fns) return;
      for (var i = 0; i < fns.length; i++) { try { fns[i](data); } catch (e) {} }
    }
    var hook = {
      __nexusShim: true,
      isDisabled: false,
      supportsFiber: true,
      supportsFlight: false,
      renderers: renderers,
      _nexusRoots: roots,
      _nexusCommits: 0,
      _nexusLastCommitAt: 0,
      inject: function (renderer) {
        var id = ++nextId;
        renderers.set(id, renderer);
        emit('renderer', { id: id, renderer: renderer });
        return id;
      },
      on: function (event, fn) { (listeners[event] = listeners[event] || []).push(fn); },
      off: function (event, fn) {
        var fns = listeners[event]; if (!fns) return;
        var i = fns.indexOf(fn); if (i >= 0) fns.splice(i, 1);
      },
      sub: function (event, fn) { hook.on(event, fn); return function () { hook.off(event, fn); }; },
      emit: emit,
      onCommitFiberRoot: function (rendererId, root) {
        if (root) roots.add(root);
        hook._nexusCommits++;
        hook._nexusLastCommitAt = Date.now();
        emit('commit', { rendererId: rendererId, root: root });
      },
      onPostCommitFiberRoot: function () {},
      onCommitFiberUnmount: function () {},
      onScheduleFiberRoot: function () {},
      setStrictMode: function () {},
      checkDCE: function () {},
      registerInternalModuleStart: function () {},
      registerInternalModuleStop: function () {},
      getFiberRoots: function () { return roots; }
    };
    Object.defineProperty(window, '__REACT_DEVTOOLS_GLOBAL_HOOK__', {
      value: hook, configurable: true, enumerable: false, writable: true
    });
  } catch (e) { /* never break the page */ }
})();
