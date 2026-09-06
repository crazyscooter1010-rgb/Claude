#!/usr/bin/env python3
"""Weekly Meta Inputs — auto-fills the "Weekly Inputs" tab's Meta Ads rows
with live data from Meta's Insights API, replacing manual weekly entry.

Account-level (not ad-set level) since Weekly Inputs is one aggregate row
per week, not a per-ad-set breakdown. Clicks/Replies = inline_link_clicks,
confirmed against the most recent existing row (tagged "Auto-pulled from
Meta"): 27,180 impressions / 409 link clicks / $1,465.73 matched Meta's
inline_link_clicks exactly for that week, not raw `clicks` (679).

Only ever fills forward from the last existing row — never touches or
backfills history before it. The current (in-progress) week's row gets
recomputed and overwritten in place on each run until the week's 7-day
span is reached, then the next run starts a new row for the following week.

Weekly Dashboard and Funnel Summary already sum from Weekly Inputs, so no
changes are needed there — their numbers just become current automatically.

Uses stdlib only (urllib) — no third-party packages required.
"""
import datetime
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

CREDS_FILE = '/Users/Logan/Documents/google_credentials.json'
NODE_TOKEN = '/Users/Logan/Documents/google_token.json'

ANALYTICS_SHEET_ID = '1xdRsyIvZlaQNrfrras-bks9TxW3c7Phq725zJxizj1U'  # Config tab lives here
CONFIG_TAB = 'Config'
CONFIG_CLIENT_NAME = 'Logan Schnider (Lead Gen)'

FULLYSCALE_SHEET_ID = '14g75lx2ZxG-pSE0bPkAsZ433s4Ay88wL0L5A8lzXZUA'
WEEKLY_INPUTS_TAB = 'Weekly Inputs'
CHANNEL = 'Meta Ads'
AUTO_NOTE = 'Auto-pulled from Meta'

GRAPH_VERSION = 'v21.0'
WEEK_SPAN_DAYS = 7  # each row covers [Week Start, Week Start + 6] inclusive


# ---------- Google Sheets (stdlib OAuth, reusing the existing token) ----------

def refresh_google_token():
    client = json.load(open(CREDS_FILE))['installed']
    tok = json.load(open(NODE_TOKEN))
    data = urllib.parse.urlencode({
        'client_id': client['client_id'],
        'client_secret': client['client_secret'],
        'refresh_token': tok['refresh_token'],
        'grant_type': 'refresh_token',
    }).encode()
    req = urllib.request.Request(client['token_uri'], data=data, method='POST')
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read())
    tok['access_token'] = body['access_token']
    if 'expires_in' in body:
        import calendar as cal
        expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=body['expires_in'])
        tok['expiry_date'] = int(cal.timegm(expiry.utctimetuple()) * 1000)
    json.dump(tok, open(NODE_TOKEN, 'w'))
    return tok['access_token']


def sheets_get(access_token, spreadsheet_id, rng):
    url = (f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/'
           f'{urllib.parse.quote(rng, safe="")}?valueRenderOption=UNFORMATTED_VALUE')
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access_token}'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read()).get('values', [])


