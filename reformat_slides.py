"""
reformat_slides.py

1. Reads the example VSL presentation to extract exact formatting
   (background color, font family, font sizes, text colors, slide size).
2. Applies that formatting to the new VSL presentation:
   - Deletes the pptx background rectangles
   - Sets proper slide background via updatePageProperties
   - Applies exact font/color/size to all text elements
"""

import os, json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES     = ['https://www.googleapis.com/auth/presentations']
CREDS_FILE = '/Users/Logan/Documents/google_credentials.json'
TOKEN_FILE = '/Users/Logan/Documents/Claude Code/fullyscale-workspace/slides_format_token.json'

EXAMPLE_ID = '1FGEQJlYaklLZ9IlfKwHAqhewtrlUIEuRUaYlujYGFHQ'
NEW_ID     = '1MVGX108Wowh469Fqmfq7u22PgzpudjaQnYW1k5ljLxY'

EMU_PER_PT = 12700


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


def rgb_to_dict(r255, g255, b255):
    return {'red': r255/255, 'green': g255/255, 'blue': b255/255}


def extract_example_format(prs):
    """Pull background fill, font family, and text color/size from example slides."""
    fmt = {
        'bg': None,
        'fonts': [],           # (fontFamily, sizePt, rgbColor, bold, content_preview)
        'slide_w': prs['pageSize']['width']['magnitude'],
        'slide_h': prs['pageSize']['height']['magnitude'],
    }

    for slide in prs['slides'][:8]:   # sample first 8 slides
        # --- Background ---
        pp = slide.get('pageProperties', {})
        bg_fill = pp.get('pageBackgroundFill', {})
        if fmt['bg'] is None and 'solidFill' in bg_fill:
            c = bg_fill['solidFill'].get('color', {})
            if 'rgbColor' in c:
                fmt['bg'] = c['rgbColor']

        # --- Text styles ---
        for elem in slide.get('pageElements', []):
            shape = elem.get('shape', {})
            for te in shape.get('text', {}).get('textElements', []):
                run = te.get('textRun', {})
                content = run.get('content', '').strip()
                style   = run.get('style', {})
                font    = style.get('fontFamily')
                size_d  = style.get('fontSize', {})
                size    = size_d.get('magnitude')
                unit    = size_d.get('unit', 'PT')
                fc      = style.get('foregroundColor', {})
                rgb     = fc.get('opaqueColor', {}).get('rgbColor')
                bold    = style.get('bold', False)
                if font and size and content:
                    fmt['fonts'].append((font, size, unit, rgb, bold, content[:40]))

    return fmt


def make_solid_bg(rgb_dict):
    return {
        'solidFill': {
            'color': {'rgbColor': rgb_dict}
        }
    }


