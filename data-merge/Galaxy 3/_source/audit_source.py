import hashlib
import io
import json
import posixpath
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image

ROOT = Path(__file__).resolve().parent
NS = {
    's': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'xdr': 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}

def unstruck(cell):
    text = cell.get('formattedValue', '')
    default = cell.get('effectiveFormat', {}).get('textFormat', {}).get('strikethrough', False)
    runs = cell.get('textFormatRuns') or [{'startIndex': 0}]
    kept, removed = [], []
    for i, run in enumerate(runs):
        start = run.get('startIndex', 0)
        end = runs[i + 1].get('startIndex', 0) if i + 1 < len(runs) else len(text)
        part = text[start:end]
        (removed if run.get('format', {}).get('strikethrough', default) else kept).append(part)
    return ''.join(kept), ''.join(removed)

source = json.loads((ROOT / 'sheet-cells.json').read_text(encoding='utf-8'))
z = zipfile.ZipFile(ROOT / 'G3 Spreadsheet.xlsx')
image_dir = ROOT / 'embedded-images'
image_dir.mkdir(exist_ok=True)
images, cells = [], []
for si, sheet in enumerate(source['sheets'], 1):
    lookup = {}
    for grid in sheet.get('data', []):
        for ri, row in enumerate(grid.get('rowData', []), grid.get('startRow', 0) + 1):
            for ci, cell in enumerate(row.get('values', []), grid.get('startColumn', 0)):
                if 'formattedValue' not in cell:
                    continue
                active, removed = unstruck(cell)
                record = {'sheet': sheet['properties']['title'], 'cell': f'{chr(65+ci)}{ri}', 'row': ri, 'column': ci,
                          'original': cell['formattedValue'], 'active': active, 'struck': removed}
                lookup[(ci, ri)] = record
                cells.append(record)
    drawing_path = f'xl/drawings/drawing{si}.xml'
    rel_path = f'xl/drawings/_rels/drawing{si}.xml.rels'
    if rel_path not in z.namelist():
        continue
    rels = {r.attrib['Id']: posixpath.normpath(posixpath.join('xl/drawings', r.attrib['Target']))
            for r in ET.fromstring(z.read(rel_path))}
    for anchor in ET.fromstring(z.read(drawing_path)):
        origin = anchor.find('xdr:from', NS)
        blip = anchor.find('.//a:blip', NS)
        if origin is None or blip is None:
            raise ValueError('Unsupported image anchor')
        ci, ri = int(origin.find('xdr:col', NS).text), int(origin.find('xdr:row', NS).text) + 1
        target = rels[blip.attrib[f'{{{NS["r"]}}}embed']]
        raw = z.read(target)
        p = image_dir / posixpath.basename(target)
        if p.exists() and p.read_bytes() != raw:
            raise ValueError('Image filename collision')
        p.write_bytes(raw)
        with Image.open(io.BytesIO(raw)) as image:
            dims, fmt = list(image.size), image.format
            image.verify()
        ext = anchor.find('xdr:ext', NS)
        stage = lookup.get((ci, 1), {}).get('active') if si >= 3 else None
        label = lookup.get((ci, ri - 1))
        images.append({'sheet': sheet['properties']['title'], 'sheet_index': si, 'cell': f'{chr(65+ci)}{ri}',
                       'row': ri, 'column': ci, 'stage': stage, 'label_cell': label['cell'] if label else None,
                       'label': label['active'] if label else None, 'struck_label': label['struck'] if label else None,
                       'media_path': target, 'local_file': str(p), 'dimensions': dims, 'format': fmt,
                       'display_pixels': [round(int(ext.attrib[k])/9525, 2) for k in ('cx', 'cy')] if ext is not None else None,
                       'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})

output = {'images': images, 'cells': cells}
(ROOT / 'source-audit.json').write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({'images': len(images), 'by_sheet': dict(Counter(i['sheet'] for i in images)),
                  'dimensions': dict(Counter('x'.join(map(str,i['dimensions'])) for i in images)),
                  'unlabelled_stage_images': [i for i in images if i['sheet_index'] >= 3 and not i['label']],
                  'struck_labels': [c for c in cells if c['struck'] and c['sheet'] not in ('legend (PLEASE READ before adding!)',)],
                  'labels_without_next_row_image': [c for c in cells if c['sheet'] in [s['properties']['title'] for s in source['sheets'][2:]] and c['row'] > 1 and c['active'] and not any(i['sheet'] == c['sheet'] and i['column'] == c['column'] and i['row'] == c['row'] + 1 for i in images)]}, indent=2, ensure_ascii=False))
