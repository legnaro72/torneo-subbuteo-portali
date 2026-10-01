import {useEffect, useRef, useState} from 'react';
import {celebrationAudioEvent} from './VictoryCelebration';

const key='piercrew-background-music';

function Speaker({enabled}:{enabled:boolean}){
  return <svg aria-hidden="true" width="21" height="21" viewBox="0 0 24 24" fill="none">
    <path d="M11.5 4.5 6.8 8H4a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.8l4.7 3.5V4.5Z" fill="currentColor"/>
    {enabled?<><path d="M15 8.5a5 5 0 0 1 0 7M17.8 5.9a8.5 8.5 0 0 1 0 12.2" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></>:
      <path d="m15.5 9 5 6m0-6-5 6" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round"/>}
  </svg>;
}

export default function MusicControl({src='/TraLeDita.mp3'}:{src?:string}){
  const audio=useRef<HTMLAudioElement>(null);
  const [enabled,setEnabled]=useState(()=>{try{return localStorage.getItem(key)==='on';}catch{return false;}});
  const [suspended,setSuspended]=useState(false);
  useEffect(()=>{
    const suspend=(event:Event)=>{const active=!!(event as CustomEvent<boolean>).detail;if(active)audio.current?.pause();setSuspended(active);};
    window.addEventListener(celebrationAudioEvent,suspend);
    return()=>window.removeEventListener(celebrationAudioEvent,suspend);
  },[]);
  useEffect(()=>{
    let cancelled=false;
    if(enabled&&!suspended){void audio.current?.play().catch(()=>{if(!cancelled)setEnabled(false);});}
    else audio.current?.pause();
    try{localStorage.setItem(key,enabled?'on':'off');}catch{}
    return()=>{cancelled=true;};
  },[enabled,src,suspended]);
  return <><button className="music-control" type="button" aria-label={enabled?'Disabilita musica di sottofondo':'Abilita musica di sottofondo'} title={enabled?'Disabilita musica di sottofondo':'Abilita musica di sottofondo'} aria-pressed={enabled} onClick={()=>setEnabled(value=>!value)}><Speaker enabled={enabled}/><span>Musica {enabled?'attiva':'spenta'}</span></button><audio ref={audio} src={src} loop preload="none"/></>;
}