def main():
    print('Authenticating...')
    service = build('slides', 'v1', credentials=get_creds())

    # ── Step 1: Read example presentation ────────────────────────────────────
    print('Reading example presentation...')
    example = service.presentations().get(presentationId=EXAMPLE_ID).execute()
    fmt = extract_example_format(example)

    print(f"\nExample slide size: {fmt['slide_w']} × {fmt['slide_h']} EMU "
          f"({fmt['slide_w']/EMU_PER_PT:.0f} × {fmt['slide_h']/EMU_PER_PT:.0f} pt)")
    print(f"Background color:   {fmt['bg']}")
    if fmt['fonts']:
        print("Fonts found:")
        seen = set()
        for f in fmt['fonts']:
            key = (f[0], round(f[1]), f[4])
            if key not in seen:
                seen.add(key)
                print(f"  font={f[0]}  size={f[1]}{f[2]}  bold={f[4]}  color={f[3]}  sample='{f[5]}'")

    # Determine background to use
    bg_color = fmt['bg'] if fmt['bg'] else {'red': 0.051, 'green': 0.051, 'blue': 0.051}

    # Determine dominant font (most common font family in example)
    from collections import Counter
    font_counts = Counter(f[0] for f in fmt['fonts'] if f[0])
    dominant_font = font_counts.most_common(1)[0][0] if font_counts else 'Lato'
    print(f"\nDominant font: {dominant_font}")

    # Build title/body color from example text styles
    # Largest text = title color, smaller = body color
    title_rgb = {'red': 1, 'green': 1, 'blue': 1}   # white fallback
    body_rgb  = {'red': 0.8, 'green': 0.8, 'blue': 0.8}  # grey fallback
    amber_rgb = {'red': 1.0, 'green': 0.757, 'blue': 0.027}  # #FFC107

    # Use actual colors from example if found
    color_by_size = [(f[1], f[3]) for f in fmt['fonts'] if f[3]]
    color_by_size.sort(key=lambda x: -x[0])
    if color_by_size:
        title_rgb = color_by_size[0][1]   # largest text color
    if len(color_by_size) > 1:
        body_rgb  = color_by_size[-1][1]  # smallest text color

    print(f"Title color: {title_rgb}")
    print(f"Body color:  {body_rgb}")

    # ── Step 2: Read new presentation ────────────────────────────────────────
    print('\nReading new presentation...')
    new_prs = service.presentations().get(presentationId=NEW_ID).execute()

    new_w = new_prs['pageSize']['width']['magnitude']
    new_h = new_prs['pageSize']['height']['magnitude']
    print(f"New slide size: {new_w} × {new_h} EMU "
          f"({new_w/EMU_PER_PT:.0f} × {new_h/EMU_PER_PT:.0f} pt)")

    # ── Step 3: Build batchUpdate requests ───────────────────────────────────
    requests = []

    for slide in new_prs['slides']:
        slide_id = slide['objectId']

        # 3a. Set slide background
        requests.append({
            'updatePageProperties': {
                'objectId': slide_id,
                'pageProperties': {
                    'pageBackgroundFill': make_solid_bg(bg_color)
                },
                'fields': 'pageBackgroundFill'
            }
        })

        elems = slide.get('pageElements', [])
        for elem in elems:
            shape = elem.get('shape', {})
            shape_type = shape.get('shapeType', '')
            has_text = bool(shape.get('text', {}).get('textElements'))
            elem_id = elem['objectId']
            size = elem.get('size', {})
            transform = elem.get('transform', {})

            # 3b. Delete background rectangles (RECTANGLE, no text, full-slide size)
            if shape_type == 'RECTANGLE' and not has_text:
                requests.append({'deleteObject': {'objectId': elem_id}})
                continue

            # 3c. Reformat text boxes
            if not has_text:
                continue

            # Determine if this is title-level or body-level text
            # Look at the text content to judge position/role
            all_text = ''.join(
                te.get('textRun', {}).get('content', '')
                for te in shape['text']['textElements']
                if 'textRun' in te
            ).strip()

            # Use transform.translateY to distinguish title (top) vs body (below)
            translate_y = transform.get('translateY', 0) if transform else 0
            is_title = translate_y < new_h * 0.25   # top quarter of slide

            # Apply font to all text in this shape
            requests.append({
                'updateTextStyle': {
                    'objectId': elem_id,
                    'textRange': {'type': 'ALL'},
                    'style': {
                        'fontFamily': dominant_font,
                        'foregroundColor': {
                            'opaqueColor': {'rgbColor': title_rgb if is_title else body_rgb}
                        },
                        'bold': True,
                    },
                    'fields': 'fontFamily,foregroundColor,bold'
                }
            })

    print(f'\nApplying {len(requests)} formatting requests...')
    # Slide API allows max 50k chars per request; chunk if needed
    CHUNK = 200
    for i in range(0, len(requests), CHUNK):
        service.presentations().batchUpdate(
            presentationId=NEW_ID,
            body={'requests': requests[i:i+CHUNK]}
        ).execute()
        print(f'  Sent requests {i+1}–{min(i+CHUNK, len(requests))}')

    print('\nDone. Open the presentation to review:')
    print(f'https://docs.google.com/presentation/d/{NEW_ID}/edit')


if __name__ == '__main__':
    main()
