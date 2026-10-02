import {useState} from 'react';
import {Trophy} from 'lucide-react';
import {TeamMark,type TeamBadge} from './TeamBadges';
import {tournamentLabel} from './presentation';
type Player={id:string;name:string;team:string;badge?:TeamBadge;listaCampionatiVinti:string[];listaGironiFFVinti:string[];listaFFElimDirettaVinte:string[]};
export function seasonOf(name:string){return tournamentLabel(name).match(/\b20\d{2}\/\d{2}\b/)?.[0]||'Stagione non indicata';}
export default function SeasonHonours({players}:{players:Player[]}){
  const [selected,setSelected]=useState('all');
  const entries=players.flatMap(p=>([['Campionato',p.listaCampionatiVinti],['Girone finale',p.listaGironiFFVinti],['Eliminazione diretta',p.listaFFElimDirettaVinte]] as [string,string[]][]).flatMap(([kind,names])=>names.map((name,i)=>({key:`${p.id}:${kind}:${i}`,name,kind,season:seasonOf(name),player:p}))));
  const seasons=[...new Set(entries.map(e=>e.season))].sort((a,b)=>a==='Stagione non indicata'?1:b==='Stagione non indicata'?-1:b.localeCompare(a));
  if(!entries.length)return <p className="results-note">Le prime vittorie entreranno qui, nella storia del club.</p>;
  return <section className="season-honours" aria-labelledby="honours-title"><div className="section-heading"><div><span className="eyebrow">LA STORIA RESTA</span><h3 id="honours-title">Le stagioni dei campioni</h3></div><label>Stagione<select value={selected} onChange={e=>setSelected(e.target.value)}><option value="all">Tutte le stagioni</option>{seasons.map(s=><option key={s}>{s}</option>)}</select></label></div>{seasons.filter(s=>selected==='all'||selected===s).map(season=><section className="season-chapter" key={season}><h4>{season}</h4><div className="season-trophies">{entries.filter(e=>e.season===season).map(e=><article key={e.key}><Trophy size={26}/><span>{e.kind}</span><h4>{tournamentLabel(e.name)}</h4><div><TeamMark name={e.player.team||e.player.name} badge={e.player.badge}/><strong>{e.player.name}</strong></div></article>)}</div></section>)}</section>;
}
