// Display-only labels: identifiers, stored names and routes remain untouched.
export function tournamentLabel(name:string):string {
  return name.replace(/^(?:(?:completato|finito)_)+/, '')
    .replace(/^fasefinaleEliminazionediretta_/, 'Finali · ')
    .replace(/^fasefinaleAGironi_/, 'Gironi finali · ')
    .replace(/CampionatoSuperba/g, 'Campionato Superba')
    .replace(/_(\d{2})_(\d{2})(?=_|$)/g, ' · 20$1/$2')
    .replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
}

export function matchDelay(index:number, all:boolean):number {
  return all ? 0 : Math.min(index, 7) * 105;
}

export type BracketMatch = {index:number;round:number;round_name?:string;home:string;away:string;home_goals:number;away_goals:number;valid:boolean;winner?:string};
export function matchWinner(match:BracketMatch) {
  if(!match.valid)return undefined;
  return match.winner || (match.home_goals>match.away_goals?match.home:match.away_goals>match.home_goals?match.away:undefined);
}

// Pairings are reseeded by the backend; never assume adjacent cards feed each other.
export function bracketLinks(matches:BracketMatch[]) {
  const rounds=[...new Set(matches.map(m=>m.round))].sort((a,b)=>a-b);
  return matches.flatMap(from=>{
    const winner=matchWinner(from), next=rounds[rounds.indexOf(from.round)+1];
    const to=winner&&next!==undefined?matches.find(m=>m.round===next&&(m.home===winner||m.away===winner)):undefined;
    return to?[{from:from.index,to:to.index,team:winner!}]:[];
  });
}
