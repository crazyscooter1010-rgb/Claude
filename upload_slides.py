"""
Uploads new_vsl_slides.pptx to Google Drive and converts it to Google Slides.

Setup (one-time):
  1. Go to console.cloud.google.com → APIs & Services → Credentials
  2. Create an OAuth 2.0 Client ID (Desktop app type)
  3. Download it as credentials.json and put it in this same folder
  4. Run:  python3 upload_slides.py
  5. A browser window will open for Google login — approve it
  6. The script prints the Google Slides URL when done
"""

import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive.file']
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE  = '/Users/Logan/Documents/google_credentials.json'
TOKEN_FILE  = os.path.join(SCRIPT_DIR, 'slides_upload_token.json')  # separate from existing token
PPTX_FILE   = os.path.join(SCRIPT_DIR, 'new_vsl_slides.pptx')


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
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

    return creds


def main():
    if not os.path.exists(PPTX_FILE):
        sys.exit(f'ERROR: pptx file not found at {PPTX_FILE}\nRun build_vsl_slides.py first.')

    print('Authenticating with Google...')
    creds   = get_credentials()
    service = build('drive', 'v3', credentials=creds)

    print('Uploading and converting to Google Slides...')
    media = MediaFileUpload(
        PPTX_FILE,
        mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
        resumable=True,
    )
    file = service.files().create(
        body={
            'name': 'New VSL Slides — Team LO',
            'mimeType': 'application/vnd.google-apps.presentation',
        },
        media_body=media,
        fields='id,webViewLink,name',
    ).execute()

    print(f"\nDone.")
    print(f"  Name : {file.get('name')}")
    print(f"  URL  : {file.get('webViewLink')}")
    print(f"  ID   : {file.get('id')}")


if __name__ == '__main__':
    main()
