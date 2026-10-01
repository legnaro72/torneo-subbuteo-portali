import {useLayoutEffect, useRef, useState} from 'react';
import {Trophy} from 'lucide-react';
import {TeamMark, type BadgeMap} from './TeamBadges';
import {bracketLinks, matchWinner, type BracketMatch} from './presentation';

export default function KnockoutBracket({matches,badges,format,champion}:{matches:BracketMatch[];badges?:BadgeMap;format:(name:string)=>string;champion?:string}) {
  const board=useRef<HTMLDivElement>(null);
  const [paths,setPaths]=useState<{d:string;highlight:boolean}[]>([]);
  const rounds=[...new Set(matches.map(m=>m.round))].sort((a,b)=>a-b);
  useLayoutEffect(()=>{
    const element=board.current;if(!element)return;
    const measure=()=>{
      const rect=element.getBoundingClientRect();
      setPaths(bracketLinks(matches).flatMap(link=>{
        const from=element.querySelector<HTMLElement>(`[data-match="${link.from}"]`), to=element.querySelector<HTMLElement>(`[data-match="${link.to}"]`);
        if(!from||!to)return [];
        const a=from.getBoundingClientRect(),b=to.getBoundingClientRect();
        const x1=a.right-rect.left,y1=a.top+a.height/2-rect.top,x2=b.left-rect.left,y2=b.top+b.height/2-rect.top,mid=(x1+x2)/2;
        return [{d:`M${x1},${y1} H${mid} V${y2} H${x2}`,highlight:link.team===champion}];
      }));
    };
    measure();const observer=new ResizeObserver(measure);observer.observe(element);
    return()=>observer.disconnect();
  },[matches,champion]);
  return <section className="results-card knockout"><div className="results-heading"><div><span className="eyebrow">LA STRADA VERSO IL TROFEO</span><h3><Trophy size={20}/>Tabellone delle finali</h3></div></div><p className="bracket-hint">Scorri per seguire i turni. Le linee collegano i vincitori agli incontri effettivamente generati.</p><div className="bracket-scroll" tabIndex={0} role="region" aria-label="Tabellone a eliminazione diretta scorrevole"><div className="bracket-board" ref={board}><svg className="bracket-lines" aria-hidden="true">{paths.map((p,i)=><path key={i} d={p.d} className={p.highlight?'champion-path':''}/>)}</svg>{rounds.map(n=><section className="bracket-round" key={n}><h4>{matches.find(r=>r.round===n)?.round_name||`Turno ${n}`}</h4><div className="bracket-round-matches">{matches.filter(r=>r.round===n).map(m=><article className={'bracket-match'+(champion&&matchWinner(m)===champion?' champion-match':'')} data-match={m.index} key={m.index}>{([['home',m.home,m.home_goals],['away',m.away,m.away_goals]] as const).map(([side,name,goals])=><div key={side} className={matchWinner(m)===name?'bracket-winner':''}><span className="team-mark"><TeamMark name={name} badge={badges?.[name]}/></span><span>{format(name)}</span><strong>{m.valid?goals:'—'}</strong>{matchWinner(m)===name&&<Trophy size={14} aria-label="Vincitore"/>}</div>)}<small>{m.valid?'Risultato validato':'Da giocare / validare'}</small></article>)}</div></section>)}</div></div>{champion&&<div className="bracket-champion"><Trophy/><span>Campione <strong>{format(champion)}</strong></span></div>}</section>;
}
