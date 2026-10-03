export type PlayableMatch = {index:number;home:string;away:string;valid:boolean;day?:number;group?:string;round?:number;round_name?:string};
export type Attendee = {id:string;name:string;teams:string[]};
const normalize=(name:string)=>name.trim().toLocaleLowerCase('it').replace(/\s+/g,' ');
export const isParticipant=(name:string)=>!!name.trim()&&!/^(riposo|riposa|bye|da definire|tbd)$/i.test(name.trim());
export function playerName(team:string){
  const separator=team.includes(' - ')?' - ':'-';
  const position=team.indexOf(separator);
  return position<0?team.trim():team.slice(position+separator.length).trim()||team.trim();
}
export function attendees(teams:string[],names:Record<string,string>={}):Attendee[]{
  const result=new Map<string,Attendee>();
  for(const team of teams.filter(isParticipant)){
    const name=names[team]?.trim()||playerName(team),id=normalize(name);
    if(!result.has(id))result.set(id,{id,name,teams:[]});
    if(!result.get(id)!.teams.includes(team))result.get(id)!.teams.push(team);
  }
  return [...result.values()].sort((a,b)=>a.name.localeCompare(b.name,'it'));
}
type Options={activeRound?:number;closed?:boolean;withdrawals?:string[];blocked?:number[]};
export function suggestMatches(matches:PlayableMatch[],players:Attendee[],present:string[],options:Options={}){
  const teamIds=new Map(players.flatMap(p=>p.teams.map(team=>[team,p.id] as const)));
  const selected=new Set(present), withdrawn=new Set(options.withdrawals),blocked=new Set(options.blocked);
  const candidates=options.closed?[]:matches.filter(m=>!m.valid&&!blocked.has(m.index)&&
    !withdrawn.has(m.home)&&!withdrawn.has(m.away)&&isParticipant(m.home)&&isParticipant(m.away)&&
    (options.activeRound===undefined||m.round===options.activeRound)&&
    selected.has(teamIds.get(m.home)!)&&selected.has(teamIds.get(m.away)!)&&teamIds.get(m.home)!==teamIds.get(m.away));
  const priority=(m:PlayableMatch)=>m.day??m.round??1;
  const stages=[...new Set(candidates.map(priority))].sort((a,b)=>a-b);
  const sorted=[...candidates].sort((a,b)=>priority(a)-priority(b)||(a.group||'').localeCompare(b.group||'','it',{numeric:true})||a.index-b.index);
  const ids=[...new Set(sorted.flatMap(m=>[teamIds.get(m.home)!,teamIds.get(m.away)!]))];
  let proposed:PlayableMatch[]=[];
  // Exact selection for normal club evenings. The comparison first maximizes
  // the number of earliest-day games, then the next day, and so on.
  if(ids.length<=18){
    const edges=sorted.map(m=>({match:m,a:ids.indexOf(teamIds.get(m.home)!),b:ids.indexOf(teamIds.get(m.away)!)}));
    const memo=new Map<number,PlayableMatch[]>();
    const better=(a:PlayableMatch[],b:PlayableMatch[])=>{
      for(const stage of stages){const delta=a.filter(m=>priority(m)===stage).length-b.filter(m=>priority(m)===stage).length;if(delta)return delta>0;}
      return false;
    };
    function solve(mask:number):PlayableMatch[]{
      if(!mask)return [];
      const cached=memo.get(mask);if(cached)return cached;
      const first=ids.findIndex((_,i)=>mask&(1<<i));
      // Explore matches before skipping, so equal solutions stay deterministic.
      let best:PlayableMatch[]=[];
      for(const e of edges){if(e.a!==first&&e.b!==first)continue;const bits=(1<<e.a)|(1<<e.b);if((mask&bits)!==bits)continue;
        const choice=[e.match,...solve(mask&~bits)];if(better(choice,best))best=choice;}
      const skip=solve(mask&~(1<<first));if(better(skip,best))best=skip;
      memo.set(mask,best);return best;
    }
    proposed=solve((1<<ids.length)-1);
  }else{
    // Bound runtime for large events: take earlier days first and, within a
    // day, favour players with fewer alternative opponents that evening.
    const degree=new Map(ids.map(id=>[id,sorted.filter(m=>teamIds.get(m.home)===id||teamIds.get(m.away)===id).length]));
    const used=new Set<string>();
    for(const m of [...sorted].sort((a,b)=>priority(a)-priority(b)||
      (degree.get(teamIds.get(a.home)!)!+degree.get(teamIds.get(a.away)!)!)-(degree.get(teamIds.get(b.home)!)!+degree.get(teamIds.get(b.away)!)!)||a.index-b.index)){
      const a=teamIds.get(m.home)!,b=teamIds.get(m.away)!;
      if(!used.has(a)&&!used.has(b)){proposed.push(m);used.add(a);used.add(b);}
    }
  }
  proposed.sort((a,b)=>sorted.indexOf(a)-sorted.indexOf(b));
  const playing=new Set(proposed.flatMap(m=>[teamIds.get(m.home),teamIds.get(m.away)]));
  return {proposed,available:candidates.length,waiting:players.filter(p=>selected.has(p.id)&&!playing.has(p.id))};
}
