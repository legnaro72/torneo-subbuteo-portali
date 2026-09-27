import {useEffect, useRef, useState, type ReactNode} from 'react';
import {ArrowLeft, ArrowRight} from 'lucide-react';

/** Keep the scroll controls outside the table so they never cover its cells. */
export default function TableScroller({children}: {children:ReactNode}) {
  const viewport=useRef<HTMLDivElement>(null);
  const [position,setPosition]=useState({overflow:false,start:true,end:false,progress:0});
  useEffect(()=>{
    const element=viewport.current;
    if(!element)return;
    const update=()=>{
      const max=element.scrollWidth-element.clientWidth;
      setPosition({overflow:max>2,start:element.scrollLeft<=2,end:element.scrollLeft>=max-2,progress:max>0?element.scrollLeft/max:0});
    };
    const observer=new ResizeObserver(update);
    observer.observe(element);
    if(element.firstElementChild)observer.observe(element.firstElementChild);
    element.addEventListener('scroll',update,{passive:true});
    update();
    return()=>{observer.disconnect();element.removeEventListener('scroll',update);};
  },[]);
  function scroll(direction:number){
    const element=viewport.current;
    if(element)element.scrollBy({left:direction*Math.max(120,element.clientWidth-160),behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
  }
  return <div className="club-table-scroller">
    {position.overflow&&<div className="table-scroll-controls">
      <span>{position.end?'Ultime colonne':position.start?'Scorri per vedere tutte le colonne':'Scorri in entrambe le direzioni'}</span>
      <button type="button" aria-label="Colonne precedenti" disabled={position.start} onClick={()=>scroll(-1)}><ArrowLeft size={17}/></button>
      <button type="button" aria-label="Colonne successive" disabled={position.end} onClick={()=>scroll(1)}><ArrowRight size={17}/></button>
      <div className="table-scroll-progress" aria-hidden="true"><i style={{left:`${position.progress*75}%`}}/></div>
    </div>}
    <div ref={viewport} className="table-scroll club-table-wrap" tabIndex={0} role="region" aria-label="Giocatori del club, tabella scorrevole">{children}</div>
  </div>;
}
