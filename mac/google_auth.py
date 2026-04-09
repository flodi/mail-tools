#!/usr/bin/env python3
"""Get a Gmail OAuth refresh token. Run on your Mac.
Requires: pip install google-auth-oauthlib
Place your google_credentials.json in the same folder.
"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://mail.google.com/']
flow = InstalledAppFlow.from_client_secrets_file('google_credentials.json', scopes=SCOPES)
flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
print("\nOpen this URL in your browser:\n")
print(auth_url)
print("\nPaste the authorization code:")
code = input()
flow.fetch_token(code=code)
print("\nRefresh token (add to config.json):")
print(flow.credentials.refresh_token)
