import json
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
from pathlib import Path

import requests

log = logging.getLogger("fordlogger")


class _CallbackHandler(BaseHTTPRequestHandler):
    auth_code = None

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            _CallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Autorisierung erfolgreich! Fenster schliessen.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Fehler: {self.path}".encode())

    def log_message(self, *a):
        pass


def _token_path(cfg: dict) -> Path:
    return Path(cfg.get("token_file", "tokens.json"))


def load_tokens(cfg: dict) -> dict:
    p = _token_path(cfg)
    if p.exists():
        return json.loads(p.read_text())
    return {}


def save_tokens(cfg: dict, tokens: dict):
    _token_path(cfg).write_text(json.dumps(tokens, indent=2))


def do_auth_flow(cfg: dict):
    params = urlencode({
        "client_id": cfg["client_id"],
        "response_type": "code",
        "redirect_uri": cfg["redirect_uri"],
        "scope": "openid offline_access",
        "state": "fordlogger",
    })
    login_url = cfg["auth_url"] + "?" + params

    print("\n" + "=" * 60)
    print("Bitte diese URL im Browser oeffnen:\n")
    print(login_url)
    print("=" * 60 + "\n")

    _CallbackHandler.auth_code = None
    server = HTTPServer(("localhost", 8080), _CallbackHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log.info("Warte auf Callback (max. 120s) ...")

    for _ in range(240):
        if _CallbackHandler.auth_code:
            break
        time.sleep(0.5)
    else:
        server.shutdown()
        raise TimeoutError("Kein Auth-Code erhalten")

    server.shutdown()
    code = _CallbackHandler.auth_code
    log.info("Auth-Code erhalten: %s...", code[:10])

    scope = f"{cfg['client_id']} offline_access openid"
    resp = requests.post(cfg["token_url"], data={
        "grant_type": "authorization_code",
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "redirect_uri": cfg["redirect_uri"],
        "code": code,
        "scope": scope,
    })
    resp.raise_for_status()
    tokens = resp.json()
    tokens["obtained_at"] = time.time()
    save_tokens(cfg, tokens)
    log.info("Tokens gespeichert in %s", _token_path(cfg))


def refresh_access_token(cfg: dict, tokens: dict) -> dict:
    log.info("Refreshing access token ...")
    scope = f"{cfg['client_id']} offline_access openid"
    resp = requests.post(cfg["token_url"], data={
        "grant_type": "refresh_token",
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "refresh_token": tokens["refresh_token"],
        "redirect_uri": cfg["redirect_uri"],
        "scope": scope,
    })
    resp.raise_for_status()
    t = resp.json()
    t["obtained_at"] = time.time()
    save_tokens(cfg, t)
    log.info("Token refreshed, laeuft in %ss ab", t.get("expires_in", "?"))
    return t


def get_valid_token(cfg: dict) -> str:
    tokens = load_tokens(cfg)
    if not tokens:
        raise RuntimeError("Keine Tokens – zuerst: python -m fordlogger --auth")
    needs_refresh = (
        "access_token" not in tokens
        or time.time() > tokens.get("obtained_at", 0) + tokens.get("expires_in", 3600) - 60
    )
    if needs_refresh:
        tokens = refresh_access_token(cfg, tokens)
    return tokens["access_token"]
