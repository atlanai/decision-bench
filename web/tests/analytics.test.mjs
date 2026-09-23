import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source = readFileSync(new URL('../../site/analytics.js', import.meta.url), 'utf8');
function setup(choice, hostname = 'decisionbench.ai', blocked = false) {
  const listeners = {}, scripts = [], stored = new Map(choice ? [['decision-bench-analytics-consent', choice]] : []);
  const window = {};
  const document = {
    querySelector: () => ({content: 'G-TEST123'}),
    createElement: () => ({setAttribute() {}, remove() {}}),
    body: {appendChild() {}}, head: {appendChild(s) {scripts.push(s);}},
    addEventListener: (name, cb) => {listeners[name] = cb;},
  };
  vm.runInNewContext(source, {window, document, location: {hostname, origin: `https://${hostname}`, pathname: '/'}, localStorage: {
    getItem(k) {if (blocked) throw Error('blocked'); return stored.get(k);}, setItem(k,v) {if (blocked) throw Error('blocked'); stored.set(k,v);},
  }});
  const choose = value => listeners.click({target: {closest: selector => selector.includes('preferences') ? null : {dataset: {analyticsChoice: value}}}});
  const events = () => (window.dataLayer || []).filter(a => a[0] === 'event');
  return {window, choose, events, scripts};
}
const page = {page_type: 'tasks', page_path: '/#/tasks', page_location: 'https://decisionbench.ai/#/tasks', page_title: 'tasks · Decision Bench'};
test('no analytics before consent; acceptance records the current page exactly once', () => {
  const h = setup(); h.window.dbAnalytics.page(page); h.window.dbAnalytics.event('ui_click', {control: 'sort'});
  assert.equal(h.scripts.length, 0); assert.equal(h.events().length, 0);
  h.choose('yes'); assert.equal(h.scripts.length, 1); assert.equal(h.events().length, 1);
  h.window.dbAnalytics.page({...page, search_active: true}); assert.equal(h.events().length, 1);
  h.window.dbAnalytics.event('ui_click', {control: 'sort'}); assert.equal(h.events()[1][2].search_active, true);
});
test('navigation counts once per transition, including back; revocation stops events and reconsent resumes', () => {
  const h = setup('yes'); h.window.dbAnalytics.page(page);
  h.window.dbAnalytics.page({...page, page_path: '/#/models'}); h.window.dbAnalytics.page(page);
  assert.equal(h.events().length, 3);
  h.choose('no'); assert.equal(h.window['ga-disable-G-TEST123'], true);
  h.window.dbAnalytics.event('ui_click', {}); h.window.dbAnalytics.page({...page, page_path: '/#/data'});
  assert.equal(h.events().length, 3);
  h.choose('yes'); assert.equal(h.events().length, 4); assert.equal(h.window['ga-disable-G-TEST123'], false); assert.equal(h.scripts.length, 1);
});
test('storage failures and nonproduction hosts fail closed', () => {
  assert.doesNotThrow(() => setup(undefined, 'decisionbench.ai', true));
  assert.equal(setup('yes', 'localhost').window.dbAnalytics, undefined);
});

// Evaluate the application adapter against a tiny public catalog, without a browser or network.
const adapter = readFileSync(new URL('../src/lib/analytics.js', import.meta.url), 'utf8').replace(/^import .*;\n/, '').replaceAll('export ', '');
function app() {
  const events = [], listeners = {};
  const B = {man: () => ({version: 'v4'}), caseMap: new Map([['public-row', {id:'public-row', task:'T-1', category:'engineering'}]]), dsOf: () => ({id:'dataset'}), taskOrder: () => ['T-1'], taskCat: () => 'engineering', MODELS: {'model-1': {}}, DATASETS: [{id:'dataset'}], categoryOrder: () => ['engineering']};
  const c = vm.createContext({B, location: {origin:'https://decisionbench.ai', href:'https://decisionbench.ai/'}, URL, URLSearchParams, window: {dbAnalytics: {page: p => events.push(['page',p]), event: (n,p) => events.push([n,p])}}, document:{addEventListener:(n,f)=>listeners[n]=f, removeEventListener(){}}});
  vm.runInContext(adapter,c);
  return {events, listeners, context:r=>c.context(r), page:r=>c.pageView(r), install:()=>c.installClicks()};
}
test('unknown route identifiers and private queries never enter metadata', () => {
  const a=app(); const r={page:'row', id:'person@example.com', q:new URLSearchParams('q=SECRET&category=SECRET&a=SECRET')};
  a.page(r); assert.equal(a.events[0][1].page_path,'/#/row'); assert(!JSON.stringify(a.events).includes('SECRET')); assert(!JSON.stringify(a.events).includes('person@'));
  a.page({...r,id:'public-row'}); assert.equal(a.events[1][1].task_id,'T-1'); assert.equal(a.events[1][1].dataset_id,'dataset');
});
test('filter changes have separate events, search tracks presence only, compare names are validated', () => {
  const a=app(), r={page:'home',id:'',q:new URLSearchParams()}; a.page(r);
  a.page({...r,q:new URLSearchParams('q=one')}); assert.equal(a.events.at(-1)[0],'filter_change');
  a.page({...r,q:new URLSearchParams('q=two')}); assert.equal(a.events.at(-1)[0],'page');
  a.page({page:'compare',id:'',q:new URLSearchParams()});
  a.page({page:'compare',id:'',q:new URLSearchParams('a=model-1&b=SECRET')});
  assert.equal(a.events.at(-1)[0],'comparison_change'); assert.equal(a.events.at(-1)[1].model_a,'model-1'); assert(!JSON.stringify(a.events).includes('SECRET'));
});
test('delegated clicks strip external paths and queries and classify downloads', () => {
  const a=app(); a.install();
  const click=(href,download=false)=>{const el={href,dataset:{},matches:()=>true,closest:()=>null,hasAttribute:()=>download}; a.listeners.click({target:{closest:()=>el}});};
  click('https://example.com/private/person?token=SECRET'); assert.equal(a.events[0][0],'outbound_click'); assert.equal(a.events[0][1].link_domain,'example.com');
  click('https://decisionbench.ai/corpus.json?token=SECRET',true); assert.equal(a.events[1][0],'file_download'); assert.equal(a.events[1][1].file_name,'corpus.json');
  click('https://decisionbench.ai/#/model/model-1?q=SECRET'); assert.equal(a.events[2][0],'navigation_click');
  assert(!JSON.stringify(a.events).includes('SECRET')); assert(!JSON.stringify(a.events).includes('private'));
});
