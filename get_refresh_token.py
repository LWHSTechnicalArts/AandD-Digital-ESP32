#!/usr/bin/env python3
"""
One-time helper: gets a Spotify refresh token for the Feather.
Run this on your COMPUTER, not on the Feather.

Works with either redirect URI registered in your Spotify app:
  - http://127.0.0.1:8888/callback  (fully automatic)

Uses only the Python standard library.
"""
import base64
import json
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

DEFAULT_REDIRECT = "http://127.0.0.1:8888/callback"
SCOPES = "user-read-currently-playing user-read-playback-state"


def wait_for_local_callback(port):
    """Runs a tiny local web server and waits for Spotify's redirect."""
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            result.update({k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Done! Go back to the terminal.</h2>")

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", port), Handler)
    while "code" not in result and "error" not in result:
        server.handle_request()
    server.server_close()
    return result


def ask_for_pasted_url():
    """For non-local redirect URIs: the user pastes the URL they land on."""
    print("After you approve, your browser will go to a page that may not load")
    print("(that's fine). Copy the FULL address from the address bar and paste it here.")
    pasted = input("\nPaste the address: ").strip()
    query = urllib.parse.urlparse(pasted).query
    return {k: v[0] for k, v in urllib.parse.parse_qs(query).items()}


def token_request(basic, fields):
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode(fields).encode(),
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def main():
    client_id = input("Spotify Client ID: ").strip()
    client_secret = input("Spotify Client Secret: ").strip()
    redirect_uri = input(
        f"Redirect URI exactly as it appears in your Spotify app\n"
        f"[press Enter for {DEFAULT_REDIRECT}]: "
    ).strip() or DEFAULT_REDIRECT

    state = secrets.token_urlsafe(16)
    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
    })

    print("\nOpening your browser. If it doesn't open, visit this URL:\n")
    print(auth_url + "\n")
    webbrowser.open(auth_url)

    parsed = urllib.parse.urlparse(redirect_uri)
    if parsed.hostname == "127.0.0.1":
        result = wait_for_local_callback(parsed.port or 80)
    else:
        result = ask_for_pasted_url()

    if "error" in result:
        sys.exit(f"Authorization failed: {result['error']}")
    if "code" not in result:
        sys.exit("No code found in that address - please try again.")
    if result.get("state") != state:
        sys.exit("State mismatch - make sure you pasted the address from THIS run.")

    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    # Swap the one-time code for tokens (the code expires quickly and works once)
    try:
        tokens = token_request(basic, {
            "grant_type": "authorization_code",
            "code": result["code"],
            "redirect_uri": redirect_uri,
        })
    except urllib.error.HTTPError as e:
        sys.exit(f"Token exchange failed: HTTP {e.code}\n{e.read().decode()}")

    refresh_token = tokens["refresh_token"]
    print(f"\nGot a refresh token ({len(refresh_token)} characters, "
          f"starts with {refresh_token[:4]}).")

    # Test it the same way the Feather will use it
    try:
        refreshed = token_request(basic, {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        })
        refresh_token = refreshed.get("refresh_token", refresh_token)
        print("Test refresh worked - this token is good.")
    except urllib.error.HTTPError as e:
        sys.exit(f"Test refresh FAILED: HTTP {e.code}\n{e.read().decode()}")

    with open("spotify_settings.txt", "w") as f:
        f.write(
            f'SPOTIFY_CLIENT_ID = "{client_id}"\n'
            f'SPOTIFY_CLIENT_SECRET = "{client_secret}"\n'
            f'SPOTIFY_REFRESH_TOKEN = "{refresh_token}"\n'
        )
    print("\nSaved to spotify_settings.txt. Copy those three lines into")
    print("settings.toml on CIRCUITPY, replacing the old SPOTIFY_ lines.")


if __name__ == "__main__":
    main()
