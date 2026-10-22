"""Export every approved Galaxy 3 build and exact multiplier with recorded decimals.

The 2026-10-22 instructions supersede cost truncation and all cheapest-build/
consecutive-multiplier selection. The pre-selection candidates are authoritative.
Run without --apply to validate and preview; --apply updates the local artifacts.
"""
import argparse
import copy
import hashlib
import json
import re
import shutil
from collections import Counter
from decimal import Decimal
from pathlib import Path
from PIL import Image

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parent
DATA = ROOT / 'galaxy3.json'
IMAGE_ROOT = (ROOT / 'images').resolve()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(name):
    return json.loads((SOURCE / name).read_text(encoding='utf-8'))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def clean(value):
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, dict):
        out = {key: clean(child) for key, child in value.items() if key != 'source'}
        if isinstance(out.get('comments'), str) and out['comments'].strip().lower().startswith('by '):
            out['comments'] = ''
        return out
    return value


def rows(data):
    return [(s['stage'], m['multiplier'], b)
            for s in data['stages'] for m in s['multipliers'] for b in m['builds']]


def build_dataset(records):
    grouped = {}
    for record in sorted(records, key=lambda r: r['sourceIndex']):
        grouped.setdefault(record['stage'], {}).setdefault(record['multiplier'], []).append(clean(record['build']))
    return {
        'formatVersion': 1, 'galaxy': 3,
        'stages': [
            {'stage': stage, 'multipliers': [
                {'multiplier': mult, 'builds': mults[mult]}
                for mult in sorted(mults, key=lambda value: Decimal(value[:-1]))
            ]} for stage, mults in grouped.items()
        ],
    }


