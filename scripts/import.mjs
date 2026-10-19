import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
export function strikeAt(cell,index) {
  let strike=!!cell.effectiveFormat?.textFormat?.strikethrough;
  for(const run of cell.textFormatRuns||[]) {
    if ((run.startIndex||0)>index) break;
    strike=run.format?.strikethrough ?? !!cell.effectiveFormat?.textFormat?.strikethrough;
  }
  return strike;
}
function colorConditions(cell) {
  const c=cell.effectiveFormat?.backgroundColor||{red:1,green:1,blue:1};
  const rgb=[c.red||0,c.green||0,c.blue||0];
  for(const [target,s,h] of [[[1,1,1],false,false],[[.6431373,.85882354,1],true,false],[[1,.6901961,.6901961],false,true],[[.72156864,.5647059,.85882354],true,true]]) if(rgb.every((x,i)=>Math.abs(x-target[i])<.005)) return {support:s,hazard:h,known:true};
  return {support:null,hazard:null,known:false};
}
export function parseCell(cell,meta) {
  const text=cell.formattedValue||'';
  const base=colorConditions(cell);
  const tokens=[...text.matchAll(/(?<![\w.])(\d+(?:\.\d+)?)(?:\s*,?\s*x\s*[-–:]?\s*|\s*-\s*)(?=\d|fail|lose|OneShot)/gi)];
  const result=[];
  let conditions={...base}, previous=0;
  for(let i=0;i<tokens.length;i++) {
    const token=tokens[i], start=token.index, end=tokens[i+1]?.index ?? text.length;
    const prefix=text.slice(previous,start);
    for(const tag of prefix.matchAll(/\b(NS|NH|SHC|SH|HS|S|H)(?:\([^)]*\))?\b/g)) {
      if(tag[1]==='SHC') continue;
      if(['S','NS','SH','HS'].includes(tag[1])) conditions.support=tag[1]!=='NS';
      if(['H','NH','SH','HS'].includes(tag[1])) conditions.hazard=tag[1]!=='NH';
    }
    const body=text.slice(start+token[0].length,end);
    const numeric=body.match(/^(\d+(?:\.\d+|\.\(\d+\)|\(\.\d+\))?)/);
    const cost=numeric?Number(numeric[0].replace(/[()]/g,'')):null;
    const reasons=[];
    if(!base.known || conditions.support===null || conditions.hazard===null) reasons.push('Unrecognized condition color; confirm support and hazard');
    if(cell.note) reasons.push('Source note needs review');
    if(/\b(?:wrong|inconsisten|outdated|not updated|not up to date|this is \d+ now|needs checking)/i.test(text)) reasons.push('Disputed or outdated source');
    if(/\b(?:dmg|damage|total|two shot|[2-9] shot|four shot|PART [AB]|FINISH ABOVE)\b|\d\s*\+\s*\d/i.test(text)) reasons.push('Multi-shot or damage entry: verify the full clear and each shot cost');
    if(/\bS\+NS\b/.test(text)) reasons.push('Mixed support requirements');
    if(/(?:thru|→|\band\b)\s*$|\dx\s*\/\s*$/i.test(prefix)) reasons.push('Shared cost or multiplier range needs review');
    const after=body.slice(numeric?.[0].length||0);
    if(/^\s*(?:\.?\?+|\d|\+|=|\/\s*\d)/.test(after)) reasons.push('Uncertain or multiple costs');
    if(/\([^)]*\d+\s*x?\s*[-–]\s*\d/.test(text) || /\([^)]*$/.test(text.slice(0,start))) reasons.push('Nested variant or contextual numeric entry');
    const resultBody=body.replace(/\/\s*(?:fail|lose)\s*$/i,'');
    if(/\?/.test(resultBody) || /\b(?:got|how|fails|fail|lose)\b/i.test(resultBody) && !/^(?:fail|lose)/i.test(resultBody)) reasons.push('Uncertain result or failure context');
    if((i===0 || /\/\s*(?:fail|lose)\s*$/i.test(prefix)) && /\b(?:fail|lose)\s*$/i.test(prefix)) reasons.push('Failed attempt');
    const failed=/^(?:fail|lose)/i.test(body);
    if(failed)reasons.push('Failed attempt');
    const bg=cell.effectiveFormat?.backgroundColor;
    const obsolete=bg && ['red','green','blue'].every(k=>Math.abs((bg[k]||0)-.6)<.005) || Array.from({length:token[0].length+(numeric?.[0].length||0)},(_,n)=>strikeAt(cell,start+n)).some(Boolean);
    result.push({...meta,id:`${meta.layoutId}:${start}`,multiplier:Number(token[1]),cost, support:conditions.support,hazard:conditions.hazard,
      special:/\b(?:SHC|SCH|[LM]\s*-?\s*\d|printed|fabricat)/i.test(text),
      segment:text.slice(start,end).trim(),status:obsolete?'obsolete':failed?'failed':reasons.length||cost===null?'review':'usable',reasons});
    previous=start+token[0].length;
  }
  const duplicates=result.filter(r=>result.some(o=>o!==r&&o.multiplier===r.multiplier&&o.support===r.support&&o.hazard===r.hazard&&o.status!=='obsolete'));
  for(const r of duplicates) if(r.status==='usable'){r.status='review';r.reasons.push('Multiple variants at the same multiplier');}
  const unparsed=[...text.matchAll(/(?<![\w.])\d+(?:\.\d+)?\s*,?\s*x\b/gi)].filter(m=>!tokens.some(t=>t.index===m.index)&&!strikeAt(cell,m.index));
  // Unparsed failures/ranges must not let an older measurement escape as an estimate.
  if(unparsed.length) for(const r of result) if(r.status==='usable') {r.status='review';r.reasons.push('Additional multiplier text needs review: '+unparsed.map(m=>m[0]).join(', '));}
  return result;
}
export function build(root,galaxy='g6') {
  if(!['g6','g7'].includes(galaxy))throw Error('Unknown galaxy');
  const sourceDir=galaxy==='g6'?'source':'source/g7';
  const workbook=JSON.parse(fs.readFileSync(path.join(root,sourceDir,'workbook.json'),'utf8'));
  const cells=[],records=[],orphanImages=[];
  for(const sheet of workbook.sheets) {
    const sheetId=sheet.properties.sheetId;
    const mapPath=path.join(root,sourceDir,`images-${sheetId}.json`);
    const mapping=fs.existsSync(mapPath)?JSON.parse(fs.readFileSync(mapPath,'utf8')):{cells:[],bundle:{assets:[]}};
    const assets=new Map(mapping.bundle.assets.map(a=>[a.url,a.path.replaceAll('\\','/')]));
    const images=new Map(mapping.cells.map(c=>[`${c.row}:${c.col}`,assets.get(c.url)]));
    const rows=sheet.data[0].rowData, headers=rows[0].values.map(c=>c.formattedValue);
    for(let row=1;row<rows.length;row++) for(let col=0;col<(rows[row].values||[]).length;col++) {
      const cell=rows[row].values[col];
      if(!cell.formattedValue?.trim()) continue;
      const address=String.fromCharCode(65+col)+(row+1),layoutId=`${sheetId}:${address}`;
      const image=images.get(`${row+2}:${col+1}`)||null;
      const meta={layoutId,battle:headers[col],sheetId,sheet:sheet.properties.title,cell:address,image};
      const parsed=parseCell(cell,meta);
      cells.push({...meta,text:cell.formattedValue,note:cell.note||'',format:cell.effectiveFormat,textFormatRuns:cell.textFormatRuns||[],recordIds:parsed.map(r=>r.id),issues:[...new Set(parsed.flatMap(r=>r.reasons)),...(!parsed.length?['No unambiguous numeric observations']:[]),...(!image?['No adjacent fleet image']:[])]});
      records.push(...parsed);
    }
    for(const img of mapping.cells) if(!cells.some(c=>c.sheetId===sheetId&&c.image===assets.get(img.url))) orphanImages.push({sheetId,...img,path:assets.get(img.url)});
  }
  const stats={cells:cells.length,records:records.length,usable:records.filter(r=>r.status==='usable').length,review:records.filter(r=>r.status==='review').length,obsolete:records.filter(r=>r.status==='obsolete').length,failed:records.filter(r=>r.status==='failed').length,missingImages:cells.filter(c=>!c.image).length,orphanImages:orphanImages.length};
  const groups=workbook.sheets.map(s=>({id:String(s.properties.sheetId),label:s.properties.title,battles:s.data[0].rowData[0].values.map(c=>c.formattedValue).filter(Boolean)}));
  const out={version:1,galaxy,sourceId:workbook.spreadsheetId,extractedAt:workbook.downloadedAt,stats,groups,battles:groups.flatMap(g=>g.battles),cells,records,orphanImages};
  fs.mkdirSync(path.join(root,'dist'),{recursive:true});fs.writeFileSync(path.join(root,'dist',galaxy==='g6'?'data.json':'data-g7.json'),JSON.stringify(out));
  fs.writeFileSync(path.join(root,sourceDir,'import-audit.json'),JSON.stringify({stats,cells:cells.filter(c=>c.issues.length),orphanImages},null,2));
  return out;
}
if(process.argv[1]===fileURLToPath(import.meta.url)) {
  const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
  for(const galaxy of process.argv[2]?[process.argv[2]]:['g6','g7'])console.log(galaxy,build(root,galaxy).stats);
}
