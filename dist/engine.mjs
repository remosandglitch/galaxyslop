export const integerCost = cost => Math.trunc(cost);
export function initialState(galaxy='g6') {
  return {version: 1, galaxy, settings: {multiplier: galaxy==='g7'?1.5:3, support: false, hazard: false, special: true}, conditions: {}, done: {}, edits: {}, custom: [], history: []};
}
export function validateState(s) {
  if (!s || s.version !== 1 || !s.settings || !Number.isFinite(s.settings.multiplier) || s.settings.multiplier <= 0 || s.settings.multiplier > 100) throw Error('Invalid multiplier or backup version.');
  if(s.galaxy!==undefined && !['g6','g7'].includes(s.galaxy))throw Error('Invalid galaxy in backup.');
  for (const k of ['support', 'hazard', 'special']) if (typeof s.settings[k] !== 'boolean') throw Error('Invalid settings.');
  for (const k of ['done','edits','conditions']) if (!s[k] || typeof s[k] !== 'object' || Array.isArray(s[k])) throw Error('Invalid backup structure.');
  if (!Array.isArray(s.custom) || !Array.isArray(s.history)) throw Error('Invalid history or observations.');
  for (const [battle,v] of Object.entries(s.done)) if (!/^B{1,2}\d+[A-Z]?$/.test(battle) || !Number.isSafeInteger(v.cost) || v.cost < 0) throw Error('Completed costs must be nonnegative integers.');
  for (const c of Object.values(s.conditions)) if (typeof c.support !== 'boolean' || typeof c.hazard !== 'boolean') throw Error('Invalid battle conditions.');
  for (const r of [...Object.values(s.edits),...s.custom]) {
    if (!Number.isFinite(r.multiplier) || r.multiplier <= 0 || r.multiplier > 100 || !Number.isFinite(r.cost) || r.cost < 0 || r.cost > 1e8 || typeof r.support !== 'boolean' || typeof r.hazard !== 'boolean' || typeof r.enabled !== 'boolean') throw Error('Invalid corrected observation.');
    if (r.shots && (!Array.isArray(r.shots) || !r.shots.length || r.shots.some(n=>!Number.isFinite(n)||n<0))) throw Error('Invalid shot costs.');
    if(r.shots && Math.abs(r.shots.reduce((a,b)=>a+b,0)-r.cost)>.001) throw Error('Shot costs must sum to the full-clear cost.');
    if(r.note!==undefined && typeof r.note!=='string') throw Error('Invalid correction note.');
    if(typeof r.special!=='boolean') throw Error('Invalid special requirement flag.');
  }
  for (const r of s.custom) if (!/^B{1,2}\d+[A-Z]?$/.test(r.battle) || typeof r.id !== 'string' || !/^\d+:[A-Z]+\d+$/.test(r.layoutId) || (r.image && !/^source\/images\/[\w/.-]+$/.test(r.image))) throw Error('Invalid custom observation.');
  for(const r of [...Object.values(s.done),...s.history]) if(!Number.isSafeInteger(r.cost)||r.cost<0||!Number.isFinite(r.multiplier)||!Number.isFinite(Date.parse(r.at))||(r.battle&&!/^B{1,2}\d+[A-Z]?$/.test(r.battle))) throw Error('Invalid completion history.');
  return s;
}
export function effectiveRecords(data, state) {
  return [...data.records.map(r => state.edits[r.id] ? {...r,...state.edits[r.id], status: state.edits[r.id].enabled ? 'usable':'disabled', local: true} : r), ...state.custom.map(r=>({...r,status:r.enabled?'usable':'disabled',local:true}))];
}
export function rankBattle(data, state, battle) {
  const conditions = state.conditions[battle] || state.settings;
  const eligible = effectiveRecords(data,state).filter(r=>r.battle===battle && r.support===conditions.support && r.hazard===conditions.hazard && r.multiplier<=state.settings.multiplier && (state.settings.special || !r.special));
  const groups = new Map();
  // Failed and uncertain observations are barriers: never carry an older success through them.
  for (const r of eligible) {
    if (r.status==='obsolete' || r.status==='disabled') continue;
    const group = groups.get(r.layoutId) || [];
    if (!group.length || r.multiplier>group[0].multiplier) groups.set(r.layoutId,[r]);
    else if (r.multiplier===group[0].multiplier) group.push(r);
  }
  return [...groups.values()].flatMap(group=>group.every(r=>r.status==='usable')?group:[]).map(r=>({...r, integer:r.shots?r.shots.reduce((n,c)=>n+integerCost(c),0):integerCost(r.cost), estimate:r.multiplier!==state.settings.multiplier})).sort((a,b)=>a.integer-b.integer || Number(a.estimate)-Number(b.estimate) || a.id.localeCompare(b.id));
}
export function shouldShow(done, best) { return !done || !!best && best.integer < done.cost; }
export function completeBattle(state,battle,cost) {
  if (!Number.isSafeInteger(cost)||cost<0) throw Error('Enter an integer FR cost.');
  const entry={battle,cost,at:new Date().toISOString(),multiplier:state.settings.multiplier};
  return {...state, done:{...state.done,[battle]:entry}, history:[...state.history,entry]};
}
