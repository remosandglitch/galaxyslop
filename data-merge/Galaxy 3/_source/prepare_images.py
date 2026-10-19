"""Copy retained workbook images without changing their original bytes."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parent
audit = json.loads((SOURCE / 'source-audit.json').read_text(encoding='utf-8'))
decisions = json.loads((SOURCE / 'import-decisions.json').read_text(encoding='utf-8'))
excluded = {(entry['sheet'], entry['cell']) for entry in decisions['excludedEntries']}
counts = Counter()
selected, skipped = [], []

for entry in sorted(audit['images'], key=lambda item: (item['sheet_index'], item['column'], item['row'])):
    reason = None
    if entry['sheet_index'] < 3:
        reason = 'Legend image, not a stage build'
    elif (entry['sheet'], entry['cell']) in excluded or (entry['sheet'], entry['label_cell']) in excluded:
        reason = 'Excluded by user decision'
    elif not entry['label'] and entry['struck_label']:
        reason = 'Caption is entirely struck through'
    elif not entry['label']:
        raise ValueError(f"Unresolved uncaptioned image: {entry['sheet']}!{entry['cell']}")
    elif not re.search(r'(?:-\s*|x\s+)(?:up to\s+)?\d+(?:\.\d+)?', entry['label']):
        reason = 'No cost listed, excluded by user rule'
    if reason:
        skipped.append({'sheet': entry['sheet'], 'cell': entry['cell'], 'reason': reason, 'media_path': entry['media_path']})
        continue
    stage = entry['stage']
    if not re.fullmatch(r'B(?:B)?\d+[AB]?', stage or ''):
        raise ValueError(f'Unexpected stage: {stage!r}')
    counts[stage] += 1
    source_path = Path(entry['local_file'])
    if source_path.resolve().parent != (SOURCE / 'embedded-images').resolve():
        raise ValueError('Image source is outside the extracted image directory')
    target = ROOT / 'images' / f'{stage}_{counts[stage]}{source_path.suffix.lower()}'
    raw = source_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != entry['sha256']:
        raise ValueError(f'Source hash mismatch: {source_path.name}')
    if target.exists() and target.read_bytes() != raw:
        raise ValueError(f'Refusing to overwrite different content: {target.name}')
    selected.append({**entry, 'output_file': target.relative_to(ROOT).as_posix()})

# Complete every preflight check before creating the output files.
(ROOT / 'images').mkdir(exist_ok=True)
for entry in selected:
    target = ROOT / entry['output_file']
    if not target.exists():
        target.write_bytes(Path(entry['local_file']).read_bytes())
    if hashlib.sha256(target.read_bytes()).hexdigest() != entry['sha256']:
        raise ValueError(f'Output hash mismatch: {target.name}')

manifest = {
    'spreadsheetId': decisions['spreadsheetId'],
    'numbering': 'Per stage, starting at 1, following top-to-bottom source order after exclusions',
    'image_bytes': 'Original workbook image bytes, unchanged',
    'images': selected,
    'skipped': skipped,
}
(SOURCE / 'image-manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({'saved_images': len(selected), 'stages': len(counts), 'by_stage': dict(counts), 'skipped_images': len(skipped), 'all_output_hashes_match': True}, indent=2))
