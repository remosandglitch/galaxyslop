Galaxy 3 data

galaxy3.json contains 161 builds across 17 stages and 145 exact multiplier
groups, organized as stages -> multipliers -> builds.
images/ contains the original full-size PNGs, named <stage>_<number>.png.
Images were copied without resizing or re-encoding. Original filenames are
preserved. All 108 referenced images are present.

Fields

stage: Stage name, such as B2A or BB1.
multiplier: One exact listed value such as "1.0x". Every listed multiplier
  from the approved entries is retained. Captions listing several multipliers
  produce separate entries that share the same image. No intermediate values
  are inferred, and equal-cost entries are not consolidated.
cost: Numeric cost with all recorded decimal digits, including parenthesized
  fractional digits from the captions. The game truncates these for display;
  this JSON preserves them. No extra precision is invented for integer costs.
costFractionalPart/costFractionalPartStatus: B7B at 2.375x has cost 27, with
  fractional part null and status "unspecified", as explicitly confirmed.
lightChoices: Required purchases at specific Lights, e.g. {"L1": "Corvette"}.
  An empty object means no Light purchases are required. Unlisted Lights do
  not require a purchase.
lightChoiceAlternatives: Complete alternative purchase combinations for the
  same build. Choose one combination. B6B's cost-31 build requires one Frigate
  and one Corvette across L1 and L2, in either order.
image: A path relative to this folder. The agreed B4B 2.375x/cost-10 entry has
  an empty string because no image is available; its setup is in Comments.
comments: Notes, including equipment notes explicitly requested as comments.
equipmentRequirements: Explicit equipment requirements where retained as
  structured data. Missing equipment fields are unspecified, not false.
  An optional ship identifies the ship explicitly named in the caption.
base: Whether the base is present for this build. False on a boss stage means
  a new run after the base was killed, not clearing leftovers from one battle.
baseDamage: Damage stated for the build.
baseShots: Number of attempts when specified. Omitted when unspecified.
baseKill: False unless a base kill was explicitly stated or confirmed.
sameBuildForAllShots: True for the confirmed B10 2.85x two-attempt build.
costBasis/baseDamageBasis: "per attempt" for that two-attempt build. Its cost
  remains 120 and damage remains 1043.1 per attempt; the cost is not summed.

Source fields and standalone source-attribution comments have been removed
from galaxy3.json. Both costs and base damage retain their recorded precision.

Hazards and Supports are optional and are omitted for Galaxy 3. Base fields
are omitted on stages where they are not applicable. Unknown shot counts
and unstated damage are omitted rather than filled with zero.

Selection and source notes

All approved builds are retained, including more expensive alternatives and
builds with identical requirements at the same multiplier. Each distinct
caption variant has its own build entry. Shared images remain shared paths.
Base and no-base builds and different layouts remain separate.

The user's 2026-10-22 instructions to list every multiplier, preserve decimals,
and keep all builds supersede the earlier cost truncation, cheapest-build
selection and consecutive-multiplier consolidation rules.

Struck-through text and all agreed exclusions were removed from the dataset.
images/ contains only files referenced by the final JSON. Unused output images
were deleted locally. The agreed entry with no image still uses an empty path.

The confirmed caption values take precedence over the screenshots for
B3B E10 (2.375x, cost 10) and B10 B6 (3.725x, cost 62, Base false).

_source/ preserves the original workbook, extracted media, decisions and
historical conversion audits. galaxy3.before-refinement.json is the old
157-build snapshot; galaxy3.before-full-export.json is the later 139-build
snapshot. Files named *.before-full-export.* document the superseded cleanup.

_source/refine_json.py is the current exporter. It rebuilds from all 161
normalizedCandidates, before any duplicate selection, and validates them
against the numeric source candidates and confirmed decisions. Run without
--apply to preview; add --apply to save. Historical deduplicatedCandidates
and duplicateSelections are audit data and are not used for the current output.
_source/refinement-report.json records the export and restored images.
_source/current-image-manifest.json lists the referenced original images.
_source/validation-report.json records verification of the current output.
