#!/usr/bin/env python3
"""Copy cell formatting (colors/bold) from the all-time Fully Scale P&L 2026
columns onto the new 2026-YTD sheet so it looks identical.

Usage:
  python3 format_pnl.py dump    # authorize + dump source formatting to /tmp/src_formats.json
  python3 format_pnl.py apply   # apply identical formatting to the new sheet
"""
import os, sys, json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES     = ['https://www.googleapis.com/auth/spreadsheets']
CREDS_FILE = '/Users/Logan/Documents/google_credentials.json'
# Reuse the credential the local google-sheets MCP server already uses
# (node-style token: access_token/refresh_token/scope/expiry_date). Has the
# spreadsheets scope, so no new browser auth is needed.
NODE_TOKEN = '/Users/Logan/Documents/google_token.json'

SRC_ID = '1jisyCThPkx9wWax4ogWVnyLKY_oVF2uEgvCIfsD9tDg'   # all-time P&L
SRC_TAB = '2023-2025'
DST_ID = '1oWf9OTLdayryxmjYQ__HR7dYte8T2vNEXQ9y8GTCB70'   # new 2026 YTD

# month blocks: source 0-based base col -> dest 0-based base col
# source Jan2026 base col = 140; each month = 5 cols. dest: col A summary, then blocks from col 1.
SRC_BASE = {0:140,1:145,2:150,3:155,4:160,5:165}
DST_BASE = {b:1+5*b for b in range(6)}
NROWS = 58          # rows 0..57
SUMMARY_COL = 0     # col A in both

def get_creds():
    client = json.load(open(CREDS_FILE))['installed']
    tok = json.load(open(NODE_TOKEN))
    creds = Credentials(
        token=tok.get('access_token'),
        refresh_token=tok.get('refresh_token'),
        token_uri=client.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=client['client_id'],
        client_secret=client['client_secret'],
        scopes=tok.get('scope', '').split() or SCOPES,
    )
    if tok.get('expiry_date'):
        import datetime
        creds.expiry = datetime.datetime.utcfromtimestamp(tok['expiry_date'] / 1000)
    if not creds.valid:
        creds.refresh(Request())
        # write back refreshed access token in node format so the MCP keeps working
        tok['access_token'] = creds.token
        if creds.expiry:
            import calendar
            tok['expiry_date'] = int(calendar.timegm(creds.expiry.utctimetuple()) * 1000)
        json.dump(tok, open(NODE_TOKEN, 'w'))
    return creds

def colletter(n0):  # 0-based index -> A1 column letters
    n = n0 + 1; s = ''
    while n:
        n, r = divmod(n-1, 26); s = chr(65+r)+s
    return s

def svc():
    return build('sheets', 'v4', credentials=get_creds())

def sheet_id(s, sid, title):
    meta = s.spreadsheets().get(spreadsheetId=sid).execute()
    for sh in meta['sheets']:
        if title is None or sh['properties']['title'] == title:
            return sh['properties']['sheetId'], meta
    raise SystemExit(f'tab {title} not found')

def dump():
    s = svc()
    # ranges: summary col + all 6 month blocks (cols 140..169)
    last_col = colletter(169)
    ranges = [f"'{SRC_TAB}'!A1:A{NROWS}", f"'{SRC_TAB}'!{colletter(140)}1:{last_col}{NROWS}"]
    fields = 'sheets(data(startRow,startColumn,rowData(values(userEnteredFormat))))'
    resp = s.spreadsheets().get(spreadsheetId=SRC_ID, ranges=ranges,
                                includeGridData=True, fields=fields).execute()
    out = {}
    for data in resp['sheets'][0]['data']:
        sc = data.get('startColumn', 0); sr = data.get('startRow', 0)
        for ri, row in enumerate(data.get('rowData', [])):
            for ci, cell in enumerate(row.get('values', [])):
                fmt = cell.get('userEnteredFormat')
                if fmt:
                    out[f'{sr+ri},{sc+ci}'] = fmt
    json.dump(out, open('/tmp/src_formats.json', 'w'))
    print('dumped', len(out), 'formatted cells to /tmp/src_formats.json')
    # quick human summary of summary col + Jan block
    def desc(f):
        bg = f.get('backgroundColor', {})
        bg = (round(bg.get('red',1),2),round(bg.get('green',1),2),round(bg.get('blue',1),2))
        tf = f.get('textFormat', {})
        fg = tf.get('foregroundColor', {})
        fg = (round(fg.get('red',0),2),round(fg.get('green',0),2),round(fg.get('blue',0),2))
        return f"bg{bg} bold={tf.get('bold',False)} fg{fg}"
    print('\n-- Summary col (col 0) --')
    for r in range(14):
        k=f'{r},0'
        if k in out: print(r, desc(out[k]))
    print('\n-- Jan block (cols 140-144) rows 0-6 --')
    for r in range(7):
        for c in range(140,145):
            k=f'{r},{c}'
            if k in out: print(f'r{r} c{c}', desc(out[k]))

