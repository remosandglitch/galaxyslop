"""Apply the user's integer-cost, consecutive-build and image-cleanup rules."""
import argparse
import copy
import hashlib
import json
from decimal import Decimal
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parent
DATA = ROOT / 'galaxy3.json'
IMAGE_ROOT = (ROOT / 'images').resolve()

# These two screenshots were inspected: Frigate A1; Corvettes A2/B4;
# Corvette Shield; no Frigate equipment. Only the screenshot/skin differs.
LAYOUT_EQUIVALENTS = {'images/B7B_5.png': 'images/B7B_4.png'}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))

def requirement_key(build):
    choices = build.get('lightChoiceAlternatives', [build.get('lightChoices', {})])
    return canonical({
        'hazards': build.get('hazards'), 'supports': build.get('supports'),
        'lights': sorted(canonical(choice) for choice in choices),
        'base': build.get('base'),
    })

def clean(value):
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, dict):
        out = {k: clean(v) for k, v in value.items()
               if k not in ('source', 'costFractionalPart', 'costFractionalPartStatus')}
        if 'cost' in out:
            out['cost'] = int(Decimal(str(out['cost'])))
        if isinstance(out.get('comments'), str) and out['comments'].strip().lower().startswith('by '):
            out['comments'] = ''
        return out
    return value

def build_key(build):
    data = {k: v for k, v in build.items() if k != 'cost'}
    data['image'] = LAYOUT_EQUIVALENTS.get(build['image'], build['image'])
    return canonical(data)

def short(stage, mult, build):
    return {'stage': stage, 'multiplier': mult, 'cost': build['cost'],
            'image': build['image'], 'requirements': json.loads(requirement_key(build))}

def refine(original):
    data = clean(copy.deepcopy(original))
    same_multiplier, consecutive = [], []
    for stage in data['stages']:
        previous, output_groups = {}, []
        for group in sorted(stage['multipliers'], key=lambda g: Decimal(g['multiplier'][:-1])):
            current = {}
            for build in group['builds']:
                key = requirement_key(build)
                if key not in current:
                    current[key] = build
                else:
                    old = current[key]
                    keep, drop = (build, old) if build['cost'] < old['cost'] else (old, build)
                    current[key] = keep
                    same_multiplier.append({'kept': short(stage['stage'], group['multiplier'], keep),
                                            'removed': short(stage['stage'], group['multiplier'], drop)})
            kept = []
            new_previous = {}
            for key, build in current.items():
                prior = previous.get(key)
                if prior and prior['build']['cost'] == build['cost'] and build_key(prior['build']) == build_key(build):
                    consecutive.append({'keptAtMultiplier': prior['runStart'],
                                        'removed': short(stage['stage'], group['multiplier'], build)})
                    run_start = prior['runStart']
                else:
                    kept.append(build)
                    run_start = group['multiplier']
                new_previous[key] = {'build': build, 'runStart': run_start}
            # Compare against every preceding listed multiplier, including suppressed
            # rows. A price change or different layout always starts a new run.
            previous = new_previous
            if kept:
                output_groups.append({'multiplier': group['multiplier'], 'builds': kept})
        stage['multipliers'] = output_groups
    return data, same_multiplier, consecutive

def rows(data):
    return [(s['stage'], m['multiplier'], b) for s in data['stages'] for m in s['multipliers'] for b in m['builds']]

def assert_clean(value):
    if isinstance(value, dict):
        require('source' not in value, 'Source metadata remains in final JSON')
        require('costFractionalPart' not in value and 'costFractionalPartStatus' not in value, 'Fractional-cost metadata remains')
        if 'cost' in value:
            require(type(value['cost']) is int, 'A cost is not an integer')
        for child in value.values():
            assert_clean(child)
    elif isinstance(value, list):
        for child in value:
            assert_clean(child)

