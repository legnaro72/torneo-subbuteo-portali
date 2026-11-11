import {useEffect, useState} from 'react';
import {api} from './api';
import {BadgeEditor, TeamMark, type TeamBadge, type BadgeMap} from './TeamBadges';
import {tournamentLabel} from './presentation';

type Detail={id:string;name:string;version:string;participants:string[];badges:BadgeMap;return_matches:boolean|null;calendar_block:string;withdrawals:string[]};
type Player={id:string;name:string;team:string;badge?:TeamBadge};
export default function ClubTournamentEditor({tournaments,players,onDirty}:{tournaments:{id:string;name:string;editable?:boolean}[];players:Player[];onDirty:(value:boolean)=>void}){
  const [id,setId]=useState(''),[data,setData]=useState<Detail|null>(null),[original,setOriginal]=useState('');
  const [sourceId,setSourceId]=useState(''),[name,setName]=useState(''),[team,setTeam]=useState('');
  const [badge,setBadge]=useState<TeamBadge>({kind:'none'}),[badgeOpen,setBadgeOpen]=useState(false);
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[dirty,setDirty]=useState(false);
  useEffect(()=>{onDirty(dirty);return()=>onDirty(false);},[dirty,onDirty]);
  const label=team.trim()?`${team.trim()} - ${name.trim()}`:name.trim();
  function reset(){setOriginal('');setSourceId('');setName('');setTeam('');setBadge({kind:'none'});setDirty(false);}
  async function load(value:string){if(dirty&&!window.confirm('Abbandonare la sostituzione non salvata?'))return;setId(value);setData(null);reset();setError('');setNotice('');if(!value)return;setBusy(true);try{setData(await api<Detail>(`/club/tournaments/${value}/manage`));}catch(e){setError(String(e instanceof Error?e.message:e));}finally{setBusy(false);}}
  async function save(kind:'calendar'|'participant'){
    if(!data)return;
    const confirmation=kind==='calendar'?(data.return_matches?'Rimuovere tutte le partite di ritorno senza risultati? Le partite di andata restano invariate.':'Aggiungere le partite di ritorno con casa e ospite invertiti? I risultati esistenti restano invariati.'):`Sostituire ${original} con ${label} in tutte le partite, anche quelle già giocate? Il nuovo partecipante eredita risultati e punti.`;
    if(!window.confirm(confirmation))return;
    setBusy(true);setError('');setNotice('');
    try{const result=await api<Detail>(`/club/tournaments/${data.id}/${kind}`,'PATCH',{version:data.version,...(kind==='calendar'?{return_matches:!data.return_matches}:{original,name:name.trim(),team:team.trim(),badge,source_id:sourceId||null})});setData(result);if(kind==='participant')reset();setNotice(kind==='calendar'?'Formula del torneo aggiornata.':'Partecipante e stemma aggiornati in tutto il torneo.');}
    catch(e){setError(String(e instanceof Error?e.message:e));}finally{setBusy(false);}
  }
  return <section className="results-card club-section"><h2>Modifica un torneo</h2><p>Gestione dei tornei all’italiana e dei gironi ancora aperti. Le modifiche riguardano il torneo selezionato; l’anagrafica del Club resta invariata.</p>
    <label>Torneo da modificare<select value={id} disabled={busy} onChange={e=>void load(e.target.value)}><option value="">Scegli un torneo…</option>{tournaments.filter(t=>t.editable).map(t=><option key={t.id} value={t.id}>{tournamentLabel(t.name)}</option>)}</select></label>
    {error&&<div className="alert error" role="alert">{error} <button type="button" disabled={busy} onClick={()=>void load(id)}>Ricarica torneo</button></div>}{notice&&<div className="alert success" role="status">{notice}</div>}
    {data&&<><h3>Formula del calendario</h3><p>{data.return_matches===null?'Calendario non standard':data.return_matches?'Andata e ritorno':'Solo andata'}</p>{data.calendar_block&&<p>{data.calendar_block}</p>}
      <button className="secondary" disabled={busy||dirty||data.return_matches===null||!!data.calendar_block||(!data.return_matches&&!!data.withdrawals.length)} onClick={()=>void save('calendar')}>{data.return_matches?'Passa a sola andata':'Aggiungi ritorno'}</button>{!data.return_matches&&!!data.withdrawals.length&&<p>Il ritorno non può essere aggiunto in presenza di ritirati.</p>}
      <h3>Sostituisci partecipante</h3><p>Il sostituto eredita tutte le partite, i risultati e i punti del partecipante uscente.</p>
      <label>Partecipante da sostituire<select disabled={busy} value={original} onChange={e=>{if(dirty&&!window.confirm('Abbandonare la sostituzione non salvata?'))return;reset();setOriginal(e.target.value);}}><option value="">Scegli il partecipante…</option>{data.participants.map(p=><option key={p} disabled={data.withdrawals.includes(p)} value={p}>{p}{data.withdrawals.includes(p)?' (già ritirato)':''}</option>)}</select></label>
      {original&&<><label>Nuovo giocatore dall’anagrafica<select disabled={busy} value={sourceId} onChange={e=>{const p=players.find(p=>p.id===e.target.value);setSourceId(e.target.value);setName(p?.name||'');setTeam(p?.team||'');setBadge(p?.badge||{kind:'none'});setDirty(true);}}><option value="">Inserimento manuale</option>{players.map(p=><option key={p.id} value={p.id}>{p.name} · {p.team}</option>)}</select></label>
        <div className="creation-options"><label>Nome giocatore<input disabled={busy||!!sourceId} maxLength={160} value={name} onChange={e=>{setName(e.target.value);setDirty(true);}}/></label><label>Squadra<input disabled={busy} maxLength={100} value={team} onChange={e=>{setTeam(e.target.value);setDirty(true);}}/></label></div>
        <div className="club-badge-choice"><span className="team-mark"><TeamMark name={label||original} badge={badge}/></span><button className="secondary" disabled={busy||!name.trim()} onClick={()=>setBadgeOpen(true)}>Scegli stemma del sostituto</button></div>
        {label&&<p><strong>{original}</strong> → <strong>{label}</strong></p>}
        <div className="modal-actions"><button className="secondary" disabled={busy} onClick={()=>{if(!dirty||window.confirm('Annullare la sostituzione?'))reset();}}>Annulla sostituzione</button><button className="primary" disabled={busy||!name.trim()||!dirty} onClick={()=>void save('participant')}>Salva sostituzione nel torneo</button></div>
      </>}
    </>}
    {badgeOpen&&<BadgeEditor participants={[label]} badges={{[label]:badge}} busy={busy} onClose={()=>setBadgeOpen(false)} onSave={async badges=>{setBadge(badges[label]||{kind:'none'});setDirty(true);setBadgeOpen(false);}}/>}
  </section>;
}
