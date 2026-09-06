/**
 * FullyScale — automatic monthly snapshot.
 * Bound to spreadsheet 14g75lx2ZxG-pSE0bPkAsZ433s4Ay88wL0L5A8lzXZUA.
 *
 * createMonthlySnapshot(): on the 1st of each month, combines values-only
 * copies of Weekly Dashboard + Funnel Summary + Ad Set Overview from the
 * PRIOR month into one new "Snapshot - <Month> <Year>" tab. Idempotent —
 * skips if that month's tab already exists.
 *
 * setupMonthlyTrigger(): run once to install the time-driven trigger
 * (1st of month, ~6am spreadsheet timezone). Safe to re-run — won't
 * create a duplicate trigger.
 */

var SOURCE_TABS = ['Weekly Dashboard', 'Funnel Summary', 'Ad Set Overview'];

function createMonthlySnapshot() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var tz = ss.getSpreadsheetTimeZone();
  var now = new Date();
  var lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  var monthName = Utilities.formatDate(lastMonth, tz, 'MMMM');
  var year = lastMonth.getFullYear();
  var tabName = 'Snapshot - ' + monthName + ' ' + year;

  if (ss.getSheetByName(tabName)) {
    Logger.log(tabName + ' already exists — skipping.');
    return;
  }

  var combined = [];
  var today = Utilities.formatDate(now, tz, 'yyyy-MM-dd');
  combined.push(['Snapshot captured automatically on ' + today + ' for ' + monthName + ' ' + year + '.']);
  combined.push([]);

  SOURCE_TABS.forEach(function (name) {
    var sheet = ss.getSheetByName(name);
    if (!sheet) return;
    var values = sheet.getDataRange().getValues();
    var width = 1;
    values.forEach(function (r) { width = Math.max(width, r.length); });
    var header = new Array(width).fill('');
    header[0] = '— ' + name.toUpperCase() + ' —'; // em dash, not "=", to avoid formula parsing
    combined.push(header);
    values.forEach(function (row) { combined.push(row); });
    combined.push([]);
    combined.push([]);
  });

  // insert right after the most recent existing "Snapshot - " tab
  var allSheets = ss.getSheets();
  var insertIndex = allSheets.length;
  for (var i = allSheets.length - 1; i >= 0; i--) {
    if (allSheets[i].getName().indexOf('Snapshot - ') === 0) {
      insertIndex = allSheets[i].getIndex();
      break;
    }
  }

  var maxCols = 1;
  combined.forEach(function (r) { maxCols = Math.max(maxCols, r.length); });
  var padded = combined.map(function (r) {
    var row = r.slice();
    while (row.length < maxCols) row.push('');
    return row;
  });

  var newSheet = ss.insertSheet(tabName, insertIndex);
  newSheet.getRange(1, 1, padded.length, maxCols).setValues(padded);
  Logger.log('Created ' + tabName + ' with ' + padded.length + ' rows.');
}

function setupMonthlyTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'createMonthlySnapshot') {
      Logger.log('Trigger already exists — not creating a duplicate.');
      return;
    }
  }
  ScriptApp.newTrigger('createMonthlySnapshot')
    .timeBased()
    .onMonthDay(1)
    .atHour(6)
    .create();
  Logger.log('Monthly trigger installed: runs on the 1st of every month around 6am.');
}
