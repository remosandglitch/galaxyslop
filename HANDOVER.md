# Unnamed Space Idle fleet planner — handover
Date: 2026-10-17

## Current implementation checkpoint — 2026-10-17

Multi-galaxy follow-up: G6 and G7 now have separate tabs. G7 source is workbook `1Cj4kstAZkQhTvUfIj6EkFuQ4uwkLiIAmt9m8ZgLL-jc`, with all three battle sheets imported: B1-B3, B4-B6, BB1 & B7. Its 15 exact battle IDs retain suffixes such as B2A and B4C. Extracts are in `source/g7/`, 72 assets in `source/images/g7/`, generated data in `dist/data-g7.json`. G7 has 73 cells / 143 observations: 70 usable, 12 review, 56 obsolete, 5 failed. Two cells lack adjacent images and one image lacks a direct text match. Floating image A5 was mapped from verified bounds; B7 B17's patch warning remains in review. G7 support thresholds are not imported; the guide links its own calculator.

`dist/galaxies.mjs` defines the tabs. `/?galaxy=g6` or `/?galaxy=g7` selects data and `/api/state?galaxy=...` selects storage. G6 keeps `local-data/state.json`; G7 uses `local-data/state-g7.json`. Settings, completions, history and corrections are isolated. Backups include galaxy identity; legacy backups without it are accepted only in G6. `npm run import` rebuilds both datasets. All 18 automated tests pass, including legacy-save compatibility, wrong-galaxy backup rejection and separate persistence across restarts. Browser tests used temporary storage and confirmed tab switching and G7 inline completion. The user's existing G6 save was preserved.

The local fleet planner is now built. Start it with `Launch Fleet Planner.cmd`; stop it with `Stop Fleet Planner.cmd`. Default URL: http://127.0.0.1:4173. Read `README.md` for usage and `VERIFICATION.md` for test evidence and limits.

UI follow-up: every battle card now has an editable integer Flight cost (FR) beside Mark done. Mark done records that value immediately; the card-level Correct button was removed. Source-observation editing remains inside setup details/audit. Draft flight costs survive filtering within the current session and are scoped to the selected multiplier, conditions and suggested setup. Desktop uses two columns across 90% of the viewport width, with fleet images scaling to card width; mobile remains one column.

Implemented: local Node server with no package dependencies, responsive fleet cards and images, multiplier input with Apply, default and per-battle support/hazard choices, nearest-lower estimate labels, integer FR ranking and ties, completion/history and lower-integer resurfacing, local corrections and added observations, JSON backup export/import, durable local file persistence, source inspection and import audit, and the user's support skip guide.

All five image bundles are now present: 556 assets total. The last two tabs contributed 198 assets. `source/legend.txt` and `source/legend.json` were added; the legend confirms the exact support/hazard/both/white colors. Gray means obsolete. Other colors are conservatively held for review even when text has explicit conditions.

Importer: `scripts/import.mjs`; generated app data: `dist/data.json`; audit: `source/import-audit.json`. 563 cells / 1,200 observations: 835 usable, 144 review, 219 obsolete, 2 failed. Nine text cells lack adjacent images; eight image references lack direct text matches. Multi-shot/damage entries, disputed notes and ambiguous variants require explicit local review. Their costs are not silently inferred. The support calculator remains partial. Individual fleet pictures have only been spot-checked, not fully validated against gameplay.

Verification: 16 automated tests pass, plus browser checks for completion, decimal-only hiding, integer resurfacing, editing, conditions, backup export/import, source audit, images and mobile layout. Launcher start/stop/restart succeeded. Test progress/corrections were restored to the clean initial state. The final launcher-owned server is running on loopback. No source-sheet edits, commits, pushes or deployment were performed.

Keep changes local. Future improvements should use the audit to resolve specific source ambiguities with the user, not silently broaden parser assumptions. Current layout identity is a source cell plus selected conditions; duplicate same-multiplier variants remain blocked until resolved/disabled. Simultaneous editing tabs do not merge saves; use one editing tab. Documentation below preserves the original research handover and should be read as historical where superseded by this checkpoint.

## Original research handover (historical)

## Project and status
Correct project: D:\ChatGPT\USN\Galaxies
This is independent of Stormgrown / JetsNLight. Do not apply that game's architecture or test runner to this website.

