"""Get a new Spotify refresh token and save it to .env.

Usage:
    python get_refresh_token.py [redirect_uri]

redirect_uri defaults to http://127.0.0.1:8888/callback and must be listed under
"Redirect URIs" in your app at https://developer.spotify.com/dashboard.
With a http://127.0.0.1 redirect the code is captured automatically; for any
other redirect you paste the URL you land on after approving.
"""
import base64
import http.server
import secrets
import sys
import urllib.parse
import webbrowser
from pathlib import Path

import requests
from dotenv import dotenv_values

ENV_PATH = Path(__file__).with_name(".env")
SCOPES = "playlist-modify-public playlist-modify-private user-modify-playback-state user-read-playback-state"


def capture_code_locally(redirect_uri):
    parsed = urllib.parse.urlparse(redirect_uri)
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" not in query and "error" not in query:
                self.send_response(404)
                self.end_headers()
                return
            result.update({k: v[0] for k, v in query.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Done - you can close this tab and return to the terminal.</h2>")

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer((parsed.hostname, parsed.port or 80), Handler)
    print(f"Waiting for Spotify to redirect to {redirect_uri} ...")
    while not result:
        server.handle_request()
    server.server_close()
    return result


def capture_code_by_paste():
    url = input("Paste the full URL your browser was redirected to: ").strip()
    return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(url).query).items()}


def save_refresh_token(token):
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    replaced = False
    for i, line in enumerate(lines):
        if line.strip().startswith("SPOTIFY_REFRESH_TOKEN="):
            lines[i] = f"SPOTIFY_REFRESH_TOKEN={token}"
            replaced = True
    if not replaced:
        lines.append(f"SPOTIFY_REFRESH_TOKEN={token}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    redirect_uri = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8888/callback"

    base64_token = dotenv_values(ENV_PATH).get("SPOTIFY_BASE64_TOKEN")
    if not base64_token:
        sys.exit("SPOTIFY_BASE64_TOKEN is missing from .env")
    client_id = base64.b64decode(base64_token).decode().split(":", 1)[0]

    state = secrets.token_urlsafe(16)
    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
        "show_dialog": "true",
    })

    print("Opening Spotify login in your browser. If it doesn't open, visit:\n" + auth_url + "\n")
    webbrowser.open(auth_url)

    host = urllib.parse.urlparse(redirect_uri).hostname
    params = capture_code_locally(redirect_uri) if host in ("127.0.0.1", "localhost") else capture_code_by_paste()

    if "error" in params:
        sys.exit(f"Spotify returned an error: {params['error']}")
    if params.get("state") != state:
        sys.exit("State mismatch - aborting (possible stale or forged redirect)")

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "authorization_code", "code": params["code"], "redirect_uri": redirect_uri},
        headers={"Authorization": f"Basic {base64_token}"},
    )
    data = response.json()
    if "refresh_token" not in data:
        sys.exit(f"Token exchange failed ({response.status_code}): {data}")

    save_refresh_token(data["refresh_token"])
    print("New refresh token saved to .env. You can now run main.py.")


if __name__ == "__main__":
    main()
