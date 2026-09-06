#!/usr/bin/env python3
"""Weekly Meta ad spend/impressions/clicks pull into the FullyScale Weekly Inputs tab.

Reads the Meta access token live from the ad-analytics Config tab each run (so a
manual token refresh there is picked up automatically, no duplicate token to
maintain). Appends the next fully-closed week and re-checks/corrects the
previously-appended week for late-arriving Meta data. Only ever touches the
Impressions/Clicks/Spend cells of the two weeks it computes each run — never
touches other channels or older manual history.

Uses stdlib only (urllib) for both the Google Sheets REST API and the Meta Graph
API, so no third-party packages are required.

Usage: python3 meta_ads_weekly_pull.py
Exits 2 with a META_TOKEN_ERROR line on stderr if the Meta token is invalid/expired.
"""
import calendar
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
GRAPH_VERSION = 'v21.0'


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
        expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=body['expires_in'])
        tok['expiry_date'] = int(calendar.timegm(expiry.utctimetuple()) * 1000)
    json.dump(tok, open(NODE_TOKEN, 'w'))
    return tok['access_token']


def sheets_get(access_token, spreadsheet_id, rng):
    url = (f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/'
           f'{urllib.parse.quote(rng, safe="")}?valueRenderOption=UNFORMATTED_VALUE')
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access_token}'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read()).get('values', [])


def sheets_update(access_token, spreadsheet_id, rng, row_values):
    url = (f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/'
           f'{urllib.parse.quote(rng, safe="")}?valueInputOption=USER_ENTERED')
    body = json.dumps({'values': [row_values]}).encode()
    req = urllib.request.Request(url, data=body, method='PUT',
                                  headers={'Authorization': f'Bearer {access_token}',
                                           'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_meta_credentials(access_token):
    rows = sheets_get(access_token, ANALYTICS_SHEET_ID, f"'{CONFIG_TAB}'!A1:F10")
    header = rows[0]
    idx = {h: i for i, h in enumerate(header)}
    for row in rows[1:]:
        if row[idx['Client Name']] == CONFIG_CLIENT_NAME:
            return row[idx['Meta Access Token']], row[idx['Meta Account ID']]
    raise SystemExit(f'Config row for {CONFIG_CLIENT_NAME} not found in {ANALYTICS_SHEET_ID}')


def fetch_meta_week(meta_token, account_id, since, until):
    params = {
        'time_range': json.dumps({'since': since.isoformat(), 'until': until.isoformat()}),
        'fields': 'spend,impressions,inline_link_clicks',
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
        return {'spend': 0.0, 'impressions': 0, 'inline_link_clicks': 0}
    row = data[0]
    return {
        'spend': float(row.get('spend', 0)),
        'impressions': int(row.get('impressions', 0)),
        'inline_link_clicks': int(row.get('inline_link_clicks', 0)),
    }


def parse_date(v):
    # UNFORMATTED_VALUE returns dates as Sheets serial numbers (epoch 1899-12-30),
    # not ISO strings.
    if isinstance(v, (int, float)):
        return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(v))
    return datetime.date.fromisoformat(v)


def numify(v):
    if v in (None, ''):
        return 0.0
    return float(str(v).replace(',', '').replace('$', '').strip())


def main():
    access_token = refresh_google_token()
    meta_token, account_id = get_meta_credentials(access_token)

    rows = sheets_get(access_token, FULLYSCALE_SHEET_ID, f"'{WEEKLY_INPUTS_TAB}'!A1:H1000")
    data_rows = rows[1:]

    meta_rows = []
    for i, r in enumerate(data_rows):
        row_num = i + 2
        if len(r) > 1 and r[1] == CHANNEL:
            r = r + [''] * (8 - len(r))
            meta_rows.append((row_num, parse_date(r[0]), r[2], r[3], r[4], r[5]))

    if not meta_rows:
        raise SystemExit('No existing "Meta Ads" rows found in Weekly Inputs — refusing to guess a start date.')

    meta_rows.sort(key=lambda x: x[1])
    last_row_num, last_start = meta_rows[-1][0], meta_rows[-1][1]
    today = datetime.date.today()
    actions = []

    # 1) Reconcile the most recently written week (late-arriving Meta data).
    last_end = last_start + datetime.timedelta(days=7)
    if today >= last_end:
        fresh = fetch_meta_week(meta_token, account_id, last_start, last_start + datetime.timedelta(days=6))
        row_num, _, old_impr, old_clicks, old_spend, notes = meta_rows[-1]
        changed = (round(fresh['impressions']) != round(numify(old_impr)) or
                   round(fresh['inline_link_clicks']) != round(numify(old_clicks)) or
                   abs(fresh['spend'] - numify(old_spend)) > 0.01)
        if changed or 'partial' in (notes or '').lower():
            sheets_update(access_token, FULLYSCALE_SHEET_ID, f"'{WEEKLY_INPUTS_TAB}'!C{row_num}:E{row_num}",
                          [fresh['impressions'], fresh['inline_link_clicks'], fresh['spend']])
            if 'partial' in (notes or '').lower():
                sheets_update(access_token, FULLYSCALE_SHEET_ID, f"'{WEEKLY_INPUTS_TAB}'!F{row_num}",
                              ['Auto-pulled from Meta'])
            actions.append(f"Corrected week of {last_start} (row {row_num}): "
                            f"impressions {old_impr}->{fresh['impressions']}, "
                            f"clicks {old_clicks}->{fresh['inline_link_clicks']}, "
                            f"spend {old_spend}->{fresh['spend']:.2f}")
        else:
            actions.append(f"Week of {last_start} unchanged, no correction needed.")

    # 2) Append the next week once it has fully closed.
    next_start = last_start + datetime.timedelta(days=7)
    next_end = next_start + datetime.timedelta(days=7)
    if today >= next_end:
        fresh = fetch_meta_week(meta_token, account_id, next_start, next_start + datetime.timedelta(days=6))
        new_row_num = last_row_num + 1
        existing = sheets_get(access_token, FULLYSCALE_SHEET_ID,
                               f"'{WEEKLY_INPUTS_TAB}'!A{new_row_num}:H{new_row_num}")
        if existing and len(existing[0]) > 1:
            raise SystemExit(f'Row {new_row_num} is not empty — aborting append to avoid overwrite.')
        sheets_update(access_token, FULLYSCALE_SHEET_ID, f"'{WEEKLY_INPUTS_TAB}'!A{new_row_num}:H{new_row_num}", [
            next_start.isoformat(), CHANNEL,
            fresh['impressions'], fresh['inline_link_clicks'], fresh['spend'],
            'Auto-pulled from Meta', f'=A{new_row_num}+7', '',
        ])
        actions.append(f"Appended week of {next_start} (row {new_row_num}): "
                        f"impressions={fresh['impressions']}, clicks={fresh['inline_link_clicks']}, "
                        f"spend={fresh['spend']:.2f}")
    else:
        actions.append(f"Week of {next_start} not complete yet (ends {next_end}) — nothing to append.")

    print('\n'.join(actions))


def notify_mac(message):
    import subprocess
    script = f'display notification {json.dumps(message)} with title "Meta Ads Weekly Pull" sound name "Basso"'
    subprocess.run(['osascript', '-e', script], check=False)


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as e:
        msg = f'META_TOKEN_ERROR: {e}'
        print(msg, file=sys.stderr)
        notify_mac('Meta token expired — refresh it in the ad-analytics Config tab. Weekly Inputs auto-pull skipped this run.')
        sys.exit(2)