At the original handover, only research and source extraction had been completed. No website, parser, server, launcher, application tests, commits, or deployment existed. The target folder was empty before that handover. Extracted data and downloaded images were copied here; original temporary working files were retained. See the current checkpoint above for implemented work.

## User request and confirmed choices
Build a LOCAL website based on this Google Sheets workbook:
https://docs.google.com/spreadsheets/d/12DA4amUPZKamX4hgUgKjbikZ_XEhZhi-Eopy2M64dpI/edit?gid=0
Title verified by connector: Copy of G6.

Important tabs: B1-10, B11-20, B21-30, B31-40, B41-46 and BB1-3.
Pictures show fleet setups; text above contains multiplier, FR cost, and important variations (beam, positions, unit modifiers, printed ships, etc.).
S = support; H = hazard; SH/HS = both. Also NS/NH. SHC means Starting Heavy Cruiser (HP node), NOT support + hazard.
Crossed-out results are obsolete or invalid and should not be recommended.

User clarified:
- Show cheapest fleet setups per battle; user selects support and hazard conditions. A full graph/path optimizer, automatic hazard-removal order, and battle prerequisites are NOT requested.
- At a multiplier between recorded results, use nearest-lower results as clearly labelled UNVERIFIED ESTIMATES.
- Marking a battle done records its completed integer FR cost. Hide it unless an available setup has a strictly LOWER integer cost. Decimal-only improvements must not resurface a battle.
- Game truncates decimal FR costs. Compare integer costs, not rounded decimals.
- Allow editing/correcting numbers locally in the website.
- Keep source Google Sheet unchanged, keep website local.

## Saved files
source/workbook.json:
- Complete bounded CellData reads for all FIVE battle tabs.
- Includes formattedValue, userEnteredValue, effectiveFormat(textFormat,backgroundColor), textFormatRuns, and notes.
- Includes first 20 rows, A:AX, of F nodes skip calc under the support property. This support calculator extraction is PARTIAL.
- Source ID and extraction date included.
- Sheets retain native properties and data[].rowData[].values[] structure.
- Header row maps columns to battle IDs. Most text rows are even rows, pictures immediately below, but inspect exceptions rather than assume blindly.
- Grid metadata exceeds actual used rows. Last nonempty text rows found: 38, 40, 42, 44, 42 respectively.

source/images-0.json: B1-10; 112 image cell references, 111 distinct downloaded assets.
source/images-697994241.json: B11-20; 132 image cell references, 130 distinct assets.
source/images-49029630.json: B21-30; 118 image cell references, 117 distinct assets.
Each mapping contains cells [{row,col,url}] (1-based sheet coordinates) and bundle.assets with matching url and asset path.
During handover asset paths were rewritten to project-relative paths under source/images/<sheetId>/; original temporary paths retained as originalPath.
All 358 downloaded assets were verified to exist before transfer. Cell count is greater because multiple cells can reference the same URL.
IMPORTANT: Images for B31-40 and B41-46 and BB1-3 have NOT yet been downloaded. Their text/formatting IS saved.
No visual QA of individual fleet pictures has been performed yet.

## Source access and successful extraction method
Google Drive connector metadata and bounded get_spreadsheet_cells calls worked.
Full raw workbook download failed: 268449600 bytes exceeded connector limit 268435456. Do not repeat that oversized method.
Anonymous HTTP access requires login. In-app browser was not signed into Google.
Chrome already had a signed-in source workbook; a separate agent-created Chrome tab successfully read HTML sheet views.
Browser content.exportGsuite('xlsx') timed out; no usable workbook export was obtained.

Successful browser method:
1. Use cua_repl browser tools, read their documentation, use signed-in Chrome.
2. HTML workbook view:
   https://docs.google.com/spreadsheets/d/12DA4amUPZKamX4hgUgKjbikZ_XEhZhi-Eopy2M64dpI/htmlview?gid=0
3. Observed iframe #pageswitcher-content pointed to:
   https://docs.google.com/spreadsheets/u/0/d/12DA4amUPZKamX4hgUgKjbikZ_XEhZhi-Eopy2M64dpI/htmlview/sheet?headers=true&gid=0
4. Navigate directly to sheet view using verified sheet ID. Inspect DOM after navigation, allowing the actual table to load before extracting. Immediate extraction once returned zero assets; a subsequent DOM read confirmed the loaded sheet.
5. Read image DOM: each img's closest tr has a th with row number; closest td.cellIndex gives 1-based column; img.src is URL.
6. Use tab.capabilities.get('pageAssets'), read documentation, then list() and bundle({inventoryId, kinds:['image']}).
   Inventory did NOT see images when nested in the workbook iframe; it DID see them when the sheet view was loaded directly.
