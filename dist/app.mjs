import {initialState,validateState,effectiveRecords,rankBattle,shouldShow,completeBattle} from './engine.mjs';
import {galaxies,validateGalaxyState} from './galaxies.mjs';
const activeGalaxy=galaxies.find(g=>g.id===new URLSearchParams(location.search).get('galaxy'))||galaxies[0];
const stateUrl=`/api/state?galaxy=${activeGalaxy.id}`;
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let data,state,view='planner',editing=null,detailBattle=null,limit=60,saving=false;
const completionDrafts=new Map();
const sourceCell=id=>data.cells.find(c=>c.layoutId===id);
const statusText={usable:'Recorded result',review:'Needs review',obsolete:'Crossed out / obsolete',failed:'Failed attempt',disabled:'Disabled locally'};
function sourceLink(c){return `https://docs.google.com/spreadsheets/d/${data.sourceId}/edit#gid=${c.sheetId}&range=${c.cell}`;}
function sourceMarkup(c){
  const cuts=[0,...(c.textFormatRuns||[]).map(r=>r.startIndex||0),c.text.length].filter((v,i,a)=>a.indexOf(v)===i).sort((a,b)=>a-b);
  return cuts.slice(0,-1).map((start,i)=>{let strike=!!c.format?.textFormat?.strikethrough;for(const r of c.textFormatRuns||[]){if((r.startIndex||0)>start)break;strike=r.format?.strikethrough??!!c.format?.textFormat?.strikethrough;}const t=esc(c.text.slice(start,cuts[i+1]));return strike?`<del>${t}</del>`:t;}).join('');
}
async function persist(next){
  if(saving)throw Error('A save is still in progress. Please try again.');
  validateGalaxyState(validateState(next),activeGalaxy.id);next.galaxy=activeGalaxy.id;saving=true;$('#save-status').textContent='Saving…';
  try{const r=await fetch(stateUrl,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(next)});const payload=await r.json();if(!r.ok)throw Error(payload.error);state=next;$('#save-status').textContent=`${activeGalaxy.label} saved on this computer`;render();}
  catch(e){$('#save-status').textContent='Save failed · changes not saved';throw e;}
  finally{saving=false;}
}
function notify(text){const el=document.createElement('div');el.className='toast';el.setAttribute('role','status');el.textContent=text;document.body.append(el);setTimeout(()=>el.remove(),4000);}
function handleError(e){notify(e.message||String(e));}
function matches(battle,text=''){
  const q=$('#search').value.trim().toLowerCase(), group=$('#group').value;
  return (!q || (/^bb?\d+[a-z]?$/.test(q)?battle.toLowerCase()===q:`${battle} ${text}`.toLowerCase().includes(q))) && (group==='all'||data.groups.find(g=>g.id===group)?.battles.includes(battle));
}
function conditionControls(battle){const c=state.conditions[battle]||state.settings;return `<div class="battle-conditions"><label>Support${state.conditions[battle]?' · battle override':''}<select data-condition="support" data-battle="${battle}" aria-label="${battle} support"><option value="false" ${!c.support?'selected':''}>No support</option><option value="true" ${c.support?'selected':''}>Support active</option></select></label><label>Hazard<select data-condition="hazard" data-battle="${battle}" aria-label="${battle} hazard"><option value="false" ${!c.hazard?'selected':''}>No hazard</option><option value="true" ${c.hazard?'selected':''}>Hazard active</option></select></label>${state.conditions[battle]?`<button data-action="default" data-battle="${battle}" title="Use default conditions">↺</button>`:''}</div>`;}
function completionForm(battle,best){
  const conditions=state.conditions[battle]||state.settings;
  const key=[battle,state.settings.multiplier,conditions.support,conditions.hazard,best?.id,best?.integer].join(':');
  const cost=completionDrafts.get(key)??best?.integer??'';
  return `<form class="completion-form" data-battle="${battle}" data-draft="${esc(key)}"><label>Flight cost (FR)<input name="cost" aria-label="${battle} flight cost (FR)" type="number" min="0" max="9007199254740991" step="1" required value="${esc(cost)}" placeholder="Actual FR"></label><button type="submit" class="primary">Mark done</button></form>`;
}
function card(battle,ranked){
  const best=ranked[0],done=state.done[battle];
  if(!best)return `<article class="card"><div class="card-head"><h2 class="battle-title">${battle}</h2><span class="badge">No usable result</span></div><div class="empty">No usable observation at or below ${state.settings.multiplier}× for these conditions.<br>Inspect the source or add your own result.</div>${conditionControls(battle)}<div class="card-footer"><button data-action="detail" data-battle="${battle}">Browse source &amp; add result</button>${completionForm(battle,best)}</div></article>`;
  const c=sourceCell(best.layoutId), ties=ranked.filter(r=>r.integer===best.integer).length;
  const req=best.note || c?.text || best.segment || 'Locally recorded setup';
  return `<article class="card"><div class="card-head"><div><p class="eyebrow">${done?'LOWER COST AVAILABLE':'CHEAPEST USABLE'}</p><h2 class="battle-title">${battle}</h2></div><div class="badges"><span class="badge ${best.estimate?'estimate':''}">${best.estimate?'UNVERIFIED ESTIMATE':`RECORDED · ${best.multiplier}×`}</span>${best.local?'<span class="badge local">LOCAL EDIT</span>':''}</div></div><div class="cost"><b>${best.integer}</b><span>FR</span><small>${best.cost} raw${best.shots?' · per-shot truncation':''}<br>${best.estimate?`from ${best.multiplier}×`:ties>1?`${ties} tied at integer cost`:''}</small></div>${done?`<p class="resurface">${done.cost-best.integer} FR below your completed ${done.cost} FR</p>`:''}${best.image?`<img class="fleet-image" src="/${esc(best.image)}" alt="${battle} fleet from ${esc(best.cell)}" loading="lazy" data-action="layout" data-id="${esc(best.layoutId)}">`:'<div class="no-image">Fleet image not available</div>'}<div class="card-body"><div class="badges"><span class="badge">${best.support?'Support':'No support'}</span><span class="badge">${best.hazard?'Hazard':'No hazard'}</span>${best.special?'<span class="badge estimate">CHECK SPECIAL REQUIREMENTS</span>':''}</div><p class="requirements ${best.special?'special':''}">${best.local ? 'Source: ' : ''}${esc(best.segment||req)}</p>${best.special?'<p class="help">This source mentions SHC, printed or L/M units. Check the full setup before using it.</p>':''}${c?.note?`<p class="source-note">${esc(c.note)}</p>`:''}${best.note?`<p class="requirements">${esc(best.note)}</p>`:''}</div>${conditionControls(battle)}<div class="card-footer">${completionForm(battle,best)}<button data-action="detail" data-battle="${battle}">Setups &amp; source (${ranked.length})</button></div></article>`;
}
function render(){
  if(!data||!state)return;
  $('#multiplier').value=state.settings.multiplier;$('#support').value=String(state.settings.support);$('#hazard').value=String(state.settings.hazard);$('#special').checked=state.settings.special;
  const ranks=new Map(data.battles.map(b=>[b,rankBattle(data,state,b)]));
  const pending=data.battles.filter(b=>shouldShow(state.done[b],ranks.get(b)[0]));
  const priced=pending.filter(b=>ranks.get(b).length);
  $('#stats').innerHTML=`<div class="stat"><b>${priced.length}</b><span>Available battles</span></div><div class="stat"><b>${Object.keys(state.done).length} / ${data.battles.length}</b><span>Marked complete</span></div><div class="stat"><b>${priced.reduce((n,b)=>n+ranks.get(b)[0].integer,0)} FR</b><span>Shown minimums · excludes missing results</span></div><div class="stat"><b>${priced.filter(b=>ranks.get(b)[0].estimate).length}</b><span>Unverified estimates shown</span></div>`;
  document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===view));
  $('#audit-filter-label').hidden=view!=='audit';$('.toolbar').hidden=view==='guide';
  if(view==='planner'){
    const filtered=pending.filter(b=>matches(b,data.cells.filter(c=>c.battle===b).map(c=>c.text).join(' ')));
    $('#content').innerHTML=filtered.length?`<div class="grid">${filtered.map(b=>card(b,ranks.get(b))).join('')}</div>`:'<div class="empty">No battles to show. Completed battles stay hidden until an available setup has a lower integer cost. Try another search or check Completed &amp; history.</div>';
  }else if(view==='audit'){
    const cells=data.cells.filter(c=>matches(c.battle,c.text+' '+c.note)&&($('#audit-filter').value==='all'||c.issues.length||c.recordIds.some(id=>data.records.find(r=>r.id===id)?.status==='obsolete')));
    $('#content').innerHTML=`<p class="audit-intro">${data.stats.cells} source cells · ${data.stats.usable} usable observations · ${data.stats.review} held for review · ${data.stats.obsolete} crossed out · ${data.stats.failed} failed. ${data.stats.missingImages} text cells have no adjacent image; ${data.stats.orphanImages} image references lack a direct text match.<br>Counts describe the original import. Local corrections are marked in setup details. ${cells.length} cells match this view.</p>${cells.slice(0,limit).map(c=>`<article class="row"><div><h3>${c.battle} · ${esc(c.sheet)} / ${c.cell}</h3><p class="source-text">${sourceMarkup(c)}</p>${c.note?`<p class="source-note">${esc(c.note)}</p>`:''}<p class="review-reason">${esc(c.issues.join(' · ')||'No import issues; inspect full requirements')}</p></div><div class="row-actions"><button data-action="layout" data-id="${c.layoutId}">Inspect &amp; correct</button><a href="${sourceLink(c)}" target="_blank" rel="noreferrer">Sheet ↗</a></div></article>`).join('')}${cells.length>limit?'<button class="more" data-action="more">Show more source cells</button>':''}`;
  }else if(view==='history'){
    const completed=Object.entries(state.done).filter(([b])=>matches(b));
    $('#content').innerHTML=`<p class="audit-intro">Completion stores the integer FR you actually spent. Changing settings or correcting observations does not rewrite your completed cost.</p>${completed.length?completed.map(([b,d])=>`<article class="row"><div><h3>${b} · ${d.cost} FR completed</h3><p>${new Date(d.at).toLocaleString()} · ${d.multiplier}×${ranks.get(b)?.[0]?` · current best ${ranks.get(b)[0].integer} FR`:''}</p></div><div class="row-actions"><button data-action="done" data-battle="${b}">Correct completed cost</button><button data-action="undo" data-battle="${b}">Reopen battle</button><button data-action="detail" data-battle="${b}">Setups</button></div></article>`).join(''):'<div class="empty">No completed battles match this view.</div>'}<h2>Completion log</h2>${[...state.history].reverse().filter(e=>matches(e.battle)).map(e=>`<p class="help">${esc(e.battle)} · ${e.cost} FR · ${new Date(e.at).toLocaleString()}</p>`).join('')||'<p class="help">Your completion records will appear here.</p>'}`;
  }else if(activeGalaxy.id==='g7'){
    $('#content').innerHTML=`<section class="guide"><h2>Support in G7</h2><p>Compare the costs of your actual layouts: <strong>support value = no-support battle costs − (with-support battle costs + cost of obtaining support).</strong></p><p>G7 support thresholds have not been verified. Check the <a href="https://docs.google.com/spreadsheets/d/${data.sourceId}/edit#gid=77408849" target="_blank" rel="noreferrer">G7 support calculator ↗</a> for its source guidance.</p><h2>Reading a result</h2><p>S = support, H = hazard, NS/NH = neither. Match both conditions before choosing a fleet. Nearest-lower results are unverified estimates. Multi-shot, disputed and unclear entries stay in the source review until you check their full-clear costs.</p><p>Progress, settings and corrections are saved separately for each galaxy. Export a backup before replacing a galaxy’s save.</p></section>`;
  }else{
    $('#content').innerHTML=`<section class="guide"><h2>When is support worth buying?</h2><p>Compare the costs of your actual layouts. These are your approximate skip guidelines, not battle prerequisites.</p><p><strong>Support value = no-support battle costs − (with-support battle costs + cost of obtaining support).</strong></p><table><thead><tr><th>Node</th><th>Approximate skip guideline</th></tr></thead><tbody>${[['F1','Around 1.5×'],['F2','Around 2.5×'],['F3','Around 2.5×'],['F4','If not fighting B26'],['F5','Around 3.5×; B33 should be cleared'],['F6','Around 3.5×'],['F7','If not fighting hazard B43'],['F8','If not fighting hazard B46 and at least 3.6×']].map(([a,b])=>`<tr><td>${a}</td><td>${b}</td></tr>`).join('')}</tbody></table><p>The extracted calculator is partial. Its 100 FR node purchases may exclude acquisition routes, so this planner does not calculate an automatic support route.</p><h2>Reading a result</h2><p>S = support, H = hazard, NS/NH = neither. SHC means Starting Heavy Cruiser (HP node). It is a fleet requirement. It does not mean support plus hazard.</p><p>Support and hazard choices must match the recorded observation. Use a battle’s controls to override the defaults. Setups and source shows the full text, including placement, weapons, printed ships and unit modifiers. Crossed-out results are excluded. Unclear costs and notes stay in review until you explicitly correct and enable them.</p><p>Nearest-lower selection happens separately for each source layout and condition. Failed or unresolved observations block older successes. Estimates are not guarantees of a clear.</p><p>Progress and edits are stored in <strong>local-data/state.json</strong> beside the launcher. Export a backup before moving computers or importing another save.</p></section>`;
  }
}
function observationRow(r){return `<div class="observation"><div><strong>${r.multiplier}× · ${r.cost===null?'Unknown FR':`${r.cost} FR`}</strong> <span class="badge ${r.status==='review'?'estimate':r.local?'local':''}">${r.local?'LOCAL · ':''}${statusText[r.status]||r.status}</span><small>${r.support===null?'Support unknown':r.support?'Support':'No support'} · ${r.hazard===null?'Hazard unknown':r.hazard?'Hazard':'No hazard'}${r.reasons?.length?' · '+esc(r.reasons.join('; ')):''}</small>${r.note?`<small>${esc(r.note)}</small>`:''}</div><button data-action="edit" data-id="${esc(r.id)}">Correct</button></div>`;}
function layoutDetail(id){
  const c=sourceCell(id);if(!c)return;
  const records=effectiveRecords(data,state).filter(r=>r.layoutId===id);
  $('#detail-content').innerHTML=`<div class="dialog-head"><h2>${c.battle} · ${c.cell}</h2><button data-close="detail" aria-label="Close details">✕</button></div><p class="help">${esc(c.sheet)} · <a href="${sourceLink(c)}" target="_blank" rel="noreferrer">Open source cell ↗</a></p>${c.image?`<img class="detail-image" src="/${esc(c.image)}" alt="${c.battle} fleet layout ${c.cell}">`:'<p class="source-note">No adjacent fleet image found.</p>'}<h3>Full source &amp; requirements</h3><p class="source-text">${sourceMarkup(c)}</p>${c.note?`<p class="source-note">${esc(c.note)}</p>`:''}${c.issues.length?`<p class="help">Import review: ${esc(c.issues.join('; '))}</p>`:''}<button data-action="add" data-id="${id}" class="primary">Add a checked observation for this setup</button><h3>Observations</h3>${records.map(observationRow).join('')}`;
  if(!$('#detail').open)$('#detail').showModal();
}
function battleDetail(battle){
  detailBattle=battle;const ranked=rankBattle(data,state,battle),cells=data.cells.filter(c=>c.battle===battle);
  $('#detail-content').innerHTML=`<div class="dialog-head"><h2>${battle} · setups &amp; source</h2><button data-close="detail" aria-label="Close details">✕</button></div><p class="help">At ${state.settings.multiplier}×, ${ranked.length} layouts match your conditions. Ties use integer FR; estimates are labelled.</p><h3>Matching layouts</h3>${ranked.map(r=>`<div class="observation"><div><strong>${r.integer} FR</strong> · ${esc(r.cell||'Local setup')}<small>${r.estimate?`UNVERIFIED ESTIMATE from ${r.multiplier}×`:'Recorded at this multiplier'} · ${r.cost} raw${r.special?' · CHECK SPECIAL REQUIREMENTS':''}</small><small>${esc(r.segment||r.note||'')}</small></div><button data-action="layout" data-id="${r.layoutId}">View fleet</button></div>`).join('')||'<p class="help">No usable matching results.</p>'}<h3>All source layouts</h3>${cells.map(c=>`<div class="observation"><div><strong>${c.cell}</strong><small>${esc(c.text.slice(0,160))}${c.text.length>160?'…':''}</small></div><button data-action="layout" data-id="${c.layoutId}">Inspect</button></div>`).join('')}`;
  if(!$('#detail').open)$('#detail').showModal();
}
function openEditor(id,isNew=false){
  const r=isNew?null:effectiveRecords(data,state).find(r=>r.id===id),c=sourceCell(isNew?id:r?.layoutId);if(!c)return;
  editing={r,c,isNew};const f=$('#edit-form');f.reset();$('#edit-title').textContent=isNew?'Add checked observation':'Correct observation';$('#edit-source').textContent=`${c.battle} · ${c.sheet} / ${c.cell}. The original sheet remains unchanged.`;
  const cond=state.conditions[c.battle]||state.settings;
  for(const k of ['multiplier','cost','support','hazard'])f.elements[k].value=String(r?.[k]??(k==='multiplier'?state.settings.multiplier:k==='cost'?'':cond[k]));
  f.elements.shots.value=r?.shots?.join(' + ')||'';f.elements.note.value=r?.note||'';f.elements.special.checked=r?.special??data.records.some(x=>x.layoutId===c.layoutId&&x.special);f.elements.enabled.checked=!!r&&r.status==='usable';
  $('#restore-record').hidden=isNew||!state.edits[id];$('#edit-error').textContent='';$('#editor').showModal();
}
function doneDialog(battle){const best=rankBattle(data,state,battle)[0];$('#detail-content').innerHTML=`<div class="dialog-head"><h2>${battle} · record completion</h2><button data-close="detail" aria-label="Close completion">✕</button></div><p>Enter the integer FR you actually spent. This battle stays hidden until a setup has a strictly lower integer cost.</p><form id="done-form"><label>Completed FR cost<input id="done-cost" type="number" min="0" step="1" required value="${state.done[battle]?.cost??best?.integer??''}"></label>${best?.estimate?'<p class="help">The suggested cost is an unverified estimate. Replace it with your actual spent FR.</p>':''}<div class="dialog-actions"><button class="primary">Save completion</button></div></form>`;if(!$('#detail').open)$('#detail').showModal();$('#done-form').onsubmit=async e=>{e.preventDefault();try{await persist(completeBattle(state,battle,Number($('#done-cost').value)));$('#detail').close();notify(`${battle} completion saved`);}catch(e){handleError(e);}};}
document.addEventListener('click',async e=>{
  const b=e.target.closest('button,[data-action]');if(!b)return;
  if(b.dataset.galaxy){if(saving){notify('Please wait for the current save.');return;}location.href=`/?galaxy=${b.dataset.galaxy}`;return;}
  if(b.dataset.close){$('#'+b.dataset.close).close();return;}
  if(b.dataset.view){view=b.dataset.view;limit=60;render();return;}
  try{const {action,battle,id}=b.dataset;
    if(action==='detail')battleDetail(battle);
    if(action==='layout')layoutDetail(id);
    if(action==='edit')openEditor(id);
    if(action==='add')openEditor(id,true);
    if(action==='done')doneDialog(battle);
    if(action==='more'){limit+=60;render();}
    if(action==='undo'){const next=structuredClone(state);delete next.done[battle];await persist(next);notify(`${battle} reopened`);}
    if(action==='default'){const next=structuredClone(state);delete next.conditions[battle];await persist(next);}
  }catch(e){handleError(e);}
});
document.addEventListener('change',async e=>{const el=e.target;if(el.dataset.condition){const next=structuredClone(state),b=el.dataset.battle;next.conditions[b]={support:state.settings.support,hazard:state.settings.hazard,...state.conditions[b],[el.dataset.condition]:el.value==='true'};try{await persist(next);}catch(e){handleError(e);render();}}});
document.addEventListener('input',e=>{const form=e.target.closest('.completion-form');if(form)completionDrafts.set(form.dataset.draft,e.target.value);});
document.addEventListener('submit',async e=>{
  const form=e.target;if(!form.matches('.completion-form'))return;
  e.preventDefault();const {battle,draft}=form.dataset,raw=form.elements.cost.value,button=form.querySelector('button');
  button.disabled=true;
  try{const next=completeBattle(state,battle,Number(raw));completionDrafts.delete(draft);await persist(next);notify(`${battle} completed at ${Number(raw)} FR`);}
  catch(error){completionDrafts.set(draft,raw);handleError(error);}
  finally{button.disabled=false;}
});
for(const id of ['support','hazard','special'])$('#'+id).addEventListener('change',async()=>{const next=structuredClone(state);next.settings[id]=id==='special'?$('#special').checked:$('#'+id).value==='true';try{await persist(next);}catch(e){handleError(e);render();}});
$('#apply-multiplier').onclick=async()=>{const next=structuredClone(state);next.settings.multiplier=Number($('#multiplier').value);try{await persist(next);}catch(e){handleError(e);render();}};
$('#multiplier').addEventListener('keydown',e=>{if(e.key==='Enter')$('#apply-multiplier').click();});
for(const id of ['search','group','audit-filter'])$('#'+id).addEventListener(id==='search'?'input':'change',()=>{limit=60;render();});
$('#edit-form').addEventListener('submit',async e=>{
  e.preventDefault();const f=e.target,shots=f.elements.shots.value.trim()?f.elements.shots.value.split('+').map(s=>Number(s.trim())):undefined;
  const patch={multiplier:Number(f.elements.multiplier.value),cost:Number(f.elements.cost.value),support:f.elements.support.value==='true',hazard:f.elements.hazard.value==='true',special:f.elements.special.checked,enabled:f.elements.enabled.checked,note:f.elements.note.value.trim(),...(shots?{shots}:{} )};
  if(shots&&Math.abs(shots.reduce((a,b)=>a+b,0)-patch.cost)>.001){$('#edit-error').textContent='Individual shot costs must add up to the full-clear cost.';return;}
  const next=structuredClone(state),{r,c,isNew}=editing;
  if(isNew)next.custom.push({...patch,id:crypto.randomUUID(),layoutId:c.layoutId,battle:c.battle,image:c.image,cell:c.cell,segment:patch.note});
  else if(state.custom.some(x=>x.id===r.id))next.custom=next.custom.map(x=>x.id===r.id?{...x,...patch,shots}:x);
  else next.edits[r.id]=patch;
  try{await persist(next);$('#editor').close();layoutDetail(c.layoutId);notify('Local observation saved');}catch(e){$('#edit-error').textContent=e.message;}
});
$('#restore-record').onclick=async()=>{try{const next=structuredClone(state);delete next.edits[editing.r.id];await persist(next);$('#editor').close();layoutDetail(editing.c.layoutId);}catch(e){handleError(e);}};
$('#export').onclick=()=>{if(!state)return;const blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`${activeGalaxy.id}-backup-${new Date().toISOString().slice(0,10)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('#import').onclick=()=>$('#backup-file').click();
$('#backup-file').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;const incoming=validateGalaxyState(validateState(JSON.parse(await file.text())),activeGalaxy.id);$('#detail-content').innerHTML=`<div class="dialog-head"><h2>Import ${activeGalaxy.label} backup</h2><button data-close="detail" aria-label="Close import">✕</button></div><p>This backup contains ${Object.keys(incoming.done).length} completed battles, ${Object.keys(incoming.edits).length} corrections and ${incoming.custom.length} added observations.</p><p>Import replaces ${activeGalaxy.label} progress and settings. Export your current backup first if you want to keep both.</p><button id="confirm-import" class="primary">Replace with this backup</button>`;$('#detail').showModal();$('#confirm-import').onclick=async()=>{try{await persist(incoming);$('#detail').close();notify('Backup imported');}catch(e){handleError(e);}};}catch(e){handleError(e);}finally{e.target.value='';}};
$('#galaxy-tabs').innerHTML=galaxies.map(g=>'<button data-galaxy="'+g.id+'" class="'+(g.id===activeGalaxy.id?'active':'')+'" aria-pressed="'+(g.id===activeGalaxy.id)+'">'+g.label+'</button>').join('');
document.title=activeGalaxy.label+' · Fleet Planner';
try{
  const responses=await Promise.all([fetch(activeGalaxy.data),fetch(stateUrl)]);
  for(const r of responses)if(!r.ok)throw Error((await r.json()).error||'Could not load planner');
  [data,state]=await Promise.all(responses.map(r=>r.json()));
  validateGalaxyState(validateState(state),activeGalaxy.id);state.galaxy=activeGalaxy.id;
  if(data.galaxy!==activeGalaxy.id)throw Error('The selected galaxy data does not match.');
  $('#group').innerHTML='<option value="all">All '+data.battles.length+' battles</option>'+data.groups.map(g=>'<option value="'+esc(g.id)+'">'+esc(g.label)+'</option>').join('');
  $('#source-snapshot').textContent=activeGalaxy.title+' · source snapshot '+data.extractedAt;
  $('#search').placeholder=activeGalaxy.id==='g7'?'B2A, BB1, beam, corvette…':'B26, BB2, beam, corvette…';
  $('#save-status').textContent=activeGalaxy.label+' saved on this computer';render();
}catch(e){$('#save-status').textContent='Could not load local data';$('#content').innerHTML='<div class="empty error">'+esc(e.message)+'. Existing files have not been changed.</div>';}