def validate_records(records, numeric, decisions, audit):
    require(len(records) == len(numeric) == 161, 'Approved source candidate count changed')
    require(sorted(r['sourceIndex'] for r in records) == list(range(len(numeric))), 'Source candidate missing or repeated')
    excluded = {(r['sheet'], r['cell']) for r in decisions['excludedEntries']}
    excluded_variants = {(r['sheet'], r['cell'], r['multiplier']) for r in decisions['excludedVariants']}
    cells = {(r['sheet'], r['cell']): r for r in audit['cells']}
    allowed = {'cost', 'lightChoices', 'lightChoiceAlternatives', 'image', 'comments',
               'base', 'baseKill', 'baseShots', 'baseDamage', 'costBasis', 'baseDamageBasis',
               'sameBuildForAllShots', 'costFractionalPart', 'costFractionalPartStatus',
               'equipmentRequirements'}
    for record in records:
        build = record['build']
        candidate = numeric[record['sourceIndex']]
        key = (record['source']['sheet'], record['source']['cell'])
        require(key not in excluded and (*key, record['multiplier']) not in excluded_variants,
                f'Explicit exclusion retained: {key}')
        require(cells[key]['active'], f'Inactive caption retained: {key}')
        require((record['stage'], record['multiplier'], *key) ==
                (candidate['stage'], candidate['multiplier'], candidate['sourceSheet'], candidate['sourceCell']),
                f'Candidate identity differs: {key}')
        require(re.fullmatch(r'B(?:B)?\d+[AB]?', record['stage']), 'Invalid stage')
        require(re.fullmatch(r'\d+\.\d+x', record['multiplier']), 'Multiplier must be one exact value')
        require(set(build) <= allowed, f'Unexpected build fields: {set(build) - allowed}')
        require(type(build['cost']) in (int, float) and build['cost'] >= 0, 'Invalid cost')
        require(Decimal(str(build['cost'])) == Decimal(candidate['cost']), f'Cost precision lost: {key}')
        require(build['image'] == candidate['image'], f'Image assignment changed: {key}')
        require(isinstance(build['comments'], str), 'Comments must be a string')
        require(('lightChoices' in build) != ('lightChoiceAlternatives' in build), 'Invalid Light choice representation')
        choices = build.get('lightChoiceAlternatives', [build.get('lightChoices', {})])
        require(choices, 'Empty Light alternative list')
        for choice in choices:
            require(isinstance(choice, dict) and all(re.fullmatch(r'L\d+', slot) and ship in ('Frigate', 'Corvette')
                                                    for slot, ship in choice.items()), 'Invalid Light choices')
        for field in ('base', 'baseKill', 'sameBuildForAllShots'):
            if field in build:
                require(type(build[field]) is bool, f'{field} must be boolean')
        if 'baseShots' in build:
            require(type(build['baseShots']) is int and build['baseShots'] > 0, 'Invalid shot count')
        if 'baseDamage' in build:
            require(type(build['baseDamage']) in (int, float) and build['baseDamage'] >= 0, 'Invalid base damage')
            if 'baseDamage' in candidate:
                require(Decimal(str(build['baseDamage'])) == Decimal(candidate['baseDamage']), 'Base damage precision lost')
        if build.get('baseKill'):
            require(build.get('base') is True, 'Base kill requires a base')
        if build.get('base') is False:
            require(build.get('baseKill') is False, 'Base-free build cannot kill a base')
        if not build['image']:
            require(key == ('B1 - B4B', 'G16'), 'Unexpected missing image')

    def find(stage, mult, sheet, cell):
        return [r['build'] for r in records if
                (r['stage'], r['multiplier'], r['source']['sheet'], r['source']['cell']) == (stage, mult, sheet, cell)]

    def one(stage, mult, sheet, cell):
        matches = find(stage, mult, sheet, cell)
        require(len(matches) == 1, f'Expected one build: {stage} {mult} {cell}')
        return matches[0]

    for override in [*decisions['acceptedEntryOverrides'], *decisions['acceptedVariantOverrides']]:
        build = one(override['stage'], override['multiplier'], override['sheet'], override['cell'])
        for field in allowed - {'costFractionalPart', 'costFractionalPartStatus'}:
            if field in override:
                expected = Decimal(override[field]) if field in ('cost', 'baseDamage') else override[field]
                actual = Decimal(str(build[field])) if field in ('cost', 'baseDamage') else build[field]
                require(actual == expected, f'Confirmed override differs: {override["cell"]} {field}')
        if override.get('equipmentInComments'):
            require('equipmentRequirements' not in build, 'Comment-only equipment became structured data')
        if 'fractionalPartStatus' in override:
            require(build['costFractionalPart'] == override['fractionalPart'] and
                    build['costFractionalPartStatus'] == override['fractionalPartStatus'], 'Unknown fraction changed')
    for mult in ('1.7x', '1.8x'):
        choices = find('B6B', mult, 'B5A-B9', 'D6')
        require({b['cost'] for b in choices} == {31, 51}, 'B6B configuration lost')
        require(next(b for b in choices if b['cost'] == 31)['lightChoiceAlternatives'] ==
                [{'L1': 'Frigate', 'L2': 'Corvette'}, {'L1': 'Corvette', 'L2': 'Frigate'}], 'B6B purchase orders changed')
        require(next(b for b in choices if b['cost'] == 51)['lightChoices'] == {}, 'B6B no-Light choice changed')
    for mult in ('1.2x', '1.4x'):
        require(one('B3B', mult, 'B1 - B4B', 'E6')['lightChoices'] == {'L1': 'Corvette'}, 'Trailing Light note lost')
    require(one('B2B', '2.375x', 'B1 - B4B', 'C2')['lightChoices'] == {}, 'Non-trailing Light note propagated')
    for mult in ('2.15x', '2.125x'):
        require(one('B6B', mult, 'B5A-B9', 'D8')['comments'] == '', 'Local equipment note propagated')
    require(not find('B2A', '1.8x', 'B1 - B4B', 'B16'), 'Partially struck variant retained')
    require(not find('B6B', '2.225x', 'B5A-B9', 'D8'), 'Partially struck variant retained')


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    apply = parser.parse_args().apply
    decisions, normalized, numeric = read('import-decisions.json'), read('normalized-candidates.json'), read('cost-candidates.json')
    require(not decisions.get('nextEntryToReview') and not decisions.get('pendingImageDiscrepancies'), 'Clarification pending')
    require(not normalized['unresolved'] and not numeric['specialCases'], 'Unresolved source data')
    records = normalized['normalizedCandidates']  # Intentionally bypass every earlier deduplication step.
    validate_records(records, numeric['candidates'], decisions, read('source-audit.json'))
    data = build_dataset(records)
    expected = Counter(canonical((r['stage'], r['multiplier'], clean(r['build']))) for r in records)
    require(Counter(canonical(row) for row in rows(data)) == expected, 'A build was removed, duplicated or changed')
    require(clean(data) == data and build_dataset(records) == data, 'Export is not stable')
    require(len(data['stages']) == 17 and sum(len(s['multipliers']) for s in data['stages']) == 145, 'Multiplier coverage changed')

    manifest = read('image-manifest.json')
    image_info = {entry['output_file']: entry for entry in manifest['images']}
    require(len(image_info) == len(manifest['images']), 'Repeated image filename')
    used = {b['image'] for _, _, b in rows(data) if b['image']}
    require(used <= image_info.keys(), 'Image absent from original manifest')
    for stage, _, build in rows(data):
        if build['image']:
            require(image_info[build['image']]['stage'] == stage, 'Image assigned to wrong stage')
    existing, source_images = {}, {}
    for path in IMAGE_ROOT.iterdir():
        name = path.relative_to(ROOT).as_posix()
        require(path.is_file() and not path.is_symlink() and path.resolve().parent == IMAGE_ROOT, 'Unexpected image path')
        require(name in image_info, f'Unrecognized image: {name}')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == image_info[name]['sha256'], f'Changed image: {name}')
        existing[name] = path
    for name in sorted(used):
        entry = image_info[name]
        path = (SOURCE / 'embedded-images' / Path(entry['media_path']).name).resolve()
        require(path.parent == (SOURCE / 'embedded-images').resolve(), 'Archive path escaped its directory')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], f'Original image hash differs: {name}')
        with Image.open(path) as img:
            require(img.format == entry['format'] == 'PNG' and list(img.size) == entry['dimensions'], f'Image format/dimensions differ: {name}')
            img.verify()
        require(re.fullmatch(re.escape(entry['stage']) + r'_\d+\.png', Path(name).name), 'Invalid image filename')
        source_images[name] = path
    missing, unused = sorted(used - existing.keys()), sorted(existing.keys() - used)
    before = json.loads(DATA.read_text(encoding='utf-8'))
    output_text = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    require(json.loads(output_text) == data, 'JSON round trip failed')
    report = {
        'status': 'passed' if apply else 'ready', 'output': 'galaxy3.json',
        'buildsBefore': len(rows(before)), 'builds': len(records), 'stages': len(data['stages']),
        'exactMultiplierGroups': sum(len(s['multipliers']) for s in data['stages']),
        'buildsWithFractionalCosts': sum(Decimal(str(b['cost'])) % 1 != 0 for _, _, b in rows(data)),
        'buildsWithUnspecifiedCostFraction': sum('costFractionalPartStatus' in b for _, _, b in rows(data)),
        'imagesReferenced': len(used), 'imagesToRestore': missing, 'unusedImagesToDelete': unused,
        'buildsWithEmptyImage': sum(not b['image'] for _, _, b in rows(data)),
        'outputAlreadyCurrent': before == data,
        'checks': ['All 161 approved source candidates retained exactly once',
                   'All 145 exact stage/multiplier groups retained without consolidation',
                   'Every cost matches its source candidate including all recorded decimal digits',
                   'Explicit omissions, missing-cost exclusions and struck-through variants remain excluded',
                   'Confirmed Base, Light, equipment, comments and unspecified-fraction decisions preserved',
                   'Each multiplier/build has its own entry; shared image references preserved',
                   'Source metadata and standalone source attribution comments removed',
                   'All referenced original images pass SHA-256, PNG and dimension checks',
                   'JSON round trip and deterministic rebuild passed'],
    }
    if apply:
        for name in missing:
            target = (ROOT / name).resolve()
            require(target.parent == IMAGE_ROOT and not target.exists(), f'Unsafe restoration target: {name}')
            shutil.copy2(source_images[name], target)
            require(hashlib.sha256(target.read_bytes()).hexdigest() == image_info[name]['sha256'], 'Restored image differs')
        temp = ROOT / 'galaxy3.refinement.tmp'
        temp.write_text(output_text, encoding='utf-8')
        temp.replace(DATA)
        for name in unused:
            path = existing[name]
            require(path.resolve().parent == IMAGE_ROOT and name not in used, 'Unsafe image deletion')
            path.unlink()
        require({p.relative_to(ROOT).as_posix() for p in IMAGE_ROOT.iterdir()} == used, 'Image set differs from references')
        require(json.loads(DATA.read_text(encoding='utf-8')) == data, 'Saved output differs')
        report['restoredImages'] = report.pop('imagesToRestore')
        report['deletedImages'] = report.pop('unusedImagesToDelete')
        report['sha256'] = hashlib.sha256(DATA.read_bytes()).hexdigest()
        report['checks'].append('images/ contains exactly the files referenced by the saved JSON')
        write_json(SOURCE / 'validation-report.json', report)
        write_json(SOURCE / 'refinement-report.json', report)
        write_json(SOURCE / 'current-image-manifest.json', {
            'images': [e for e in manifest['images'] if e['output_file'] in used],
            'numbering': 'Original per-stage filenames preserved; all referenced originals restored.',
        })
        if decisions.get('outputRefinement', {}).get('selection') != 'all approved builds':
            decisions.setdefault('outputRuleHistory', []).append({
                'supersededOn': '2026-10-22', 'rules': copy.deepcopy(decisions.get('outputRefinement', {})),
                'reason': 'User requested every listed multiplier, decimals, and all builds.',
            })
        decisions['confirmedRules']['duplicateBuilds'] = 'Keep all approved builds, including more expensive alternatives and matching requirements; no cheapest-build selection.'
        decisions['confirmedRules']['costPrecision'] = 'Preserve all recorded decimal digits. Keep the explicitly unspecified fractional part unknown.'
        decisions['confirmedRules']['multiplierCoverage'] = 'Keep every listed exact multiplier with all its approved builds; never consolidate across multipliers.'
        decisions['outputRefinement'] = {
            'selection': 'all approved builds',
            'costs': decisions['confirmedRules']['costPrecision'],
            'sameMultiplier': decisions['confirmedRules']['duplicateBuilds'],
            'consecutiveMultipliers': decisions['confirmedRules']['multiplierCoverage'],
            'exclusions': 'Explicitly omitted entries, missing-cost entries and struck-through text remain excluded.',
            'baseClarification': 'Base and no-base builds remain separate.',
            'sourceInformation': 'Root/per-build source fields and standalone author attributions are omitted.',
            'imageCleanup': 'Keep exactly referenced originals, restoring archived images as needed; preserve filenames.',
            'script': '_source/refine_json.py',
            'authority': ['We should list every listed multiplier and also have the decimals.', 'Also all builds.'],
        }
        decisions['normalization']['duplicateSelectionStatus'] = 'Historical comparison only; current output uses all normalizedCandidates.'
        decisions['status'] = f"Complete: {len(records)} builds, 145 exact multiplier groups, {len(used)} images, original decimal costs and no source metadata."
        decisions['output'] = {k: report[k] for k in ('output', 'sha256', 'stages', 'exactMultiplierGroups', 'builds', 'imagesReferenced', 'buildsWithEmptyImage')}
        decisions['output']['validationReport'] = '_source/validation-report.json'
        write_json(SOURCE / 'import-decisions.json', decisions)
    else:
        write_json(SOURCE / 'refinement-plan.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'checks'}, indent=2))


if __name__ == '__main__':
    main()
