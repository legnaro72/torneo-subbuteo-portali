const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(module,filename)=>module._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,filename);
const {studioPages}=require('../src/Studio.tsx');
const {seasonOf}=require('../src/SeasonHonours.tsx');

test('Regia keeps separate groups on the same day and preserves saved scores',()=>{
 const match=(index,group,day)=>({index,group,day,home:'A',away:'B',home_goals:3,away_goals:1,valid:true});
 const matches=[match(0,'Girone A',1),match(1,'Girone B',1),match(2,'Girone A',1),match(3,'Girone A',2)];
 const pages=studioPages(matches);
 assert.deepEqual(pages.map(p=>p.key),['Girone A:1','Girone B:1','Girone A:2']);
 assert.deepEqual(pages[0].matches.map(m=>m.index),[0,2]);
 assert.equal(pages[0].matches[0].home_goals,3);
 assert.equal(matches.length,4);
});
test('Regia supports final names and Swiss rounds without invented days',()=>{
 const pages=studioPages([{index:0,round:1,round_name:'Semifinale'},{index:1,round:2},{index:2,round:1,round_name:'Semifinale'}]);
 assert.deepEqual(pages.map(p=>p.label),['Semifinale','Turno 2']);
 assert.equal(pages[0].matches.length,2);
 assert.deepEqual(studioPages([]),[]);
});
test('honours use the recorded season and never infer one from unrelated years',()=>{
 assert.equal(seasonOf('finito_CampionatoPierCrew_24_25'),'2024/25');
 assert.equal(seasonOf('Coppa · 2026/27'),'2026/27');
 assert.equal(seasonOf('Coppa 2026'),'Stagione non indicata');
});
