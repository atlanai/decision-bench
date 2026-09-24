import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {gzipSync} from 'node:zlib';

const root = new URL('../', import.meta.url);
const read = name => readFileSync(new URL(name, root), 'utf8');
test('source entry uses compiled CSS and no browser Tailwind compiler', () => {
  const html = read('index.html');
  assert(!html.includes('@tailwindcss/browser'));
  assert(!html.includes('text/tailwindcss'));
  assert.match(html, /src\/styles\.css/);
  assert.match(html, /<noscript>/);
  assert.match(html, /rel="canonical" href="https:\/\/decisionbench.ai\/"/);
  assert.match(html, /name="description"/);
});
test('generated viewer defers record bodies and is smaller than complete data', {skip: !existsSync(new URL('../site/viewer.json', root))}, () => {
  const viewer = read('../site/viewer.json'), full = read('../site/data.json');
  assert(gzipSync(viewer).length < gzipSync(full).length * .75);
  const index = JSON.parse(viewer), source = JSON.parse(full);
  assert.equal(index.cases.length, source.cases.length);
  assert.equal(index.results.length, source.results.length);
  assert.deepEqual(index.runs, source.runs);
  const fullCases = new Map(source.cases.map(c => [c.id, c]));
  const fullResults = Map.groupBy(source.results, r => r.case_id);
  for (const c of index.cases) {
    assert(!Object.hasOwn(c, 'state'));
    assert.match(c.detail_url, /^details\/[a-f0-9]{64}\.json$/);
    assert(existsSync(new URL(`../site/${c.detail_url}`, root)));
    const detail = JSON.parse(read(`../site/${c.detail_url}`));
    assert.deepEqual(detail.case, fullCases.get(c.id));
    assert.deepEqual(detail.results, fullResults.get(c.id) || []);
    assert.equal(detail.corpus_sha256, source.corpus_sha256);
  }
});
