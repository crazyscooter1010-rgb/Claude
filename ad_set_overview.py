#!/usr/bin/env python3
"""Ad Set Overview — cost per lead / booked call / show, per Meta ad set.

Layout: one row per ad set, with Last 30 Days and Previous 30 Days metrics
side by side (grouped column headers) plus Change (Δ) columns — modeled on
the "FullyScale_CPL_CPBC_by_AdSet" comparison sheet's row/column structure.
Active ad sets sort first (by Last-30 spend), then everything else (Paused/
Campaign Paused/etc.) below — not interleaved. Color coding (Status
green/red, Cost per Booked Call / Cost per Show green/yellow/red by
threshold) is unchanged from prior versions of this script.
A separate Last 7 Days block (single period, no comparison) follows below.

Booked/Show ground truth comes from the Lead Log tab (manually verified by
Logan's team) rather than GHL calendar/tag data — spot-checked against real
contacts and found GHL's "no show" tags can go stale after a reschedule,
while Lead Log's Call Booked?/Showed? columns reflect the lead's final
outcome.

Ad-set attribution comes from each lead's GHL contact `attributionSource
.adSetId` (first-touch attribution, stored directly on the contact — no
need to hop through the ad). ~1 in 4 leads in spot checks lacked this (
multi-touch leads whose first touch wasn't Meta) — those land in a
separate UNATTRIBUTED row rather than being dropped or guessed at.

Fully recomputes and overwrites the "Ad Set Overview" tab each run (a
snapshot view, not a ledger like Weekly Inputs).

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
LEAD_LOG_TAB = 'Lead Log'
OVERVIEW_TAB = 'Ad Set Overview'
SOURCE_FILTER = 'Meta Ads'

GHL_ENV_FILE = '/Users/Logan/Documents/Claude Code/gohighlevel-cli/.env'
GHL_API_BASE = 'https://services.leadconnectorhq.com'
GHL_VERSION = '2021-07-28'

GRAPH_VERSION = 'v21.0'

LAST7_DAYS = 7

UNATTRIBUTED_LABEL = 'UNATTRIBUTED (no ad set match)'

N_COMPARISON_COLS = 18  # Ad Set, Status, 7 Previous-30 cols, 7 Last-30 cols, 2 Change cols
N_LAST7_COLS = 9        # Ad Set, Status, Spend, Leads, CPL, Booked, CPBC, Shows, Cost/Show


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


def sheets_meta(access_token, spreadsheet_id):
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access_token}'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def sheets_batch_update(access_token, spreadsheet_id, requests):
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate'
    body = json.dumps({'requests': requests}).encode()
    req = urllib.request.Request(url, data=body, method='POST',
                                  headers={'Authorization': f'Bearer {access_token}',
                                           'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def sheets_values_update(access_token, spreadsheet_id, rng, values):
    url = (f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/'
           f'{urllib.parse.quote(rng, safe="")}?valueInputOption=USER_ENTERED')
    body = json.dumps({'values': values}).encode()
    req = urllib.request.Request(url, data=body, method='PUT',
                                  headers={'Authorization': f'Bearer {access_token}',
                                           'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def sheets_values_clear(access_token, spreadsheet_id, rng):
    url = (f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/'
           f'{urllib.parse.quote(rng, safe="")}:clear')
    req = urllib.request.Request(url, data=b'{}', method='POST',
                                  headers={'Authorization': f'Bearer {access_token}',
                                           'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def ensure_tab_exists(access_token, spreadsheet_id, title):
    meta = sheets_meta(access_token, spreadsheet_id)
    for sh in meta['sheets']:
        if sh['properties']['title'] == title:
            return sh['properties']['sheetId']
    resp = sheets_batch_update(access_token, spreadsheet_id, [
        {'addSheet': {'properties': {'title': title}}}
    ])
    return resp['replies'][0]['addSheet']['properties']['sheetId']


# ---------- Meta Graph API ----------

def fetch_meta_adset_spend(meta_token, account_id, date_preset=None, time_range=None):
    params = {
        'level': 'adset',
        'fields': 'spend,adset_id,adset_name',
        'limit': '200',
        'access_token': meta_token,
    }
    if time_range:
        params['time_range'] = json.dumps(time_range)
    else:
        params['date_preset'] = date_preset
    url = f'https://graph.facebook.com/{GRAPH_VERSION}/act_{account_id}/insights?' + urllib.parse.urlencode(params)
    result = {}
    while url:
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                body = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = json.loads(e.read())
        if 'error' in body:
            raise RuntimeError(f"Meta API error: {body['error'].get('message')} (code {body['error'].get('code')})")
        for row in body.get('data', []):
            result[row['adset_id']] = {
                'name': row.get('adset_name', row['adset_id']),
                'spend': float(row.get('spend', 0)),
            }
        url = body.get('paging', {}).get('next')
    return result


_STATUS_LABELS = {
    'ACTIVE': 'Active',
    'PAUSED': 'Paused',
    'ADSET_PAUSED': 'Paused',
    'CAMPAIGN_PAUSED': 'Campaign Paused',
    'ARCHIVED': 'Archived',
    'DELETED': 'Deleted',
    'PENDING_REVIEW': 'Pending Review',
    'DISAPPROVED': 'Disapproved',
    'PREAPPROVAL': 'Pending Review',
    'PENDING_BILLING_INFO': 'Pending Billing',
    'IN_PROCESS': 'In Process',
    'WITH_ISSUES': 'With Issues',
}


def fetch_adset_statuses(meta_token, account_id):
    """Current name + effective_status for every ad set in the account (not
    window-scoped — these are live object properties, unlike spend which is
    time-bounded). Pulling name here too (not just from Meta Insights) lets a
    brand-new ad set still show up by name even before it has any recorded
    spend/leads — otherwise it would be entirely invisible until Insights
    caught up, which reads as "everything's paused" when it's really just
    missing."""
    params = {
        'fields': 'id,name,effective_status',
        'limit': '500',
        'access_token': meta_token,
    }
    url = f'https://graph.facebook.com/{GRAPH_VERSION}/act_{account_id}/adsets?' + urllib.parse.urlencode(params)
    result = {}
    while url:
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                body = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = json.loads(e.read())
        if 'error' in body:
            raise RuntimeError(f"Meta API error: {body['error'].get('message')} (code {body['error'].get('code')})")
        for row in body.get('data', []):
            raw = row.get('effective_status', '')
            result[row['id']] = {
                'name': row.get('name', row['id']),
                'status': _STATUS_LABELS.get(raw, raw.replace('_', ' ').title()),
            }
        url = body.get('paging', {}).get('next')
    return result


def get_meta_credentials(access_token):
    rows = sheets_get(access_token, ANALYTICS_SHEET_ID, f"'{CONFIG_TAB}'!A1:F10")
    header = rows[0]
    idx = {h: i for i, h in enumerate(header)}
    for row in rows[1:]:
        if row[idx['Client Name']] == CONFIG_CLIENT_NAME:
            return row[idx['Meta Access Token']], row[idx['Meta Account ID']]
    raise SystemExit(f'Config row for {CONFIG_CLIENT_NAME} not found in {ANALYTICS_SHEET_ID}')


# ---------- GoHighLevel API ----------

def load_ghl_env():
    env = {}
    with open(GHL_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env['GHL_API_KEY'], env['GHL_LOCATION_ID']


def ghl_get_contact_adset_id(api_key, contact_id):
    url = f'{GHL_API_BASE}/contacts/{contact_id}'
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {api_key}',
        'Version': GHL_VERSION,
        'Accept': 'application/json',
        # Cloudflare in front of leadconnectorhq.com blocks urllib's default
        # "Python-urllib/x.y" User-Agent as a bot signature (403 error 1010).
        # A requests-style UA (what the working `ghl` CLI sends) passes fine.
        'User-Agent': 'python-requests/2.31.0',
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError:
        return None
    contact = body.get('contact', body)
    return (contact.get('attributionSource') or {}).get('adSetId')


# ---------- Lead Log ----------

def parse_sheet_date(v):
    if isinstance(v, (int, float)):
        return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(v))
    return datetime.date.fromisoformat(str(v)[:10])


def read_meta_leads(access_token, window_start):
    """Return list of dicts for every Meta Ads lead with Date In >= window_start."""
    rows = sheets_get(access_token, FULLYSCALE_SHEET_ID, f"'{LEAD_LOG_TAB}'!A1:AC2000")
    header, data_rows = rows[0], rows[1:]
    idx = {h: i for i, h in enumerate(header)}
    leads = []
    for r in data_rows:
        if len(r) <= idx.get('Clean Source', 28):
            r = r + [''] * (29 - len(r))
        clean_source = r[idx['Clean Source']]
        if clean_source != SOURCE_FILTER:
            continue
        date_in_raw = r[idx['Date In']]
        if not date_in_raw:
            continue
        date_in = parse_sheet_date(date_in_raw)
        if date_in < window_start:
            continue
        leads.append({
            'lead_id': r[idx['Lead ID']],
            'date_in': date_in,
            'booked': r[idx['Call Booked?']] == 'Y',
            'showed': r[idx['Showed?']] == 'Y',
        })
    return leads


# ---------- Aggregation ----------

def aggregate_window(leads_in_window, adset_spend, lead_adset_map):
    """Roll spend (per ad set, from Meta) and leads/booked/shows (per ad set,
    from the Lead Log + GHL attribution) into one dict per ad set, plus a
    separate unattributed bucket. Returns (agg: adset_id -> metrics, unattributed: metrics)."""
    agg = {}
    for adset_id, info in adset_spend.items():
        agg[adset_id] = {'name': info['name'], 'spend': info['spend'], 'leads': 0, 'booked': 0, 'shows': 0}
    unattributed = {'spend': 0.0, 'leads': 0, 'booked': 0, 'shows': 0}

    for lead in leads_in_window:
        adset_id = lead_adset_map.get(lead['lead_id'])
        bucket = agg.get(adset_id) if adset_id else None
        if bucket is None:
            unattributed['leads'] += 1
            if lead['booked']:
                unattributed['booked'] += 1
            if lead['showed']:
                unattributed['shows'] += 1
            continue
        bucket['leads'] += 1
        if lead['booked']:
            bucket['booked'] += 1
        if lead['showed']:
            bucket['shows'] += 1
    return agg, unattributed


def finalize_block_rows(agg, unattributed, adset_status):
    """Turn an aggregate_window() result into a sorted list of row-dicts for
    a single-period block (used for the Last 7 Days section). Currently-
    Active ad sets always get a row, even at zero spend/leads — a brand-new
    ad set with no Meta Insights data yet would otherwise vanish from the
    tab entirely instead of showing as on with no data."""
    rows = []
    seen = set()
    for adset_id, v in agg.items():
        seen.add(adset_id)
        status = adset_status.get(adset_id, {}).get('status', '')
        if v['spend'] > 0 or v['leads'] > 0 or status == 'Active':
            rows.append({'name': v['name'], 'status': status,
                         'spend': v['spend'], 'leads': v['leads'], 'booked': v['booked'], 'shows': v['shows']})
    for adset_id, info in adset_status.items():
        if adset_id in seen or info.get('status') != 'Active':
            continue
        rows.append({'name': info.get('name', adset_id), 'status': 'Active',
                     'spend': 0.0, 'leads': 0, 'booked': 0, 'shows': 0})
    rows.sort(key=lambda v: (v['status'] != 'Active', -v['spend']))
    if unattributed['leads'] > 0:
        rows.append({'name': UNATTRIBUTED_LABEL, 'status': '', **unattributed})
    return rows


def cost_cell(spend, count, is_unattributed):
    if is_unattributed:
        return 'n/a'
    if count == 0:
        return ''
    return round(spend / count, 2)


def metric_cells(spend, leads, booked, shows, is_unattributed):
    """[Spend, Leads, CPL, Booked, CPBC, Shows, Cost/Show] for one ad set, one period."""
    return [
        round(spend, 2), leads, cost_cell(spend, leads, is_unattributed),
        booked, cost_cell(spend, booked, is_unattributed),
        shows, cost_cell(spend, shows, is_unattributed),
    ]


def delta_cell(last_val, prev_val):
    if isinstance(last_val, (int, float)) and isinstance(prev_val, (int, float)):
        return round(last_val - prev_val, 2)
    return ''


def render_single_block(rows):
    """9-col rows: Ad Set, Status, Spend, Leads, CPL, Booked, CPBC, Shows, Cost/Show + TOTAL row."""
    out = []
    total = {'spend': 0.0, 'leads': 0, 'booked': 0, 'shows': 0}
    for r in rows:
        is_unattr = r['name'] == UNATTRIBUTED_LABEL
        cells = metric_cells(r['spend'], r['leads'], r['booked'], r['shows'], is_unattr)
        out.append([r['name'], r['status'], *cells])
        if not is_unattr:
            total['spend'] += r['spend']
        total['leads'] += r['leads']
        total['booked'] += r['booked']
        total['shows'] += r['shows']
    total_cells = metric_cells(total['spend'], total['leads'], total['booked'], total['shows'], False)
    out.append(['TOTAL', '', *total_cells])
    return out


def build_comparison_table(prev_agg, prev_unattr, last_agg, last_unattr, adset_status):
    """18-col rows: Ad Set, Status, [Last 30: 7 cols], [Previous 30: 7 cols],
    CPL Δ, CPBC Δ. Active ad sets sorted first (by Last-30 spend descending),
    then everything else (Paused/Campaign Paused/etc.) below (by Last-30
    spend descending) — so active and paused ad sets aren't interleaved.
    TOTAL row last."""
    # Union in every currently-Active ad set id too, not just ones Meta
    # Insights already has spend/leads rows for — a brand-new ad set can be
    # genuinely Active with zero Insights data yet, and would otherwise
    # disappear from the tab entirely instead of showing as on with no data.
    active_ids = {aid for aid, info in adset_status.items() if info.get('status') == 'Active'}
    ids = set(prev_agg) | set(last_agg) | active_ids
    empty = {'name': None, 'spend': 0.0, 'leads': 0, 'booked': 0, 'shows': 0}
    entries = []
    for adset_id in ids:
        p = prev_agg.get(adset_id, empty)
        l = last_agg.get(adset_id, empty)
        status = adset_status.get(adset_id, {}).get('status', '')
        if status != 'Active' and p['spend'] == 0 and p['leads'] == 0 and l['spend'] == 0 and l['leads'] == 0:
            continue
        entries.append({
            'name': l['name'] or p['name'] or adset_status.get(adset_id, {}).get('name') or adset_id,
            'status': status,
            'prev': p, 'last': l,
        })
    entries.sort(key=lambda e: (e['status'] != 'Active', -e['last']['spend']))

    if prev_unattr['leads'] > 0 or last_unattr['leads'] > 0:
        entries.append({'name': UNATTRIBUTED_LABEL, 'status': '', 'prev': prev_unattr, 'last': last_unattr, 'is_unattr': True})

    rows = []
    total_prev = {'spend': 0.0, 'leads': 0, 'booked': 0, 'shows': 0}
    total_last = {'spend': 0.0, 'leads': 0, 'booked': 0, 'shows': 0}
    for e in entries:
        is_unattr = e.get('is_unattr', False)
        p, l = e['prev'], e['last']
        prev_cells = metric_cells(p['spend'], p['leads'], p['booked'], p['shows'], is_unattr)
        last_cells = metric_cells(l['spend'], l['leads'], l['booked'], l['shows'], is_unattr)
        rows.append([
            e['name'], e['status'], *last_cells, *prev_cells,
            delta_cell(last_cells[2], prev_cells[2]),  # CPL Δ
            delta_cell(last_cells[4], prev_cells[4]),  # CPBC Δ
        ])
        if not is_unattr:
            total_prev['spend'] += p['spend']
            total_last['spend'] += l['spend']
        total_prev['leads'] += p['leads']; total_prev['booked'] += p['booked']; total_prev['shows'] += p['shows']
        total_last['leads'] += l['leads']; total_last['booked'] += l['booked']; total_last['shows'] += l['shows']

    tp_cells = metric_cells(total_prev['spend'], total_prev['leads'], total_prev['booked'], total_prev['shows'], False)
    tl_cells = metric_cells(total_last['spend'], total_last['leads'], total_last['booked'], total_last['shows'], False)
    rows.append([
        'TOTAL', '', *tl_cells, *tp_cells,
        delta_cell(tl_cells[2], tp_cells[2]),
        delta_cell(tl_cells[4], tp_cells[4]),
    ])
    return rows


STATUS_GREEN = {'red': 0.80, 'green': 0.93, 'blue': 0.80}
STATUS_RED = {'red': 0.96, 'green': 0.78, 'blue': 0.78}
COST_GREEN = {'red': 0.80, 'green': 0.93, 'blue': 0.80}
COST_YELLOW = {'red': 1.0, 'green': 0.95, 'blue': 0.70}
COST_RED = {'red': 0.96, 'green': 0.78, 'blue': 0.78}
COST_DARK_RED = {'red': 0.60, 'green': 0.0, 'blue': 0.0}
COST_DARK_RED_TEXT = {'red': 1.0, 'green': 1.0, 'blue': 1.0}
HEADER_GREY = {'red': 0.85, 'green': 0.85, 'blue': 0.85}

# Per-metric thresholds — CPL and CPBC have tighter, metric-specific bands;
# CPS (Cost per Show) keeps the original generic band since it wasn't asked
# to change. Anything at or beyond 2x the green cutoff is dark red — a
# "go shut this off" signal, not just a normal red flag.
CPL_GOOD_MAX = 150   # < $150 -> green
CPL_WARN_MAX = 250   # $150-$250 -> yellow; $250-$300 -> red; $300+ -> dark red
CPBC_GOOD_MAX = 200  # < $200 -> green
CPBC_WARN_MAX = 300  # $200-$300 -> yellow; $300-$400 -> red; $400+ -> dark red
CPS_GOOD_MAX = 300   # < $300 -> green
CPS_WARN_MAX = 500   # $300-$500 -> yellow; $500-$600 -> red; $600+ -> dark red


def _cost_color(value, good_max, warn_max):
    """Returns (background, text_color) — text_color is None unless the
    background is dark enough to need white text."""
    if not isinstance(value, (int, float)):
        return None, None
    if value >= good_max * 2:
        return COST_DARK_RED, COST_DARK_RED_TEXT
    if value < good_max:
        return COST_GREEN, None
    if value < warn_max:
        return COST_YELLOW, None
    return COST_RED, None


def _cell_fill(sheet_id, row0, col0, color, text_color=None):
    cell = {'backgroundColor': color}
    fields = 'userEnteredFormat.backgroundColor'
    if text_color:
        cell['textFormat'] = {'foregroundColor': text_color}
        fields = 'userEnteredFormat(backgroundColor,textFormat.foregroundColor)'
    return {'repeatCell': {
        'range': {'sheetId': sheet_id, 'startRowIndex': row0, 'endRowIndex': row0 + 1,
                  'startColumnIndex': col0, 'endColumnIndex': col0 + 1},
        'cell': {'userEnteredFormat': cell},
        'fields': fields}}


def _range(sheet_id, r0, r1, c0, c1):
    return {'sheetId': sheet_id, 'startRowIndex': r0, 'endRowIndex': r1, 'startColumnIndex': c0, 'endColumnIndex': c1}


def apply_formatting(access_token, sheet_id, all_rows, comparison_bounds, last7_bounds, prev_label, last_label):
    """comparison_bounds: (data_start0, data_end0_exclusive, total_row0) for the
    Previous/Last 30 comparison table (header rows 0-1, data starts at row 2).
    last7_bounds: (caption_row0, header_row0, data_start0, data_end0_exclusive, total_row0)
    for the trailing Last 7 Days block."""
    n_rows = len(all_rows)
    cmp_start, cmp_end, cmp_total = comparison_bounds
    caption_row, l7_header, l7_start, l7_end, l7_total = last7_bounds

    reqs = [
        # Clean slate: unmerge and wipe formatting on the whole sheet first.
        # Column layout/merges can shift between script versions, and
        # values.clear() only clears content, not format/merges — a stale
        # layout would otherwise persist forever.
        {'unmergeCells': {'range': _range(sheet_id, 0, n_rows, 0, N_COMPARISON_COLS)}},
        {'repeatCell': {'range': _range(sheet_id, 0, n_rows, 0, N_COMPARISON_COLS),
                         'cell': {'userEnteredFormat': {}}, 'fields': 'userEnteredFormat'}},
        {'updateSheetProperties': {'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 2}},
                                    'fields': 'gridProperties.frozenRowCount'}},
        # Merge the two-row grouped header: Ad Set / Status span both header
        # rows; Previous 30 / Last 30 / Change each span their column group.
        {'mergeCells': {'range': _range(sheet_id, 0, 2, 0, 1), 'mergeType': 'MERGE_ALL'}},
        {'mergeCells': {'range': _range(sheet_id, 0, 2, 1, 2), 'mergeType': 'MERGE_ALL'}},
        {'mergeCells': {'range': _range(sheet_id, 0, 1, 2, 9), 'mergeType': 'MERGE_ALL'}},
        {'mergeCells': {'range': _range(sheet_id, 0, 1, 9, 16), 'mergeType': 'MERGE_ALL'}},
        {'mergeCells': {'range': _range(sheet_id, 0, 1, 16, 18), 'mergeType': 'MERGE_ALL'}},
        # Header rows: bold + grey, both rows, full comparison-table width.
        {'repeatCell': {'range': _range(sheet_id, 0, 2, 0, N_COMPARISON_COLS),
                         'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': HEADER_GREY,
                                                         'horizontalAlignment': 'CENTER'}},
                         'fields': 'userEnteredFormat(textFormat,backgroundColor,horizontalAlignment)'}},
    ]

    # ---- Comparison table (Last 30 | Previous 30 | Change) ----
    reqs.append({'repeatCell': {'range': _range(sheet_id, cmp_start, cmp_end, 6, 7),
                                 'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}},
                                 'fields': 'userEnteredFormat.textFormat'}})  # Last-30 CPBC bold
    reqs.append({'repeatCell': {'range': _range(sheet_id, cmp_start, cmp_end, 13, 14),
                                 'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}},
                                 'fields': 'userEnteredFormat.textFormat'}})  # Previous-30 CPBC bold
    reqs.append({'repeatCell': {'range': _range(sheet_id, cmp_total, cmp_total + 1, 0, N_COMPARISON_COLS),
                                 'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}},
                                 'fields': 'userEnteredFormat.textFormat'}})  # TOTAL row bold
    for col in (2, 4, 6, 8, 9, 11, 13, 15, 16, 17):  # currency: spend/CPL/CPBC/CostPerShow x2 periods + deltas
        reqs.append({'repeatCell': {'range': _range(sheet_id, cmp_start, cmp_end, col, col + 1),
                                     'cell': {'userEnteredFormat': {'numberFormat': {'type': 'CURRENCY', 'pattern': '"$"#,##0'}}},
                                     'fields': 'userEnteredFormat.numberFormat'}})
    for col in (3, 5, 7, 10, 12, 14):  # integer: leads/booked/shows x2 periods
        reqs.append({'repeatCell': {'range': _range(sheet_id, cmp_start, cmp_end, col, col + 1),
                                     'cell': {'userEnteredFormat': {'numberFormat': {'type': 'NUMBER', 'pattern': '0'}}},
                                     'fields': 'userEnteredFormat.numberFormat'}})

    # ---- Last 7 Days block ----
    reqs.append({'repeatCell': {'range': _range(sheet_id, caption_row, caption_row + 1, 0, 1),
                                 'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}},
                                 'fields': 'userEnteredFormat.textFormat'}})
    reqs.append({'repeatCell': {'range': _range(sheet_id, l7_header, l7_header + 1, 0, N_LAST7_COLS),
                                 'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': HEADER_GREY}},
                                 'fields': 'userEnteredFormat(textFormat,backgroundColor)'}})
    reqs.append({'repeatCell': {'range': _range(sheet_id, l7_start, l7_end, 6, 7),
                                 'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}},
                                 'fields': 'userEnteredFormat.textFormat'}})  # CPBC bold
    reqs.append({'repeatCell': {'range': _range(sheet_id, l7_total, l7_total + 1, 0, N_LAST7_COLS),
                                 'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}},
                                 'fields': 'userEnteredFormat.textFormat'}})  # TOTAL row bold
    for col in (2, 4, 6, 8):
        reqs.append({'repeatCell': {'range': _range(sheet_id, l7_start, l7_end, col, col + 1),
                                     'cell': {'userEnteredFormat': {'numberFormat': {'type': 'CURRENCY', 'pattern': '"$"#,##0'}}},
                                     'fields': 'userEnteredFormat.numberFormat'}})
    for col in (3, 5, 7):
        reqs.append({'repeatCell': {'range': _range(sheet_id, l7_start, l7_end, col, col + 1),
                                     'cell': {'userEnteredFormat': {'numberFormat': {'type': 'NUMBER', 'pattern': '0'}}},
                                     'fields': 'userEnteredFormat.numberFormat'}})

    # ---- Per-row conditional coloring: Status green/red, plus Cost per
    # Lead / Cost per Booked Call / Cost per Show green/yellow/red, each by
    # its own threshold. ----
    def color_rows(row_range, status_col, cost_col_thresholds):
        for r0 in row_range:
            row = all_rows[r0]
            if not row or row[0] == '':
                continue  # spacer row
            status = row[status_col] if len(row) > status_col else ''
            if status == 'Active':
                reqs.append(_cell_fill(sheet_id, r0, status_col, STATUS_GREEN))
            elif 'Paused' in status:
                reqs.append(_cell_fill(sheet_id, r0, status_col, STATUS_RED))
            for col, good_max, warn_max in cost_col_thresholds:
                val = row[col] if len(row) > col else ''
                color, text_color = _cost_color(val, good_max, warn_max)
                if color:
                    reqs.append(_cell_fill(sheet_id, r0, col, color, text_color))

    # Column layout: 4/11 = CPL (Last/Prev), 6/13 = CPBC (Last/Prev), 8/15 = CPS (Last/Prev).
    color_rows(range(cmp_start, cmp_end), 1, [
        (4, CPL_GOOD_MAX, CPL_WARN_MAX), (11, CPL_GOOD_MAX, CPL_WARN_MAX),
        (6, CPBC_GOOD_MAX, CPBC_WARN_MAX), (13, CPBC_GOOD_MAX, CPBC_WARN_MAX),
        (8, CPS_GOOD_MAX, CPS_WARN_MAX), (15, CPS_GOOD_MAX, CPS_WARN_MAX),
    ])
    color_rows(range(l7_start, l7_end), 1, [
        (4, CPL_GOOD_MAX, CPL_WARN_MAX),
        (6, CPBC_GOOD_MAX, CPBC_WARN_MAX),
        (8, CPS_GOOD_MAX, CPS_WARN_MAX),
    ])

    # "Go shut it off" flag: an ad set that's burned >= 2x the CPL green
    # cutoff with literally zero leads has no computable CPL (division by
    # zero leads), so the per-column coloring above leaves it blank — the
    # worst-performing ad sets would otherwise show no color at all. Paint
    # just the CPL and CPBC cells dark red instead (not the whole metric
    # block — Spend/Leads/Booked/Shows/CPS should stay uncolored).
    def flag_dead_spend(row_range, spend_col, leads_col, cpl_col, cpbc_col):
        for r0 in row_range:
            row = all_rows[r0]
            if not row or row[0] in ('', 'TOTAL', UNATTRIBUTED_LABEL):
                continue
            spend = row[spend_col] if len(row) > spend_col else ''
            leads = row[leads_col] if len(row) > leads_col else ''
            if (isinstance(spend, (int, float)) and isinstance(leads, (int, float))
                    and leads == 0 and spend >= CPL_GOOD_MAX * 2):
                for col in (cpl_col, cpbc_col):
                    reqs.append(_cell_fill(sheet_id, r0, col, COST_DARK_RED, COST_DARK_RED_TEXT))

    flag_dead_spend(range(cmp_start, cmp_end), 2, 3, 4, 6)     # Last-30 block: CPL col 4, CPBC col 6
    flag_dead_spend(range(cmp_start, cmp_end), 9, 10, 11, 13)  # Previous-30 block: CPL col 11, CPBC col 13
    flag_dead_spend(range(l7_start, l7_end), 2, 3, 4, 6)       # Last 7 Days: CPL col 4, CPBC col 6

    # Compact sizing: fixed (narrow) column widths instead of auto-resize —
    # short abbreviated headers mean the data no longer needs wide columns —
    # plus a smaller font and tighter row height so the whole table fits on
    # one screen without side-scrolling. Ad Set text is clipped (not
    # wrapped) so a long ad-set name can't blow out the row height.
    col_widths = [190, 95, 62, 44, 54, 56, 58, 48, 52,
                  62, 44, 54, 56, 58, 48, 52, 58, 58]
    for i, width in enumerate(col_widths):
        reqs.append({'updateDimensionProperties': {
            'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': i, 'endIndex': i + 1},
            'properties': {'pixelSize': width}, 'fields': 'pixelSize'}})
    reqs.append({'updateDimensionProperties': {
        'range': {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': 0, 'endIndex': n_rows},
        'properties': {'pixelSize': 18}, 'fields': 'pixelSize'}})
    reqs.append({'repeatCell': {'range': _range(sheet_id, 0, n_rows, 0, N_COMPARISON_COLS),
                                 'cell': {'userEnteredFormat': {'wrapStrategy': 'CLIP'}},
                                 'fields': 'userEnteredFormat.wrapStrategy'}})
    # Global font size, applied last so its granular field mask (fontSize
    # only) layers on top of the bold/background requests above instead of
    # being wiped by their coarser 'userEnteredFormat.textFormat' masks.
    reqs.append({'repeatCell': {'range': _range(sheet_id, 0, n_rows, 0, N_COMPARISON_COLS),
                                 'cell': {'userEnteredFormat': {'textFormat': {'fontSize': 8}}},
                                 'fields': 'userEnteredFormat.textFormat.fontSize'}})

    sheets_batch_update(access_token, FULLYSCALE_SHEET_ID, reqs)


def main():
    access_token = refresh_google_token()
    meta_token, account_id = get_meta_credentials(access_token)
    ghl_key, _ = load_ghl_env()

    today = datetime.date.today()
    last30_start = today - datetime.timedelta(days=30)
    prev30_start = today - datetime.timedelta(days=60)
    prev30_end = last30_start - datetime.timedelta(days=1)
    last7_start = today - datetime.timedelta(days=LAST7_DAYS)

    widest_start = prev30_start
    all_leads = read_meta_leads(access_token, widest_start)
    print(f'Meta Ads leads in Lead Log since {widest_start}: {len(all_leads)}')

    lead_adset_map = {}
    for lead in all_leads:
        lead_adset_map[lead['lead_id']] = ghl_get_contact_adset_id(ghl_key, lead['lead_id'])
    matched = sum(1 for v in lead_adset_map.values() if v)
    print(f'Ad-set attribution matched: {matched}/{len(all_leads)}')
    if len(all_leads) >= 5 and matched == 0:
        # A real ~25-33% unattributed rate is expected (multi-touch leads).
        # Zero matches on a non-trivial batch means the GHL API call itself is
        # broken (bad token, blocked request, etc.), not real attribution gaps.
        # Refuse to overwrite a good tab with a falsely-all-unattributed one.
        raise RuntimeError(
            f'GHL attribution lookup returned 0/{len(all_leads)} matches — '
            'this almost certainly means the GHL API call is failing (bad '
            'token/blocked request), not that attribution is genuinely zero. '
            'Skipping the sheet write.')

    adset_status = fetch_adset_statuses(meta_token, account_id)

    last30_spend = fetch_meta_adset_spend(meta_token, account_id, date_preset='last_30d')
    prev30_spend = fetch_meta_adset_spend(
        meta_token, account_id,
        time_range={'since': prev30_start.isoformat(), 'until': prev30_end.isoformat()})
    last7_spend = fetch_meta_adset_spend(meta_token, account_id, date_preset='last_7d')

    last30_leads = [l for l in all_leads if l['date_in'] >= last30_start]
    prev30_leads = [l for l in all_leads if prev30_start <= l['date_in'] < last30_start]
    last7_leads = [l for l in all_leads if l['date_in'] >= last7_start]

    last30_agg, last30_unattr = aggregate_window(last30_leads, last30_spend, lead_adset_map)
    prev30_agg, prev30_unattr = aggregate_window(prev30_leads, prev30_spend, lead_adset_map)
    last7_agg, last7_unattr = aggregate_window(last7_leads, last7_spend, lead_adset_map)

    prev_label = f'{prev30_start:%b %-d}–{prev30_end:%b %-d}'
    last_label = f'{last30_start:%b %-d}–{today:%b %-d}'
    last7_label = f'{last7_start:%b %-d}–{today:%b %-d}'

    header_row0 = ['Ad Set', 'Status',
                   f'LAST 30 ({last_label})', '', '', '', '', '', '',
                   f'PREV 30 ({prev_label})', '', '', '', '', '', '',
                   'CHANGE', '']
    header_row1 = ['', '',
                   'Spend', 'Leads', 'CPL', 'Booked', 'CPBC', 'Shows', 'CPS',
                   'Spend', 'Leads', 'CPL', 'Booked', 'CPBC', 'Shows', 'CPS',
                   'CPL Δ', 'CPBC Δ']

    comparison_rows = build_comparison_table(prev30_agg, prev30_unattr, last30_agg, last30_unattr, adset_status)
    total_row = comparison_rows[-1]
    print(f'Last 30 Days ({last_label}): spend=${total_row[2]}, leads={total_row[3]}, '
          f'booked={total_row[5]}, shows={total_row[7]}')
    print(f'Previous 30 Days ({prev_label}): spend=${total_row[9]}, leads={total_row[10]}, '
          f'booked={total_row[12]}, shows={total_row[14]}')

    all_rows = [header_row0, header_row1]
    all_rows.extend(comparison_rows)
    cmp_start, cmp_end = 2, len(all_rows)
    cmp_total = cmp_end - 1

    all_rows.append([''] * N_COMPARISON_COLS)  # spacer

    caption_row = len(all_rows)
    all_rows.append([f'Last 7 Days ({last7_label})'])

    l7_header = len(all_rows)
    all_rows.append(['Ad Set', 'Status', 'Spend', 'Leads', 'CPL', 'Booked', 'CPBC', 'Shows', 'CPS'])

    last7_rows = finalize_block_rows(last7_agg, last7_unattr, adset_status)
    last7_table = render_single_block(last7_rows)
    l7_start = len(all_rows)
    all_rows.extend(last7_table)
    l7_end = len(all_rows)
    l7_total = l7_end - 1
    print(f'Last 7 Days: spend=${last7_table[-1][2]}, leads={last7_table[-1][3]}, '
          f'booked={last7_table[-1][5]}, shows={last7_table[-1][7]}')

    sheet_id = ensure_tab_exists(access_token, FULLYSCALE_SHEET_ID, OVERVIEW_TAB)
    sheets_values_clear(access_token, FULLYSCALE_SHEET_ID, f"'{OVERVIEW_TAB}'!A1:R500")
    sheets_values_update(access_token, FULLYSCALE_SHEET_ID, f"'{OVERVIEW_TAB}'!A1", all_rows)
    apply_formatting(access_token, sheet_id, all_rows,
                      (cmp_start, cmp_end, cmp_total),
                      (caption_row, l7_header, l7_start, l7_end, l7_total),
                      prev_label, last_label)
    print(f'Wrote {len(all_rows)} rows to "{OVERVIEW_TAB}".')


def notify_mac(message):
    import subprocess
    script = f'display notification {json.dumps(message)} with title "Ad Set Overview Refresh" sound name "Basso"'
    subprocess.run(['osascript', '-e', script], check=False)


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as e:
        msg = f'META_TOKEN_ERROR: {e}'
        print(msg, file=sys.stderr)
        notify_mac('Ad Set Overview refresh failed — check the Meta token (Config tab) or GHL API access. Tab was not overwritten.')
        sys.exit(2)
