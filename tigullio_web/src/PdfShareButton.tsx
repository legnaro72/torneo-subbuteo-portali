import WhatsAppIcon from './WhatsAppIcon';
import {useState} from 'react';
import {X} from 'lucide-react';
import {pdfFileFromResponse,savePlayNowPdf} from './playNowPdf';
import './pdfShare.css';

export const whatsappGroup='Campionato Tigullio';
export default function PdfShareButton({url,filename,title,revision='',disabled=false}:{url:string;filename:string;title:string;revision?:string;disabled?:boolean}){
  const key=JSON.stringify([url,revision]);
  const [prepared,setPrepared]=useState<{key:string;file:File}|null>(null);
  const [busy,setBusy]=useState(false),[open,setOpen]=useState(false),[fallback,setFallback]=useState(''),[error,setError]=useState('');
  const ready=prepared?.key===key;
  async function share(){
    setError('');setOpen(true);
    if(ready){
      try{await navigator.share({files:[prepared.file],title,text:title});setOpen(false);}
      catch(e){if(!(e instanceof DOMException&&e.name==='AbortError'))setError('Condivisione non riuscita. Scarica il PDF con il pulsante PDF e allegalo in WhatsApp.');}
      return;
    }
    setBusy(true);
    try{
      const file=await pdfFileFromResponse(await fetch(url,{credentials:'same-origin'}),filename);
      if(typeof navigator.share==='function'&&typeof navigator.canShare==='function'&&navigator.canShare({files:[file]})){
        setPrepared({key,file});setFallback('');
      }else{savePlayNowPdf(file);setFallback(key);}
    }catch(e){setError(e instanceof Error?e.message:'Preparazione del PDF non riuscita. Riprova.');}
    finally{setBusy(false);}
  }
  return <span className="pdf-share"><button type="button" className="secondary compact whatsapp-button" disabled={disabled||busy} onClick={()=>void share()} title={`Condividi il PDF nel gruppo ${whatsappGroup}`}><WhatsAppIcon/>{busy?'Preparazione…':ready?'WhatsApp · PDF pronto':'WhatsApp'}</button>
    {open&&<span className="pdf-share-info"><button type="button" className="pdf-share-close" aria-label="Chiudi indicazioni WhatsApp" onClick={()=>setOpen(false)}><X size={16}/></button>{error?<span role="alert">{error}</span>:<span role="status">{busy?'Preparazione del PDF con i dati salvati…':ready?<>PDF pronto. Premi di nuovo <strong>WhatsApp · PDF pronto</strong>, scegli WhatsApp e il gruppo <strong>{whatsappGroup}</strong>.</>:fallback===key?<>PDF scaricato. Apri WhatsApp, cerca <strong>{whatsappGroup}</strong> e allega <strong>{filename}</strong> dai Download. <a className="whatsapp-button" href="https://web.whatsapp.com/" target="_blank" rel="noopener noreferrer"><WhatsAppIcon/>Apri WhatsApp</a></>:<>I dati sono cambiati. Premi WhatsApp per preparare il PDF aggiornato.</>}</span>}</span>}
  </span>;
}
