#!/usr/bin/env python3
"""nexus-rea — the NO-MCP runtime path. Plain Playwright: pre-load the React DevTools hook shim, open the page, run the
runtime inventory in the page's main world, print JSON. Optional --selector runs the bippy-lite probe on one element.

  pip install playwright && python -m playwright install chromium        (or point --chromium at a local binary)
  python3 react-inventory.py https://react.dev --wait 4
  python3 react-inventory.py https://app.example.com --selector 'button[data-cy-command-toolbar]'

Read-only. Public pages only. The shim is the same bytes the nexus-browser MCP pre-loads; nothing here needs a server.
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
def read(name): return open(os.path.join(HERE, name), encoding="utf-8").read()
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("url"); ap.add_argument("--wait", type=float, default=3.0, help="seconds after load for hydration")
    ap.add_argument("--selector", help="run the bippy-lite probe on this CSS selector"); ap.add_argument("--limit", type=int, default=6000)
    ap.add_argument("--chromium", help="path to a chromium binary (else Playwright's)"); ap.add_argument("--headed", action="store_true")
    a = ap.parse_args()
    try: from playwright.sync_api import sync_playwright
    except ImportError: sys.exit("pip install playwright && python -m playwright install chromium")
    shim = read("react-hook-shim.js"); inv = read("react-inventory.js"); probe = read("bippy-lite.js")
    with sync_playwright() as p:
        kw = {"headless": not a.headed}
        if a.chromium: kw["executable_path"] = a.chromium
        b = p.chromium.launch(**kw); ctx = b.new_context(); ctx.add_init_script(shim)   # BEFORE any page script
        pg = ctx.new_page(); pg.goto(a.url, wait_until="load", timeout=60000); time.sleep(a.wait)
        out = json.loads(pg.evaluate("(" + inv.strip() + ")", {"limit": a.limit}))
        if a.selector:
            out["probe"] = pg.evaluate("(" + probe.strip() + ")", {"selector": a.selector})
        b.close()
    json.dump(out, sys.stdout, indent=2); print()
if __name__ == "__main__": main()
