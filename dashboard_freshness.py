#!/usr/bin/env python3
"""Dashboard freshness probe for the FullyScale Weekly Performance Dashboard.

Answers one question the dashboard itself cannot: how old is the data BEHIND
each number? The daily refresh keeps relabelling Live Meta / Ad Set Overview as
"T30 (<30 days ago>-<today>)" even when the underlying Meta Raw rows stopped
days earlier, so a frozen feed looks current and the CPLs/CPBCs just quietly
read low. (That is exactly what happened 2026-08-30 -> 2026-09-07: the Meta
token was invalidated, every Meta number froze, and nothing on the dashboard
said so.)

Checks each feed's TRUE data-through date, checks the credential each feed
depends on, and stamps the verdict onto Weekly Dashboard!A11 so the staleness
is visible where the numbers are read. Prints a STATUS: line per feed for the
scheduled job to act on.

Exit code is always 0 unless the probe itself broke — "data is stale" is a
finding to report, not a crash. Use --no-stamp to probe without writing.

Uses stdlib only, and the Google/Sheets helpers already proven in
weekly_meta_inputs.py.
"""
import argparse
import datetime
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

_spec = importlib.util.spec_from_file_location('wmi', os.path.join(HERE, 'weekly_meta_inputs.py'))
wmi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wmi)

FULLYSCALE_SHEET_ID = wmi.FULLYSCALE_SHEET_ID
ANALYTICS_SHEET_ID = wmi.ANALYTICS_SHEET_ID
DASHBOARD_TAB = 'Weekly Dashboard'
STAMP_CELL = 'A11'          # empty spacer row directly above the metric table
SHEET_EPOCH = datetime.date(1899, 12, 30)

# A feed is only "stale" once it is later than this many days behind. Meta and
# GHL land daily; the QBO P&L and the weekly Meta rows are weekly jobs, so they
# are allowed to be a week old before anyone should care.
TOLERANCE_DAYS = {
    'meta_raw': 2,
    'ghl_raw': 2,
    'live_meta': 2,
    'weekly_inputs': 9,   # staleness is decided by missing weeks, not age
    'qbo_pnl': 6,         # weekly job: a single missed Monday must show up
}


def to_date(value):
    """Sheets hands back either an ISO-ish string or a serial number."""
    s = str(value).strip()
    if not s:
        return None
    if s.replace('.', '', 1).isdigit():
        return SHEET_EPOCH + datetime.timedelta(days=int(float(s)))
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y'):
        try:
            return datetime.datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


def max_date_in_column(token, sheet_id, rng):
    rows = wmi.sheets_get(token, sheet_id, rng)
    dates = [to_date(r[0]) for r in rows if r and str(r[0]).strip()]
    dates = [d for d in dates if d]
    return max(dates) if dates else None


def check_meta_token(token):
    """Returns (ok, detail). The single credential every Meta feed depends on."""
    try:
        meta_token, account_id = wmi.get_meta_credentials(token)
    except Exception as exc:                                    # noqa: BLE001
        return False, f'could not read Config tab: {exc}'
    if not meta_token:
        return False, 'Config!B2 is empty'
    url = 'https://graph.facebook.com/v21.0/me?access_token=' + urllib.parse.quote(meta_token)
    try:
        urllib.request.urlopen(url, timeout=20).read()
        return True, f'valid (acct {account_id})'
    except urllib.error.HTTPError as exc:
        try:
            msg = json.loads(exc.read())['error'].get('message', '')
        except Exception:                                       # noqa: BLE001
            msg = f'HTTP {exc.code}'
        return False, msg
    except Exception as exc:                                    # noqa: BLE001
        return False, str(exc)


def weeks_missing(last_week_start, today):
    """Full 7-day buckets that have closed since the last row was written."""
    if not last_week_start:
        return 0
    n, cursor = 0, last_week_start + datetime.timedelta(days=7)
    while cursor + datetime.timedelta(days=6) <= today:
        n += 1
        cursor += datetime.timedelta(days=7)
    return n


