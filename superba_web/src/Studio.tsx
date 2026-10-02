import {useEffect, useRef, useState, type CSSProperties} from 'react';
import {createPortal} from 'react-dom';
import {ArrowLeft, ArrowRight, ChevronDown, Maximize, RotateCcw, Tv, X} from 'lucide-react';
import {TeamMark, type BadgeMap} from './TeamBadges';
import {tournamentLabel, matchDelay} from './presentation';

type Game={index:number;home:string;away:string;home_goals:number;away_goals:number;valid:boolean;day?:number;group?:string;round?:number;round_name?:string};
export function studioPages(matches:Game[]) {
  const pages=new Map<string,{key:string;label:string;matches:Game[]}>();
  for(const m of matches){
    const key=m.day!==undefined?`${m.group||''}:${m.day}`:`round:${m.round}`;
    if(!pages.has(key))pages.set(key,{key,label:m.day!==undefined?`${m.group?`${m.group} · `:''}Giornata ${m.day}`:m.round_name||`Turno ${m.round}`,matches:[]});
    pages.get(key)!.matches.push(m);
  }
  return [...pages.values()];
}

export default function Studio({tournament,matches,badges,initialKey,dirty=false}:{tournament:string;matches:Game[];badges?:BadgeMap;initialKey?:string;dirty?:boolean}){
  const [open,setOpen]=useState(false);
  return <><button type="button" className="secondary studio-launch" disabled={!matches.length} onClick={()=>setOpen(true)}><Tv size={17}/>Modalità Regia</button>{open&&<StudioScreen {...{tournament,matches,badges,initialKey,dirty}} onClose={()=>setOpen(false)}/>}</>;
}
function StudioScreen({tournament,matches,badges,initialKey,dirty,onClose}:{tournament:string;matches:Game[];badges?:BadgeMap;initialKey?:string;dirty:boolean;onClose:()=>void}){
  const pages=studioPages(matches), dialog=useRef<HTMLDialogElement>(null);
  const [page,setPage]=useState(()=>Math.max(0,pages.findIndex(p=>p.key===initialKey))),[batch,setBatch]=useState(0),[replay,setReplay]=useState(0),[notice,setNotice]=useState('');
  const [pageSize,setPageSize]=useState(()=>Math.max(2,Math.min(6,Math.floor((window.innerHeight-360)/110))));
  useEffect(()=>{const resize=()=>{setPageSize(Math.max(2,Math.min(6,Math.floor((window.innerHeight-360)/110))));setBatch(0);};window.addEventListener('resize',resize);return()=>window.removeEventListener('resize',resize);},[]);
  const current=pages[Math.min(page,pages.length-1)], batches=Math.ceil(current.matches.length/pageSize);
  const rows=current.matches.slice(batch*pageSize,batch*pageSize+pageSize);
  useEffect(()=>{const previous=document.activeElement as HTMLElement|null,overflow=document.body.style.overflow;dialog.current?.showModal();document.body.style.overflow='hidden';return()=>{document.body.style.overflow=overflow;previous?.focus();};},[]);
  function move(delta:number){setPage(p=>Math.max(0,Math.min(pages.length-1,p+delta)));setBatch(0);}
  return createPortal(<dialog ref={dialog} className="studio" aria-labelledby="studio-title" onCancel={e=>{e.preventDefault();onClose();}} onKeyDown={e=>{if(e.target instanceof HTMLSelectElement)return;if(e.key==='ArrowRight'){e.preventDefault();move(1);}if(e.key==='ArrowLeft'){e.preventDefault();move(-1);}}}>
    <header className="studio-head"><img src="/logo-superba.jpg" alt="Logo Superba"/><div><span>SUPERBA · MATCH NIGHT</span><h2 id="studio-title">{tournamentLabel(tournament)}</h2></div><button type="button" aria-label="Chiudi Regia" onClick={onClose} autoFocus><X/></button></header>
    <div className="studio-ribbon"><strong>{current.label}</strong><span>{current.matches.filter(m=>m.valid).length} / {current.matches.length} risultati validati</span></div>
    <div className="studio-games" key={`${current.key}:${batch}:${replay}`}>{rows.map((m,i)=><article className="studio-game" key={m.index} style={{'--match-delay':`${matchDelay(i,false)}ms`} as CSSProperties}><div><TeamMark name={m.home} badge={badges?.[m.home]}/><strong>{m.home}</strong></div><div className={'studio-score'+(!m.valid?' pending':'')}><b>{m.valid?m.home_goals:'–'}</b><span>:</span><b>{m.valid?m.away_goals:'–'}</b><small>{m.valid?'VALIDATO':'DA VALIDARE'}</small></div><div><TeamMark name={m.away} badge={badges?.[m.away]}/><strong>{m.away}</strong></div></article>)}</div>
    <footer className="studio-controls"><button type="button" disabled={page===0} onClick={()=>move(-1)} aria-label="Giornata o turno precedente"><ArrowLeft/></button><label className="sr-only" htmlFor="studio-page">Giornata o turno</label><span className="studio-select"><select id="studio-page" value={page} onChange={e=>{setPage(Number(e.target.value));setBatch(0);}}>{pages.map((p,i)=><option key={p.key} value={i}>{p.label}</option>)}</select><ChevronDown size={16} aria-hidden="true"/></span><button type="button" disabled={page===pages.length-1} onClick={()=>move(1)} aria-label="Giornata o turno successivo"><ArrowRight/></button><button type="button" onClick={()=>setReplay(n=>n+1)}><RotateCcw size={17}/>Ripeti</button>{batches>1&&<button type="button" onClick={()=>setBatch(b=>(b+1)%batches)}>Incontri {batch+1}/{batches} · Avanti</button>}<button type="button" onClick={async()=>{try{if(document.fullscreenElement===dialog.current)await document.exitFullscreen();else if(dialog.current?.requestFullscreen)await dialog.current.requestFullscreen();else setNotice('La Regia occupa già tutta la finestra disponibile.');}catch{setNotice('Schermo intero non disponibile: puoi continuare nella finestra.');}}}><Maximize size={17}/>Schermo intero</button></footer>
    <p className="studio-note" role="status">{notice|| (dirty?'Sono mostrati i dati salvati. Le modifiche in bozza non vengono proiettate.':'Risultati salvati · Usa le frecce per cambiare giornata · Esc per uscire')}</p>
  </dialog>,document.body);
}
