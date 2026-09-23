const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');

function viewer(hash = '#/') {
  const element = {style: {}, addEventListener() {}, classList: {toggle() {}, add() {}, remove() {}}};
  const context = vm.createContext({
    console, URLSearchParams, setTimeout, clearTimeout, addEventListener() {},
    document: {querySelector: () => element, querySelectorAll: () => [], addEventListener() {}},
    window: {addEventListener() {}}, location: {hash}, history: {replaceState() {}},
    localStorage: {getItem() {return null;}}, ResizeObserver: class {observe() {}},
    fetch: () => new Promise(() => {}), matchMedia: () => ({matches: false}),
  });
  vm.runInContext(fs.readFileSync('site/app.js', 'utf8'), context);
  vm.runInContext(`
    data={manifest:{categories:{test:{name:'Test'}},tasks:{T:{name:'Task',category:'test',modality:'text'}}}};
    allCases=[{id:'row',title:'Example',category:'test',task:'T',state:{text:'Example'},questions:[{id:'decision',gold:'a',options:{a:'A',b:'B'}}]}];
    caseMap=new Map(allCases.map(c=>[c.id,c]));
    registerModel({id:'test-model',label:'Test model',provider:'openai-compatible'},true);
    RUNS=[{id:'run',model_id:'test-model',metrics:{cases:1},coverage:{full:true}}];
    recordMap.set('run:row',{scores:[{correct:true,label:'a',gold:'a',confidence:.9,probabilities:{a:.9,b:.1},brier:.02,log_loss:.1}],status:'ok',duration_ms:100,cost_usd:.001,tokens:{input:10,output:5}});
    parseRoute();
  `, context);
  return expression => vm.runInContext(expression, context);
}

test('populated leaderboard and task page render latency without formatter shadowing', () => {
  const run = viewer();
  assert.match(run('home()'), /100 ms/);
  assert.match(run("taskPage('T')"), /100 ms/);
});

test('hostile URL modality cannot become HTML in populated results', () => {
  const attack = '<img src=x onerror=alert(1)>';
  const run = viewer('#/?modality=' + encodeURIComponent(attack));
  assert.equal(run("route.q.get('modality')"), null);
  assert.ok(!run('home()').includes(attack));
  // Also protect the template when a caller sets a filter without parsing a route.
  run('route.q.set("modality", ' + JSON.stringify(attack) + ')');
  assert.ok(!run('home()').includes(attack));
});

test('valid modality survives and external links reject executable schemes', () => {
  const run = viewer('#/?modality=text');
  assert.equal(run("route.q.get('modality')"), 'text');
  assert.equal(run("ext('javascript:alert(1)','source')"), 'source');
  assert.match(run("ext('https://example.com','source')"), /href="https:\/\/example.com"/);
});