7. Match bundled asset URLs to cell URLs; preserve mapping.

Verified sheet IDs:
B1-10: 0
B11-20: 697994241
B21-30: 49029630
B31-40: 1589854559
B41-46 and BB1-3: 872145342
F nodes skip calc: 77408849
legend (please read before adding!): 267726191
Fixed Filter Here + image: 609545009
Do not depend on previous browser tab IDs surviving.

## Parsing findings and pitfalls
- A cell can contain several multipliers and costs, each with its own rich-text strikethrough. Exclude only affected observations, not automatically the entire cell. Base text format and textFormatRuns both matter.
- Higher multipliers sometimes produce WORSE costs. Never choose the historical minimum across lower multiplier observations and call it the current measured cost. Determine nearest-lower observation per layout/conditions first, then rank layouts.
- Preserve full source text and notes alongside extracted records, with sheet/cell links for correction.
- Conditions can change WITHIN one cell. Example B21-30 A8 contains S/H results followed by NS/H result.
- Explicit tags and background colors both occur. B11-20 G2 has no H prefix but hazard-red background.
- Common background RGB colors:
  support: (0.6431373,0.85882354,1)
  hazard: (1,0.6901961,0.6901961)
  both: (0.72156864,0.5647059,0.85882354)
  white: (1,1,1).
  Other colors exist; do not blindly treat every red/orange as a hazard. Legend says red can also mark failed attempts; yellow can mark nonstandard builds.
- Legend says bold = best for that stat; italic = best at that stat but worse than a nearby stat; struck-through = superseded. Rank actual usable numbers, not bold alone.
- Text formats vary: 48.(77), 53(.84), 80.??, missing x, comma typos, spaces, x and x sharing a cost, arrows denoting ranges, failed attempts, one-shot costs vs committed amounts, multiple-shot total costs/damage.
- BB and late hazard fights have multi-shot entries such as 140+130.34=270.34, costs vs damage, and alternate second-run arrangements. Do not accidentally rank a single shot's cost as a full clear. Retain ambiguous records for manual review rather than silently fabricating exact values.
- Notes sometimes contradict numeric text. Example B1-10 H16 contains dispute/correction comments. B31-40 D8 explicitly says screenshot below is wrong and gives a different placement.
- No parser has been written or validated yet. Need an import audit for unparsed/ambiguous cells and missing images.
- Some configurations require L/M fabricated units or SHC. Preserve these requirements prominently; decide how to expose them without claiming all configurations fit every user's fleet.

## User-provided support skip guide
This is approximate, not a hard gate; always compare actual layout costs.
Value of support = sum(no-support battle costs) - [sum(with-support battle costs) + cost of obtaining support].
F1: skippable around 1.5x
F2: around 2.5x
F3: around 2.5x
F4: if not fighting B26
F5: around 3.5x, B33 should be cleared
F6: around 3.5x
F7: if not fighting hazard B43
F8: if not fighting hazard B46 and at least 3.6x
The calculator sheet's first block lists support node purchases at 100 FR, but may not include route acquisition costs. Don't assume a complete route model from it.
Do not replace the user's rough guide with discrepant older calculator notes without explanation.

## Suggested next steps
1. Read this handover and inspect the saved data in this project.
2. Finish image acquisition for last two tabs through signed-in Chrome.
3. Build and audit a robust data importer; retain uncertain entries and full notes for review.
4. Implement local website with multiplier input, explicit support/hazard choices, cheapest usable layout cards and images, estimate badges, done/history controls, local numeric editing, and durable persistence with backup export/import.
5. Show integer FR prominently and raw decimal secondarily; compare truncation per actual cost, with careful handling of multi-shot entries.
6. Validate ranking, conditions, rich-text exclusions, estimates, ties, done/resurfacing, edits and persistence. Verify images and responsive UI in browser.
7. Deliver local launcher and usage instructions. No publishing or Git action was authorized.

## Research outside the sheet
Briefly inspected the Fleet wiki and guide index, but the clarified scope doesn't need a route graph:
https://spaceidle.game-vault.net/wiki/Fleet
https://spaceidle.game-vault.net/wiki/Guide:Galaxies
No external game mechanics have been implemented.