def sheets_values_update(access_token, spreadsheet_id, rng, values):
    url = (f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/'
           f'{urllib.parse.quote(rng, safe="")}?valueInputOption=USER_ENTERED')
    body = json.dumps({'values': values}).encode()
    req = urllib.request.Request(url, data=body, method='PUT',
                                  headers={'Authorization': f'Bearer {access_token}',
                                           'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def get_meta_credentials(access_token):
    rows = sheets_get(access_token, ANALYTICS_SHEET_ID, f"'{CONFIG_TAB}'!A1:F10")
    header = rows[0]
    idx = {h: i for i, h in enumerate(header)}
    for row in rows[1:]:
        if row[idx['Client Name']] == CONFIG_CLIENT_NAME:
            return row[idx['Meta Access Token']], row[idx['Meta Account ID']]
    raise SystemExit(f'Config row for {CONFIG_CLIENT_NAME} not found in {ANALYTICS_SHEET_ID}')


# ---------- Meta Graph API ----------

def fetch_account_week(meta_token, account_id, since, until):
    """Account-level impressions/link-clicks/spend for one date range
    (inclusive on both ends). Returns zeros if Meta has no row at all for
    the window (e.g. campaigns fully paused that week)."""
    params = {
        'level': 'account',
        'time_range': json.dumps({'since': since.isoformat(), 'until': until.isoformat()}),
        'fields': 'impressions,inline_link_clicks,spend',
        'access_token': meta_token,
    }
    url = f'https://graph.facebook.com/{GRAPH_VERSION}/act_{account_id}/insights?' + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
    if 'error' in body:
        raise RuntimeError(f"Meta API error: {body['error'].get('message')} (code {body['error'].get('code')})")
    data = body.get('data', [])
    if not data:
        return 0, 0, 0.0
    row = data[0]
    return int(row.get('impressions', 0)), int(row.get('inline_link_clicks', 0)), float(row.get('spend', 0))


# ---------- Date helpers ----------

EXCEL_EPOCH = datetime.date(1899, 12, 30)


def parse_sheet_date(v):
    if isinstance(v, (int, float)):
        return EXCEL_EPOCH + datetime.timedelta(days=int(v))
    return datetime.date.fromisoformat(str(v)[:10])


def to_excel_serial(d):
    return (d - EXCEL_EPOCH).days


def main():
    access_token = refresh_google_token()
    meta_token, account_id = get_meta_credentials(access_token)
    today = datetime.date.today()

    rows = sheets_get(access_token, FULLYSCALE_SHEET_ID, f"'{WEEKLY_INPUTS_TAB}'!A1:H2000")
    header, data_rows = rows[0], rows[1:]
    idx = {h: i for i, h in enumerate(header)}

    week_row_map = {}  # week_start(date) -> sheet row number (1-indexed)
    for i, r in enumerate(data_rows):
        if len(r) <= idx['Channel'] or r[idx['Channel']] != CHANNEL:
            continue
        ws = parse_sheet_date(r[idx['Week Start (Mon)']])
        week_row_map[ws] = i + 2  # +1 for header, +1 for 1-indexing

    if not week_row_map:
        raise RuntimeError(f'No existing "{CHANNEL}" rows found in "{WEEKLY_INPUTS_TAB}" — '
                            'refusing to guess a start date. Add at least one row first.')

    next_free_row = len(data_rows) + 2  # next blank row after the last data row
    ws_cursor = max(week_row_map)

    updated, created = [], []
    while ws_cursor <= today:
        window_end = min(ws_cursor + datetime.timedelta(days=WEEK_SPAN_DAYS - 1), today)
        impressions, link_clicks, spend = fetch_account_week(meta_token, account_id, ws_cursor, window_end)
        week_end_label = ws_cursor + datetime.timedelta(days=WEEK_SPAN_DAYS)

        if ws_cursor in week_row_map:
            row_num = week_row_map[ws_cursor]
            sheets_values_update(access_token, FULLYSCALE_SHEET_ID,
                                  f"'{WEEKLY_INPUTS_TAB}'!C{row_num}:F{row_num}",
                                  [[impressions, link_clicks, round(spend, 2), AUTO_NOTE]])
            updated.append((ws_cursor, impressions, link_clicks, spend))
        else:
            row_num = next_free_row
            sheets_values_update(access_token, FULLYSCALE_SHEET_ID,
                                  f"'{WEEKLY_INPUTS_TAB}'!A{row_num}:G{row_num}",
                                  [[to_excel_serial(ws_cursor), CHANNEL, impressions, link_clicks,
                                    round(spend, 2), AUTO_NOTE, to_excel_serial(week_end_label)]])
            week_row_map[ws_cursor] = row_num
            next_free_row += 1
            created.append((ws_cursor, impressions, link_clicks, spend))

        ws_cursor += datetime.timedelta(days=WEEK_SPAN_DAYS)

    for ws, impr, clicks, spend in updated:
        print(f'Updated week of {ws}: impressions={impr}, link_clicks={clicks}, spend=${spend:,.2f}')
    for ws, impr, clicks, spend in created:
        print(f'Created week of {ws}: impressions={impr}, link_clicks={clicks}, spend=${spend:,.2f}')
    if not updated and not created:
        print('Nothing to do — Weekly Inputs is already current.')


def notify_mac(message):
    import subprocess
    script = f'display notification {json.dumps(message)} with title "Weekly Meta Inputs Refresh" sound name "Basso"'
    subprocess.run(['osascript', '-e', script], check=False)


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as e:
        msg = f'META_TOKEN_ERROR: {e}'
        print(msg, file=sys.stderr)
        notify_mac('Weekly Meta Inputs refresh failed — check the Meta token (Config tab) or Weekly Inputs structure.')
        sys.exit(2)
