const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
require.extensions['.ts']=(module,filename)=>module._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,filename);
const {attendees,suggestMatches}=require('../src/matchSuggestions.ts');
const match=(index,home,away,day=1,extra={})=>({index,home,away,day,group:'Girone 1',valid:false,...extra});
function suggest(matches,options={},present){const people=attendees(matches.flatMap(m=>[m.home,m.away]));return suggestMatches(matches,people,present||people.map(p=>p.id),options);}
test('earliest pending day wins even over more simultaneous later games',()=>{
 const rows=[match(0,'A','B',1),match(1,'A','C',2),match(2,'B','D',2),match(3,'E','F',3)];
 assert.deepEqual(suggest(rows).proposed.map(m=>m.index),[0,3]);
 assert.equal(suggest(rows).waiting.length,2);
});
test('ties use the combination that gets more people playing',()=>{
 const rows=[match(0,'A','B'),match(1,'A','C'),match(2,'B','D')];
 assert.deepEqual(suggest(rows).proposed.map(m=>m.index),[1,2]);
});
test('valid scores, drafts, withdrawals, absences and byes are excluded',()=>{
 const rows=[match(0,'A','B',1,{valid:true}),match(1,'A','C'),match(2,'A','D'),match(3,'A','RIPOSA'),match(4,'C','D'),match(5,'A','E')];
 assert.equal(suggest(rows,{blocked:[1],withdrawals:['D']},['a','b','c','d']).available,0);
 assert.equal(suggest(rows,{closed:true}).available,0);
 assert.equal(suggestMatches(rows,attendees(['A','B']),[]).available,0);
});
test('one player with two team labels can only occupy one table',()=>{
 const rows=[match(0,'Genoa - Luca','Bologna - Paolo'),match(1,'Inter-Luca','Milan-Marco')];
 const people=attendees(rows.flatMap(m=>[m.home,m.away]));
 assert.equal(people.length,3);
 assert.equal(suggestMatches(rows,people,people.map(p=>p.id)).proposed.length,1);
 assert.equal(suggest([match(0,'Genoa-Luca','Inter-Luca')]).available,0);
});
test('Swiss participant data identifies names including the bye player',()=>{
 const people=attendees(['Team A','Team B','Team C'],{'Team A':'Anna','Team B':'Anna','Team C':'Carlo'});
 assert.equal(people.length,2);assert.deepEqual(people[0].teams,['Team A','Team B']);
});
test('Swiss and knockout proposals stay in the generated active round',()=>{
 const rows=[match(0,'A','B',undefined,{round:1}),match(1,'C','D',undefined,{round:2,round_name:'Semifinale'}),match(2,'E','F',undefined,{round:3})];
 assert.deepEqual(suggest(rows,{activeRound:2}).proposed.map(m=>m.index),[1]);
 assert.deepEqual(suggest(rows,{activeRound:4}).proposed,[]);
});
test('groups and reverse fixtures remain distinct; proposals never mutate results',()=>{
 const rows=[match(0,'A','B',2),match(1,'B','A',1,{group:'Girone 2'}),match(2,'C','D',1)];
 const before=JSON.stringify(rows);
 assert.deepEqual(suggest(rows).proposed.map(m=>m.index),[2,1]);
 assert.equal(JSON.stringify(rows),before);
});
test('large events preserve day priority and have no concurrent player conflicts',()=>{
 const rows=[];for(let i=0;i<64;i+=2)rows.push(match(i,`P${i}`,`P${i+1}`,1));
 for(let i=0;i<62;i+=2)rows.push(match(100+i,`P${i}`,`P${i+2}`,2));
 const result=suggest(rows).proposed;
 assert.equal(result.length,32);assert.ok(result.every(m=>m.day===1));
 assert.equal(new Set(result.flatMap(m=>[m.home,m.away])).size,64);
});
