#!/usr/bin/env python3
"""Get an Office 365 OAuth refresh token. Run on your Mac.
Requires: pip install msal
Edit CLIENT_ID, TENANT_ID before running.
Add http://localhost:8400 as redirect URI in Azure portal.
"""
import msal, json, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

CLIENT_ID = "YOUR_AZURE_CLIENT_ID"
TENANT_ID = "YOUR_TENANT_ID"
REDIRECT_URI = "http://localhost:8400"
SCOPES = ["https://outlook.office.com/IMAP.AccessAsUser.All"]

result_code = None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global result_code
        params = parse_qs(urlparse(self.path).query)
        if 'code' in params:
            result_code = params['code'][0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Done. Close this window.")
    def log_message(self, *args): pass

app = msal.PublicClientApplication(CLIENT_ID, authority=f"https://login.microsoftonline.com/{TENANT_ID}")
webbrowser.open(app.get_authorization_request_url(SCOPES, redirect_uri=REDIRECT_URI))
server = HTTPServer(('localhost', 8400), Handler)
while result_code is None:
    server.handle_request()
result = app.acquire_token_by_authorization_code(result_code, SCOPES, redirect_uri=REDIRECT_URI)
if 'refresh_token' in result:
    print("\nRefresh token (add to config.json):")
    print(result['refresh_token'])
else:
    print("Error:", result.get('error_description'))
