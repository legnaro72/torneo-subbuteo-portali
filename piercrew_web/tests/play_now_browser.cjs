// Run against a local Vite server; every API request is mocked, never MongoDB.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const os=require('node:os');
const fs=require('node:fs');
const origin=process.env.PLAY_NOW_URL||'http://127.0.0.1:5179';
const teams=['Genoa - Andrea','Bologna - Marco','Parma - Paolo','Roma - Luca'];
const badges=Object.fromEntries(teams.map(t=>[t,{kind:'none'}]));
const m=(index,a,b,day)=>({index,home:teams[a],away:teams[b],home_goals:0,away_goals:0,valid:false,day,group:'Girone 1'});
const league={id:'one',name:'Prova serata',version:'v1',matches:[m(0,0,1,1),m(1,2,3,1),m(2,0,2,2),m(3,1,3,2)],standings:[],withdrawals:[],complete:false,closed:false,archived:false,badges};
const rounds={...league,active_round:2,finished:false,participants:teams.map(Squadra=>({Squadra,Giocatore:Squadra.split(' - ')[1]})),matches:league.matches.map((row,i)=>({...row,day:undefined,round:i<2?1:2,valid:i<2,round_name:i<2?'Semifinale':'Finale'}))};
(async()=>{
 if(!fs.readFileSync(path.join(__dirname,'../src/clubFeatures.ts'),'utf8').includes('playNowEnabled = true'))return;
 const browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL||undefined});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900},serviceWorkers:'block'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const exports=[];
  await page.route('**/api/**',route=>{
   const p=new URL(route.request().url()).pathname;
   if(p.endsWith('/export.pdf'))return route.fulfill({contentType:'application/pdf',body:Buffer.from('%PDF-1.4\n% mocked tournament/club report\n')});
   if(p.endsWith('/play-now.pdf')){
    exports.push(route.request().postDataJSON());
    return route.fulfill({contentType:'application/pdf',body:Buffer.from('%PDF-1.4\n% mocked download for browser UI test\n')});
   }
   if(p==='/api/tournaments/one/results'&&route.request().method()==='PATCH'){
    for(const result of route.request().postDataJSON().results){const row=league.matches.find(m=>m.index===result.index);Object.assign(row,{home_goals:result.home,away_goals:result.away,valid:result.valid});}
    league.version='v2';return route.fulfill({json:league});
   }
   const data=p==='/api/config'?{demo:true,writes_enabled:true}:p==='/api/auth/me'?{id:'tester',username:'Andrea',role:'A',password_verified:true}:
    p==='/api/tournaments'?[{id:'one',name:league.name,matches:4,played:0,groups:1}]:p==='/api/tournaments/one'?league:
    p==='/api/swiss'||p==='/api/finals'?[{id:'one',name:league.name,mode:'ko',finished:false,rounds:2}]:p==='/api/swiss/one'||p==='/api/finals/one'?rounds:[];
   return route.fulfill({json:data});
  });
  async function checkReportShare(filename){
   await page.evaluate(()=>{
    Object.defineProperty(navigator,'canShare',{configurable:true,value:()=>true});
    Object.defineProperty(navigator,'share',{configurable:true,value:async data=>{window.reportFile={name:data.files[0].name,type:data.files[0].type};}});
   });
   const share=page.locator('.pdf-share');
   await share.getByRole('button',{name:'WhatsApp',exact:true}).click();
   await share.getByRole('button',{name:'WhatsApp · PDF pronto',exact:true}).waitFor();
   assert.match(await share.innerText(),/Campionato PierCrew/);
   await share.getByRole('button',{name:'WhatsApp · PDF pronto',exact:true}).click();
   assert.deepEqual(await page.evaluate(()=>window.reportFile),{name:filename,type:'application/pdf'});
  }
  for(const kind of ['italiana','finali','svizzero']){
   await page.goto(`${origin}/torneo/${kind}/${encodeURIComponent(league.name)}`);
   await checkReportShare(kind==='italiana'?'gazzettino-piercrew.pdf':`gazzettino-${kind}-piercrew.pdf`);
   await page.getByRole('button',{name:'Gioca ora',exact:true}).click();
   await page.getByRole('button',{name:'Tutti presenti',exact:true}).click();
   await page.locator('.play-game').first().waitFor();
   assert.equal(await page.locator('.play-game').count(),kind==='italiana'?4:2,'complete preview hides available matches');
   await page.getByRole('button',{name:'In campo insieme (2)',exact:true}).click();
   const download=page.waitForEvent('download');
   await page.getByRole('button',{name:/Scarica PDF/}).click();
   assert.equal((await download).suggestedFilename(),'partite-disponibili-piercrew.pdf');
   assert.equal(exports.at(-1).indices.length,kind==='italiana'?4:2,'PDF must contain the full list even in simultaneous view');
   await page.evaluate(()=>{
    Object.defineProperty(navigator,'canShare',{configurable:true,value:()=>true});
    Object.defineProperty(navigator,'share',{configurable:true,value:async data=>{window.sharedPdf={name:data.files[0].name,size:data.files[0].size};}});
   });
   await page.locator('.play-now').getByRole('button',{name:'WhatsApp',exact:true}).click();
   await page.locator('.play-now').getByRole('button',{name:'WhatsApp · PDF pronto',exact:true}).click();
   assert.equal((await page.evaluate(()=>window.sharedPdf)).name,'partite-disponibili-piercrew.pdf');
   await page.evaluate(()=>Object.defineProperty(navigator,'share',{configurable:true,value:async()=>{throw new DOMException('Cancelled','AbortError');}}));
   await page.locator('.play-now').getByRole('button',{name:'WhatsApp · PDF pronto',exact:true}).click();
   assert.equal(await page.locator('.play-proposals [role="alert"]').count(),0,'share cancellation should not be an error');
   await page.getByRole('button',{name:'Partite',exact:true}).click();
   await page.getByRole('button',{name:'Gioca ora',exact:true}).click();
   await page.evaluate(()=>Object.defineProperty(navigator,'canShare',{configurable:true,value:()=>false}));
   const fallbackDownload=page.waitForEvent('download');
   await page.locator('.play-now').getByRole('button',{name:'WhatsApp',exact:true}).click();
   assert.equal((await fallbackDownload).suggestedFilename(),'partite-disponibili-piercrew.pdf');
   await page.locator('.play-now').getByRole('link',{name:'Apri WhatsApp'}).waitFor();
   await page.getByRole('button',{name:'In campo insieme (2)',exact:true}).click();
   assert.equal(await page.locator('.play-game').count(),2);
   assert.ok(await page.locator('.play-game .team-mark').first().isVisible(),'Premium team mark hidden');
   assert.match(await page.locator('.play-game').first().innerText(),kind==='italiana'?/Giornata 1/:/Finale/);
   if(kind==='italiana'){
    await page.screenshot({path:path.join(os.tmpdir(),'piercrew-play-now-desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(os.tmpdir(),'piercrew-play-now-mobile.png'),fullPage:true});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'mobile overflow');
   }
   await page.locator('.play-game button').first().click();
   await page.locator('.tournament-results').waitFor();
   if(kind==='italiana'){
    await page.getByRole('checkbox',{name:`Valida ${teams[0]} contro ${teams[1]}`}).check();
    await page.getByRole('button',{name:'Gioca ora',exact:true}).click();
    await page.getByRole('button',{name:'In campo insieme (1)',exact:true}).click();
    assert.equal(await page.locator('.play-game').count(),1,'draft was proposed again');
    await page.getByRole('button',{name:'Salva risultati',exact:true}).click();
    await page.locator('.savebar').waitFor({state:'hidden'});
   }
   await page.getByRole('button',{name:'Gioca ora',exact:true}).click();
   await page.getByRole('button',{name:kind==='italiana'?'In campo insieme (1)':'In campo insieme (2)',exact:true}).click();
   assert.equal(await page.locator('.play-game').count(),kind==='italiana'?1:2,'attendance or saved results not reflected');
   await page.getByRole('button',{name:'Svuota',exact:true}).click();
   assert.equal(await page.locator('.play-game').count(),0);
   await page.getByRole('heading',{name:'Seleziona almeno due presenti'}).waitFor();
   await page.getByRole('textbox',{name:'Cerca tra i partecipanti'}).fill('Andrea');
   assert.equal(await page.locator('.play-player').count(),1);
   console.log(`${kind}: attendance, proposals, navigation, reset and mobile OK`);
  }
  await page.goto(`${origin}/club`);
  await checkReportShare('club-piercrew.pdf');
  await page.reload();
  await page.evaluate(()=>Object.defineProperty(navigator,'canShare',{configurable:true,value:()=>false}));
  const clubDownload=page.waitForEvent('download');
  await page.locator('.pdf-share').getByRole('button',{name:'WhatsApp',exact:true}).click();
  assert.equal((await clubDownload).suggestedFilename(),'club-piercrew.pdf');
  assert.match(await page.locator('.pdf-share-info').innerText(),/Campionato PierCrew/);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'share popover overflows mobile');
  console.log('PDF tournaments and Club: native attachment and fallback download OK');
  assert.deepEqual(errors,[]);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
