/**
 * FullyScale — nightly QA sentinel for the Lead Log + Call Attempts tabs.
 * Bound to spreadsheet 14g75lx2ZxG-pSE0bPkAsZ433s4Ay88wL0L5A8lzXZUA ("Fullyscale Tracking (Active)").
 *
 * Built after two manual "SOP fix CRM and Lead Log" audits (Sept 11 and Sept 19, 2026)
 * turned up the same categories of errors on largely the same leads. The underlying
 * process (per "Daily Call List after Logan called...") is fully manual — update GHL,
 * separately Cmd-F the sheet and hand-insert a row, separately update the Opportunity
 * stage — with no cross-check between the three. This script is the cross-check: it
 * doesn't fix data (never auto-edits a lead's data), it flags exactly the failure
 * patterns that keep recurring so they get caught same-day instead of a week+ later.
 *
 * runQaSentinel(): scans both tabs, writes findings to a "QA Flags" tab (rebuilt each
 * run), and emails a summary if anything is found.
 * setupQaTrigger(): run once to install the daily time-based trigger. Safe to re-run.
 *
 * CONFIG below has the tab/header names as best confirmed from the live sheet. If a
 * column isn't found (name drifted), the script logs a CONFIG WARNING row instead of
 * failing silently or crashing — check the QA Flags tab first if results look empty.
 */

var CONFIG = {
  LEAD_LOG_TAB: 'Lead Log',
  CALL_TAB_CANDIDATES: ['Call Attempts', 'Call Attempt List', 'Call Log'],
  QA_TAB: 'QA Flags',
  ALERT_EMAIL: 'crazyscooter1010@gmail.com',
  // Lead Log headers, confirmed from the live sheet.
  LEAD_LOG_COLS: {
    leadId: 'Lead ID',
    name: 'Name',
    dateIn: 'Date In',
    firstTouchDate: 'First-Touch Date',
    timeToFirstTouch: 'Time to First Touch (hrs)',
    engagementDate: 'Engagement Date',
    bookingDate: 'Booking Date',
    scheduledCallDate: 'Scheduled Call Date',
    showed: 'Showed?',
    showDate: 'Show Date',
    offerMade: 'Offer Made?',
    closed: 'Closed?',
    closeDate: 'Close Date'
  },
  // Call Attempts headers, confirmed 2026-09-20 against the live tab. Note: the
  // attempt-code column (e.g. "A-001") has no header text at all — it's always
  // column A — so it's handled by fixed position in findCallAttemptIssues, not by
  // name lookup here.
  CALL_TAB_COLS: {
    leadId: 'Lead ID',
    date: 'Attempt Date',
    attemptNum: 'Attempt #',
    channel: 'Channel',
    outcome: 'Outcome'
  }
};

function runQaSentinel() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var flags = [];

  var leadLogSheet = ss.getSheetByName(CONFIG.LEAD_LOG_TAB);
  if (leadLogSheet) {
    flags = flags.concat(findLeadLogIssues(leadLogSheet));
  } else {
    flags.push(configWarning('Lead Log tab "' + CONFIG.LEAD_LOG_TAB + '" not found.'));
  }

  var callSheet = findCallTab(ss);
  if (callSheet) {
    flags = flags.concat(findCallAttemptIssues(callSheet));
  } else {
    flags.push(configWarning('No Call Attempts tab found among: ' + CONFIG.CALL_TAB_CANDIDATES.join(', ')));
  }

  writeFlags(ss, flags);
  maybeEmailSummary(flags);
  Logger.log('QA sentinel run complete: ' + flags.length + ' flag(s).');
}

function findCallTab(ss) {
  for (var i = 0; i < CONFIG.CALL_TAB_CANDIDATES.length; i++) {
    var sheet = ss.getSheetByName(CONFIG.CALL_TAB_CANDIDATES[i]);
    if (sheet) return sheet;
  }
  return null;
}

function configWarning(message) {
  return { tab: 'CONFIG', row: '-', leadId: '-', name: '-', issue: 'CONFIG WARNING', detail: message };
}

