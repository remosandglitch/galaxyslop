import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {initialState,validateState,completeBattle,rankBattle} from '../dist/engine.mjs';
import {validateGalaxyState} from '../dist/galaxies.mjs';
test('backups retain galaxy provenance, including legacy G6 saves',()=>{
  const legacy=initialState();delete legacy.galaxy;
  assert.equal(validateGalaxyState(legacy,'g6'),legacy);
  assert.throws(()=>validateGalaxyState(legacy,'g7'),/G6/);
  assert.throws(()=>validateGalaxyState(initialState('g7'),'g6'),/G7/);
  assert.throws(()=>validateState({...legacy,galaxy:123}),/galaxy/);
  assert.equal(validateState(completeBattle(initialState('g7'),'B4C',20)).done.B4C.cost,20);
});
test('G7 import preserves lettered battles, independent source identity and local image paths',()=>{
  const data=JSON.parse(fs.readFileSync(new URL('../dist/data-g7.json',import.meta.url)));
  assert.equal(data.sourceId,'1Cj4kstAZkQhTvUfIj6EkFuQ4uwkLiIAmt9m8ZgLL-jc');
  assert.deepEqual(data.battles,['B1','B2A','B2B','B2C','B3A','B3C','B3D','B4A','B4B','B4C','B5','B5D','B6','BB1','B7']);
  assert.equal(data.groups.length,3);
  for(const c of data.cells){assert.ok(data.battles.includes(c.battle));if(c.image){assert.match(c.image,/^source\/images\/g7\//);assert.ok(fs.existsSync(new URL('../'+c.image,import.meta.url)));}}
  assert.ok(rankBattle(data,initialState('g7'),'B2A').length>0);
  assert.ok(data.cells.find(c=>c.sheetId===872145342&&c.cell==='B17').issues.length>0);
});
