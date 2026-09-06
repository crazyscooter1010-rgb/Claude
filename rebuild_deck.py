"""
rebuild_deck.py

Wipes the new presentation and rebuilds it to match the EXAMPLE deck exactly:
  - white background, black Inter text, centered
  - short distilled on-screen phrases that COMPLEMENT the new script (not duplicate it)
  - same slide-type system: big statements, punch slides, header+progressive bullets, step slides
No em dashes anywhere.
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

WHITE = {'red': 1.0, 'green': 1.0, 'blue': 1.0}
BLACK = {'red': 0.0, 'green': 0.0, 'blue': 0.0}
FONT  = 'Inter'

W = 12192000
H = 6858000
MX = 457200                      # 0.5in side margin
CW = W - 2 * MX                  # content width


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


# ── Deck content ───────────────────────────────────────────────────────────────
# type: 'big'   -> one big centered statement (55pt bold)
#       'punch' -> medium centered statement, vertically centered (32pt regular)
#       'head'  -> section header near top (30pt bold), optional bullets below (32pt)
#       'step'  -> "Step N" big left label (55pt bold) + left body (32pt)

DECK = [
    # ---- HOOK ----
    {'type': 'big',   'title': 'Most of your production is tied to a small group of realtors'},
    {'type': 'punch', 'title': 'That creates two problems'},
    {'type': 'head',  'title': 'Two Problems',
     'bullets': ['Newer LOs don’t have enough referral partners yet']},
    {'type': 'head',  'title': 'Two Problems',
     'bullets': ['Newer LOs don’t have enough referral partners yet',
                 'One agent slows down and even a top LO’s pipeline drops']},
    {'type': 'punch', 'title': 'Top teams build a buyer pipeline they actually control'},

    # ---- PROBLEM / PAIN ----
    {'type': 'head',  'title': 'The Problem…'},
    {'type': 'head',  'title': 'The Problem…',
     'bullets': ['You just try to buy more leads',
                 'Zillow / Realtor.com / Webinar funnels']},
    {'type': 'head',  'title': 'The Problem…',
     'bullets': ['You just try to buy more leads',
                 'Zillow / Realtor.com / Webinar funnels',
                 'A few good leads buried under a pile of junk',
                 'No system to route them to the right LO']},
    {'type': 'punch', 'title': 'More leads by itself fixes nothing'},
    {'type': 'head',  'title': 'What You Actually Need',
     'bullets': ['Real buyers who can purchase in the next 3 to 12 months',
                 'Routed to the right person on your team']},

    # ---- BIG PROMISE ----
    {'type': 'punch', 'title': 'How we fix this…'},
    {'type': 'punch', 'title': 'A Meta Ads + CRM system that runs like it’s in-house'},
    {'type': 'head',  'title': 'What It Does',
     'bullets': ['Bring in exclusive first-time homebuyer leads',
                 'Score every lead so you know who to call first',
                 'Route each buyer to the right LO',
                 'Turn buyers into stronger agent relationships']},

    # ---- WHO THIS IS FOR ----
    {'type': 'head',  'title': 'Who This Is For'},
    {'type': 'head',  'title': 'Who This Is For',
     'bullets': ['Licensed LOs leading a team of loan officers']},
    {'type': 'head',  'title': 'Who This Is For',
     'bullets': ['Licensed LOs leading a team of loan officers',
                 'Can invest $3K–$6K/month in ad spend, on top of the retainer']},
    {'type': 'head',  'title': 'Who This Is For',
     'bullets': ['Licensed LOs leading a team of loan officers',
                 'Can invest $3K–$6K/month in ad spend, on top of the retainer',
                 'Will run a real, daily follow-up process']},
    {'type': 'punch', 'title': 'Who this is NOT for'},
    {'type': 'head',  'title': 'Who This Is NOT For',
     'bullets': ['Solo LOs with no team',
                 '“Teams” of only processors or assistants',
                 'LOs who are maxed out or won’t call online leads']},

    # ---- MECHANISM ----
    {'type': 'step',  'title': 'Step 1',
     'bullets': ['High-Volume Andromeda Campaign',
                 '50 to 100 angles, hooks, and creatives',
                 'Calling out specific neighborhoods and buyer situations',
                 'All from your own ad account']},
    {'type': 'step',  'title': 'Step 2'},
    {'type': 'step',  'title': 'Step 2',
     'bullets': ['Lead Scoring',
                 'Every lead scored green, yellow, or red',
                 'Based on credit, income, and buying timeline',
                 'Your best people work the green leads first']},
    {'type': 'step',  'title': 'Step 3',
     'bullets': ['Win and Deepen Agent Relationships',
                 'More referrals from agents you already work with',
                 'A prospecting tool to lock in new agent partners']},
    {'type': 'punch', 'title': 'Stop begging agents for business. Start bringing them buyers.'},

    # ---- PROOF + ECONOMICS + CTA ----
    {'type': 'punch', 'title': 'Running right now in Dallas, San Diego, and Phoenix'},
    {'type': 'big',   'title': 'One or two new agent partners can pay for the whole system for a year'},
    {'type': 'head',  'title': 'The Simple Math',
     'bullets': ['Can’t see 1 to 2 extra purchase deals a month?',
                 'Then it’s probably not a fit',
                 '(That is after ad spend and our fee)']},
    {'type': 'head',  'title': 'Next Steps'},
    {'type': 'head',  'title': 'Next Steps',
     'bullets': ['Click the button around this video',
                 'Answer a few quick questions about your team',
                 'Pick a time on the calendar']},
    {'type': 'big',   'title': 'A buyer pipeline you actually control'},
]


def text_box(slide_id, box_id, text, x, y, w, h, size, bold, align, valign,
             line_spacing=100, space_below=0):
    reqs = [
        {'createShape': {
            'objectId': box_id, 'shapeType': 'TEXT_BOX',
            'elementProperties': {
                'pageObjectId': slide_id,
                'size': {'width': {'magnitude': w, 'unit': 'EMU'},
                         'height': {'magnitude': h, 'unit': 'EMU'}},
                'transform': {'scaleX': 1, 'scaleY': 1,
                              'translateX': x, 'translateY': y, 'unit': 'EMU'}}}},
        {'insertText': {'objectId': box_id, 'text': text, 'insertionIndex': 0}},
        {'updateTextStyle': {
            'objectId': box_id, 'textRange': {'type': 'ALL'},
            'style': {'fontFamily': FONT, 'bold': bold,
                      'fontSize': {'magnitude': size, 'unit': 'PT'},
                      'foregroundColor': {'opaqueColor': {'rgbColor': BLACK}}},
            'fields': 'fontFamily,bold,fontSize,foregroundColor'}},
        {'updateParagraphStyle': {
            'objectId': box_id, 'textRange': {'type': 'ALL'},
            'style': {'alignment': align,
                      'lineSpacing': line_spacing,
                      'spaceBelow': {'magnitude': space_below, 'unit': 'PT'}},
            'fields': 'alignment,lineSpacing,spaceBelow'}},
        {'updateShapeProperties': {
            'objectId': box_id,
            'shapeProperties': {'contentAlignment': valign},
            'fields': 'contentAlignment'}},
    ]
    return reqs


def build_slide(i, spec):
    n = f'{i:02d}'
    slide_id = f'slide_{n}'
    reqs = [
        {'createSlide': {'objectId': slide_id, 'insertionIndex': i,
                         'slideLayoutReference': {'predefinedLayout': 'BLANK'}}},
        {'updatePageProperties': {
            'objectId': slide_id,
            'pageProperties': {'pageBackgroundFill': {'solidFill': {'color': {'rgbColor': WHITE}}}},
            'fields': 'pageBackgroundFill'}},
    ]

    t = spec['type']
    title = spec['title']
    bullets = spec.get('bullets')

    if t == 'big':
        reqs += text_box(slide_id, f'box_{n}_t', title, MX, 0, CW, H,
                         size=48, bold=True, align='CENTER', valign='MIDDLE',
                         line_spacing=110)

    elif t == 'punch':
        reqs += text_box(slide_id, f'box_{n}_t', title, MX, 0, CW, H,
                         size=32, bold=False, align='CENTER', valign='MIDDLE',
                         line_spacing=115)

    elif t == 'head':
        # header near top
        reqs += text_box(slide_id, f'box_{n}_h', title, MX, 313716, CW, 900000,
                         size=30, bold=True, align='CENTER', valign='TOP')
        if bullets:
            body = '\n'.join(bullets)
            reqs += text_box(slide_id, f'box_{n}_b', body, MX, 1801875, CW,
                             H - 1801875 - 457200,
                             size=30, bold=False, align='CENTER', valign='TOP',
                             line_spacing=150, space_below=10)

    elif t == 'step':
        reqs += text_box(slide_id, f'box_{n}_h', title, MX, 491625, CW, 900000,
                         size=54, bold=True, align='START', valign='TOP')
        if bullets:
            body = '\n'.join(bullets)
            reqs += text_box(slide_id, f'box_{n}_b', body, MX, 1801875, CW,
                             H - 1801875 - 457200,
                             size=30, bold=False, align='START', valign='TOP',
                             line_spacing=150, space_below=10)

    return reqs


def main():
    service = build('slides', 'v1', credentials=get_creds())

    # 1. Delete all existing slides
    prs = service.presentations().get(presentationId=NEW_ID).execute()
    del_reqs = [{'deleteObject': {'objectId': s['objectId']}} for s in prs.get('slides', [])]
    if del_reqs:
        service.presentations().batchUpdate(
            presentationId=NEW_ID, body={'requests': del_reqs}).execute()
        print(f'Deleted {len(del_reqs)} old slides.')

    # 2. Build new slides
    all_reqs = []
    for i, spec in enumerate(DECK):
        all_reqs += build_slide(i, spec)

    CHUNK = 250
    for j in range(0, len(all_reqs), CHUNK):
        service.presentations().batchUpdate(
            presentationId=NEW_ID, body={'requests': all_reqs[j:j+CHUNK]}).execute()
        print(f'  applied {j+1}-{min(j+CHUNK, len(all_reqs))}')

    print(f'\nBuilt {len(DECK)} slides.')
    print(f'https://docs.google.com/presentation/d/{NEW_ID}/edit')


if __name__ == '__main__':
    main()