def main():
    args = argparse.ArgumentParser()
    args.add_argument('--apply', action='store_true')
    apply = args.parse_args().apply
    before_bytes = DATA.read_bytes()
    original = json.loads(before_bytes)
    data, duplicate_removals, run_removals = refine(original)
    assert_clean(data)
    # An idempotence check detects accidental cascading removal of nonconsecutive rows.
    second, second_duplicates, second_runs = refine(data)
    require(second == data and not second_duplicates and not second_runs, 'Refinement is not stable')
    before_rows, after_rows = rows(original), rows(data)
    for stage in data['stages']:
        for group in stage['multipliers']:
            keys = [requirement_key(b) for b in group['builds']]
            require(len(keys) == len(set(keys)), 'Duplicate requirements remain at one multiplier')
    # Every retained build must come from the input with only the requested edits.
    for stage, mult, build in after_rows:
        require(any(s == stage and m == mult and clean(b) == build for s, m, b in before_rows), 'Unexpected build mutation')
    require([s['stage'] for s in data['stages']] == [s['stage'] for s in original['stages']], 'Stage lost during refinement')

    manifest = json.loads((SOURCE / 'image-manifest.json').read_text(encoding='utf-8'))
    image_info = {entry['output_file']: entry for entry in manifest['images']}
    used_images = {b['image'] for _, _, b in after_rows if b['image']}
    existing = {}
    for path in IMAGE_ROOT.iterdir():
        require(path.is_file() and not path.is_symlink(), f'Unexpected entry in images/: {path.name}')
        require(path.resolve().parent == IMAGE_ROOT, 'Image path escapes the intended directory')
        name = path.relative_to(ROOT).as_posix()
        require(name in image_info, f'Unrecognized image: {name}')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == image_info[name]['sha256'], f'Image content changed: {name}')
        existing[name] = path
    require(used_images <= existing.keys(), 'A referenced image is missing')
    unused = sorted(set(existing) - used_images)

    # Confirm real timing reversals and the user's clarified exceptions.
    lookup = {(s, m): [b for ss, mm, b in after_rows if ss == s and mm == m] for s, m, _ in after_rows}
    def costs(stage, mult):
        return {b['cost'] for b in lookup.get((stage, mult), [])}
    require([costs('B8', m) for m in ('2.65x', '2.825x', '2.975x')] == [{29}, {30}, {29}], 'B8 cost increase/return was lost')
    require([costs('B6B', m) for m in ('2.025x', '2.125x', '2.15x')] == [{22}, {21}, {22}], 'B6B cost reversal was lost')
    for mult, expected in [('3.05x', {170, 82}), ('3.725x', {110, 62})]:
        require(costs('B10', mult) == expected, 'Base and no-base builds were merged')
        require({b['base'] for b in lookup[('B10', mult)]} == {True, False}, 'Base states were not preserved')
    require(14 in costs('B2A', '1.1x') and 14 in costs('B2A', '1.2x'), 'Different layouts were merged')
    require(22 not in costs('B2A', '1.1x') and 20 in costs('B2A', '1.1x'), 'Cheapest same-multiplier build was not selected')
    require(costs('B7B', '2.9x') == {19} and not costs('B7B', '3.25x'), 'Equivalent B7B layout was not consolidated')

    report = {
        'status': 'passed' if apply else 'ready', 'output': 'galaxy3.json',
        'buildsBefore': len(before_rows), 'builds': len(after_rows),
        'stages': len(data['stages']),
        'exactMultiplierGroups': sum(len(s['multipliers']) for s in data['stages']),
        'costsTruncated': sum(Decimal(str(b['cost'])) != int(Decimal(str(b['cost']))) for _, _, b in before_rows),
        'sameMultiplierBuildsRemoved': duplicate_removals,
        'consecutiveBuildsRemoved': run_removals,
        'imagesReferenced': len(used_images), 'unusedImagesToDelete': unused,
        'buildsWithEmptyImage': sum(not b['image'] for _, _, b in after_rows),
        'layoutEvidence': {
            'equivalent': [{'images': ['images/B7B_4.png', 'images/B7B_5.png'],
                            'placement': {'A1': 'Frigate', 'A2': 'Corvette', 'B4': 'Corvette'},
                            'equipment': 'Corvette Shield; no Frigate equipment'}],
            'differentLayoutsVisuallyChecked': [
                ['B2A_3.png', 'B2A_4.png'], ['B2A_8.png', 'B2A_7.png'],
                ['B4A_4.png', 'B4A_3.png'], ['B5A_3.png', 'B5A_4.png'],
                ['B5B_5.png', 'B5B_6.png'], ['B6A_3.png', 'B6A_4.png'],
                ['B6B_4.png', 'B6B_5.png'],
            ],
        },
        'checks': ['All costs are integers, truncated rather than rounded',
                   'Source metadata and source attribution comments removed',
                   'Same-multiplier minimum uses hazards, supports, Light choices and Base status',
                   'Consecutive equal costs collapse only for the same build/layout',
                   'Both directions of timing-related cost changes preserved',
                   'Base/no-base and different-layout exceptions preserved',
                   'Every referenced image exists and matches the original SHA-256',
                   'Changes are stable when applied again'],
    }
    if apply:
        backup = SOURCE / 'galaxy3.before-refinement.json'
        if not backup.exists():
            backup.write_bytes(before_bytes)
        output_text = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
        require(json.loads(output_text) == data, 'JSON round trip failed')
        temp = ROOT / 'galaxy3.refinement.tmp'
        temp.write_text(output_text, encoding='utf-8')
        temp.replace(DATA)
        # Only explicit files within the checked images directory are deleted.
        # Source archives remain available separately under _source/.
        for name in unused:
            path = existing[name]
            require(path.resolve().parent == IMAGE_ROOT and name not in used_images, 'Unsafe image deletion target')
            path.unlink()
        remaining = {p.relative_to(ROOT).as_posix() for p in IMAGE_ROOT.iterdir()}
        require(remaining == used_images, 'Image cleanup does not match final references')
        require(json.loads(DATA.read_text(encoding='utf-8')) == data, 'Saved JSON differs from validated output')
        report['deletedImages'] = report.pop('unusedImagesToDelete')
        report['sha256'] = hashlib.sha256(DATA.read_bytes()).hexdigest()
        report['checks'].append('images/ contains exactly the images referenced by the final JSON')
        old_report = SOURCE / 'validation-report.json'
        historical_report = SOURCE / 'initial-validation-report.json'
        if old_report.exists() and not historical_report.exists():
            historical_report.write_bytes(old_report.read_bytes())
        old_report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        (SOURCE / 'refinement-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        current_manifest = {'images': [entry for entry in manifest['images'] if entry['output_file'] in used_images],
                            'numbering': 'Original filenames preserved; gaps after deletion are intentional.'}
        (SOURCE / 'current-image-manifest.json').write_text(json.dumps(current_manifest, indent=2) + '\n', encoding='utf-8')
        decisions_path = SOURCE / 'import-decisions.json'
        decisions = json.loads(decisions_path.read_text(encoding='utf-8'))
        decisions['outputRefinement'] = {
            'costs': 'Truncate all costs to integers and remove fractional-cost metadata.',
            'sameMultiplier': 'Keep the cheapest build for identical hazards, supports, Light choices and Base status; equipment/layout differences do not protect a more expensive build at the same multiplier.',
            'baseClarification': 'User explicitly confirmed keeping base and no-base builds separate.',
            'consecutiveMultipliers': 'Retain the lowest multiplier in an uninterrupted run with the same integer cost and same build/layout. Preserve rises, falls and returns to earlier costs.',
            'layoutClarification': 'User explicitly confirmed that different layouts stay separate across consecutive multipliers.',
            'sourceInformation': 'Removed root/per-build source fields and source-attribution comments from the output JSON.',
            'imageCleanup': 'Delete unreferenced output images locally; preserve filenames of retained images.',
            'script': '_source/refine_json.py',
        }
        decisions['status'] = f"Complete after refinement: {len(after_rows)} builds, {len(used_images)} referenced images, integer costs and no source metadata."
        decisions['output'] = {k: report[k] for k in ('output', 'sha256', 'stages', 'exactMultiplierGroups', 'builds', 'imagesReferenced', 'buildsWithEmptyImage')}
        decisions['output']['validationReport'] = '_source/validation-report.json'
        decisions_path.write_text(json.dumps(decisions, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    else:
        (SOURCE / 'refinement-plan.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('layoutEvidence', 'checks', 'sameMultiplierBuildsRemoved', 'consecutiveBuildsRemoved')}, indent=2))
    print(json.dumps({'sameMultiplierBuildsRemoved': len(duplicate_removals), 'consecutiveBuildsRemoved': len(run_removals)}))

if __name__ == '__main__':
    main()
