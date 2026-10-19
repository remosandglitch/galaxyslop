import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {initialState,rankBattle,shouldShow,completeBattle,validateState} from '../dist/engine.mjs';
import {parseCell,strikeAt} from '../scripts/import.mjs';
const record=(id,multiplier,cost,extra={})=>({id,layoutId:'0:A2',battle:'B1',multiplier,cost,support:false,hazard:false,status:'usable',special:false,...extra});
const fixture=text=>({formattedValue:text,effectiveFormat:{backgroundColor:{red:1,green:1,blue:1},textFormat:{strikethrough:false}}});
const meta={layoutId:'0:A2',battle:'B1'};
test('nearest lower per layout, never historical minimum; exact and estimate distinction',()=>{
  const state=initialState(),data={records:[record('a',2,10.9),record('b',3,22.8),record('c',2.5,19.9,{layoutId:'0:A4'})]};
  const ranked=rankBattle(data,state,'B1');assert.equal(ranked[0].id,'c');assert.equal(ranked[0].estimate,true);assert.equal(ranked[1].cost,22.8);assert.equal(ranked[1].estimate,false);
  state.settings.multiplier=1;assert.equal(rankBattle(data,state,'B1').length,0);
});
test('integer ties and done resurfacing ignore decimal-only improvements',()=>{
  const state=initialState(),data={records:[record('a',3,20.01),record('b',3,20.99,{layoutId:'0:A4'})]};
  const ranked=rankBattle(data,state,'B1');assert.deepEqual(ranked.map(r=>r.integer),[20,20]);assert.equal(shouldShow({cost:20},ranked[0]),false);assert.equal(shouldShow({cost:21},ranked[0]),true);assert.equal(shouldShow({cost:21},undefined),false);
});
test('strict conditions, per-battle override, special equipment filter',()=>{
  const state=initialState(),data={records:[record('a',3,5,{support:true}),record('b',3,6,{hazard:true}),record('c',3,7,{special:true})]};
  assert.equal(rankBattle(data,state,'B1')[0].id,'c');state.settings.special=false;assert.equal(rankBattle(data,state,'B1').length,0);state.conditions.B1={support:true,hazard:false};assert.equal(rankBattle(data,state,'B1')[0].id,'a');
});
test('failed and review results block older measurements; obsolete results excluded',()=>{
  const state=initialState();for(const status of ['failed','review'])assert.equal(rankBattle({records:[record('a',2,5),record('b',3,null,{status})]},state,'B1').length,0);
  assert.equal(rankBattle({records:[record('a',2,5),record('b',3,3,{status:'obsolete'})]},state,'B1')[0].id,'a');
});
test('local corrections change ranking; shot costs truncate separately',()=>{
  const state=initialState();state.edits.a={multiplier:3,cost:21.8,shots:[10.9,10.9],support:false,hazard:false,special:false,enabled:true};
  const result=rankBattle({records:[record('a',3,30)]},state,'B1')[0];assert.equal(result.integer,20);assert.equal(result.local,true);validateState(state);
});
test('completion history survives settings changes and serialization',()=>{
  const next=completeBattle(initialState(),'B1',20);next.settings.multiplier=4;assert.equal(next.done.B1.cost,20);assert.equal(next.done.B1.multiplier,3);assert.deepEqual(validateState(JSON.parse(JSON.stringify(next))),next);assert.throws(()=>completeBattle(next,'B1',20.8));
});
test('backup validation rejects invalid costs, settings, shot totals and history',()=>{
  const state=initialState();assert.throws(()=>validateState({...state,settings:{...state.settings,multiplier:NaN}}));
  assert.throws(()=>validateState({...state,history:[{cost:'<script>',at:'bad'}]}));
  assert.throws(()=>validateState({...state,edits:{a:{multiplier:3,cost:8,shots:[5,5],support:false,hazard:false,special:false,enabled:true}}}));
});
test('condition transitions in one cell; SHC is equipment, not SH',()=>{
  const results=parseCell(fixture('S/H: 2x-40 / NS/H: 3x-30 / NS/NH/SHC: 4x-20'),meta);
  assert.deepEqual(results.map(r=>[r.support,r.hazard]),[[true,true],[false,true],[false,false]]);assert.ok(results.every(r=>r.special));
  const shc=parseCell(fixture('SHC: 3x-20'),meta)[0];assert.equal(shc.support,false);assert.equal(shc.hazard,false);
});
test('exact legend colors support unlabeled observations; unknown colors need review',()=>{
  const c=fixture('3x-20');c.effectiveFormat.backgroundColor={red:1,green:.6901961,blue:.6901961};assert.equal(parseCell(c,meta)[0].hazard,true);
  c.effectiveFormat.backgroundColor={red:1,green:.2,blue:.2};c.formattedValue='S/H: 3x-20';assert.equal(parseCell(c,meta)[0].status,'review');
});
test('rich-text strikes exclude only affected observations; base format is inherited',()=>{
  const c=fixture('2x-20 / 3x-15');c.textFormatRuns=[{}, {startIndex:8,format:{strikethrough:true}}];assert.deepEqual(parseCell(c,meta).map(r=>r.status),['usable','obsolete']);
  c.effectiveFormat.textFormat.strikethrough=true;c.textFormatRuns=[{format:{strikethrough:false}},{startIndex:8}];assert.equal(strikeAt(c,0),false);assert.equal(strikeAt(c,8),true);
});
test('parenthesized decimals, missing x, and one-shot committed amounts parse safely',()=>{
  for(const text of ['3x-48.(77)','3x-48(.77)','3.0 - 48.77','3x 48.77 of 100, one shot']) {const r=parseCell(fixture(text),meta)[0];assert.equal(r.cost,48.77);assert.equal(r.status,'usable');}
});
test('a failed earlier measurement does not invalidate a later successful measurement',()=>{
  assert.deepEqual(parseCell(fixture('3x-fail\n3.25x-20'),meta).map(r=>r.status),['failed','usable']);
  assert.deepEqual(parseCell(fixture('2x-30 / fail 2.5x-20 / 3x-15'),meta).map(r=>r.status),['usable','review','usable']);
});
test('uncertainty, multiple shots, duplicate variants, notes, ranges never silently rank',()=>{
  for(const text of ['3x-80.??','3x-140+130.34=270.34','3x-200 (900 damage)','3x-40 30','3x-40 / 3x-30 (beam)','2x thru 3x-20','2x-20 / 3x (failed)'])assert.ok(parseCell(fixture(text),meta).every(r=>r.status!=='usable'),text);
  const c=fixture('3x-20');c.note='actually not S';assert.equal(parseCell(c,meta)[0].status,'review');
});
test('real source regressions: mixed conditions, red hazard, dispute, wrong image, multi-shot',()=>{
  const w=JSON.parse(fs.readFileSync(new URL('../source/workbook.json',import.meta.url)));
  const cell=(sheet,row,col)=>w.sheets[sheet].data[0].rowData[row-1].values[col-1];
  const mixed=parseCell(cell(2,8,1),meta);assert.deepEqual(mixed.map(r=>[r.support,r.hazard]),[[true,true],[true,true],[false,true]]);
  assert.equal(parseCell(cell(1,2,7),meta)[0].hazard,true);
  for(const c of [cell(0,16,8),cell(3,8,4),cell(4,6,9)])assert.ok(parseCell(c,meta).every(r=>r.status!=='usable'));
});
test('import has all battles, stable IDs, safe costs and existing images',()=>{
  const d=JSON.parse(fs.readFileSync(new URL('../dist/data.json',import.meta.url)));assert.equal(d.battles.length,49);assert.equal(new Set(d.records.map(r=>r.id)).size,d.records.length);
  for(const r of d.records.filter(r=>r.status==='usable')){assert.ok(Number.isFinite(r.cost)&&r.cost>=0);assert.equal(typeof r.support,'boolean');assert.equal(typeof r.hazard,'boolean');}
  for(const c of d.cells.filter(c=>c.image))assert.ok(fs.existsSync(new URL('../'+c.image,import.meta.url)),c.image);
});
