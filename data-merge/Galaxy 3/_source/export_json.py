"""Export and validate Galaxy 3 after all user clarifications are resolved."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from PIL import Image

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parent

def read(name):
    return json.loads((SOURCE / name).read_text(encoding='utf-8'))

def require(condition, message):
    if not condition:
        raise ValueError(message)

decisions = read('import-decisions.json')
require(not decisions.get('outputRefinement'),
        'The final dataset now uses the newer refinement rules. This historical exporter is disabled to avoid restoring removed data/images; use refine_json.py for the current output.')
normalized = read('normalized-candidates.json')
manifest = read('image-manifest.json')
audit = read('source-audit.json')
numeric = read('cost-candidates.json')
require(not decisions.get('nextEntryToReview'), 'A clarification is still pending')
require(not decisions.get('pendingImageDiscrepancies'), 'An image discrepancy is still pending')
require(not normalized['unresolved'], 'A caption annotation is still unresolved')
require(not numeric['specialCases'], 'A numeric extraction case is still unresolved')

records = normalized['deduplicatedCandidates']
grouped = {}
for record in records:
    group = grouped.setdefault(record['stage'], {}).setdefault(record['multiplier'], [])
    group.append({**record['build'], 'source': record['source']})

dataset = {
    'formatVersion': 1,
    'galaxy': 3,
    'source': {
        'title': 'G3 Spreadsheet',
        'url': f"https://docs.google.com/spreadsheets/d/{decisions['spreadsheetId']}/edit",
    },
    'stages': [
        {'stage': stage, 'multipliers': [
            {'multiplier': mult, 'builds': mults[mult]}
            for mult in sorted(mults, key=lambda value: Decimal(value[:-1]))
        ]} for stage, mults in grouped.items()
    ],
}

# Validate every output image against the original workbook media, including unused alternatives.
images = {entry['output_file']: entry for entry in manifest['images']}
require(len(images) == len(manifest['images']), 'Duplicate image filenames in manifest')
require(len(list((ROOT / 'images').glob('*'))) == len(images), 'Unexpected image files')
stage_image_numbers = defaultdict(list)
for name, entry in images.items():
    path = (ROOT / name).resolve()
    require(path.parent == (ROOT / 'images').resolve(), f'Image path escapes images directory: {name}')
    match = re.fullmatch(r'(B(?:B)?\d+[AB]?)_(\d+)\.png', path.name)
    require(match and match.group(1) == entry['stage'], f'Invalid image filename: {name}')
    stage_image_numbers[entry['stage']].append(int(match.group(2)))
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == entry['sha256'], f'Image hash mismatch: {name}')
    require(data == Path(entry['local_file']).read_bytes(), f'Image differs from source: {name}')
    with Image.open(path) as img:
        require(img.format == 'PNG' and list(img.size) == entry['dimensions'], f'Image dimensions/format differ: {name}')
        img.verify()
for stage, numbers in stage_image_numbers.items():
    require(sorted(numbers) == list(range(1, len(numbers) + 1)), f'Nonconsecutive image numbering: {stage}')

excluded_entries = {(entry['sheet'], entry['cell']) for entry in decisions['excludedEntries']}
excluded_variants = {(entry['sheet'], entry['cell'], entry['multiplier']) for entry in decisions['excludedVariants']}
source_cells = {(cell['sheet'], cell['cell']): cell for cell in audit['cells']}
allowed_fields = {'cost', 'lightChoices', 'lightChoiceAlternatives', 'image', 'comments', 'source',
                  'base', 'baseKill', 'baseShots', 'baseDamage', 'costBasis', 'baseDamageBasis',
                  'sameBuildForAllShots', 'costFractionalPart', 'costFractionalPartStatus', 'equipmentRequirements'}
flattened = []
used_images = set()
for stage in dataset['stages']:
    require(re.fullmatch(r'B(?:B)?\d+[AB]?', stage['stage']), 'Invalid stage name')
    for multiplier in stage['multipliers']:
        require(re.fullmatch(r'\d+\.\d+x', multiplier['multiplier']), 'Invalid exact multiplier')
        require(multiplier['builds'], 'Empty multiplier group')
        for build in multiplier['builds']:
            require(set(build) <= allowed_fields, f'Unexpected fields: {set(build) - allowed_fields}')
            require(type(build['cost']) in (int, float) and build['cost'] >= 0, 'Invalid cost')
            require(isinstance(build['comments'], str), 'Comments must be a string')
            require(('lightChoices' in build) != ('lightChoiceAlternatives' in build), 'Light choices must be exact or alternatives')
            choices = build.get('lightChoiceAlternatives', [build.get('lightChoices', {})])
            for choice in choices:
                require(isinstance(choice, dict), 'Light choices must map slots to ships')
                require(all(re.fullmatch(r'L\d+', slot) and ship in ('Frigate', 'Corvette') for slot, ship in choice.items()), 'Invalid Light choice')
            for field in ('base', 'baseKill', 'sameBuildForAllShots'):
                if field in build:
                    require(type(build[field]) is bool, f'{field} must be boolean')
            if 'baseShots' in build:
                require(type(build['baseShots']) is int and build['baseShots'] > 0, 'Invalid shot count')
            if 'baseDamage' in build:
                require(type(build['baseDamage']) in (int, float) and build['baseDamage'] >= 0, 'Invalid base damage')
            if build.get('baseKill'):
                require(build.get('base') is True, 'Base kill requires a base')
            if build.get('base') is False:
                require(build.get('baseKill') is False, 'Base-free build cannot kill a base')
            key = (build['source']['sheet'], build['source']['cell'])
            require(key not in excluded_entries, f'Excluded entry present: {key}')
            require((*key, multiplier['multiplier']) not in excluded_variants, 'Excluded variant present')
            require(source_cells[key]['active'], f'Struck-through or missing caption retained: {key}')
            if build['image']:
                require(build['image'] in images, 'Broken image reference')
                require(images[build['image']]['stage'] == stage['stage'], 'Image belongs to a different stage')
                used_images.add(build['image'])
            else:
                require(key == ('B1 - B4B', 'G16'), 'Unexpected missing image')
            flattened.append((stage['stage'], multiplier['multiplier'], build))

def find(stage, mult, sheet, cell):
    return [b for s, m, b in flattened if (s, m, b['source']['sheet'], b['source']['cell']) == (stage, mult, sheet, cell)]

def one(stage, mult, sheet, cell):
    found = find(stage, mult, sheet, cell)
    require(len(found) == 1, f'Expected one build for {stage} {mult} {cell}')
    return found[0]

# Check the user's corrections against final fields, not just intermediate parser output.
for override in [*decisions['acceptedEntryOverrides'], *decisions['acceptedVariantOverrides']]:
    if 'multiplier' not in override:
        continue
    build = one(override['stage'], override['multiplier'], override['sheet'], override['cell'])
    for field in ('base', 'baseKill', 'baseShots', 'sameBuildForAllShots', 'lightChoices', 'comments'):
        if field in override:
            require(build[field] == override[field], f'User override not honored: {override["cell"]} {field}')
    if 'cost' in override:
        require(Decimal(str(build['cost'])) == Decimal(override['cost']), 'User-confirmed cost differs')
    if 'baseDamage' in override:
        require(Decimal(str(build['baseDamage'])) == Decimal(override['baseDamage']), 'User-confirmed damage differs')
    if override.get('equipmentInComments'):
        require('equipmentRequirements' not in build, 'Comment-only equipment leaked into structured fields')

for mult in ('1.7x', '1.8x'):
    choices = find('B6B', mult, 'B5A-B9', 'D6')
    require({b['cost'] for b in choices} == {31, 51}, 'Both B6B cost configurations must survive')
    cheap = next(b for b in choices if b['cost'] == 31)
    require(cheap['lightChoiceAlternatives'] == [{'L1': 'Frigate', 'L2': 'Corvette'}, {'L1': 'Corvette', 'L2': 'Frigate'}], 'B6B purchase orders differ')
    require(next(b for b in choices if b['cost'] == 51)['lightChoices'] == {}, 'B6B 51 requires no Light purchases')
for mult in ('1.2x', '1.4x'):
    require(one('B3B', mult, 'B1 - B4B', 'E6')['lightChoices'] == {'L1': 'Corvette'}, 'Trailing Light requirement not shared')
require(one('B2B', '2.375x', 'B1 - B4B', 'C2')['lightChoices'] == {}, 'Non-trailing Light note incorrectly propagated')
require(one('B7B', '2.375x', 'B5A-B9', 'F6')['costFractionalPart'] is None, 'Unknown fractional cost was invented')
for mult in ('2.15x', '2.125x'):
    require(one('B6B', mult, 'B5A-B9', 'D8')['comments'] == '', 'Local equipment comment incorrectly propagated')
require(not find('B2A', '1.8x', 'B1 - B4B', 'B16'), 'Partially struck variant retained')
require(not find('B6B', '2.225x', 'B5A-B9', 'D8'), 'Partially struck variant retained')
for row in normalized['duplicateSelections']:
    require(not find(row['stage'], row['multiplier'], row['omittedSource']['sheet'], row['omittedSource']['cell']), 'Discarded duplicate survived')
    kept = one(row['stage'], row['multiplier'], row['keptSource']['sheet'], row['keptSource']['cell'])
    require(kept['cost'] == row['keptCost'] <= row['omittedCost'], 'Cheapest duplicate was not selected')
require(len(records) == len(flattened) == 157, 'Unexpected build count')
require(len(dataset['stages']) == 17 and len(images) == 108, 'Unexpected stage or image count')

# Write only after all content, references and original-image checks pass.
text = json.dumps(dataset, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
require(json.loads(text) == dataset, 'JSON serialization changed data')
output = ROOT / 'galaxy3.json'
output.write_text(text, encoding='utf-8')
require(json.loads(output.read_text(encoding='utf-8')) == dataset, 'Saved JSON differs from validated data')

report = {
    'status': 'passed', 'output': 'galaxy3.json',
    'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
    'stages': len(dataset['stages']),
    'exactMultiplierGroups': sum(len(s['multipliers']) for s in dataset['stages']),
    'builds': len(flattened), 'originalImages': len(images), 'imagesReferenced': len(used_images),
    'buildsWithEmptyImage': sum(not b['image'] for _, _, b in flattened),
    'originalImagesNotNeededAfterDeduplication': sorted(set(images) - used_images),
    'duplicatesRemoved': len(normalized['duplicateSelections']),
    'checks': [
        'JSON round trip and field types', 'Every nonempty image reference resolves to the correct stage',
        'All 108 image bytes, SHA-256 hashes, dimensions and formats match the source originals',
        'Sequential per-stage image naming', 'User-confirmed values, comments and omissions',
        'Two valid Light purchase orders retained for B6B', 'Trailing versus local Light annotation scope',
        'Unspecified fractional cost preserved', 'Struck-through variants excluded',
        'Cheapest matching builds selected', 'Distinct base and Light configurations preserved',
    ],
    'byStage': [{'stage': stage['stage'], 'multiplierGroups': len(stage['multipliers']),
                 'builds': sum(len(m['builds']) for m in stage['multipliers'])} for stage in dataset['stages']],
}
(SOURCE / 'validation-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
decisions['status'] = 'Complete. galaxy3.json contains 157 builds across 17 stages; all 108 original images and final data checks passed.'
decisions['output'] = {k: report[k] for k in ('output', 'sha256', 'stages', 'exactMultiplierGroups', 'builds', 'originalImages', 'imagesReferenced', 'buildsWithEmptyImage')}
decisions['output']['validationReport'] = '_source/validation-report.json'
(SOURCE / 'import-decisions.json').write_text(json.dumps(decisions, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k not in ('checks', 'byStage')}, indent=2))
