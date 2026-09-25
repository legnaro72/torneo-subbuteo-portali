const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const ts = require('typescript');

require.extensions['.tsx'] = (module, filename) => {
  const source = fs.readFileSync(filename, 'utf8');
  const output = ts.transpileModule(source, {compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022, esModuleInterop: true,
  }}).outputText;
  module._compile(output, filename);
};

const {CustomCrest, defaultCrest} = require('../src/CustomCrest.tsx');
const {TeamMark, automaticClub} = require('../src/TeamBadges.tsx');
const render = component => renderToStaticMarkup(React.createElement(component.type, component.props));

test('editing crest configuration updates the SVG without interpreting team text as markup', () => {
  const initial = defaultCrest('Superba');
  const first = render(React.createElement(CustomCrest, {config: initial}));
  const updated = render(React.createElement(CustomCrest, {config: {...initial, primary: '#ff0000',
    shape: 'circle', icon: 'trophy', title: '<img onerror=alert(1)>'}}));
  assert.match(first, /<svg/);
  assert.match(updated, /#ff0000/);
  assert.match(updated, /&lt;IMG/);
  assert.doesNotMatch(updated, /<img onerror/);
  assert.notEqual(first, updated);
});

test('common team mark supports custom, flag, club and no-image modes', () => {
  const config = defaultCrest('Superba');
  assert.match(render(React.createElement(TeamMark, {name: 'Superba', badge: {kind: 'custom', config}})), /<svg/);
  assert.match(render(React.createElement(TeamMark, {name: 'Italia', badge: {kind: 'flag', ref: 'IT'}})), /flagcdn.com\/it.svg/);
  assert.match(render(React.createElement(TeamMark, {name: 'Genoa', badge: {kind: 'club', ref: 'File:Genoa.svg', url: 'https:\/\/example.com\/Genoa.svg'}})), /Genoa.svg/);
  assert.equal(render(React.createElement(TeamMark, {name: 'Italia', badge: {kind: 'none'}})), 'I');
});

test('recognised clubs receive an automatic crest without overriding manual choices', () => {
  assert.equal(automaticClub('Genoa CFC - Mario')?.ref, 'football-logos:logos/italy/Genoa.svg');
  assert.equal(automaticClub('Genoa CFC-Mario')?.ref, 'football-logos:logos/italy/Genoa.svg');
  assert.equal(automaticClub('AS Roma')?.ref, 'football-logos:logos/italy/Roma.svg');
  assert.equal(automaticClub('Paris Saint-Germain - Mario')?.ref,
    'football-logos:logos/france/Paris_Saint-Germain_(PSG).svg');
  assert.equal(automaticClub('Club sconosciuto'), undefined);
  assert.match(render(React.createElement(TeamMark, {name: 'Genoa CFC'})), /Genoa\.svg/);
  assert.match(render(React.createElement(TeamMark, {name: 'Italia'})), /flagcdn\.com\/it\.svg/);
  assert.match(render(React.createElement(TeamMark, {name: 'Olanda'})), /flagcdn\.com\/nl\.svg/);
  assert.match(render(React.createElement(TeamMark, {name: 'Inghilterra'})), /flagcdn\.com\/gb-eng\.svg/);
  assert.equal(render(React.createElement(TeamMark, {name: 'Genoa CFC', badge: {kind: 'none'}})), 'G');
});
