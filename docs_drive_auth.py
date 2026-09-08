"""
One-time OAuth bootstrap for full Google Docs + Drive read/write access.

This is what lets Claude actually edit the body of an existing Google Doc,
not just create new files or edit Sheets cells. Separate token from the
sheets-mcp one (that one is spreadsheets + drive.readonly, this one is
documents + full drive).

Setup:
  Run:  /usr/bin/python3 docs_drive_auth.py
  A browser window opens for Google login. Approve it.
  Token saves to ~/Documents/google_docs_drive_token.json
"""

from google_docs_drive import get_credentials, TOKEN_FILE

if __name__ == "__main__":
    creds = get_credentials()
    print("Token saved to", TOKEN_FILE)
    print("Scopes granted:", creds.scopes)