function colIndex(headerRow, name) {
  for (var i = 0; i < headerRow.length; i++) {
    if (String(headerRow[i]).trim().toLowerCase() === name.trim().toLowerCase()) return i;
  }
  return -1;
}

function isYes(value) {
  var v = String(value).trim().toLowerCase();
  return v === 'y' || v === 'yes' || v === 'true';
}

function findLeadLogIssues(sheet) {
  var flags = [];
  var values = sheet.getDataRange().getValues();
  if (values.length < 2) return flags;
  var header = values[0];
  var c = {};
  for (var key in CONFIG.LEAD_LOG_COLS) {
    c[key] = colIndex(header, CONFIG.LEAD_LOG_COLS[key]);
    if (c[key] === -1) flags.push(configWarning('Lead Log column "' + CONFIG.LEAD_LOG_COLS[key] + '" not found.'));
  }

  var seenLeadIds = {};
  var dateCols = ['firstTouchDate', 'engagementDate', 'bookingDate', 'scheduledCallDate', 'showDate', 'closeDate'];

  for (var r = 1; r < values.length; r++) {
    var row = values[r];
    var rowNum = r + 1;
    var name = c.name >= 0 ? row[c.name] : '';
    var leadId = c.leadId >= 0 ? row[c.leadId] : '';

    if (!name && !leadId) continue; // blank trailing row

    if (name && /test/i.test(name)) {
      flags.push(flag(sheet, rowNum, leadId, name, 'Test/junk row', 'Name contains "test" — looks like leftover test data in a live range.'));
    }

    if (!name) {
      flags.push(flag(sheet, rowNum, leadId, name, 'Missing name', 'Row has a Lead ID but no Name.'));
    }

    if (leadId) {
      if (seenLeadIds[leadId]) {
        flags.push(flag(sheet, rowNum, leadId, name, 'Duplicate Lead ID', 'Also appears on row ' + seenLeadIds[leadId] + '.'));
      } else {
        seenLeadIds[leadId] = rowNum;
      }
    }

    dateCols.forEach(function (key) {
      var idx = c[key];
      if (idx === -1) return;
      var v = row[idx];
      if (typeof v === 'number' && v > 20000 && v < 80000) {
        flags.push(flag(sheet, rowNum, leadId, name, 'Raw serial date', CONFIG.LEAD_LOG_COLS[key] + ' = ' + v + ' — stored as a number, not a formatted date. Reformat the cell as Date and re-enter.'));
      }
    });

    if (c.showed >= 0 && isYes(row[c.showed])) {
      if (c.offerMade >= 0 && !row[c.offerMade]) {
        flags.push(flag(sheet, rowNum, leadId, name, 'Showed but no Offer Made value', 'Showed? = Y but Offer Made? is blank — post-call step never completed.'));
      }
      if (c.bookingDate >= 0 && !row[c.bookingDate]) {
        flags.push(flag(sheet, rowNum, leadId, name, 'Showed but no Booking Date', 'Showed? = Y but Booking Date is blank.'));
      }
    }
  }

  return flags;
}

