# Lessons

Entries added after corrections. Format: "When X, do Y instead."

<!-- Add entries below as corrections are made -->

When appending rows to a Google Sheet that has a title row followed by blank rows and then data, do not use append_rows — it detects the title as the first "table" and inserts after row 1 (starting at row 3), overwriting critical cells. Use update_cells with an explicit row range instead.

When Logan needs to paste large code into a web editor (Apps Script, etc.), do not have him copy from the chat — chat copies truncate silently. Pipe the file to pbcopy with sandbox disabled (a sandboxed pbcopy never reaches the real clipboard) and have him paste from there.

When a Google Maps JS (v3.65+) map silently renders white — no tiles, no console errors, scaffolding present — check the container CSS first: a div sized by opposing edge offsets (left+right / top+bottom) measures as zero and the renderer never starts. Give the map container explicit width/height (calc() works).

When cloning cell formats across columns that have different number formats (e.g., a P&L where the expense-amount column is whole-dollar "$"#,##0 but the income-amount column is 2-decimal "$"#,##0.00), clone each column's OWN format — do not reuse one reference column's format for all amount columns, or you silently round values like $616.34 to $616.

When the google-sheets MCP only exposes value ops and you need Sheets formatting/column-deletes, do not start a new OAuth flow — reuse the token the local sheets-mcp server already uses (~/Documents/google_token.json, has the spreadsheets scope). See memory reference-sheets-api-token.

When a wide Sheets layout suddenly looks broken (a month/block shifted right, empty leading columns), suspect inserted columns: check the header row positions and delete the empty inserted columns with deleteDimension — data, formulas, and formatting all shift back into place. Don't rebuild from scratch.

When labeling per-entity data pulled across multiple sheets/accounts (e.g., client name from each Config tab), bind the identifying label to each row at read time and key off the source ID — do not hand-transcribe a name→ID map in a later script. A one-position shift silently mislabels every account while the numbers stay right, which is nearly invisible. When the same metric is reported across N similar sheets, re-read the identifier from the same source in the final computation so names can't drift.

When creating a Python venv or pip editable install, do not place the project under a path containing a colon (the workspace `Claude Code 5:30` has one). Python's `venv` hard-refuses ("Refusing to create a venv ... contains the PATH separator :") and PYTHONPATH/.pth entries split on `:`. Put Python projects in a colon-free path (e.g. ~/Documents/<name>) and point any wrapper/skill at that absolute path instead.

When applying ffmpeg's `deshake` filter to footage that was shot on a gimbal (already smooth), do not assume stabilization always helps — measure it. Applying `deshake` to already-trimmed short clips (2-3s) with no motion-history warm-up can make already-stable footage measurably shakier (confirmed with `ffmpeg -vf vmafmotion` motion scores: processed clips scored higher than the raw source in 2/2 spot checks). Before applying any stabilizer, spot-check raw footage's actual motion first, and if it's already smooth (typical of gimbal-shot real estate/product walkthroughs), skip the filter entirely rather than defaulting to it.

When a Hyperframes (or similar headless-Chrome render) composition references a custom font by `font-family` name only (e.g. "Archivo Black"), do not assume the renderer resolves Google Fonts automatically even if the linter passes with 0 warnings — verify by rendering and visually inspecting a zoomed-in text frame. It silently fell back to a generic system font that looked completely different. Fix by embedding the actual font via `@font-face { src: url(<fonts.gstatic.com woff2 URL>) }` with `font-display: block` (not `swap`, since a one-shot render has no "later" to swap into) — fetch the real woff2 URL via `curl https://fonts.googleapis.com/css2?family=<Font+Name>`.

When picking cut/trim points from a batch of raw video clips, do not judge each clip from a single static thumbnail frame — it hides motion quality, duplicate takes, and mistakes that only appear late in a clip (camera operator's feet stepping into frame, a ladder coming into view, walking bob). Use the `/watch` skill (or at minimum a multi-frame filmstrip per clip) to actually see each clip's motion before selecting in/out points. On a real job this caught: two separate "same shot twice" duplicate-take pairs I'd missed from thumbnails alone, and confirmed a trim window was safely before the camera operator's feet became visible late in a clip.

When a user says video transitions look like "fake transitions" they don't want, don't reach for crossfade/dissolve effects between cuts as a quality improvement — some users (and some professional real-estate video styles) want pure hard cuts throughout, zero dissolves, even between shots with big exposure swings. Confirm the target style against a reference video if one exists rather than assuming crossfades read as more polished.
