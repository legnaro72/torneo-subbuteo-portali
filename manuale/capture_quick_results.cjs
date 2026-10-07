// Real Superba UI at smartphone width, with isolated example data and mocked APIs.
const {chromium}=require('playwright');
const path=require('node:path');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const out=path.join(__dirname,'risorse');
const teams=['Belgio - Ruben Paz','Croazia - Bomber69','Grecia - Pedino','Malta - Futzal'];
const match=(index,home,away,day,valid=false)=>({index,home:teams[home],away:teams[away],day,group:'Girone 1',valid,home_goals:valid?1:0,away_goals:valid?4:0});
const league={id:'one',name:'Serata al club',version:'v1',matches:[match(0,0,1,1),match(1,2,3,1),match(2,1,0,2,true),match(3,3,2,2)],standings:[],withdrawals:[],complete:false,closed:false,archived:false};
const option=(i,confidence=1,reversed=false)=>{const m=league.matches[i];return {match_id:String(i),matchday_number:m.day,group:m.group,participant1:m.home,participant2:m.away,existing_score1:m.home_goals,existing_score2:m.away_goals,has_result:m.valid,confidence,reversed};};
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true,serviceWorkers:'block'});
  page.setDefaultTimeout(15000);
  await page.route('https://flagcdn.com/*.svg',route=>route.fulfill({contentType:'image/svg+xml',body:fs.readFileSync(path.join(out,'flag-'+path.basename(new URL(route.request().url()).pathname)))}));
  await page.route('**/api/**',route=>{
   const p=new URL(route.request().url()).pathname;
   if(p.endsWith('/rapid-results/analyze'))return route.fulfill({json:{source:'text',original_text:route.request().postDataJSON().raw_text,results:[{raw_segment:'Ruben - Bomber 1-4',spoken_matchday:null,participant1_text:'Ruben',participant2_text:'Bomber',score1:1,score2:4,selected_match:option(0,.85),confidence:.85,alternatives:[option(0,.85),option(2,.74,true)],status:'ambiguous'}]}});
   if(p.endsWith('/rapid-results')){Object.assign(league.matches[0],{home_goals:1,away_goals:4,valid:true});league.version='v2';return route.fulfill({json:league});}
   return route.fulfill({json:p==='/api/config'?{demo:true,writes_enabled:true}:p==='/api/auth/me'?{id:'tester',username:'Andrea',role:'A',password_verified:true}:p==='/api/tournaments'?[{id:'one',name:league.name,matches:4,played:1,groups:1}]:p==='/api/tournaments/one'?league:[]});
  });
  await page.goto('http://127.0.0.1:5179/torneo/italiana/Serata%20al%20club');
  await page.getByRole('button',{name:'Inserimento rapido',exact:true}).waitFor();
  // Hide only the fixed navigation in detail crops, so it cannot cover controls.
  await page.addStyleTag({content:'nav[aria-label="Navigazione principale"]{visibility:hidden!important}'});
  await page.locator('.tournament-toolbar').screenshot({path:path.join(out,'comandi-aggiornati.png')});
  await page.getByRole('button',{name:'Impostazioni',exact:true}).click();
  await page.getByRole('button',{name:'Premium',exact:true}).click();
  await page.getByRole('button',{name:'Tutte le partite',exact:true}).click();
  await page.locator('.match-settings').screenshot({path:path.join(out,'impostazioni-aggiornate.png')});
  await page.getByRole('button',{name:'Per giornata',exact:true}).click();
  await page.getByRole('button',{name:'Impostazioni',exact:true}).click();
  await page.locator('.tournament-results').screenshot({path:path.join(out,'risultati-aggiornati.png')});
  await page.screenshot({path:path.join(out,'risultati-schermo.png')});
  await page.getByRole('button',{name:'Inserimento rapido',exact:true}).click();
  await page.getByRole('textbox',{name:'Testo originale'}).fill('Ruben - Bomber 1-4');
  await page.locator('.quick-results').screenshot({path:path.join(out,'rapido-testo.png')});
  await page.getByRole('button',{name:'Analizza risultati',exact:true}).click();
  await page.getByRole('button',{name:'Conferma associazione',exact:true}).waitFor();
  // Confirm every element fits the mobile dialog, rather than merely hiding overflow.
  assert(await page.locator('.quick-results').evaluate(el=>el.scrollWidth<=el.clientWidth+1));
  await page.locator('.quick-row').first().screenshot({path:path.join(out,'rapido-verifica.png')});
  await page.locator('.quick-match-picker summary').click();
  await page.locator('.quick-match-picker').screenshot({path:path.join(out,'rapido-selettore.png')});
  await page.locator('.quick-match-picker summary').click();
  await page.locator('.quick-alternatives:not(.quick-match-picker) summary').click();
  await page.locator('.quick-alternatives:not(.quick-match-picker)').screenshot({path:path.join(out,'rapido-proposte.png')});
  await page.locator('.quick-alternatives:not(.quick-match-picker) summary').click();
  await page.getByRole('button',{name:'Conferma associazione',exact:true}).click();
  assert(await page.getByRole('button',{name:'Conferma e salva risultati',exact:true}).isEnabled());
  await page.locator('.quick-results').screenshot({path:path.join(out,'rapido-salva.png')});
  const reviewBox=await page.locator('.quick-review').boundingBox();
  const actionsBox=await page.locator('.quick-results .modal-actions').boundingBox();
  await page.screenshot({path:path.join(out,'rapido-conferma.png'),clip:{x:reviewBox.x,y:reviewBox.y,width:reviewBox.width,height:actionsBox.y+actionsBox.height-reviewBox.y}});
  await page.getByRole('button',{name:'Conferma e salva risultati',exact:true}).click();
  await page.getByText('Risultati inseriti e salvati.',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Informazioni applicazione',exact:true}).click();
  await page.locator('.app-info-modal').screenshot({path:path.join(out,'info-aggiornate.png')});
  console.log('Captured smartphone screenshots; analyze, confirm and save flow checked with mocked data.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
