#!/usr/bin/env python3
"""grok-build transport-capture proxy.

A trivial HTTP forward-proxy that logs the full request/response transport
(headers + JSON body) between the grok-build CLI and its upstream, then
forwards. grok connects over PLAIN HTTP to this proxy's base_url, so no TLS
cert / mitmproxy is needed.

Usage:
    PORT=8899 UPSTREAM=https://api.x.ai LOG=/tmp/grok-transport.jsonl \
        python3 grok-build-proxy.py

Then point grok at it by adding to ~/.grok/config.toml (BACK IT UP FIRST):
    [model.captured]
    base_url = "http://127.0.0.1:8899/v1"
    env_key  = "XAI_API_KEY"          # references env var -> no secret on disk
    model    = "grok-build-0.1"        # id sent to the API

and run:  grok -p "..." -m captured --always-approve

To route to a DIFFERENT (external) provider instead of api.x.ai, set UPSTREAM
(e.g. https://api.openai.com, http://localhost:11434) and the model/key to match.
"""
import http.server, socketserver, urllib.request, urllib.error, json, datetime, os

PORT = int(os.environ.get("PORT", "8899"))
UPSTREAM = os.environ.get("UPSTREAM", "https://api.x.ai").rstrip("/")
LOG = os.environ.get("LOG", "/tmp/grok-transport.jsonl")
HOP = {"host", "content-length", "connection", "transfer-encoding", "content-encoding"}


def _log(rec):
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _handle(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        req = {
            "ts": datetime.datetime.utcnow().isoformat(),
            "dir": "REQUEST",
            "method": self.command,
            "path": self.path,
            "headers": {k: v for k, v in self.headers.items()},
        }
        try:
            req["body"] = json.loads(body)
        except Exception:
            req["body"] = body.decode("utf-8", "replace")[:8000]
        _log(req)

        fwd_headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        r = urllib.request.Request(
            UPSTREAM + self.path,
            data=body or None,
            headers=fwd_headers,
            method=self.command,
        )
        try:
            with urllib.request.urlopen(r, timeout=180) as resp:
                data, status, rh = resp.read(), resp.status, dict(resp.getheaders())
        except urllib.error.HTTPError as e:
            data, status, rh = e.read(), e.code, dict(e.headers)
        except Exception as e:
            data = json.dumps({"proxy_error": str(e)}).encode()
            status, rh = 502, {"Content-Type": "application/json"}

        _log({
            "ts": datetime.datetime.utcnow().isoformat(),
            "dir": "RESPONSE",
            "status": status,
            "resp_headers": rh,
            "body_preview": data.decode("utf-8", "replace")[:4000],
        })

        self.send_response(status)
        for k, v in rh.items():
            if k.lower() not in HOP:
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_POST = _handle
    do_GET = _handle


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    open(LOG, "w").close()  # truncate on start
    with socketserver.TCPServer(("127.0.0.1", PORT), H) as s:
        print(f"grok-build-proxy on 127.0.0.1:{PORT} -> {UPSTREAM}  (log: {LOG})")
        s.serve_forever()
