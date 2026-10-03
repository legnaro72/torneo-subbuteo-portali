import {useMemo,useState} from 'react';
import {ArrowRight,Search,Users,Zap} from 'lucide-react';
import {TeamMark,type BadgeMap} from './TeamBadges';
import {attendees,suggestMatches,type PlayableMatch} from './matchSuggestions';
import './playNow.css';

type Props={matches:PlayableMatch[];storageKey:string;badges?:BadgeMap;withdrawals?:string[];activeRound?:number;closed?:boolean;blocked?:number[];participants?:{Squadra:string;Giocatore:string}[];onOpen:(match:PlayableMatch)=>void};
const emptyTeams:string[]=[],emptyBlocked:number[]=[],emptyParticipants:{Squadra:string;Giocatore:string}[]=[];
export default function PlayNow({matches,storageKey,badges,withdrawals=emptyTeams,activeRound,closed=false,blocked=emptyBlocked,participants=emptyParticipants,onOpen}:Props){
  const players=useMemo(()=>attendees([...matches.flatMap(m=>[m.home,m.away]),...participants.map(p=>p.Squadra)].filter(team=>!withdrawals.includes(team)),Object.fromEntries(participants.map(p=>[p.Squadra,p.Giocatore]))),[matches,participants,withdrawals]);
  const [selected,setSelected]=useState<string[]>(()=>{try{const stored=JSON.parse(sessionStorage.getItem(storageKey)||'[]');return Array.isArray(stored)?stored.filter(x=>typeof x==='string'):[];}catch{return [];}});
  const [search,setSearch]=useState('');
  const present=selected.filter(id=>players.some(p=>p.id===id));
  const result=useMemo(()=>suggestMatches(matches,players,present,{activeRound,closed,withdrawals,blocked}),[matches,players,selected,activeRound,closed,withdrawals,blocked]);
  const visible=players.filter(p=>`${p.name} ${p.teams.join(' ')}`.toLocaleLowerCase('it').includes(search.toLocaleLowerCase('it')));
  function choose(ids:string[]){setSelected(ids);try{sessionStorage.setItem(storageKey,JSON.stringify(ids));}catch{/* Attendance still works in memory. */}}
  const roundLabel=(m:PlayableMatch)=>m.day!==undefined?`${m.group?`${m.group} · `:''}Giornata ${m.day}`:m.round_name||`Turno ${m.round}`;
  return <section className="play-now" aria-label="Gioca ora">
    <div className="results-card play-attendance"><div className="section-heading"><div><h2><Users size={21}/>Chi c’è stasera?</h2><p>Seleziona i presenti. Le proposte danno precedenza alle prime giornate, con una sola partita per giocatore.</p></div><span className="badge">{present.length} presenti</span></div>
      <div className="play-selection-tools"><label className="search"><Search size={17}/><input aria-label="Cerca tra i partecipanti" placeholder="Cerca giocatore o squadra…" value={search} onChange={e=>setSearch(e.target.value)}/></label><button type="button" className="secondary compact" onClick={()=>choose(players.map(p=>p.id))}>Tutti presenti</button><button type="button" className="text-button" disabled={!present.length} onClick={()=>choose([])}>Svuota</button></div>
      <div className="play-players">{visible.map(p=><label key={p.id} className={'play-player'+(present.includes(p.id)?' selected':'')}><input type="checkbox" checked={present.includes(p.id)} onChange={e=>choose(e.target.checked?[...present,p.id]:present.filter(id=>id!==p.id))}/><span className="team-mark"><TeamMark name={p.teams[0]} badge={badges?.[p.teams[0]]}/></span><span><strong>{p.name}</strong><small>{p.teams.join(' · ')}</small></span></label>)}</div>{!visible.length&&<p className="empty">Nessun partecipante corrisponde alla ricerca.</p>}
    </div>
    <div className="results-card play-proposals"><div className="results-heading"><h3><Zap size={18}/>In campo insieme</h3><span role="status">{result.proposed.length} incontri suggeriti</span></div>
      {blocked.length>0&&<p className="results-note">Le partite con modifiche in bozza sono escluse: salva i risultati per aggiornare i suggerimenti.</p>}
      {activeRound!==undefined&&!closed&&<p className="results-note">Proposte dal turno attivo {activeRound}. Gli abbinamenti dei turni successivi saranno disponibili dopo la loro generazione.</p>}
      <div className="play-games">{result.proposed.map(m=><article className="play-game" key={m.index}><small>{roundLabel(m)}</small><div className="play-pair"><div><span className="team-mark"><TeamMark name={m.home} badge={badges?.[m.home]}/></span><strong>{m.home}</strong></div><span className="play-versus">VS</span><div><span className="team-mark"><TeamMark name={m.away} badge={badges?.[m.away]}/></span><strong>{m.away}</strong></div></div><button type="button" className="secondary compact" onClick={()=>onOpen(m)} aria-label={`Apri ${m.home} contro ${m.away}`}>Apri {m.day!==undefined?'giornata':'turno'}<ArrowRight size={16}/></button></article>)}</div>
      {!result.proposed.length&&<div className="empty"><Zap size={25}/><h3>{closed?'Torneo concluso':present.length<2?'Seleziona almeno due presenti':'Nessun incontro disponibile'}</h3><p>{closed?'Non ci sono partite da proporre.':present.length<2?'Scegli i giocatori qui sopra per comporre la serata.':'Tra i presenti non ci sono incontri ancora da validare e disponibili in questo momento.'}</p></div>}
      {result.proposed.length>0&&<p className="results-note">{result.available} incontri disponibili tra i presenti. Questa proposta può essere giocata contemporaneamente; si aggiorna quando salvi i risultati o cambi le presenze.</p>}
      {present.length>=2&&!closed&&result.waiting.length>0&&<p className="play-waiting"><strong>In attesa in questa proposta:</strong> {result.waiting.map(p=>p.name).join(', ')}.</p>}
    </div>
  </section>;
}
