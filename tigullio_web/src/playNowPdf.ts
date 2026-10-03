export async function preparePlayNowPdf(path:string,version:string,indices:number[]){
  const response=await fetch(`/api${path}/play-now.pdf`,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Tigullio-Request':'1'},body:JSON.stringify({version,indices})});
  return pdfFileFromResponse(response,'partite-disponibili-tigullio.pdf');
}
export async function pdfFileFromResponse(response:Response,filename:string){
  if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(typeof body.detail==='string'?body.detail:'Download del PDF non riuscito. Riprova.');}
  if(!response.headers.get('Content-Type')?.includes('application/pdf'))throw new Error('Il server non ha restituito un PDF valido. Riprova.');
  return new File([await response.blob()],filename,{type:'application/pdf'});
}
export function savePlayNowPdf(file:File){
  const url=URL.createObjectURL(file),link=document.createElement('a');
  link.href=url;link.download=file.name;document.body.appendChild(link);link.click();link.remove();
  window.setTimeout(()=>URL.revokeObjectURL(url),30000);
}