WHITE_BOLD = {'backgroundColor': {'red': 1, 'green': 1, 'blue': 1},
              'textFormat': {'bold': True}}

def apply():
    s = svc()
    f = json.load(open('/tmp/src_formats.json'))
    grid = json.load(open('/tmp/new_sheet_grid_trim.json'))
    dst_sid, _ = sheet_id(s, DST_ID, None)
    # canonical formats cloned from the standard (Jan) block, col 0 summary
    HDR0, HDR1, HDR2, HDR2B = f['0,140'], f['1,140'], f['2,140'], f['2,141']
    AMT, LBL = f['3,140'], f['3,141']
    reqs = []
    def rc(r0, r1, c0, c1, fmt):
        reqs.append({'repeatCell': {
            'range': {'sheetId': dst_sid, 'startRowIndex': r0, 'endRowIndex': r1,
                      'startColumnIndex': c0, 'endColumnIndex': c1},
            'cell': {'userEnteredFormat': fmt}, 'fields': 'userEnteredFormat'}})
    for b in range(6):
        db = DST_BASE[b]
        # last data row (0-based) in this block
        last = 2
        for r in range(len(grid)):
            if any(str(grid[r][db+o]).strip() for o in range(5)):
                last = r
        rc(0, 1, db, db+5, HDR0)        # month-name header
        rc(1, 2, db, db+5, HDR1)        # Amount Spent / Payed
        rc(2, 3, db, db+5, HDR2)        # subheader row
        rc(2, 3, db+1, db+2, HDR2B)     # "From" bold
        rc(2, 3, db+4, db+5, HDR2B)     # "Expenses" bold
        if last >= 3:
            rc(3, last+1, db,   db+1, AMT)   # expense $ (light green)
            rc(3, last+1, db+1, db+2, LBL)   # From labels (light yellow)
            rc(3, last+1, db+2, db+3, AMT)   # income $ (light green)
            rc(3, last+1, db+4, db+5, LBL)   # Expenses labels (light yellow)
    # summary column (col A)
    rc(0, 1, 0, 1, f['0,0'])    # title -> light blue bold
    rc(3, 4, 0, 1, f['8,0'])    # "Total Invested (Spent)" -> teal bold
    rc(4, 5, 0, 1, WHITE_BOLD)  # invested value
    rc(5, 6, 0, 1, f['10,0'])   # "Total Made (Payed)" -> green bold
    rc(6, 7, 0, 1, WHITE_BOLD)  # made value
    rc(7, 8, 0, 1, f['12,0'])   # "Total Profit / Difference"
    rc(8, 9, 0, 1, WHITE_BOLD)  # profit value
    s.spreadsheets().batchUpdate(spreadsheetId=DST_ID, body={'requests': reqs}).execute()
    print('applied', len(reqs), 'format ranges to new sheet')

def fix():
    """Repair the new sheet: 2 empty columns got inserted at B/C, shifting every
    month +2. Delete them (data/formulas/formatting all shift back), then restore
    2-decimal currency on the income columns."""
    s = svc()
    dst_sid, _ = sheet_id(s, DST_ID, None)
    # 1) delete the two empty inserted columns B,C (0-based indices 1,2)
    s.spreadsheets().batchUpdate(spreadsheetId=DST_ID, body={'requests': [
        {'deleteDimension': {'range': {'sheetId': dst_sid, 'dimension': 'COLUMNS',
                                       'startIndex': 1, 'endIndex': 3}}}]}).execute()
    # 2) income (off2) columns -> 2-decimal currency, preserving background color
    cur2 = {'numberFormat': {'type': 'CURRENCY', 'pattern': '"$"#,##0.00'}}
    reqs = []
    for b in range(6):
        off2 = (1 + 5 * b) + 2            # post-delete 0-based income column
        reqs.append({'repeatCell': {
            'range': {'sheetId': dst_sid, 'startRowIndex': 3, 'endRowIndex': 70,
                      'startColumnIndex': off2, 'endColumnIndex': off2 + 1},
            'cell': {'userEnteredFormat': cur2},
            'fields': 'userEnteredFormat.numberFormat'}})
    s.spreadsheets().batchUpdate(spreadsheetId=DST_ID, body={'requests': reqs}).execute()
    print('deleted 2 empty cols B/C; set income columns to 2-decimal currency')

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'dump'
    {'dump': dump, 'apply': apply, 'fix': fix}[mode]()
