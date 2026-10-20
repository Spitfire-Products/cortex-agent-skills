// nexus-rea — bippy-lite: a one-shot fiber probe. Call as (function)(args) in the page's MAIN world AFTER the hook shim.
// args: { selector } (CSS) or { x, y } (viewport point). Returns { available, componentName, componentStack, props,
// sourceLocation, nextjsResolved } or { available:false, error }. Resolves the fiber through the DevTools hook's renderer
// (findFiberByHostInstance) first, then DOM __reactFiber$ keys. Named after bippy (aidenybai), the full fiber library
// Nexus Terminal uses in-app; this is an independent, dependency-free probe. Source of truth:
// nexus-terminal/modules/nexus-sense/tools/injectable/bippy-lite.injectable.ts (same bytes).
(function(args) {
  try {
    var hook = window.__REACT_DEVTOOLS_GLOBAL_HOOK__;

    // Stack/fiber cache (WeakMap keyed on DOM element — from react-grab pattern)
    // Avoids redundant fiber lookups when same element is inspected multiple times
    if (!window.__nexusFiberCache) {
      window.__nexusFiberCache = typeof WeakMap !== 'undefined' ? new WeakMap() : null;
    }
    var fiberCache = window.__nexusFiberCache;

    // Check if React is present
    if (!hook || !hook.renderers || hook.renderers.size === 0) {
      return {
        available: false,
        error: 'No React detected (no __REACT_DEVTOOLS_GLOBAL_HOOK__ or no renderers)'
      };
    }

    // Get the first renderer
    var renderer = null;
    var rendererIterator = hook.renderers.values();
    var first = rendererIterator.next();
    if (!first.done) {
      renderer = first.value;
    }

    if (!renderer) {
      return {
        available: false,
        error: 'React hook exists but no renderer found'
      };
    }

    // If no selector, return availability info
    if (!args || !args.selector) {
      return {
        available: true,
        rendererCount: hook.renderers.size,
        reactVersion: renderer.version || null
      };
    }

    // Find the target element
    var element = document.querySelector(args.selector);
    if (!element) {
      return {
        available: true,
        error: 'Element not found for selector: ' + args.selector
      };
    }

    // Get fiber from element (with cache)
    var fiber = null;

    // Check cache first (WeakMap keyed on DOM element)
    if (fiberCache && fiberCache.has(element)) {
      fiber = fiberCache.get(element);
    }

    // Method 1: Use renderer's findFiberByHostInstance
    if (!fiber && renderer.findFiberByHostInstance) {
      fiber = renderer.findFiberByHostInstance(element);
    }

    // Method 2: Check __reactFiber$ or __reactInternalInstance$ keys on the element
    if (!fiber) {
      var keys = Object.keys(element);
      for (var i = 0; i < keys.length; i++) {
        if (keys[i].startsWith('__reactFiber$') || keys[i].startsWith('__reactInternalInstance$')) {
          fiber = element[keys[i]];
          break;
        }
      }
    }

    // Cache the fiber lookup result
    if (fiber && fiberCache) {
      fiberCache.set(element, fiber);
    }

    if (!fiber) {
      return {
        available: true,
        error: 'Could not find React fiber for element: ' + args.selector
      };
    }

    // Helper: get display name from fiber
    function getDisplayName(fiberNode) {
      if (!fiberNode || !fiberNode.type) return null;
      var type = fiberNode.type;
      if (typeof type === 'string') return type; // DOM element like 'div'
      if (type.displayName) return type.displayName;
      if (type.name) return type.name;
      // ForwardRef, memo wrappers
      if (type.render) {
        return type.render.displayName || type.render.name || null;
      }
      return null;
    }

    // Helper: check if name should be filtered out
    // Comprehensive filter lists from react-grab research
    var NON_COMPONENT_PREFIXES = ['motion.', 'styled.', 'chakra.', 'ark.', 'Primitive.', 'Slot.'];
    var NEXT_INTERNALS = [
      'InnerLayoutRouter', 'OuterLayoutRouter', 'RenderFromTemplateContext',
      'ScrollAndFocusHandler', 'InnerScrollAndFocusHandler',
      'ErrorBoundary', 'LoadingBoundary', 'NotFoundBoundary',
      'RedirectBoundary', 'MetadataBoundary', 'ViewportBoundary',
      'HTTPAccessFallbackBoundary', 'HotReload', 'Router', 'AppRouter',
      'ServerRoot', 'RSCComponent', 'ClientPageRoot', 'ClientSegmentRoot',
      'LayoutSegment', 'RootLayout', 'ClientSegment', 'Loading',
      'NotFound', 'Error', 'GlobalError', 'Template',
      'ServerInsertedHTMLProvider', 'BuildHTTPHeaders', 'PreloadCss', 'FlightData'
    ];
    var REACT_INTERNALS = [
      'Provider', 'Consumer', 'Context', 'Fragment', 'Suspense',
      'StrictMode', 'Profiler', 'SuspenseList',
      'OffscreenComponent', 'LegacyHiddenComponent'
    ];
    function shouldFilterName(name) {
      if (!name) return true;
      if (name.charAt(0) === '_' || name.charAt(0) === '$') return true;
      // Check non-component prefixes (e.g. motion.div, styled.button)
      for (var p = 0; p < NON_COMPONENT_PREFIXES.length; p++) {
        if (name.indexOf(NON_COMPONENT_PREFIXES[p]) === 0) return true;
      }
      // Check Next.js internals (exact match)
      for (var n = 0; n < NEXT_INTERNALS.length; n++) {
        if (name === NEXT_INTERNALS[n]) return true;
      }
      // Check React internals (substring match for wrappers like ForwardRef(...))
      var reactFilterPatterns = REACT_INTERNALS.concat(['ForwardRef(', 'Memo(']);
      for (var k = 0; k < reactFilterPatterns.length; k++) {
        if (name.indexOf(reactFilterPatterns[k]) !== -1) return true;
      }
      // Skip lowercase names (DOM elements like div, span)
      if (name.charAt(0) === name.charAt(0).toLowerCase() && name.charAt(0) !== name.charAt(0).toUpperCase()) {
        return true;
      }
      return false;
    }

    // Get component name from nearest non-host fiber
    var componentName = null;
    var inspectFiber = fiber;
    while (inspectFiber) {
      var name = getDisplayName(inspectFiber);
      if (name && !shouldFilterName(name)) {
        componentName = name;
        break;
      }
      inspectFiber = inspectFiber.return;
    }

    // Build component stack (walk up fiber.return)
    var componentStack = [];
    var current = fiber;
    var maxDepth = 15;
    while (current && componentStack.length < maxDepth) {
      var stackName = getDisplayName(current);
      if (stackName && !shouldFilterName(stackName)) {
        componentStack.push(stackName);
      }
      current = current.return;
    }

    // Extract props (shallow, serializable only)
    var props = null;
    if (fiber.memoizedProps) {
      props = {};
      var propKeys = Object.keys(fiber.memoizedProps);
      for (var j = 0; j < propKeys.length; j++) {
        var propKey = propKeys[j];
        if (propKey === 'children') continue; // Skip children (too verbose)
        var val = fiber.memoizedProps[propKey];
        var valType = typeof val;
        if (valType === 'string' || valType === 'number' || valType === 'boolean' || val === null) {
          props[propKey] = val;
        } else if (valType === 'function') {
          props[propKey] = '[function]';
        } else if (Array.isArray(val)) {
          props[propKey] = '[array(' + val.length + ')]';
        } else if (valType === 'object') {
          props[propKey] = '[object]';
        }
      }
    }

    // Try to find source location (if available via _debugSource or _debugOwner)
    var sourceLocation = null;
    var sourceFiber = fiber;
    while (sourceFiber) {
      if (sourceFiber._debugSource) {
        var src = sourceFiber._debugSource;
        sourceLocation = {
          fileName: src.fileName || null,
          lineNumber: src.lineNumber || null,
          columnNumber: src.columnNumber || null
        };
        break;
      }
      // Also check _debugOwner chain (React 19+)
      if (sourceFiber._debugOwner && sourceFiber._debugOwner._debugSource) {
        var ownerSrc = sourceFiber._debugOwner._debugSource;
        sourceLocation = {
          fileName: ownerSrc.fileName || null,
          lineNumber: ownerSrc.lineNumber || null,
          columnNumber: ownerSrc.columnNumber || null
        };
        break;
      }
      sourceFiber = sourceFiber.return;
    }

    // Next.js server component symbolication — resolve minified source locations
    // via the __nextjs_original-stack-frames endpoint (available in Next.js dev mode)
    var nextjsResolved = false;
    if (sourceLocation && sourceLocation.fileName && window.__NEXT_DATA__) {
      try {
        // Check if filename looks minified (no path separators or very short)
        var fn = sourceLocation.fileName;
        if (fn && (fn.indexOf('/') === -1 || fn.length < 10)) {
          // Attempt synchronous XHR for symbolication (blocking but fast in dev)
          var xhr = new XMLHttpRequest();
          var params = 'file=' + encodeURIComponent(fn) +
            '&lineNumber=' + (sourceLocation.lineNumber || 0) +
            '&column=' + (sourceLocation.columnNumber || 0);
          xhr.open('GET', '/__nextjs_original-stack-frames?' + params, false);
          xhr.send();
          if (xhr.status === 200) {
            var resolved = JSON.parse(xhr.responseText);
            if (resolved && resolved.originalStackFrame) {
              sourceLocation = {
                fileName: resolved.originalStackFrame.file || sourceLocation.fileName,
                lineNumber: resolved.originalStackFrame.lineNumber || sourceLocation.lineNumber,
                columnNumber: resolved.originalStackFrame.column || sourceLocation.columnNumber
              };
              nextjsResolved = true;
            }
          }
        }
      } catch (e) { /* symbolication is best-effort */ }
    }

    return {
      available: true,
      componentName: componentName,
      componentStack: componentStack.length > 0 ? componentStack : undefined,
      props: props,
      sourceLocation: sourceLocation,
      nextjsResolved: nextjsResolved || undefined
    };
  } catch (err) {
    return {
      available: false,
      error: err instanceof Error ? err.message : String(err)
    };
  }
})
