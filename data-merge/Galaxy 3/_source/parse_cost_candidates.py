"""Extract numeric candidates; do not infer unresolved requirement scopes."""
import json
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))

audit, decisions, manifest = read('source-audit.json'), read('import-decisions.json'), read('image-manifest.json')
sheet_cells = read('sheet-cells.json')
rich_cells = {}
for sheet in sheet_cells['sheets']:
    for block in sheet.get('data', []):
        for row_offset, row in enumerate(block.get('rowData', [])):
            for col_offset, cell in enumerate(row.get('values', [])):
                rich_cells[(sheet['properties']['title'], block.get('startRow', 0) + row_offset,
                            block.get('startColumn', 0) + col_offset)] = cell
cells = {(c['sheet'], c['cell']): c for c in audit['cells']}
records = {(i['sheet'], i['label_cell']): {'stage': i['stage'], 'image': i['output_file']} for i in manifest['images']}
entry_overrides = {(o['sheet'], o['cell']): o for o in decisions['acceptedEntryOverrides']}
build_configurations = {(o['sheet'], o['cell']): o for o in decisions.get('acceptedBuildConfigurations', [])}
variant_overrides = {(o['sheet'], o['cell'], o['multiplier']): o for o in decisions['acceptedVariantOverrides']}
excluded_variants = {(o['sheet'], o['cell'], o['multiplier']) for o in decisions['excludedVariants']}
for key, override in entry_overrides.items():
    if override.get('image') == '':
        records[key] = {'stage': override['stage'], 'image': ''}

def parts(caption):
    depth, start = 0, 0
    for index, char in enumerate(caption):
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == '/' and depth == 0:
            if caption[start:index].strip():
                yield caption[start:index].strip()
            start = index + 1
    if caption[start:].strip():
        yield caption[start:].strip()

def multiplier(text):
    value = format(Decimal(text), 'f').rstrip('0').rstrip('.') if '.' in text else text
    if '.' not in value:
        value += '.0'
    return value + 'x'

def shared_light_annotation(key, caption):
    """Apply the user's trailing-note convention only to uninterrupted groups."""
    if len(list(parts(caption))) < 2 or caption.count('(') != 1 or caption.count(')') != 1:
        return None
    note = re.search(r'\(([^()]*)\)\s*$', caption)
    if not note or not re.search(r'\bL\d+\b', note.group(1), re.IGNORECASE):
        return None
    source = cells[key]
    raw = rich_cells[(key[0], source['row'] - 1, source['column'])]
    text = raw.get('userEnteredValue', {}).get('stringValue', '')
    default_bold = raw.get('effectiveFormat', {}).get('textFormat', {}).get('bold', False)
    runs = raw.get('textFormatRuns', [])
    bold_states = set()
    if not runs or runs[0].get('startIndex', 0) > 0:
        bold_states.add(default_bold)
    for run in runs:
        if run.get('startIndex', 0) < len(text):
            bold_states.add(run.get('format', {}).get('bold', default_bold))
    if len(bold_states) > 1:
        return None
    return note.group(1).strip()

def cost_number(token):
    match = re.fullmatch(r'(\d+)(?:\.(\d+)|\(\.(\d+)\)|\.\((\d+)\)|\(\?\)|\?)?', token)
    if not match:
        raise ValueError(f'Unsupported cost token: {token!r}')
    fraction = next((v for v in match.groups()[1:] if v is not None), None)
    return match.group(1) + ('.' + fraction if fraction is not None else '')

