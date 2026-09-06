from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

# Colors
BG_COLOR = RGBColor(0x0D, 0x0D, 0x0D)       # near-black background
TITLE_COLOR = RGBColor(0xFF, 0xFF, 0xFF)      # white
BODY_COLOR = RGBColor(0xCC, 0xCC, 0xCC)       # light grey
ACCENT_COLOR = RGBColor(0xFF, 0xC1, 0x07)     # amber — emphasis words

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H

blank_layout = prs.slide_layouts[6]  # completely blank


def add_slide(title_text=None, bullets=None,
              title_size=54, body_size=36,
              title_color=TITLE_COLOR, body_color=BODY_COLOR,
              center_body=False):
    """
    Add a slide.
    title_text  : string shown at top (or center if no bullets)
    bullets     : list of strings for body text
    center_body : center the body text block vertically
    """
    slide = prs.slides.add_slide(blank_layout)

    # Dark background rectangle
    bg = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        0, 0, SLIDE_W, SLIDE_H
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG_COLOR
    bg.line.fill.background()

    if title_text is None:
        return slide

    has_bullets = bullets and len(bullets) > 0

    if not has_bullets:
        # Full-slide centered title
        txBox = slide.shapes.add_textbox(
            Inches(0.75), Inches(2.0),
            Inches(11.83), Inches(3.5)
        )
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = title_text
        run.font.bold = True
        run.font.size = Pt(title_size)
        run.font.color.rgb = title_color
    else:
        # Title at top, bullets below
        title_box = slide.shapes.add_textbox(
            Inches(0.75), Inches(0.55),
            Inches(11.83), Inches(1.5)
        )
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = title_text
        run.font.bold = True
        run.font.size = Pt(title_size)
        run.font.color.rgb = title_color

        body_box = slide.shapes.add_textbox(
            Inches(0.75), Inches(1.9),
            Inches(11.83), Inches(5.0)
        )
        tf = body_box.text_frame
        tf.word_wrap = True
        for i, bullet in enumerate(bullets):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.alignment = PP_ALIGN.LEFT
            p.space_before = Pt(10)
            run = p.add_run()
            run.text = bullet
            run.font.size = Pt(body_size)
            run.font.color.rgb = body_color

    return slide


def add_step_slide(step_label, step_title, bullets):
    """Step slides: bold step number + title, then bullets."""
    slide = prs.slides.add_slide(blank_layout)
    bg = slide.shapes.add_shape(1, 0, 0, SLIDE_W, SLIDE_H)
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG_COLOR
    bg.line.fill.background()

    header = slide.shapes.add_textbox(
        Inches(0.75), Inches(0.45), Inches(11.83), Inches(1.1)
    )
    tf = header.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    r1 = p.add_run()
    r1.text = step_label + "  "
    r1.font.bold = True
    r1.font.size = Pt(44)
    r1.font.color.rgb = ACCENT_COLOR
    r2 = p.add_run()
    r2.text = step_title
    r2.font.bold = True
    r2.font.size = Pt(44)
    r2.font.color.rgb = TITLE_COLOR

    body_box = slide.shapes.add_textbox(
        Inches(0.75), Inches(1.75), Inches(11.83), Inches(5.2)
    )
    tf = body_box.text_frame
    tf.word_wrap = True
    for i, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_before = Pt(12)
        run = p.add_run()
        run.text = bullet
        run.font.size = Pt(34)
        run.font.color.rgb = BODY_COLOR

    return slide


# ─── SLIDES ───────────────────────────────────────────────────────────────────

# 1 — Opening hook
add_slide(
    "If you've got a team of loan officers, you already know this.",
    title_size=52
)

# 2 — Core problem statement
add_slide(
    "Most of your production is still tied\nto a small group of realtors.",
    title_size=50
)

# 3 — The two problems (title only)
add_slide("That creates two problems.", title_size=54)

# 4 — Problem 1
add_slide(
    "Problem 1",
    ["Newer LOs don't have enough referral partners yet.\n"
     "So they're stuck trying to build momentum from scratch."],
    title_size=46, body_size=34
)

