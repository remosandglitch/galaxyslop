Galaxy 3 data

galaxy3.json contains the final data, organized as stages -> multipliers -> builds.
images/ contains the original full-size PNGs, named <stage>_<number>.png.
Images were copied without resizing or re-encoding. Original filenames are
preserved; gaps in numbering result from deleting unused images.

Fields

stage: Stage name, such as B2A or BB1.
multiplier: A listed value such as "1.0x". Consecutive entries with the same
  integer cost and same build/layout keep only their lowest multiplier.
  This does not establish results at unlisted intermediate multipliers.
cost: Integer cost. Fractional digits are discarded, not rounded.
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

Source fields, source-attribution comments and fractional-cost metadata have
been removed from galaxy3.json. Base damage retains its original precision.

Hazards and Supports are optional and are omitted for Galaxy 3. Base fields
are omitted on stages where they are not applicable. Unknown shot counts
and unstated damage are omitted rather than filled with zero.

Selection and source notes

At the same stage/multiplier, only the cheapest build is kept for matching
Hazards, Supports, Light choices and Base status. Equipment or layout
differences do not keep a more expensive build at that same multiplier.
For equal integer costs with matching requirements, the first entry is kept.

Across consecutive multipliers, equal costs are consolidated only when the
build/layout also matches. Different layouts remain separate. Price increases,
decreases and returns to an earlier price are all retained. A different layout
or an interrupted sequence starts a new run. Base and no-base builds remain
separate, as explicitly confirmed.

Struck-through text and all agreed exclusions were removed from the dataset.
images/ contains only files referenced by the final JSON. Unused output images
were deleted locally. The agreed entry with no image still uses an empty path.

The confirmed caption values take precedence over the screenshots for
B3B E10 (2.375x, cost 10) and B10 B6 (3.725x, cost 62, Base false).

_source/ preserves the original workbook, extracted media, decisions and
historical conversion audits. galaxy3.before-refinement.json is the previous
157-build snapshot. Earlier export scripts describe that historical snapshot;
refine_json.py applies the latest cost, consolidation and cleanup rules.
_source/refinement-report.json records each removed entry and image.
_source/current-image-manifest.json lists the retained original images.
_source/validation-report.json records verification of the current output.