candidates, issues, skipped = [], [], []
for key, info in records.items():
    caption = cells[key]['active']
    if key in build_configurations:
        confirmed = build_configurations[key]
        for value in confirmed['multipliers']:
            for config in confirmed['configurations']:
                candidate = {'stage': info['stage'], 'multiplier': value, 'cost': config['cost'],
                    'image': info['image'], 'sourceSheet': key[0], 'sourceCell': key[1],
                    'sourceCost': config['cost'], 'sourceSuffix': config['sourceSuffix'],
                    'sourceCaption': caption}
                for field in ('lightChoices', 'lightChoiceAlternatives'):
                    if field in config:
                        candidate[field] = config[field]
                candidates.append(candidate)
        continue
    shared_note = shared_light_annotation(key, caption)
    waiting = []
    for piece in parts(caption):
        match = re.fullmatch(r'(?:Stats\s+)?(\d+(?:\.\d+)?)x?\s*(?:-\s*)?(.*)', piece)
        if not match:
            raise ValueError(f'Unparsed caption fragment {key}: {piece!r}')
        mult, tail = multiplier(match.group(1)), match.group(2).strip()
        if (*key, mult) in excluded_variants:
            skipped.append({'sheet': key[0], 'cell': key[1], 'multiplier': mult})
            continue
        if not tail:
            waiting.append(mult)
            continue
        override = variant_overrides.get((*key, mult)) or entry_overrides.get(key, {})
        cm = re.match(r'(\d+(?:\.\(\d+\)|\(\.\d+\)|\.\d+|\(\?\)|\?)?)(.*)', tail)
        if cm:
            token, suffix = cm.group(1), cm.group(2).strip()
            cost = override.get('cost', cost_number(token))
        elif override.get('cost') is not None:
            token, suffix, cost = None, tail, override['cost']
        else:
            raise ValueError(f'No parseable cost in retained entry {key}: {piece!r}')
        for value in [*waiting, mult]:
            candidate = {'stage': info['stage'], 'multiplier': value, 'cost': cost,
                'image': info['image'], 'sourceSheet': key[0], 'sourceCell': key[1],
                'sourceCost': token, 'sourceSuffix': suffix, 'sourceCaption': caption}
            if shared_note is not None:
                candidate['sharedLightAnnotation'] = shared_note
            confirmed_fields = dict(entry_overrides.get(key, {}))
            confirmed_fields.update(variant_overrides.get((*key, value), {}))
            if confirmed_fields.get('multiplier', value) == value:
                for field in ('lightChoices', 'comments', 'equipmentInComments', 'base', 'baseDamage',
                              'baseDamageBasis', 'baseShots', 'baseKill', 'sameBuildForAllShots',
                              'costBasis', 'fractionalPart', 'fractionalPartStatus'):
                    if field in confirmed_fields:
                        candidate[field] = confirmed_fields[field]
            candidates.append(candidate)
        waiting = []
        if 'with 0 ships' in suffix:
            issues.append({'sheet': key[0], 'cell': key[1], 'type': 'multiple costs with different Light choices', 'text': caption})
    if waiting:
        raise ValueError(f'Multipliers without a listed shared cost: {key}: {waiting}')

for candidate in candidates:
    if candidate['sourceSheet'] != 'BB1 & B10':
        continue
    suffix = candidate['sourceSuffix']
    damage = re.search(r'(\d+(?:\.\d+)?)\s*dmg\b', suffix, re.IGNORECASE)
    if damage:
        candidate.setdefault('base', True)
        candidate.setdefault('baseDamage', damage.group(1))
    if re.search(r'\bone shot\b', suffix, re.IGNORECASE):
        candidate.setdefault('base', True)
        candidate.setdefault('baseShots', 1)
        candidate.setdefault('baseKill', True)
    candidate.setdefault('baseKill', False)
    # Unstated shot counts remain absent, as explicitly requested by the user.

result = {'status': 'Intermediate numeric extraction. Requirements and final duplicate selection are not resolved here.',
          'candidates': candidates, 'skippedVariants': skipped, 'specialCases': issues}
(ROOT / 'cost-candidates.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({'sourceCaptions': len(records), 'numericCandidatesIncludingConfirmedConfigurations': len(candidates),
                  'stages': len(set(c['stage'] for c in candidates)), 'specialCases': issues,
                  'unparsedRetainedCaptions': 0}, indent=2))