# 5 — Problem 2
add_slide(
    "Problem 2",
    ["Even experienced LOs are vulnerable.\n"
     "If a main agent slows down, switches lenders, or stops sending deals — "
     "their pipeline takes a hit.\n"
     "And when that happens across the team, your branch numbers feel it."],
    title_size=46, body_size=32
)

# 6 — What this video is about
add_slide(
    "In this video, I'll show you how top mortgage teams\n"
    "are using Meta Ads to build a buyer pipeline they actually control.",
    title_size=46
)

# 7 — The Problem… (title only, progressive)
add_slide("The Problem…", title_size=58)

# 8 — Problem: what teams try
add_slide(
    "The Problem…",
    ["Most teams try to fix this by buying more leads.\n"
     "Zillow. Realtor.com. Webinar funnels."],
    title_size=54, body_size=36
)

# 9 — Problem: what happens
add_slide(
    "The Problem…",
    ["Most teams try to fix this by buying more leads.\n"
     "Zillow. Realtor.com. Webinar funnels.",
     "And it usually turns into the same thing.\n"
     "A few decent leads buried under a pile of junk.\n"
     "No clear system for routing them to the right LO."],
    title_size=54, body_size=32
)

# 10 — The real problem
add_slide(
    "More leads by itself does not fix anything.",
    title_size=54
)

# 11 — What you actually need
add_slide(
    "What you actually need:\n\n"
    "A steady flow of real buyers routed to the right people on your team.",
    title_size=44
)

# 12 — Now your team has options
add_slide(
    "When you have that…",
    ["Newer LOs have real buyers to follow up with — not just hoping referrals show up.",
     "Top producers can layer on more purchase volume with the agents they already work with.",
     "And as a branch leader, you have something concrete to recruit and retain with."],
    title_size=46, body_size=32
)

# 13 — Big promise
add_slide(
    "And that's exactly what we build.",
    title_size=54
)

# 14 — What we build
add_slide(
    "We help mortgage teams set up and run\na Meta Ads + CRM system that feels in-house.",
    title_size=46
)

# 15 — Goals
add_slide(
    "The goal is simple.",
    ["Bring in exclusive first-time homebuyer leads in your markets.",
     "Score those leads so your team knows who to call first.",
     "Route them to the right LO on your team.",
     "Use those buyers to create more conversations and stronger agent relationships."],
    title_size=50, body_size=30
)

# 16 — Who this is for (title only)
add_slide("Who This Is For", title_size=58)

# 17 — Who this is for + bullet 1
add_slide(
    "Who This Is For",
    ["Licensed LOs who are leading a team of other loan officers"],
    title_size=54, body_size=36
)

# 18 — Who this is for + bullets 1+2
add_slide(
    "Who This Is For",
    ["Licensed LOs who are leading a team of other loan officers",
     "Who can invest at least $3K–$6K/month in Meta ad spend on top of our retainer"],
    title_size=54, body_size=34
)

# 19 — Who this is for + bullets 1+2+3
add_slide(
    "Who This Is For",
    ["Licensed LOs who are leading a team of other loan officers",
     "Who can invest at least $3K–$6K/month in Meta ad spend on top of our retainer",
     "Who will put a real follow-up process in place — calling, texting, and working leads every day"],
    title_size=54, body_size=32
)

# 20 — Who this is NOT for
add_slide("Who This Is NOT For", title_size=58)

# 21 — Not for details
add_slide(
    "Who This Is NOT For",
    ["Solo LOs without a team",
     "Teams of only processors or assistants — no LOs to actually work leads",
     "Teams already maxed out, or LOs who refuse to call online leads"],
    title_size=50, body_size=34
)

# 22 — Step 1
add_step_slide(
    "Step 1",
    "High-Volume Andromeda Campaign",
    ["We launch 50–100 angles, hooks, and creatives into YOUR ad account",
     "Not two generic ads — specific callouts for neighborhoods and buyer situations",
     "This gives Meta enough variety to find people who are actually raising their hand"]
)

