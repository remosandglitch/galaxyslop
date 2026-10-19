export const galaxies = [
  {id:'g6',label:'G6',title:'Copy of G6',data:'/data.json'},
  {id:'g7',label:'G7',title:'G7',data:'/data-g7.json'}
];
export function validateGalaxyState(state, galaxy) {
  if(!galaxies.some(g=>g.id===galaxy)) throw Error('Unknown galaxy.');
  if((state.galaxy??'g6')!==galaxy) throw Error(`This backup belongs to ${(state.galaxy??'g6').toUpperCase()}, not ${galaxy.toUpperCase()}. Switch to the matching galaxy first.`);
  return state;
}
