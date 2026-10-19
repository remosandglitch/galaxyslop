# Galaxies local fleet planner

## Moving to another client

Clone this repository, then open its root folder in the new client. Read `TRANSFER-START-HERE.txt` and give the new agent `NEXT-GALAXY-GUIDE.txt`. The repository includes G6/G7 save snapshots and the separate `data-merge/Galaxy 3` preparation work. Generated ZIPs and split download packages are excluded. Keep future progress changes local unless you intentionally want to share updated saves.

Double-click **Launch Fleet Planner.cmd**. The planner opens at <http://127.0.0.1:4173>. It runs entirely on this computer, using saved G6 and G7 snapshots from 17 October 2026. Node.js 20 or newer is required; no package installation is needed. The launcher reuses an already running planner from this folder.

Use **Stop Fleet Planner.cmd** to stop the launcher-owned background server. Closing the browser alone does not stop it.

## Using the planner

Select **G6** or **G7** at the top. Each galaxy keeps its own settings, completed battles, history and corrections. Backup export applies to the selected galaxy, and import rejects a backup from another galaxy. Older backups without a galaxy label belong to G6. Desktop cards fill 90% of the screen in two columns; mobile uses one column.

1. Enter your fleet damage and health multiplier and click **Apply**.
2. Choose default support and hazard conditions. Individual battle controls override these defaults; the reset arrow returns that battle to the defaults.
3. Compare the cheapest usable setup for each battle. Large costs are integer FR, truncated rather than rounded. Raw decimal costs remain visible. Integer ties are listed under **Setups & source**.
4. Open an image or **Setups & source** to inspect the full source text, ship positions, modifiers, notes and equipment requirements. **Include special builds** includes cells mentioning SHC, printed units or L/M units; it is not a guarantee that your fleet meets every requirement.
5. Edit **Flight cost (FR)** beside **Mark done** on each battle card, then click **Mark done** to save that integer cost directly. The field starts with the suggested integer cost, or stays blank when there is no usable result. Completed battles remain hidden until an available setup is strictly cheaper in integer FR. Decimal-only improvements do not resurface them. Correct or reopen them in **Completed & history**.
6. For changes to source observations, open a setup's details or **Source & import audit → Inspect & correct**, then use **Correct**. Check the “use this result” box only after reviewing the setup. Unchecking it disables that observation locally. **Restore source value** removes a correction. You can add checked observations to an existing source setup, including cells the importer could not parse. Editing a card's flight cost changes the completion cost, not the source observation.
7. Export backups regularly. Import shows the backup contents before replacing your current progress and edits.

## What estimates mean

At an unrecorded multiplier, the planner uses the nearest lower usable observation separately for each source layout and selected conditions, then compares integer FR costs across those layouts. It does not use a historical minimum within a layout. A failed or unresolved nearest observation prevents an older success from being carried forward. Crossed-out observations are excluded.

All nonexact matches are labelled **UNVERIFIED ESTIMATE**, including multipliers above the last recorded observation. A higher multiplier can give a worse result. “Cheapest usable” refers to the observations accepted by this importer, not a claim of the best possible fleet in the game.

## Import coverage and review

- G6: all 49 battles from the five battle tabs are included. The following counts describe G6.
- 563 nonempty source cells produced 1,200 observations: 835 usable, 144 held for review, 219 crossed out/obsolete, and 2 failed.
- 556 downloaded assets are retained across the five image bundles. Images are associated with the cell immediately above, with exceptions left visible in the audit.
- Nine text cells lack an adjacent image. Eight image references have no direct text match; some are page decoration or unlocated images, and two are additional B22 arrangements without their own text.
- The audit retains source text, rich-text strikethrough, notes, coordinates, links and import reasons. Ambiguous multipliers, condition colors, duplicated variants, disputed notes, damage figures and multi-shot entries are held for review. No costs are inferred from the fleet pictures.
- Multi-shot corrections can supply individual shot costs. The displayed integer total is the sum of truncated shot costs. Their raw sum must equal the entered full-clear total.
- A source cell is treated as one layout per condition. Ambiguous within-cell variants require review. If two observations have the same multiplier and conditions, resolve or disable the ambiguous duplicate before using that layout at that multiplier.
- The support guide preserves the user's approximate guidelines. The support calculator extraction remains partial; no route graph, battle prerequisites or automatic hazard-removal order is implemented.

G7 includes 15 exact battle labels across three sheets, including lettered variants such as B2A and B4C. Its 73 source cells produced 143 observations: 70 usable, 12 review, 56 obsolete and 5 failed. There are 72 images, two text cells without adjacent images and one image without a direct text match. G7 support thresholds have not been verified; its guide links to the G7 calculator.

The Google Sheets are unchanged. The app does not automatically refresh them. G6 source files remain in `source/`; G7 extracts and audit are in `source/g7/`, with images under `source/images/g7/`. Generated data is `dist/data.json` and `dist/data-g7.json`.

## Your local data

Progress, settings, corrections and completion history are saved in `local-data/state.json` for G6 and `local-data/state-g7.json` for G7, independent of browser storage. Each successful replacement preserves the preceding save with a `.previous` suffix. Export/import backups are portable JSON files. Keep the entire project folder to preserve source images and application files.

If the saved file is corrupt, the server refuses to overwrite it. Stop the planner, preserve that file, then restore a known good backup to the matching galaxy's state file before restarting. A failed save is shown in the page header. Use one active editing browser tab per galaxy; simultaneous tabs for the same galaxy do not merge changes.

## Maintenance and verification

Run `npm test` for the importer, ranking, persistence and server tests. Run `npm run import` after intentionally updating source extracts, then restart/reload the planner. No dependencies are downloaded by these commands.

Use `npm start` for a foreground server. A different port can be selected with the `FLEET_PORT` environment variable. The server binds only to `127.0.0.1`, checks host/origin on requests, and does not expose local progress files as static downloads.

See `VERIFICATION.md` for checks performed and their limits.
