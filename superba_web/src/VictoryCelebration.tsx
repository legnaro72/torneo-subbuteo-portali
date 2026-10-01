import {useEffect, useRef, useState, type CSSProperties} from 'react';
import {createPortal} from 'react-dom';
import {RotateCcw, Trophy, Volume2, VolumeX, X} from 'lucide-react';
import {TeamMark, type BadgeMap} from './TeamBadges';
import {tournamentLabel} from './presentation';

export const celebrationAudioEvent='superba-celebration-audio';
type Winner={name:string;group?:string};
export default function VictoryCelebration({tournament,winners,badges}:{tournament:string;winners:Winner[];badges?:BadgeMap}) {
  const [open,setOpen]=useState(false);
  if(!winners.length)return null;
  return <><section className="champion-banner"><Trophy size={28}/><div><span className="eyebrow">{winners.length>1?'I VINCITORI DEI GIRONI':'IL VINCITORE'}</span><strong>{winners.map(w=>w.name).join(' · ')}</strong></div><button type="button" className="victory-button" onClick={()=>setOpen(true)}><Trophy size={17}/>Celebra {winners.length>1?'vincitori':'vincitore'}</button></section>{open&&<Ceremony tournament={tournament} winners={winners} badges={badges} onClose={()=>setOpen(false)}/>}</>;
}

function Ceremony({tournament,winners,badges,onClose}:{tournament:string;winners:Winner[];badges?:BadgeMap;onClose:()=>void}) {
  const dialog=useRef<HTMLDialogElement>(null), audio=useRef<HTMLAudioElement>(null);
  const [replay,setReplay]=useState(0), [sound,setSound]=useState(true), [audioError,setAudioError]=useState(false);
  useEffect(()=>{
    const previous=document.activeElement as HTMLElement|null, overflow=document.body.style.overflow;
    dialog.current?.showModal();document.body.style.overflow='hidden';
    return()=>{document.body.style.overflow=overflow;previous?.focus();};
  },[]);
  useEffect(()=>{
    window.dispatchEvent(new CustomEvent(celebrationAudioEvent,{detail:sound}));
    return()=>{window.dispatchEvent(new CustomEvent(celebrationAudioEvent,{detail:false}));};
  },[sound]);
  useEffect(()=>{
    const player=audio.current;
    let cancelled=false;
    if(sound&&player){player.currentTime=0;player.volume=.55;void player.play().catch(()=>{if(!cancelled){setAudioError(true);setSound(false);}});}
    else player?.pause();
    const stop=window.setTimeout(()=>setSound(false),12000);
    return()=>{cancelled=true;window.clearTimeout(stop);player?.pause();};
  },[sound,replay]);
  return createPortal(<dialog ref={dialog} className="ceremony" aria-labelledby="ceremony-title" onCancel={e=>{e.preventDefault();onClose();}} onClick={e=>{if(e.target===e.currentTarget)onClose();}}><div className="ceremony-stage">
    <button type="button" className="ceremony-close" aria-label="Chiudi premiazione" onClick={onClose} autoFocus><X/></button>
    <div key={replay} className="ceremony-scene">
      <div className="ceremony-confetti" aria-hidden="true">{Array.from({length:64},(_,i)=><i key={i} style={{'--x':`${(i*37)%100}%`,'--drift':`${((i*71)%260)-130}px`,'--delay':`${(i%8)*.055}s`,'--duration':`${3.1+(i%9)*.16}s`,'--spin':`${360+(i%5)*180}deg`,'--color':['var(--club-accent)','var(--club-paper)','var(--club-primary)'][i%3]} as CSSProperties}/>)}</div>
      <p className="ceremony-kicker">SUPERBA · IL MOMENTO DELLA GLORIA</p>
      <div className="ceremony-cup" aria-hidden="true"><Trophy strokeWidth={1}/></div>
      <h2 id="ceremony-title">{winners.length>1?'I campioni dei gironi':'Il campione sei tu.'}</h2>
      <p className="ceremony-tournament">{tournamentLabel(tournament)}</p>
      <div className={'ceremony-winners'+(winners.length>1?' multiple':'')}>{winners.map(w=><article key={`${w.group||''}:${w.name}`}><span className="ceremony-badge"><TeamMark name={w.name} badge={badges?.[w.name]}/></span>{w.group&&<span className="ceremony-group">{w.group}</span>}<strong>{w.name}</strong><span className="ceremony-winner-label">VINCITORE</span></article>)}</div>
      <p className="ceremony-signature">Un piccolo campo. Una grande vittoria.</p>
    </div>
    <div className="ceremony-controls"><button type="button" onClick={()=>{setReplay(n=>n+1);setAudioError(false);setSound(true);}}><RotateCcw size={17}/>Ripeti</button><button type="button" aria-pressed={sound} onClick={()=>{setAudioError(false);setSound(v=>!v);}}>{sound?<Volume2 size={17}/>:<VolumeX size={17}/>}Audio {sound?'attivo':'spento'}</button><button type="button" onClick={onClose}>Torna al torneo</button></div>
    {audioError&&<p role="status" className="ceremony-audio-note">Audio non disponibile. La premiazione continua senza musica.</p>}
    <audio ref={audio} src="/wearethechamp.mp3" preload="none"/>
  </div></dialog>,document.body);
}