function findCallAttemptIssues(sheet) {
  var flags = [];
  var values = sheet.getDataRange().getValues();
  if (values.length < 2) return flags;
  var header = values[0];
  var c = {};
  for (var key in CONFIG.CALL_TAB_COLS) {
    c[key] = colIndex(header, CONFIG.CALL_TAB_COLS[key]);
    if (c[key] === -1) flags.push(configWarning('Call Attempts column "' + CONFIG.CALL_TAB_COLS[key] + '" not found.'));
  }
  c.code = 0; // attempt-code column (e.g. "A-001") is always column A; it has no header text to match by name
  if (c.leadId === -1 || c.date === -1) return flags; // can't do anything useful without these

  var seenCodes = {};
  var byLead = {}; // leadId -> [{row, date, channel}]

  for (var r = 1; r < values.length; r++) {
    var row = values[r];
    var rowNum = r + 1;
    var leadId = row[c.leadId];
    if (!leadId) continue;

    if (c.code >= 0 && row[c.code]) {
      var code = String(row[c.code]).trim();
      if (seenCodes[code]) {
        flags.push(flag(sheet, rowNum, leadId, '', 'Duplicate attempt code', 'Code "' + code + '" also on row ' + seenCodes[code] + ' — likely a copy-paste instead of a new incremented row.'));
      } else {
        seenCodes[code] = rowNum;
      }
    }

    if (c.outcome >= 0 && !row[c.outcome]) {
      flags.push(flag(sheet, rowNum, leadId, '', 'Missing outcome', 'Attempt row has no Outcome recorded.'));
    }

    var dateVal = row[c.date];
    var dateOnly = dateVal instanceof Date
      ? Utilities.formatDate(dateVal, sheet.getParent().getSpreadsheetTimeZone(), 'yyyy-MM-dd')
      : String(dateVal);

    if (!byLead[leadId]) byLead[leadId] = [];
    byLead[leadId].push({ row: rowNum, date: dateOnly, channel: c.channel >= 0 ? row[c.channel] : '' });
  }

  for (var lid in byLead) {
    var attempts = byLead[lid];
    var byDate = {};
    attempts.forEach(function (a) {
      byDate[a.date] = byDate[a.date] || [];
      byDate[a.date].push(a);
    });
    for (var d in byDate) {
      if (byDate[d].length > 1) {
        var channels = byDate[d].map(function (a) { return a.channel; }).join(' + ');
        var rows = byDate[d].map(function (a) { return a.row; }).join(', ');
        flags.push(flag(sheet, rows, lid, '', 'Possible double-counted attempt', d + ': ' + byDate[d].length + ' attempt rows same day (' + channels + '). Verify this wasn\'t one real touch (e.g. call + follow-up text) logged twice by the auto-attempt workflow.'));
      }
    }
  }

  return flags;
}

function flag(sheet, row, leadId, name, issue, detail) {
  return { tab: sheet.getName(), row: row, leadId: leadId, name: name, issue: issue, detail: detail };
}

function writeFlags(ss, flags) {
  var qaSheet = ss.getSheetByName(CONFIG.QA_TAB);
  if (!qaSheet) qaSheet = ss.insertSheet(CONFIG.QA_TAB);
  qaSheet.clear();

  var tz = ss.getSpreadsheetTimeZone();
  var stamp = Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd HH:mm');
  var out = [['Run: ' + stamp, '', '', '', '', '']];
  out.push(['Tab', 'Row', 'Lead ID', 'Name', 'Issue', 'Detail']);
  flags.forEach(function (f) {
    out.push([f.tab, f.row, f.leadId, f.name, f.issue, f.detail]);
  });
  if (flags.length === 0) out.push(['—', '—', '—', '—', 'No issues found', '']);

  qaSheet.getRange(1, 1, out.length, 6).setValues(out);
  qaSheet.getRange(2, 1, 1, 6).setFontWeight('bold');
}

function maybeEmailSummary(flags) {
  if (!CONFIG.ALERT_EMAIL || flags.length === 0) return;
  var byIssue = {};
  flags.forEach(function (f) {
    byIssue[f.issue] = (byIssue[f.issue] || 0) + 1;
  });
  var lines = Object.keys(byIssue).map(function (k) { return '- ' + k + ': ' + byIssue[k]; });
  var body = flags.length + ' QA flag(s) found in the Fullyscale Tracking sheet.\n\n'
    + lines.join('\n')
    + '\n\nFull detail in the "QA Flags" tab.';
  MailApp.sendEmail(CONFIG.ALERT_EMAIL, 'FullyScale sheet QA: ' + flags.length + ' flag(s)', body);
}

function setupQaTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'runQaSentinel') {
      Logger.log('Trigger already exists — not creating a duplicate.');
      return;
    }
  }
  ScriptApp.newTrigger('runQaSentinel')
    .timeBased()
    .everyDays(1)
    .atHour(7)
    .create();
  Logger.log('Daily QA trigger installed: runs every day around 7am.');
}