def probe(token, today):
    feeds = {}

    # --- Meta daily rows: feeds Ad Set Overview + Live Meta T30/T90 ---
    meta_through = max_date_in_column(token, ANALYTICS_SHEET_ID, "'Meta Raw'!B2:B50000")
    feeds['meta_raw'] = {
        'label': 'Meta Raw (daily ad data -> Ad Set Overview, Live Meta)',
        'through': meta_through,
    }

    # --- GHL leads: feeds Lead Log and everything downstream of it ---
    ghl_through = max_date_in_column(token, ANALYTICS_SHEET_ID, "'GHL Raw'!F2:F50000")
    feeds['ghl_raw'] = {
        'label': 'GHL Raw (leads -> Lead Log, funnel, source scorecard)',
        'through': ghl_through,
    }

    # --- Weekly Inputs: the weekly Meta rows behind This Week / Last Week ---
    rows = wmi.sheets_get(token, FULLYSCALE_SHEET_ID, "'Weekly Inputs'!A1:H2000")
    starts = [to_date(r[0]) for r in rows[1:]
              if len(r) > 1 and r[1] == wmi.CHANNEL and str(r[0]).strip()]
    starts = [d for d in starts if d]
    last_start = max(starts) if starts else None
    missing = weeks_missing(last_start, today)
    feeds['weekly_inputs'] = {
        'label': 'Weekly Inputs (weekly Meta rows -> This Week / Last Week columns)',
        'through': (last_start + datetime.timedelta(days=6)) if last_start else None,
        'missing_weeks': missing,
        'extra': f'{missing} closed week(s) not yet written',
    }

    # --- Live Meta stamp: proves the daily refresh ran, NOT that data moved ---
    live = wmi.sheets_get(token, FULLYSCALE_SHEET_ID, "'Live Meta'!A2:C2")
    live_run = None
    if live and len(live[0]) > 1:
        live_run = to_date(str(live[0][1])[:10])
    feeds['live_meta'] = {
        'label': 'Live Meta (refresh job last ran)',
        'through': live_run,
        'extra': 'job ran, but its window is only as good as Meta Raw above',
    }

    # --- QBO P&L ---
    pnl = wmi.sheets_get(token, FULLYSCALE_SHEET_ID, "'P&L Actuals (QBO)'!A2:C2")
    pnl_synced = to_date(pnl[0][1]) if pnl and len(pnl[0]) > 1 else None
    hdr = wmi.sheets_get(token, FULLYSCALE_SHEET_ID, "'P&L Actuals (QBO)'!A4:Z4")
    latest_month = hdr[0][-1] if hdr and hdr[0] else '?'
    feeds['qbo_pnl'] = {
        'label': 'P&L Actuals (QBO)',
        'through': pnl_synced,
        'extra': f'latest column: {latest_month}',
    }

    for key, feed in feeds.items():
        through = feed['through']
        feed['age'] = (today - through).days if through else None
        # The weekly rows sit on drifting 7-day buckets, so plain age gives
        # false alarms — a perfectly current tab can still end 7 days ago.
        # Whether a CLOSED week is missing is the exact signal.
        if key == 'weekly_inputs':
            feed['stale'] = through is None or feed['missing_weeks'] > 0
        else:
            feed['stale'] = through is None or feed['age'] > TOLERANCE_DAYS[key]
    return feeds


def build_stamp(feeds, token_ok, token_detail, today):
    stale = [f for f in feeds.values() if f['stale']]
    if not stale and token_ok:
        return (f"✓ Data verified {today:%-m/%-d}: Meta through "
                f"{feeds['meta_raw']['through']:%-m/%-d}, leads through "
                f"{feeds['ghl_raw']['through']:%-m/%-d}, P&L synced "
                f"{feeds['qbo_pnl']['through']:%-m/%-d}.")
    parts = []
    meta = feeds['meta_raw']
    if meta['stale']:
        parts.append(f"Meta data ends {meta['through']:%-m/%-d} ({meta['age']}d stale) "
                     f"— T30/T90, CPL, CPBC and spend are UNDERSTATED")
    if feeds['ghl_raw']['stale']:
        parts.append(f"leads end {feeds['ghl_raw']['through']:%-m/%-d}")
    if feeds['weekly_inputs']['stale']:
        parts.append(f"weekly Meta rows: {feeds['weekly_inputs']['extra']}")
    if feeds['qbo_pnl']['stale']:
        parts.append(f"P&L last synced {feeds['qbo_pnl']['through']:%-m/%-d}")
    if not token_ok:
        parts.append(f"Meta token DEAD ({token_detail[:60]}) — refresh Config!B2 "
                     f"in the ad-analytics sheet")
    return f"⚠ Checked {today:%-m/%-d}: " + '; '.join(parts) + '.'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-stamp', action='store_true',
                    help='probe and report without writing to the dashboard')
    args = ap.parse_args()

    token = wmi.refresh_google_token()
    today = datetime.date.today()

    token_ok, token_detail = check_meta_token(token)
    feeds = probe(token, today)

    print(f'FRESHNESS PROBE {today}')
    print(f'STATUS: meta_token {"OK" if token_ok else "DEAD"} | {token_detail}')
    for key, feed in feeds.items():
        through = feed['through'].isoformat() if feed['through'] else 'UNKNOWN'
        flag = 'STALE' if feed['stale'] else 'OK'
        extra = f" | {feed['extra']}" if feed.get('extra') else ''
        print(f"STATUS: {key} {flag} | through {through} "
              f"({feed['age']}d) | {feed['label']}{extra}")

    stamp = build_stamp(feeds, token_ok, token_detail, today)
    print(f'STAMP: {stamp}')
    if not args.no_stamp:
        wmi.sheets_values_update(token, FULLYSCALE_SHEET_ID,
                                 f"'{DASHBOARD_TAB}'!{STAMP_CELL}", [[stamp]])
        print(f'Wrote stamp to {DASHBOARD_TAB}!{STAMP_CELL}')

    blocked = [k for k, f in feeds.items() if f['stale']]
    print(f'SUMMARY: {"all feeds current" if not blocked and token_ok else "stale: " + ", ".join(blocked) or "stale: -"}'
          f'{"" if token_ok else " | meta token needs refresh"}')


if __name__ == '__main__':
    sys.exit(main())
