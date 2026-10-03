import {useMemo,useState} from 'react';
import {ArrowRight,Download,MessageCircle,Search,Users,Zap} from 'lucide-react';
import {TeamMark,type BadgeMap} from './TeamBadges';
import {attendees,suggestMatches,type PlayableMatch} from './matchSuggestions';
import './playNow.css';
import {preparePlayNowPdf,savePlayNowPdf} from './playNowPdf';

type Props={matches:PlayableMatch[];storageKey:string;exportPath:string;version:string;badges?:BadgeMap;withdrawals?:string[];activeRound?:number;closed?:boolean;blocked?:number[];participants?:{Squadra:string;Giocatore:string}[];onOpen:(match:PlayableMatch)=>void};
const emptyTeams:string[]=[],emptyBlocked:number[]=[],emptyParticipants:{Squadra:string;Giocatore:string}[]=[];
export default function PlayNow({matches,storageKey,exportPath,version,badges,withdrawals=emptyTeams,activeRound,closed=false,blocked=emptyBlocked,participants=emptyParticipants,onOpen}:Props){
  const [exporting,setExporting]=useState(false),[exportError,setExportError]=useState('');
  const [prepared,setPrepared]=useState<{key:string;file:File}|null>(null);
  const [fallbackKey,setFallbackKey]=useState('');
  async function exportPdf(){setExporting(true);setExportError('');try{savePlayNowPdf(await preparePlayNowPdf(exportPath,version,result.eligible.map(m=>m.index)));}catch(e){setExportError(e instanceof Error?e.message:'Download non riuscito. Verifica la connessione e riprova.');}finally{setExporting(false);}}
  const players=useMemo(()=>attendees([...matches.flatMap(m=>[m.home,m.away]),...participants.map(p=>p.Squadra)].filter(team=>!withdrawals.includes(team)),Object.fromEntries(participants.map(p=>[p.Squadra,p.Giocatore]))),[matches,participants,withdrawals]);
  const [selected,setSelected]=useState<string[]>(()=>{try{const stored=JSON.parse(sessionStorage.getItem(storageKey)||'[]');return Array.isArray(stored)?stored.filter(x=>typeof x==='string'):[];}catch{return [];}});
  const [search,setSearch]=useState('');
  const [preview,setPreview]=useState<'all'|'together'>('all');
  const present=selected.filter(id=>players.some(p=>p.id===id));
  const result=useMemo(()=>suggestMatches(matches,players,present,{activeRound,closed,withdrawals,blocked}),[matches,players,selected,activeRound,closed,withdrawals,blocked]);
  const visible=players.filter(p=>`${p.name} ${p.teams.join(' ')}`.toLocaleLowerCase('it').includes(search.toLocaleLowerCase('it')));
  const games=preview==='all'?result.eligible:result.proposed;
  const exportKey=JSON.stringify([exportPath,version,result.eligible.map(m=>m.index)]);
  const shareReady=prepared?.key===exportKey;
  async function sharePdf(){
    setExportError('');
    if(shareReady){
      // A second, direct tap retains the user activation required on iOS.
      try{await navigator.share({files:[prepared.file],title:'Superba - Partite disponibili',text:'Gli incontri disponibili tra i presenti al campionato Superba.'});}
      catch(e){if(!(e instanceof DOMException&&e.name==='AbortError'))setExportError('Condivisione non riuscita. Puoi scaricare il PDF e allegarlo in WhatsApp.');}
      return;
    }
    setExporting(true);
    try{
      const file=await preparePlayNowPdf(exportPath,version,result.eligible.map(m=>m.index));
      if(typeof navigator.share==='function'&&typeof navigator.canShare==='function'&&navigator.canShare({files:[file]})){setPrepared({key:exportKey,file});setFallbackKey('');}
      else{savePlayNowPdf(file);setFallbackKey(exportKey);}
    }catch(e){setExportError(e instanceof Error?e.message:'Preparazione del PDF non riuscita. Riprova.');}
    finally{setExporting(false);}
  }
  function choose(ids:string[]){setSelected(ids);try{sessionStorage.setItem(storageKey,JSON.stringify(ids));}catch{/* Attendance still works in memory. */}}
  const roundLabel=(m:PlayableMatch)=>m.day!==undefined?`${m.group?`${m.group} · `:''}Giornata ${m.day}`:m.round_name||`Turno ${m.round}`;
  return <section className="play-now" aria-label="Gioca ora">
    <div className="results-card play-attendance"><div className="section-heading"><div><h2><Users size={21}/>Chi c’è stasera?</h2><p>Seleziona i presenti. Le proposte danno precedenza alle prime giornate, con una sola partita per giocatore.</p></div><span className="badge">{present.length} presenti</span></div>
      <div className="play-selection-tools"><label className="search"><Search size={17}/><input aria-label="Cerca tra i partecipanti" placeholder="Cerca giocatore o squadra…" value={search} onChange={e=>setSearch(e.target.value)}/></label><button type="button" className="secondary compact" onClick={()=>choose(players.map(p=>p.id))}>Tutti presenti</button><button type="button" className="text-button" disabled={!present.length} onClick={()=>choose([])}>Svuota</button></div>
      <div className="play-players">{visible.map(p=><label key={p.id} className={'play-player'+(present.includes(p.id)?' selected':'')}><input type="checkbox" checked={present.includes(p.id)} onChange={e=>choose(e.target.checked?[...present,p.id]:present.filter(id=>id!==p.id))}/><span className="team-mark"><TeamMark name={p.teams[0]} badge={badges?.[p.teams[0]]}/></span><span><strong>{p.name}</strong><small>{p.teams.join(' · ')}</small></span></label>)}</div>{!visible.length&&<p className="empty">Nessun partecipante corrisponde alla ricerca.</p>}
    </div>
    <div className="results-card play-proposals"><div className="results-heading"><h3><Zap size={18}/>{preview==='all'?'Incontri disputabili':'In campo insieme'}</h3><span role="status">{games.length} incontri {preview==='all'?'disponibili':'simultanei'}</span></div>
      <div className="play-preview-switch"><div className="segmented" role="group" aria-label="Anteprima incontri"><button type="button" className={preview==='all'?'active':''} aria-pressed={preview==='all'} onClick={()=>setPreview('all')}>Tutti gli incontri ({result.available})</button><button type="button" className={preview==='together'?'active':''} aria-pressed={preview==='together'} onClick={()=>setPreview('together')}>In campo insieme ({result.proposed.length})</button></div></div>
      <div className="play-pdf-actions"><button type="button" className="primary compact" disabled={!result.available||exporting} onClick={()=>void exportPdf()}><Download size={17}/>{exporting?'Preparazione PDF…':`Scarica PDF (${result.available})`}</button><button type="button" className="secondary compact" disabled={!result.available||exporting} onClick={()=>void sharePdf()}><MessageCircle size={17}/>{shareReady?'WhatsApp · PDF pronto':'WhatsApp'}</button><p>Il PDF include tutti gli incontri disponibili.</p></div>
      {shareReady&&<p className="results-note" role="status">PDF pronto. Premi “WhatsApp · PDF pronto”, scegli WhatsApp e poi il gruppo del campionato.</p>}
      {fallbackKey===exportKey&&<div className="play-pdf-actions" role="status"><p>PDF scaricato. Questo browser non condivide allegati: apri WhatsApp, scegli il gruppo del campionato e allega il file dai Download.</p><a className="secondary compact" href="https://web.whatsapp.com/" target="_blank" rel="noopener noreferrer">Apri WhatsApp<ArrowRight size={16}/></a></div>}
      {exportError&&<div className="alert error" role="alert">{exportError}</div>}
      <p className="results-note">{preview==='all'?'Anteprima completa, ordinata dalle prime giornate. Un giocatore può comparire in più incontri: queste partite vanno disputate in momenti diversi.':'Una proposta di partite da giocare contemporaneamente, senza impegnare lo stesso giocatore in più incontri.'}</p>
      {blocked.length>0&&<p className="results-note">Le partite con modifiche in bozza sono escluse: salva i risultati per aggiornare i suggerimenti.</p>}
      {activeRound!==undefined&&!closed&&<p className="results-note">Proposte dal turno attivo {activeRound}. Gli abbinamenti dei turni successivi saranno disponibili dopo la loro generazione.</p>}
      <div className="play-games">{games.map(m=><article className="play-game" key={m.index}><small>{roundLabel(m)}</small><div className="play-pair"><div><span className="team-mark"><TeamMark name={m.home} badge={badges?.[m.home]}/></span><strong>{m.home}</strong></div><span className="play-versus">VS</span><div><span className="team-mark"><TeamMark name={m.away} badge={badges?.[m.away]}/></span><strong>{m.away}</strong></div></div><button type="button" className="secondary compact" onClick={()=>onOpen(m)} aria-label={`Apri ${m.home} contro ${m.away}`}>Apri {m.day!==undefined?'giornata':'turno'}<ArrowRight size={16}/></button></article>)}</div>
      {!result.proposed.length&&<div className="empty"><Zap size={25}/><h3>{closed?'Torneo concluso':present.length<2?'Seleziona almeno due presenti':'Nessun incontro disponibile'}</h3><p>{closed?'Non ci sono partite da proporre.':present.length<2?'Scegli i giocatori qui sopra per comporre la serata.':'Tra i presenti non ci sono incontri ancora da validare e disponibili in questo momento.'}</p></div>}
      {games.length>0&&<p className="results-note">L’anteprima si aggiorna quando salvi i risultati o cambi le presenze.</p>}
      {preview==='together'&&present.length>=2&&!closed&&result.waiting.length>0&&<p className="play-waiting"><strong>In attesa in questa proposta:</strong> {result.waiting.map(p=>p.name).join(', ')}.</p>}
    </div>
  </section>;
}