# 23 — Step 2 (title only)
add_slide("Step 2", title_size=58)

# 24 — Step 2 with content
add_step_slide(
    "Step 2",
    "Lead Scoring",
    ["Every lead drops into a mortgage-specific CRM",
      "Scored green / yellow / red based on Credit, Income, and Buying Timeline",
      "Green = stronger income, workable credit, realistic timeline to buy",
      "Your best people focus on green. Newer LOs or ISAs work yellow and red."]
)

# 25 — Step 3
add_step_slide(
    "Step 3",
    "Win and Deepen Agent Relationships",
    ["Now your team isn't waiting for agents to send the next deal",
     "You have buyers coming in — and a system to sort them",
     "Use those opportunities to get more referrals from agents you already work with",
     "And use them as a prospecting tool to lock in new agent relationships"]
)

# 26 — The real shift
add_slide(
    "Instead of begging agents for business,\nyour team becomes the one bringing real buyer opportunities to the table.",
    title_size=44
)

# 27 — Markets
add_slide(
    "We're running this right now in:",
    ["Dallas  ·  San Diego  ·  Phoenix  ·  and more"],
    title_size=50, body_size=40
)

# 28 — Pattern
add_slide(
    "The pattern is consistent.",
    ["The team starts getting a base of green leads to work.",
     "Newer LOs finally have real buyers to call.",
     "And in many cases, one or two new agent relationships cover the cost of the system for the year."],
    title_size=50, body_size=32
)

# 29 — Simple economics
add_slide(
    "The simplest way to think about it:",
    ["If you can't see a realistic path where your team closes at least\n"
     "1–2 extra purchase deals a month from this — don't book a call.\n\n"
     "If you can see that path, and you have LOs who will actually follow up — keep reading."],
    title_size=44, body_size=30
)

# 30 — What you actually get (title only)
add_slide("What You Actually Get", title_size=58)

# 31 — What you get + bullet 1
add_slide(
    "What You Actually Get",
    ["50–100 ads launched into YOUR ad account"],
    title_size=54, body_size=36
)

# 32 — What you get + bullets 1+2
add_slide(
    "What You Actually Get",
    ["50–100 ads launched into YOUR ad account",
     "Ongoing campaign management to maximize green leads"],
    title_size=54, body_size=36
)

# 33 — What you get + bullets 1+2+3
add_slide(
    "What You Actually Get",
    ["50–100 ads launched into YOUR ad account",
     "Ongoing campaign management to maximize green leads",
     "Exclusivity — we only work with 1 LO team per territory"],
    title_size=54, body_size=34
)

# 34 — What you invest (title only)
add_slide("What You Invest", title_size=58)

# 35 — What you invest + bullet 1
add_slide(
    "What You Invest",
    ["Upfront build fee"],
    title_size=54, body_size=36
)

# 36 — What you invest + bullets 1+2
add_slide(
    "What You Invest",
    ["Upfront build fee",
     "Ongoing management retainer (billed every 28 days)"],
    title_size=54, body_size=36
)

# 37 — What you invest + bullets 1+2+3
add_slide(
    "What You Invest",
    ["Upfront build fee",
     "Ongoing management retainer (billed every 28 days)",
     "Meta ad spend ($3K–$6K/month)"],
    title_size=54, body_size=34
)

# 38 — Next Steps (title only)
add_slide("Next Steps", title_size=58)

# 39 — Next Steps with bullets
add_slide(
    "Next Steps",
    ["Click the button around this video",
     "Answer a few quick questions about your team, markets, and current lead flow",
     "Pick a time on the calendar — we'll walk through exactly what this looks like for your branch"],
    title_size=54, body_size=32
)

# ─── SAVE ─────────────────────────────────────────────────────────────────────
out_path = "/Users/Logan/Documents/Claude Code/fullyscale-workspace/new_vsl_slides.pptx"
prs.save(out_path)
print(f"Saved: {out_path}")
