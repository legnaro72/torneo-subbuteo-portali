// Tournament/player text is drawn as text, never interpreted as markup.
async function loadBadge(mark:Element|null|undefined):Promise<{image:HTMLImageElement;url:string}|null>{
  if(!mark)return null;
  let blob:Blob;
  try{
    if(mark instanceof SVGElement){
      blob=new Blob([new XMLSerializer().serializeToString(mark)],{type:'image/svg+xml'});
    }else if(mark instanceof HTMLImageElement){
      const src=mark.currentSrc||mark.src;
      if(!src)return null;
      let response:Response;
      if(/^https?:\/\//i.test(src)&&new URL(src).origin!==location.origin){
        // Try the existing image URL first; the authenticated image route
        // handles providers that display in <img> but deny canvas CORS.
        try{response=await fetch(src,{mode:'cors',referrerPolicy:'no-referrer'});if(!response.ok)throw new Error('Stemma non disponibile.');}
        catch{response=await fetch(`/api/badge-image?url=${encodeURIComponent(src)}`,{credentials:'same-origin'});}
      }else response=await fetch(src,{credentials:'same-origin'});
      if(!response.ok)throw new Error('Stemma non disponibile.');
      blob=await response.blob();
    }else return null;
    const url=URL.createObjectURL(blob),image=new Image();
    try{image.src=url;await image.decode();return {image,url};}
    catch(error){URL.revokeObjectURL(url);throw error;}
  }catch{return null;}
}

export async function downloadChampionCard(tournament:string,winner:string,group?:string,mark?:Element|null){
  const canvas=document.createElement('canvas');canvas.width=1200;canvas.height=1500;
  const ctx=canvas.getContext('2d');if(!ctx)throw new Error('Il browser non supporta la cartolina.');
  const theme=getComputedStyle(document.documentElement), dark=theme.getPropertyValue('--club-dark').trim()||'#164d32',accent=theme.getPropertyValue('--club-accent').trim()||'#ffda45',paper=theme.getPropertyValue('--club-paper').trim()||'#fffdf1',primary=theme.getPropertyValue('--club-primary').trim()||'#187442';
  ctx.fillStyle=dark;ctx.fillRect(0,0,1200,1500);
  const glow=ctx.createRadialGradient(600,430,0,600,430,700);glow.addColorStop(0,primary);glow.addColorStop(1,dark);ctx.fillStyle=glow;ctx.fillRect(0,0,1200,1500);
  ctx.strokeStyle=accent;ctx.lineWidth=2;ctx.strokeRect(42,42,1116,1416);
  ctx.globalAlpha=.18;for(let i=0;i<7;i++){ctx.beginPath();ctx.arc(600,470,190+i*35,0,Math.PI*2);ctx.stroke();}ctx.globalAlpha=1;
  const logo=new Image();logo.src='/logo-piercrew.jpg';
  try{await Promise.race([logo.decode(),new Promise((_,reject)=>setTimeout(()=>reject(new Error('Logo non disponibile')),3000))]);const ratio=Math.min(140/logo.width,140/logo.height);ctx.save();ctx.beginPath();ctx.arc(600,165,70,0,Math.PI*2);ctx.clip();ctx.drawImage(logo,600-logo.width*ratio/2,165-logo.height*ratio/2,logo.width*ratio,logo.height*ratio);ctx.restore();}catch{/* The branded text remains if the local logo is unavailable. */}
  ctx.textAlign='center';ctx.fillStyle=paper;ctx.font='bold 24px sans-serif';ctx.fillText('PIERCREW · SUBBUTEO',600,280);
  // Trophy silhouette, drawn natively for a sharp downloadable image.
  ctx.strokeStyle=accent;ctx.fillStyle=accent;ctx.lineWidth=14;ctx.lineJoin='round';ctx.beginPath();ctx.moveTo(505,365);ctx.lineTo(695,365);ctx.lineTo(676,478);ctx.quadraticCurveTo(600,570,524,478);ctx.closePath();ctx.fill();
  ctx.beginPath();ctx.moveTo(507,392);ctx.lineTo(457,392);ctx.quadraticCurveTo(450,493,540,493);ctx.moveTo(693,392);ctx.lineTo(743,392);ctx.quadraticCurveTo(750,493,660,493);ctx.moveTo(600,522);ctx.lineTo(600,585);ctx.moveTo(548,590);ctx.lineTo(652,590);ctx.stroke();
  const badge=await loadBadge(mark);
  let badgeDrawn=false;
  if(badge){
    try{
      const {image}=badge;
      if(image.naturalWidth&&image.naturalHeight){
        const scale=Math.min(112/image.naturalWidth,112/image.naturalHeight);
        const width=image.naturalWidth*scale,height=image.naturalHeight*scale;
        ctx.drawImage(image,600-width/2,610+(112-height)/2,width,height);
        badgeDrawn=true;
      }
    }catch{/* A broken badge must not prevent the card download. */
    }finally{URL.revokeObjectURL(badge.url);}
  }
  const textBlock=(text:string,y:number,maxSize:number,maxWidth:number,maxLines:number)=>{
    let lines:string[]=[],size=maxSize;
    for(;size>=14;size-=2){ctx.font=`bold ${size}px sans-serif`;lines=[''];for(const word of text.split(/\s+/)){const n=lines.length-1,candidate=lines[n]?`${lines[n]} ${word}`:word;if(ctx.measureText(candidate).width>maxWidth&&lines[n])lines.push(word);else lines[n]=candidate;}if(lines.length<=maxLines&&lines.every(l=>ctx.measureText(l).width<=maxWidth))break;}
    lines.slice(0,maxLines).forEach((line,i)=>ctx.fillText(line,600,y+i*size*1.25,maxWidth));
  }
  ctx.font='bold 22px sans-serif';ctx.fillText(group?'VINCITORE DEL GIRONE':'CAMPIONE',600,badgeDrawn?760:680);
  textBlock(winner,badgeDrawn?860:785,70,980,3);
  ctx.fillStyle=paper;textBlock(tournament,1080,35,980,3);
  if(group){ctx.fillStyle=accent;textBlock(group,1235,28,980,2);}
  ctx.fillStyle=paper;ctx.font='22px sans-serif';ctx.fillText('Un piccolo campo. Una grande vittoria.',600,1375);
  const blob=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(value=>value?resolve(value):reject(new Error('Impossibile creare la cartolina.')),'image/png'));
  const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=`PierCrew-campione-${winner.replace(/[^\p{L}\p{N} -]/gu,'').slice(0,65)||'vincitore'}.png`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
}
