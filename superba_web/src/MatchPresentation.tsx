import {useEffect, useLayoutEffect, useRef, type ReactNode} from 'react';
import {Check, Clock, Trophy} from 'lucide-react';
import {TeamMark, type BadgeMap} from './TeamBadges';
import {tournamentLabel} from './presentation';

export function TournamentHeading({name}:{name:string}) {
  const label=tournamentLabel(name), season=label.match(/ · (20\d{2}\/\d{2})/);
  return <><h1>{season?label.replace(season[0],''):label}</h1>{season&&<p className="tournament-season">Stagione {season[1]}</p>}</>;
}

export function LoadingPanel({label='Caricamento in corso…'}:{label?:string}) {
  return <div className="loading-panel" role="status"><span>{label}</span><div aria-hidden="true"><i/><i/><i/></div></div>;
}

export function DiscardDialog({onCancel,onConfirm}:{onCancel:()=>void;onConfirm:()=>void}) {
  const dialog=useRef<HTMLDialogElement>(null);
  useEffect(()=>{const previous=document.activeElement as HTMLElement|null;dialog.current?.showModal();return()=>previous?.focus();},[]);
  return <dialog ref={dialog} className="discard-dialog" aria-labelledby="discard-title" onCancel={event=>{event.preventDefault();onCancel();}}><h2 id="discard-title">Conserva le tue modifiche</h2><p>Questa azione scarterà le modifiche del club non salvate. Puoi tornare alla pagina e salvarle prima di continuare.</p><div className="modal-actions"><button type="button" className="primary" autoFocus onClick={onCancel}>Torna alle modifiche</button><button type="button" className="secondary" onClick={onConfirm}>Scarta modifiche</button></div></dialog>;
}

export function MatchScore({home,away,value,editable,busy,onChange}:{home:string;away:string;value:{home:number;away:number;valid:boolean};editable:boolean;busy:boolean;onChange:(patch:{home?:number;away?:number})=>void}) {
  if(!editable)return <div className={'score broadcast-score'+(!value.valid?' provisional':'')} aria-label={`${home} ${value.home}, ${away} ${value.away}. ${value.valid?'Risultato validato':'Risultato da validare'}`}><strong>{value.home}</strong><span>:</span><strong>{value.away}</strong></div>;
  const select=(e:{currentTarget:HTMLInputElement})=>e.currentTarget.select();
  return <div className="score"><input aria-label={`Gol casa ${home}`} type="number" min={0} max={20} value={value.home} disabled={busy} onFocus={select} onClick={select} onChange={e=>onChange({home:Number(e.target.value)})}/><span>:</span><input aria-label={`Gol ospite ${away}`} type="number" min={0} max={20} value={value.away} disabled={busy} onFocus={select} onClick={select} onChange={e=>onChange({away:Number(e.target.value)})}/></div>;
}

export function MatchStatus({valid}:{valid:boolean}) {
  return <span className={'match-status '+(valid?'confirmed':'')} title={valid?'Risultato validato':'Risultato da validare'}><span className="sr-only">{valid?'Risultato validato':'Risultato da validare'}</span>{valid?<Check size={16} aria-hidden="true"/>:<Clock size={16} aria-hidden="true"/>}</span>;
}

export function LeaderCard({name,points,played,badges}:{name:string;points:number;played:number;badges?:BadgeMap}) {
  if(!played)return null;
  return <div className="leader-card"><span className="leader-emblem"><Trophy size={22}/></span><div><span className="eyebrow">IN TESTA ALLA CLASSIFICA</span><strong>{name}</strong></div><span className="team-mark"><TeamMark name={name} badge={badges?.[name]}/></span><div className="leader-points"><strong>{points}</strong><small>punti</small></div></div>;
}

// FLIP only on an actual update while the table remains visible. No invented rank changes.
export function StandingsBody({children,revision}:{children:ReactNode;revision:string}) {
  const body=useRef<HTMLTableSectionElement>(null);
  const positions=useRef(new Map<string,number>());
  useLayoutEffect(()=>{
    const rows=Array.from(body.current?.querySelectorAll<HTMLTableRowElement>('tr[data-team]')||[]);
    const next=new Map<string,number>();
    for(const row of rows){
      const key=row.dataset.team!, top=row.offsetTop, old=positions.current.get(key);
      next.set(key,top);
      if(old!==undefined&&old!==top&&!window.matchMedia('(prefers-reduced-motion: reduce)').matches)
        row.animate([{transform:`translateY(${old-top}px)`},{transform:'translateY(0)'}],{duration:420,easing:'cubic-bezier(.2,.7,.2,1)'});
    }
    positions.current=next;
  },[revision]);
  return <tbody ref={body}>{children}</tbody>;
}
