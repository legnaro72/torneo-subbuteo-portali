const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const ts = require('typescript');

require.extensions['.ts'] = (module, filename) => {
  const source = fs.readFileSync(filename, 'utf8');
  module._compile(ts.transpileModule(source, {compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
  }}).outputText, filename);
};

const {preferredViewMode} = require('../src/viewModePreference.ts');

test('Premium becomes the default once while later explicit selections persist', () => {
  let stored = '{}';
  global.localStorage = {getItem: () => stored};
  assert.equal(preferredViewMode('view'), 'premium');
  stored = JSON.stringify({viewMode: 'compact'});
  assert.equal(preferredViewMode('view'), 'premium');
  stored = JSON.stringify({viewMode: 'standard'});
  assert.equal(preferredViewMode('view'), 'standard');
  stored = JSON.stringify({viewMode: 'compact', viewModeVersion: 2});
  assert.equal(preferredViewMode('view'), 'compact');
  delete global.localStorage;
});
