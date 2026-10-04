// Screenshots of the real UI with isolated demonstration data; no database access.
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const out=path.join(__dirname,'risorse');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block'});
  const teams=['Genoa - Andrea','Bologna - Marco','Parma - Paolo','Roma - Luca'];
  const m=(index,a,b,day)=>({index,home:teams[a],away:teams[b],home_goals:0,away_goals:0,valid:false,day,group:'Girone 1'});
  const league={id:'one',name:'Serata al club',version:'v1',matches:[m(0,0,1,1),m(1,2,3,1),m(2,0,2,2),m(3,1,3,2)],standings:[],withdrawals:[],complete:false,closed:false,archived:false,badges:Object.fromEntries(teams.map(t=>[t,{kind:'none'}]))};
  await page.route('**/api/**',route=>{
   const p=new URL(route.request().url()).pathname;
   if(p.endsWith('.pdf'))return route.fulfill({contentType:'application/pdf',body:Buffer.from('%PDF-1.4\n% demonstration only')});
   return route.fulfill({json:p==='/api/config'?{demo:true,writes_enabled:true}:p==='/api/auth/me'?{id:'tester',username:'Andrea',role:'A',password_verified:true}:p==='/api/tournaments'?[{id:'one',name:league.name,matches:4,played:0,groups:1}]:p==='/api/tournaments/one'?league:[]});
  });
  await page.goto('http://127.0.0.1:5179/torneo/italiana/Serata%20al%20club');
  await page.getByRole('button',{name:'Gioca ora',exact:true}).click();
  await page.getByRole('button',{name:'Tutti presenti',exact:true}).click();
  // Hide fixed navigation only in these detail captures so it cannot cover a player.
  await page.addStyleTag({content:'nav[aria-label="Navigazione principale"]{visibility:hidden !important}'});
  await page.locator('.play-attendance').screenshot({path:path.join(out,'presenze.png')});
  await page.getByRole('button',{name:'In campo insieme (2)',exact:true}).click();
  await page.locator('.play-proposals').screenshot({path:path.join(out,'proposte.png')});
  await page.evaluate(()=>{
   Object.defineProperty(navigator,'canShare',{configurable:true,value:()=>true});
   Object.defineProperty(navigator,'share',{configurable:true,value:async()=>{}});
  });
  await page.locator('.play-now').getByRole('button',{name:'WhatsApp',exact:true}).click();
  await page.getByRole('button',{name:'WhatsApp · PDF pronto',exact:true}).waitFor();
  await page.locator('.play-proposals').screenshot({path:path.join(out,'whatsapp.png')});
  Object.assign(league.matches[0],{valid:true,home_goals:2,away_goals:1});
  await page.reload();
  await page.setViewportSize({width:1280,height:850});
  await page.getByRole('button',{name:'Modalità Regia',exact:true}).click();
  await page.waitForTimeout(1800);
  await page.locator('.studio').screenshot({path:path.join(out,'regia.png')});
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
