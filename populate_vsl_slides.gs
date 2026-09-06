// Run this from Extensions → Apps Script inside the presentation.
// Select buildVSLSlides and click Run.

function buildVSLSlides() {
  var prs = SlidesApp.getActivePresentation();
  var W = prs.getPageWidth();
  var H = prs.getPageHeight();

  // ── Remove all existing slides ──────────────────────────────────────────
  var existing = prs.getSlides();
  for (var i = existing.length - 1; i >= 0; i--) {
    existing[i].remove();
  }

  // ── Colors & layout constants ───────────────────────────────────────────
  var BG    = '#0D0D0D';
  var WHITE = '#FFFFFF';
  var GREY  = '#CCCCCC';
  var AMBER = '#FFC107';
  var M = 43;          // left/right margin in points (~0.6 in)
  var CW = W - M * 2; // content width

  // ── Helpers ─────────────────────────────────────────────────────────────

  function newSlide() {
    var sl = prs.appendSlide(SlidesApp.PredefinedLayout.BLANK);
    sl.getBackground().setSolidFill(BG);
    return sl;
  }

  // Full-slide centered statement
  function fullSlide(text, size) {
    var sl = newSlide();
    var box = sl.insertTextBox(text, M, H * 0.15, CW, H * 0.70);
    var tf = box.getText();
    tf.getTextStyle().setFontSize(size || 40).setBold(true).setForegroundColor(WHITE);
    tf.getParagraphs().forEach(function(p) {
      p.getRange().getParagraphStyle()
        .setParagraphAlignment(SlidesApp.ParagraphAlignment.CENTER);
    });
    box.setContentAlignment(SlidesApp.ContentAlignment.MIDDLE);
    return sl;
  }

  // Title at top + body bullets below
  function bulletSlide(title, bullets, titleSize, bodySize) {
    var sl = newSlide();

    var titleBox = sl.insertTextBox(title, M, 22, CW, 70);
    var ttf = titleBox.getText();
    ttf.getTextStyle().setFontSize(titleSize || 36).setBold(true).setForegroundColor(WHITE);
    ttf.getParagraphs().forEach(function(p) {
      p.getRange().getParagraphStyle()
        .setParagraphAlignment(SlidesApp.ParagraphAlignment.START);
    });
    titleBox.setContentAlignment(SlidesApp.ContentAlignment.TOP);

    if (bullets && bullets.length > 0) {
      var bodyText = bullets.join('\n\n');
      var bodyBox = sl.insertTextBox(bodyText, M, 105, CW, H - 120);
      var btf = bodyBox.getText();
      btf.getTextStyle().setFontSize(bodySize || 26).setForegroundColor(GREY);
      btf.getParagraphs().forEach(function(p) {
        p.getRange().getParagraphStyle()
          .setParagraphAlignment(SlidesApp.ParagraphAlignment.START);
      });
      bodyBox.setContentAlignment(SlidesApp.ContentAlignment.TOP);
    }
    return sl;
  }

  // Step slide: amber step number + white title + grey bullets
  function stepSlide(num, title, bullets, bodySize) {
    var sl = newSlide();
    var stepLabel = num + '   ';
    var fullHeader = stepLabel + title;

    var headerBox = sl.insertTextBox(fullHeader, M, 22, CW, 60);
    var htf = headerBox.getText();
    htf.getTextStyle().setFontSize(36).setBold(true).setForegroundColor(WHITE);
    // Color the step label amber
    htf.getRange(0, stepLabel.length).getTextStyle().setForegroundColor(AMBER);
    htf.getParagraphs().forEach(function(p) {
      p.getRange().getParagraphStyle()
        .setParagraphAlignment(SlidesApp.ParagraphAlignment.START);
    });
    headerBox.setContentAlignment(SlidesApp.ContentAlignment.TOP);

    if (bullets && bullets.length > 0) {
      var bodyText = bullets.join('\n\n');
      var bodyBox = sl.insertTextBox(bodyText, M, 95, CW, H - 110);
      var btf = bodyBox.getText();
      btf.getTextStyle().setFontSize(bodySize || 26).setForegroundColor(GREY);
      btf.getParagraphs().forEach(function(p) {
        p.getRange().getParagraphStyle()
          .setParagraphAlignment(SlidesApp.ParagraphAlignment.START);
      });
      bodyBox.setContentAlignment(SlidesApp.ContentAlignment.TOP);
    }
    return sl;
  }

  // ── Slide definitions ────────────────────────────────────────────────────

  // 1 — Opening hook
  fullSlide(
    'If you\'ve got a team of loan officers,\nyou already know this.',
    38
  );

  // 2 — Core problem
  fullSlide(
    'Most of your production is still tied\nto a small group of realtors.',
    40
  );

  // 3 — Two problems
  fullSlide('That creates two problems.', 48);

  // 4 — Problem 1
  bulletSlide(
    'Problem 1',
    ['Newer LOs don\'t have enough referral partners yet.\nSo they\'re stuck trying to build momentum from scratch.'],
    40, 30
  );

  // 5 — Problem 2
  bulletSlide(
    'Problem 2',
    ['Even experienced LOs are vulnerable.\nIf a main agent slows down, switches lenders, or stops sending deals — their pipeline takes a hit.\nAnd when that happens across the team, your branch numbers feel it.'],
    40, 28
  );

  // 6 — What this video is about
  fullSlide(
    'In this video, I\'ll show you how top mortgage teams\nare using Meta Ads to build a buyer pipeline\nthey actually control.',
    36
  );

  // 7 — The Problem… (title only)
  fullSlide('The Problem…', 52);

  // 8 — Problem: what teams try
  bulletSlide(
    'The Problem…',
    ['Most teams try to fix this by buying more leads.\nZillow. Realtor.com. Webinar funnels.'],
    48, 32
  );

  // 9 — Problem: what happens
  bulletSlide(
    'The Problem…',
    [
      'Most teams try to fix this by buying more leads.\nZillow. Realtor.com. Webinar funnels.',
      'It usually turns into the same thing.\nA few decent leads buried under a pile of junk.\nNo clear system for routing them to the right LO.'
    ],
    46, 28
  );

  // 10 — The real problem
  fullSlide('More leads by itself does not fix anything.', 46);

  // 11 — What you actually need
  fullSlide(
    'What you actually need:\n\nA steady flow of real buyers routed\nto the right people on your team.',
    36
  );

  // 12 — Now your team has options
  bulletSlide(
    'When you have that…',
    [
      'Newer LOs have real buyers to follow up with — not just hoping referrals show up.',
      'Top producers can layer on more purchase volume with the agents they already work with.',
      'And as a branch leader, you have something concrete to recruit and retain with.'
    ],
    40, 28
  );

  // 13 — Big promise
  fullSlide('And that\'s exactly what we build.', 48);

  // 14 — What we build
  fullSlide(
    'We help mortgage teams set up and run\na Meta Ads + CRM system that feels in-house.',
    38
  );

  // 15 — Goals
  bulletSlide(
    'The goal is simple.',
    [
      'Bring in exclusive first-time homebuyer leads in your markets.',
      'Score those leads so your team knows who to call first.',
      'Route them to the right LO on your team.',
      'Use those buyers to create more conversations and stronger agent relationships.'
    ],
    44, 26
  );

  // 16 — Who this is for (title only)
  fullSlide('Who This Is For', 52);

  // 17 — Who this is for + bullet 1
  bulletSlide(
    'Who This Is For',
    ['Licensed LOs who are leading a team of other loan officers'],
    48, 30
  );

  // 18 — Who this is for + bullets 1+2
  bulletSlide(
    'Who This Is For',
    [
      'Licensed LOs who are leading a team of other loan officers',
      'Who can invest at least $3K–$6K/month in Meta ad spend on top of our retainer'
    ],
    48, 28
  );

  // 19 — Who this is for + bullets 1+2+3
  bulletSlide(
    'Who This Is For',
    [
      'Licensed LOs who are leading a team of other loan officers',
      'Who can invest at least $3K–$6K/month in Meta ad spend on top of our retainer',
      'Who will put a real follow-up process in place — calling, texting, and working leads every day'
    ],
    46, 26
  );

  // 20 — Who this is NOT for (title only)
  fullSlide('Who This Is NOT For', 52);

  // 21 — Not for details
  bulletSlide(
    'Who This Is NOT For',
    [
      'Solo LOs without a team',
      'Teams of only processors or assistants — no LOs to actually work leads',
      'Teams already maxed out, or LOs who refuse to call online leads'
    ],
    46, 28
  );

  // 22 — Step 1
  stepSlide(
    'Step 1',
    'High-Volume Andromeda Campaign',
    [
      'We launch 50–100 angles, hooks, and creatives into YOUR ad account',
      'Not two generic ads — specific callouts for neighborhoods and buyer situations',
      'This gives Meta enough variety to find people who are actually raising their hand'
    ],
    28
  );

  // 23 — Step 2 (title only)
  fullSlide('Step 2', 52);

  // 24 — Step 2 with content
  stepSlide(
    'Step 2',
    'Lead Scoring',
    [
      'Every lead drops into a mortgage-specific CRM',
      'Scored green / yellow / red based on Credit, Income, and Buying Timeline',
      'Green = stronger income, workable credit, realistic timeline to buy',
      'Your best people focus on green. Newer LOs or ISAs work yellow and red.'
    ],
    26
  );

  // 25 — Step 3
  stepSlide(
    'Step 3',
    'Win and Deepen Agent Relationships',
    [
      'Now your team isn\'t waiting for agents to send the next deal',
      'You have buyers coming in — and a system to sort them',
      'Use those opportunities to get more referrals from agents you already work with',
      'And use them as a prospecting tool to lock in new agent relationships'
    ],
    26
  );

  // 26 — The real shift
  fullSlide(
    'Instead of begging agents for business,\nyour team becomes the one bringing\nreal buyer opportunities to the table.',
    38
  );

  // 27 — Markets
  bulletSlide(
    'We\'re running this right now in:',
    ['Dallas  ·  San Diego  ·  Phoenix  ·  and more'],
    46, 36
  );

  // 28 — Pattern
  bulletSlide(
    'The pattern is consistent.',
    [
      'The team starts getting a base of green leads to work.',
      'Newer LOs finally have real buyers to call.',
      'In many cases, one or two new agent relationships cover the cost of the system for the year.'
    ],
    44, 28
  );

  // 29 — Simple economics
  bulletSlide(
    'The simplest way to think about it:',
    [
      'If you can\'t see a realistic path where your team closes at least 1–2 extra purchase deals a month from this — don\'t book a call.',
      'If you can see that path, and your LOs will actually follow up, here\'s what to do next.'
    ],
    40, 28
  );

  // 30 — What you actually get (title only)
  fullSlide('What You Actually Get', 52);

  // 31 — What you get + bullet 1
  bulletSlide(
    'What You Actually Get',
    ['50–100 ads launched into YOUR ad account'],
    48, 30
  );

  // 32 — What you get + bullets 1+2
  bulletSlide(
    'What You Actually Get',
    [
      '50–100 ads launched into YOUR ad account',
      'Ongoing campaign management to maximize green leads'
    ],
    48, 28
  );

  // 33 — What you get + bullets 1+2+3
  bulletSlide(
    'What You Actually Get',
    [
      '50–100 ads launched into YOUR ad account',
      'Ongoing campaign management to maximize green leads',
      'Exclusivity — we only work with 1 LO team per territory'
    ],
    46, 28
  );

  // 34 — What you invest (title only)
  fullSlide('What You Invest', 52);

  // 35 — What you invest + bullet 1
  bulletSlide(
    'What You Invest',
    ['Upfront build fee'],
    48, 30
  );

  // 36 — What you invest + bullets 1+2
  bulletSlide(
    'What You Invest',
    [
      'Upfront build fee',
      'Ongoing management retainer (billed every 28 days)'
    ],
    48, 28
  );

  // 37 — What you invest + bullets 1+2+3
  bulletSlide(
    'What You Invest',
    [
      'Upfront build fee',
      'Ongoing management retainer (billed every 28 days)',
      'Meta ad spend ($3K–$6K/month)'
    ],
    46, 28
  );

  // 38 — Next Steps (title only)
  fullSlide('Next Steps', 52);

  // 39 — Next Steps with bullets
  bulletSlide(
    'Next Steps',
    [
      'Click the button around this video',
      'Answer a few quick questions about your team, markets, and current lead flow',
      'Pick a time on the calendar — we\'ll walk through exactly what this looks like for your branch'
    ],
    46, 28
  );

  prs.saveAndClose();
  Logger.log('Done — ' + prs.getSlides().length + ' slides created.');
}
