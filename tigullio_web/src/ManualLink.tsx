import {BookOpen} from 'lucide-react';

export default function ManualLink({onDownload}:{onDownload:()=>void}){
  // Avoid handing an inline PDF to the embedded viewer of an installed Android app.
  const download=/Android/i.test(navigator.userAgent)&&window.matchMedia('(display-mode: standalone)').matches;
  return <a className="manual-control" href={`/api/manuale-utente.pdf${download?'?download=true':''}`}
    target={download?undefined:'_blank'} rel="noopener noreferrer"
    download={download?'Manuale_utente_Tigullio.pdf':undefined}
    onClick={()=>{if(download)onDownload();}}
    title={download?'Scarica il manuale e aprilo dal lettore PDF del telefono':'Manuale utente Tigullio'}
    aria-label="Manuale utente Tigullio"><BookOpen size={17}/><span>Manuale</span></a>;
}
