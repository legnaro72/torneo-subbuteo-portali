const assert=require('node:assert/strict');
const fs=require('node:fs');
const test=require('node:test');
const ts=require('typescript');
require.extensions['.ts']=(module,filename)=>module._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,filename);
const {reconcileFavourite,removeFavourite}=require('../src/favourites.ts');

test('a missing tournament clears only its own favourite after a successful archive lookup',()=>{
 const saved={italiana:{id:'a',name:'Campionato'},finali:{id:'b',name:'Finale'}};
 assert.deepEqual(reconcileFavourite(saved,'italiana',[]),{finali:saved.finali});
 assert.deepEqual(saved.italiana,{id:'a',name:'Campionato'});
});

test('an existing tournament keeps its favourite and refreshes a renamed title',()=>{
 const saved={svizzero:{id:'s',name:'Vecchio nome'}};
 assert.deepEqual(reconcileFavourite(saved,'svizzero',[{id:'s',name:'Nuovo nome'}]),{svizzero:{id:'s',name:'Nuovo nome'}});
 assert.equal(reconcileFavourite(saved,'svizzero',[saved.svizzero]),saved);
});

test('manual removal works independently of the archive and a stale response cannot clear a replacement',()=>{
 const saved={italiana:{id:'new',name:'Nuovo'},finali:{id:'f',name:'Finale'}};
 assert.equal(removeFavourite(saved,'italiana','old'),saved);
 assert.deepEqual(removeFavourite(saved,'italiana'),{finali:saved.finali});
});
