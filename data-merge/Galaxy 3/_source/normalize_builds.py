"""Normalize confirmed caption data, keeping unresolved interpretations out of Comments."""
import json
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))

def number(value):
    parsed = Decimal(str(value))
    return int(parsed) if parsed == parsed.to_integral_value() else float(parsed)

decisions = read('import-decisions.json')
candidates = read('cost-candidates.json')['candidates']
image_fields = {(x['sheet'], x['cell']): x for x in decisions.get('imageDerivedFields', [])}

# Only explicit, unambiguous equipment wording is normalized here.
equipment_notes = {
    '(W/ Corvette Shield)': {'ship': 'Corvette', 'shield': True},
    '(W/ Armour and Shield)': {'armour': True, 'shield': True},
    '(L1 - Corvette/Use Shield)': {'shield': True},
    '(L1 - Frigate W/Armour and shield)': {'ship': 'Frigate', 'armour': True, 'shield': True},
    '(L1 - Corvette w/CL and shield)': {'ship': 'Corvette', 'CL': True, 'shield': True},
    '(L1 corv, SH, no AR)': {'shield': True, 'armour': False},
}
no_additional_comment = {
    '(no base)', '(no L1)', '(with no ships chosen)', 'with 0 ships', 'with frigate+corvette',
    '(L1 - Corvette)', '(L1 corv)', '(L1 Frigate)', '(L1 - Frigate)',
    '(L1 - Corvette / L2 - Frigate)', '(L1/L2 corv, SH, AR)',
}

records, unresolved = [], []
for index, candidate in enumerate(candidates):
    key = (candidate['sourceSheet'], candidate['sourceCell'])
    suffix = candidate['sourceSuffix']
    build = {'cost': number(candidate['cost']), 'lightChoices': {},
             'image': candidate['image'], 'comments': candidate.get('comments', '')}
    if 'lightChoiceAlternatives' in candidate:
        del build['lightChoices']
        build['lightChoiceAlternatives'] = candidate['lightChoiceAlternatives']
    elif 'lightChoices' in candidate:
        build['lightChoices'] = candidate['lightChoices']
    else:
        light_text = candidate.get('sharedLightAnnotation') or suffix
        for match in re.finditer(r'\b(L\d+)\s*(?:-\s*)?(corv(?:ette)?|frigate)\b', light_text, re.I):
            build['lightChoices'][match.group(1).upper()] = (
                'Corvette' if match.group(2).lower().startswith('corv') else 'Frigate')
        if re.search(r'\bL\d+\b', light_text, re.I) and not build['lightChoices'] and not re.search(r'\bno L\d+\b', light_text, re.I):
            unresolved.append({'sheet': key[0], 'cell': key[1], 'multiplier': candidate['multiplier'],
                               'issue': 'Unresolved Light choices', 'text': light_text})

    for field in ('base', 'baseKill', 'baseShots', 'sameBuildForAllShots', 'costBasis', 'baseDamageBasis'):
        if field in candidate:
            build[field] = candidate[field]
    if 'baseDamage' in candidate:
        build['baseDamage'] = number(candidate['baseDamage'])
    if 'fractionalPartStatus' in candidate:
        build['costFractionalPart'] = candidate['fractionalPart']
        build['costFractionalPartStatus'] = candidate['fractionalPartStatus']
    if key in image_fields:
        build.setdefault('base', image_fields[key]['base'])

    requirement_comment = ''
    if suffix in equipment_notes:
        if not candidate.get('equipmentInComments'):
            build['equipmentRequirements'] = equipment_notes[suffix]
    elif suffix == '(Corvette w/CL + shield)' and key == ('B1 - B4B', 'G16'):
        # This user-requested comment also contains placement requirements.
        requirement_comment = build['comments']
    elif suffix == '(L1/L2 corv, SH, AR)':
        requirement_comment = build['comments']
    elif suffix == '(no SH and AR)':
        if candidate.get('equipmentInComments') and build['comments']:
            requirement_comment = build['comments']
        else:
            unresolved.append({'sheet': key[0], 'cell': key[1], 'multiplier': candidate['multiplier'],
                               'issue': 'Scope of no: neither Shield nor Armour, or no Shield with Armour?', 'text': suffix})
    elif suffix == '(L1 - Corvette / Advisor has 27 but I couldn\'t match it)':
        build['comments'] = "Advisor has 27 but I couldn't match it."
    elif suffix.startswith('by '):
        build['comments'] = suffix
    elif suffix in no_additional_comment or not suffix:
        pass
    elif candidate['sourceSheet'] == 'BB1 & B10' and (re.search(r'\bdmg\b|\d+dmg\b|\bshot\b', suffix, re.I)):
        # Damage/shot metadata and the confirmed deployment comment are already structured.
        pass
    else:
        unresolved.append({'sheet': key[0], 'cell': key[1], 'multiplier': candidate['multiplier'],
                           'issue': 'Unclassified source annotation', 'text': suffix})

    source = {'sheet': key[0], 'cell': key[1]}
    records.append({'stage': candidate['stage'], 'multiplier': candidate['multiplier'],
                    'build': build, 'source': source, 'requirementComment': requirement_comment,
                    'sourceIndex': index})

# Historical duplicate-selection comparison only. The current exporter keeps
# every entry in normalizedCandidates, per the user's 2026-10-22 instructions.
groups = defaultdict(list)
for record in records:
    requirement = {k: v for k, v in record['build'].items()
                   if k not in ('cost', 'image', 'comments', 'costFractionalPart', 'costFractionalPartStatus')}
    requirement['commentRequirements'] = record['requirementComment']
    signature = (record['stage'], record['multiplier'], json.dumps(requirement, sort_keys=True))
    groups[signature].append(record)

kept, duplicates = [], []
for group in groups.values():
    group.sort(key=lambda r: (Decimal(str(r['build']['cost'])), r['sourceIndex']))
    kept.append(group[0])
    for other in group[1:]:
        duplicates.append({'stage': other['stage'], 'multiplier': other['multiplier'],
                           'keptSource': group[0]['source'], 'keptCost': group[0]['build']['cost'],
                           'omittedSource': other['source'], 'omittedCost': other['build']['cost']})
kept.sort(key=lambda r: r['sourceIndex'])

result = {'status': 'Internal normalization audit. Current export uses all normalizedCandidates; duplicate-selection fields are historical comparisons only.',
          'normalizedCandidates': records, 'deduplicatedCandidates': kept,
          'duplicateSelections': duplicates, 'unresolved': unresolved}
(ROOT / 'normalized-candidates.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({'normalizedCandidates': len(records), 'deduplicatedCandidates': len(kept),
                  'duplicateSelections': duplicates, 'unresolved': unresolved}, indent=2))
