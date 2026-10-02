const assert=require('node:assert/strict');
const fs=require('node:fs');
const test=require('node:test');
const ts=require('typescript');
require.extensions['.ts']=(module,filename)=>module._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,filename);
const {tournamentLabel,bracketLinks,matchWinner,matchDelay}=require('../src/presentation.ts');

test('legacy names become display labels without conflating copies or arbitrary names',()=>{
 assert.equal(tournamentLabel('CampionatoPierCrew_26_27'),'Campionato PierCrew · 2026/27');
 assert.equal(tournamentLabel('CampionatoPierCrew_26_27_backup'),'Campionato PierCrew · 2026/27 backup');
 assert.equal(tournamentLabel('finito_fasefinaleEliminazionediretta_CampionatoPierCrew_26_27'),'Finali · Campionato PierCrew · 2026/27');
 assert.equal(tournamentLabel('Coppa 2026 · Genova'),'Coppa 2026 · Genova');
});

test('bracket connections follow actual reseeding rather than card adjacency',()=>{
 const row=(index,round,home,away,valid=true)=>({index,round,home,away,home_goals:2,away_goals:0,valid});
 const matches=[row(0,1,'A','H'),row(1,1,'B','G'),row(2,1,'C','F'),row(3,1,'D','E'),row(4,2,'A','D'),row(5,2,'B','C'),row(6,3,'A','B',false)];
 assert.deepEqual(bracketLinks(matches),[{from:0,to:4,team:'A'},{from:1,to:5,team:'B'},{from:2,to:5,team:'C'},{from:3,to:4,team:'D'},{from:4,to:6,team:'A'},{from:5,to:6,team:'B'}]);
 assert.equal(matchWinner({...matches[0],valid:false}),undefined);
 assert.equal(matchWinner({...matches[0],home_goals:1,away_goals:1}),undefined);
 assert.deepEqual(bracketLinks(matches.slice(0,4)),[]);
});

test('day reveal stays bounded and filtered archives never queue a long sequence',()=>{
 assert.equal(matchDelay(1,false),310);
 assert.equal(matchDelay(500,false),2170);
 assert.equal(matchDelay(500,true),0);
});
