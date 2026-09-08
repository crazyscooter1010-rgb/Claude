"""
Shared auth helper for full Google Docs + Drive read/write access.

Run with /usr/bin/python3 specifically, not whatever python3 resolves to on
PATH. On the MacBook, `python3` resolves to Homebrew's interpreter, which does
not have the google-api libraries installed. Apple's system /usr/bin/python3
does, on both this machine and the Mac Mini, so scripts using this module
should invoke that interpreter directly.

One-time setup: /usr/bin/python3 docs_drive_auth.py
Then import get_docs_service() / get_drive_service() from here.
"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]
CREDS_FILE = "/Users/Logan/Documents/google_credentials.json"
TOKEN_FILE = "/Users/Logan/Documents/google_docs_drive_token.json"


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


def get_docs_service():
    return build("docs", "v1", credentials=get_credentials())


def get_drive_service():
    return build("drive", "v3", credentials=get_credentials())
