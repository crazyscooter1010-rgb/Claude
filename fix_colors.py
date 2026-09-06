"""
fix_colors.py — flips the new presentation to white background / black text
to match the example presentation style.
"""

import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES     = ['https://www.googleapis.com/auth/presentations']
CREDS_FILE = '/Users/Logan/Documents/google_credentials.json'
TOKEN_FILE = '/Users/Logan/Documents/Claude Code/fullyscale-workspace/slides_format_token.json'
NEW_ID     = '1MVGX108Wowh469Fqmfq7u22PgzpudjaQnYW1k5ljLxY'

BLACK = {'red': 0.0, 'green': 0.0, 'blue': 0.0}
WHITE = {'red': 1.0, 'green': 1.0, 'blue': 1.0}


def get_creds():
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
    service = build('slides', 'v1', credentials=get_creds())
    prs = service.presentations().get(presentationId=NEW_ID).execute()

    requests = []

    for slide in prs['slides']:
        slide_id = slide['objectId']

        # 1. White slide background
        requests.append({
            'updatePageProperties': {
                'objectId': slide_id,
                'pageProperties': {
                    'pageBackgroundFill': {
                        'solidFill': {'color': {'rgbColor': WHITE}}
                    }
                },
                'fields': 'pageBackgroundFill'
            }
        })

        for elem in slide.get('pageElements', []):
            shape = elem.get('shape', {})
            if not shape.get('text', {}).get('textElements'):
                continue

            elem_id = elem['objectId']

            # 2. Black text on all text boxes
            requests.append({
                'updateTextStyle': {
                    'objectId': elem_id,
                    'textRange': {'type': 'ALL'},
                    'style': {
                        'foregroundColor': {'opaqueColor': {'rgbColor': BLACK}}
                    },
                    'fields': 'foregroundColor'
                }
            })

            # 3. Remove any explicit shape background fill so it's transparent
            requests.append({
                'updateShapeProperties': {
                    'objectId': elem_id,
                    'shapeProperties': {
                        'shapeBackgroundFill': {'propertyState': 'NOT_RENDERED'}
                    },
                    'fields': 'shapeBackgroundFill'
                }
            })

    print(f'Sending {len(requests)} requests...')
    CHUNK = 200
    for i in range(0, len(requests), CHUNK):
        service.presentations().batchUpdate(
            presentationId=NEW_ID,
            body={'requests': requests[i:i+CHUNK]}
        ).execute()
        print(f'  {i+1}–{min(i+CHUNK, len(requests))} done')

    print('\nDone: https://docs.google.com/presentation/d/' + NEW_ID + '/edit')


if __name__ == '__main__':
    main()
