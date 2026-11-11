// Actual local UI, isolated fixtures, no production requests or database writes.
const {chromium}=require('playwright');
const path=require('node:path');
const assert=require('node:assert/strict');
const out=path.join(__dirname,'risorse');
const groups=Array.from({length:4},(_,g)=>({name:`Girone ${g+1}`,teams:Array.from({length:4},(_,p)=>`Squadra ${g+1}${p+1} - Giocatore ${g+1}${p+1}`)}));
const source={id:'source',name:'completato_Torneo dimostrativo',ranking:groups.flatMap(g=>g.teams.map(team=>({team,points:6,difference:3,gf:5}))),placement_groups:groups};
const matches=groups[0].teams.flatMap((_,p)=>[0,1].map((_,i)=>({index:p*2+i,round:1,round_name:'Semifinali',placement:p+1,home:groups[i*2].teams[p],away:groups[i*2+1].teams[p],home_goals:2,away_goals:1,valid:true,winner:groups[i*2].teams[p]})));
matches.push(...groups[0].teams.map((_,p)=>({index:8+p,round:2,round_name:'Finale',placement:p+1,home:groups[0].teams[p],away:groups[2].teams[p],home_goals:0,away_goals:0,valid:false})));
const final={id:'final',name:'fasefinaleEliminazionediretta_Torneo dimostrativo - Tabelloni per posizione',version:'a'.repeat(64),matches,active_round:2,finished:false,brackets:[1,2,3,4].map(position=>({position,label:`Tabellone ${position}° classificati`})),badges:{}};
const detail={id:'league',name:'Campionato dimostrativo',version:'a'.repeat(64),participants:['Roma - Luca','Parma - Paolo','Genoa - Andrea'],badges:{},return_matches:false,calendar_block:'',withdrawals:[]};
const players=[{id:'new',name:'Marco',team:'Bologna',potential:4,role:'R',activation_state:'reader',badge:{kind:'flag',ref:'IT'},NCampionatiVinti:0,listaCampionatiVinti:[],NGironiFFVinti:0,listaGironiFFVinti:[],NFFElimDirettaVinte:0,listaFFElimDirettaVinte:[]}];
detail.groups=['Girone 1'];
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 try{
  const page=await browser.newPage({viewport:{width:720,height:1100},deviceScaleFactor:2,serviceWorkers:'block'});
  page.setDefaultTimeout(15000);
  await page.route('**/api/**',async route=>{
   const p=new URL(route.request().url()).pathname;
   const data=p==='/api/config'?{demo:true,writes_enabled:true}:p==='/api/auth/me'?{id:'admin',username:'Andrea',role:'A',password_verified:true}:p==='/api/finals/sources'?[source]:p==='/api/finals'?(route.request().method()==='POST'?{id:'final'}:[{id:'final',name:final.name,mode:'ko',placement:true,finished:false}]):p==='/api/finals/final'?final:p==='/api/club/players'?players:p==='/api/club/tournaments'?[{id:'league',scope:'italiana',name:detail.name,championship:true,editable:true}]:p.endsWith('/manage')?detail:[];
   if(p.endsWith('/calendar')){detail.return_matches=route.request().postDataJSON().return_matches;return route.fulfill({json:detail});}
   return route.fulfill({json:data});
  });
  // Avoid remote artwork requests in the illustrative fixtures.
  await page.route('https://flagcdn.com/**',route=>route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 40"><path fill="#fff" d="M0 0h60v40H0z"/><path fill="#009246" d="M0 0h20v40H0z"/><path fill="#ce2b37" d="M40 0h20v40H40z"/></svg>'}));
  await page.goto('http://127.0.0.1:5179/finali');
  await page.getByRole('button',{name:'Nuovo torneo',exact:true}).click();
  await page.locator('.competition-create select').nth(1).selectOption('placement');
  await page.addStyleTag({content:'nav[aria-label="Navigazione principale"]{visibility:hidden!important}'});
  await page.locator('.creation-options').screenshot({path:path.join(out,'novembre-formula.png')});
  await page.locator('.group-preview section').first().screenshot({path:path.join(out,'novembre-incroci.png')});
  assert(await page.getByRole('button',{name:'Genera fase finale',exact:true}).isEnabled());
  await page.getByRole('button',{name:'Genera fase finale',exact:true}).click();
  await page.getByRole('button',{name:'Tabellone',exact:true}).click();
  await page.locator('.knockout').first().screenshot({path:path.join(out,'novembre-tabellone.png')});
  await page.goto('http://127.0.0.1:5179/club');
  await page.setViewportSize({width:390,height:1300});
  await page.addStyleTag({content:'nav[aria-label="Navigazione principale"]{visibility:hidden!important}'});
  await page.getByRole('button',{name:'Archivio tornei',exact:true}).click();
  await page.getByLabel(/^Torneo da modificare/).selectOption('league');
  assert.equal(await page.getByRole('heading',{name:'Rinomina un girone',exact:true}).count(),0);
  const editor=page.locator('section').filter({has:page.getByRole('heading',{name:'Modifica un torneo',exact:true})});
  await editor.screenshot({path:path.join(out,'novembre-calendario.png')});
  page.on('dialog',dialog=>dialog.accept());
  await page.getByRole('button',{name:'Aggiungi ritorno',exact:true}).click();
  await page.getByText('Formula del torneo aggiornata.',{exact:true}).waitFor();
  await editor.screenshot({path:path.join(out,'novembre-ritorno.png')});
  await page.getByLabel(/^Partecipante da sostituire/).selectOption('Roma - Luca');
  await page.getByLabel(/^Nuovo giocatore dall’anagrafica/).selectOption('new');
  await editor.screenshot({path:path.join(out,'novembre-sostituzione.png')});
  const formStart=await page.getByRole('heading',{name:'Sostituisci partecipante',exact:true}).boundingBox();
  const box=await editor.boundingBox();
  // Retain the original pixels below the substitution heading as a labelled detail.
  const crest=await page.locator('.club-badge-choice').boundingBox();
  require('node:fs').writeFileSync(path.join(out,'novembre-crop.json'),JSON.stringify({top:Math.round((formStart.y-box.y)*2),confirmation:Math.round((crest.y-box.y)*2)}));
  assert(await page.getByRole('button',{name:'Salva sostituzione nel torneo',exact:true}).isEnabled());
  await page.getByRole('button',{name:'Annulla sostituzione',exact:true}).click();
  detail.groups=['Girone 1','Girone 2'];
  await page.reload();
  await page.addStyleTag({content:'nav[aria-label="Navigazione principale"]{visibility:hidden!important}'});
  await page.getByRole('button',{name:'Archivio tornei',exact:true}).click();
  await page.getByLabel(/^Torneo da modificare/).selectOption('league');
  await page.getByLabel(/^Girone da rinominare/).selectOption('Girone 1');
  await page.getByLabel('Nuovo nome del girone',{exact:true}).fill('Girone Oro');
  await page.locator('.group-rename').screenshot({path:path.join(out,'novembre-girone.png')});
  assert(await page.getByRole('button',{name:'Salva nome girone',exact:true}).isEnabled());
  console.log('Captured six actual UI examples; finals creation and calendar conversion checked with isolated fixtures.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
