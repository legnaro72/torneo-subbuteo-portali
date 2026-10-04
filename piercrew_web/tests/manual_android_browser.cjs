// Browser routing regression test; system navigation flicker needs a physical phone.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 try{
  for(const [android,standalone] of [[true,true],[true,false],[false,true]]){
   const page=await browser.newPage({serviceWorkers:'block',userAgent:android?'Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36':undefined});
   await page.addInitScript(standalone=>{
    const original=window.matchMedia.bind(window);
    window.matchMedia=query=>query==='(display-mode: standalone)'?{...original(query),matches:standalone}:original(query);
   },standalone);
   await page.route('**/api/**',route=>{
    const url=new URL(route.request().url());
    if(url.pathname.endsWith('/manuale-utente.pdf'))return route.fulfill({contentType:'application/pdf',headers:{'Content-Disposition':'attachment; filename="Manuale_utente_PierCrew.pdf"'},body:'%PDF-1.4\n% test'});
    return route.fulfill({json:url.pathname==='/api/auth/me'?{id:'test',username:'Test',role:'A',password_verified:true}:url.pathname==='/api/config'?{demo:true,writes_enabled:true}:[]});
   });
   await page.goto('http://127.0.0.1:5179/');
   const manual=page.getByRole('link',{name:'Manuale utente PierCrew',exact:true});
   await manual.waitFor();
   if(android&&standalone){
    assert.equal(await manual.getAttribute('href'),'/api/manuale-utente.pdf?download=true');
    assert.equal(await manual.getAttribute('target'),null);
    const download=page.waitForEvent('download');await manual.click();
    assert.equal((await download).suggestedFilename(),'Manuale_utente_PierCrew.pdf');
    assert.equal(page.context().pages().length,1);
    await page.getByText(/Manuale richiesto in download/).waitFor();
   }else{
    assert.equal(await manual.getAttribute('href'),'/api/manuale-utente.pdf');
    assert.equal(await manual.getAttribute('target'),'_blank');
    assert.equal(await manual.getAttribute('download'),null);
   }
   await page.close();
  }
  console.log('Manual: Android installed download; browser/desktop inline unchanged OK');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
