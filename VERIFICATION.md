# Verification — 17 October 2026

## G6 and G7 tabs

18 automated tests pass. Added coverage for galaxy provenance, legacy G6 backups, G7 lettered battle IDs, source identity and image paths. Server integration verifies separate progress, conditions and corrections across restart, rejects wrong-galaxy backups and unknown galaxy requests, and preserves the original G6 filename.

Browser checks used temporary storage: B2A flight cost changed from 12 to 9 and saved through Mark done. It remained at 9 after switching to G6 and back; G6 history stayed empty. G7 group BB1 & B7 showed exactly those two battles. Its guide linked to its own calculator without G6 thresholds. Both fleet images decoded successfully. Desktop displayed two columns with the main area at 90% of the available viewport. No warnings or errors appeared in captured browser logs. The original G6 save was not used for test mutations.

G7 import: 15 battles, 73 text cells, 143 records (70 usable, 12 review, 56 obsolete, 5 failed), 72 downloaded images. Two text cells lack adjacent images and one image lacks a matching text cell. G6 import counts remain unchanged.

## Inline completion and wider desktop follow-up

Browser smoke checks used an isolated local server and separate temporary progress storage. Editing B1's inline flight cost from 11 to 9 and pressing Mark done immediately saved 9 FR in completion history and hid the battle. Fractional costs were rejected, a draft value survived filtering away and back, and a battle without a usable suggestion had a blank required cost field. No browser warnings/errors were captured. User progress on the normal server was not modified. The card-level Correct button was removed; the history correction and source-review tools remain available.

Desktop was changed to two columns, a 90%-width content area without the previous width cap, and images with natural height at full card width. The existing mobile single-column layout remains.

## Automated checks

`npm test`: **18 passed, 0 failed** after the multi-galaxy changes. No package dependencies were installed.

Covered:

- Nearest-lower selection per source layout before ranking, including worsening higher-multiplier results.
- Integer truncation, ties and strictly lower-integer resurfacing.
- Exact support/hazard filtering, per-battle overrides and special-build filtering.
- Failed/review observations blocking older successes; obsolete observations excluded.
- Local corrections, multi-shot cost sums and per-shot integer truncation.
- Completion history, JSON round trips and invalid backup rejection.
- Within-cell condition changes, SHC semantics, exact legend colors and unknown colors.
- Rich-text strikethrough and base-format inheritance.
- Decimal variants, missing x, one-shot spent-versus-committed amounts.
- Unclear/multiple costs, duplicate variants, range syntax, unparsed multipliers, disputed notes and multi-shot/damage review gates.
- Failed earlier observations do not contaminate subsequent successes.
- Real source regressions: B21 mixed conditions, B17 hazard background, B8 dispute, B34 wrong-image note, BB3 multi-shot cost.
- All 49 battles, stable unique observation IDs and existence of referenced image files.
- Server state survives restart; previous-save backup preserved; corrupt saves not overwritten; cross-origin writes and static path traversal rejected; static source/progress files outside approved paths unavailable.

The initial sandbox run passed pure tests but blocked the loopback connection with EACCES. The full suite was rerun successfully outside that sandbox. This was an environment restriction, not a skipped test.

## Browser checks

Verified in the in-app browser against the loopback app:

- Loaded the real local data and fleet cards; no app errors in captured browser logs.
- B1 completed at 11 FR: hidden at 3× (11.54 raw), still hidden at 3.25× (11.52 raw), resurfaced at 3.5× (10.52 raw, 10 integer FR).
- Corrected that observation to 9.8 locally: card showed 9 FR, local-edit badge and a 2 FR improvement; source text remained unchanged.
- Per-battle support override filtered the result.
- Exported the pristine backup through the browser, then imported it through the file chooser and confirmation. Test progress, settings, overrides and corrections were cleared by restoring that backup.
- Inspected late-battle B31 image at full size; its decoded dimensions were 509 × 286. Checked audit display of BB3 multi-shot entries and review reasons.
- Checked desktop and 390 × 844 mobile layouts. Fixed a narrow multiplier input. Mobile document width stayed within the viewport. Reset the temporary viewport afterwards.
- Added an explicit Apply button to make multiplier updates reliable in both normal use and browser automation.

Saved screenshots: `qa/desktop.png`, `qa/mobile.png`.

## Source and launcher checks

- All five image mappings retained. Remaining image acquisition added 92 B31–40 cell references / 90 assets and 108 late-tab references / 108 assets.
- All 556 assets exist and have recognizable image signatures: 549 PNG, 7 JPEG. Extensionless images are served with the correct media type.
- Imported 563 cells / 1,200 observations: 835 usable, 144 review, 219 obsolete, 2 failed.
- Nine text cells have no adjacent image; eight image references lack a direct text match, including unlocated/page images and additional B22 images. These remain in the import audit.
- Launcher start, verified process-specific stop and restart all succeeded. It verifies application identity and workspace root before reusing a server.

## Limits

This verifies application behavior and conservative source handling, not gameplay success or the accuracy of every spreadsheet entry. Fleet pictures were spot-checked, not exhaustively compared with all text variations. Review entries need a human decision or explicit local correction before recommendation. The partial support calculator is not a route model. Concurrent editing tabs do not merge changes. Use a single active editing tab and exported backups.

The source Google Sheet was not changed. No Git operations or publishing were performed.
