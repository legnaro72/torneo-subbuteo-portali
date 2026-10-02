import {useEffect,useState} from 'react';
import {Trophy, Flag, ArrowUpRight} from 'lucide-react';
import {api,type Tournament} from './api';
import {TeamMark} from './TeamBadges';
import {LoadingPanel} from './MatchPresentation';

export default function ChampionshipStory({id,revision,onOpen}:{id:string;revision:string;onOpen:()=>void}){
  const [data,setData]=useState<Tournament|null>(null),[error,setError]=useState(false);
  useEffect(()=>{let cancelled=false;setData(null);setError(false);api<Tournament>(`/tournaments/${id}`).then(t=>{if(!cancelled)setData(t);}).catch(()=>{if(!cancelled)setError(true);});return()=>{cancelled=true;};},[id,revision]);
  if(error)return <p className="results-note">Il riepilogo non è disponibile in questo momento. Puoi aprire il campionato.</p>;
  if(!data)return <LoadingPanel label="Il campionato prende forma…"/>;
  const groups=[...new Set(data.standings.map(s=>s.Girone))], leaders=groups.flatMap(g=>data.standings.filter(s=>s.Girone===g).slice(0,1)).filter(s=>s.G>0);
  const played=data.matches.filter(m=>m.valid),last=[...played].sort((a,b)=>b.day-a.day||b.index-a.index)[0], progress=data.matches.length?Math.round(100*played.length/data.matches.length):0;
  return <section className="championship-story" aria-label="Il campionato in primo piano"><article><span className="story-eyebrow"><Trophy size={16}/>{leaders.length>1?'AL COMANDO DEI GIRONI':'AL COMANDO'}</span>{leaders.length?leaders.map(s=><div className="story-leader" key={s.Girone}><TeamMark name={s.Squadra} badge={data.badges?.[s.Squadra]}/><div><strong>{s.Squadra}</strong><small>{groups.length>1?`${s.Girone} · `:''}{s.Punti} punti · {s.G} partite</small></div></div>):<p>La corsa al titolo deve ancora cominciare.</p>}</article><article><span className="story-eyebrow"><Flag size={16}/>LA CORSA AL TITOLO</span><strong className="story-progress">{progress}<small>%</small></strong><div className="story-track" role="progressbar" aria-label="Partite validate" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}><i style={{width:`${progress}%`}}/></div><p>{played.length} incontri validati su {data.matches.length}</p></article><article><span className="story-eyebrow">DAL CALENDARIO</span>{last?<><div className="story-result"><span>{last.home}</span><b>{last.home_goals} : {last.away_goals}</b><span>{last.away}</span></div><p>Ultimo risultato in ordine di calendario · G{last.day}{groups.length>1?` · ${last.group}`:''}</p></>:<p>Il primo risultato scriverà la storia.</p>}<button type="button" onClick={onOpen}>Entra nel campionato<ArrowUpRight size={16}/></button></article></section>;
}
