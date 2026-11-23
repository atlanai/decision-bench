import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
globalThis.document = {querySelector: () => null};
const B = await import('../src/lib/bench.js');
B.init(JSON.parse(readFileSync(new URL('../../site/data.json', import.meta.url), 'utf8')), {});

test('the picked models come from ?m=, in order, without repeats or unknown ids, at most four', () => {
  const ids = ['a', 'b', 'c', 'd', 'e'];
  assert.deepEqual(B.pickKeys(new URLSearchParams('m=c,a,c,zz,b,d,e'), ids), ['c', 'a', 'b', 'd']);
});

test('an old Compare link with ?a= and ?b= opens the same two models', () => {
  assert.deepEqual(B.pickKeys(new URLSearchParams('a=d&b=b'), ['a', 'b', 'c', 'd']), ['d', 'b']);
});

test('with no usable pick the page opens on the top two models', () => {
  assert.deepEqual(B.pickKeys(new URLSearchParams(''), ['a', 'b', 'c']), ['a', 'b']);
  assert.deepEqual(B.pickKeys(new URLSearchParams('m=zz'), ['a', 'b', 'c']), ['a', 'b']);
  assert.deepEqual(B.pickKeys(new URLSearchParams('m=c'), ['a', 'b', 'c']), ['c', 'a']);
});

test('a split row is one where the models disagree, and it matches the pair verdict', () => {
  const [a, b] = B.RUNS, rows = B.splits([a, b], B.allCases), g = B.pairGap(B.RUNS, B.allCases, a.id, b.id);
  const split = rows.filter(r => r.kind === 'split');
  assert.equal(rows.length, g.rows);
  assert.equal(split.filter(r => r.oks[0]).length, g.wins);
  assert.equal(split.filter(r => r.oks[1]).length, g.losses);
  for (const r of rows) assert.equal(r.kind, r.oks.every(Boolean) ? 'right' : r.oks.some(Boolean) ? 'split' : 'wrong');
});

test('a row that any picked model was not scored on is left out', () => {
  const [a, b] = B.RUNS, scored = B.allCases.filter(c => B.result(a.id, c.id) && B.result(b.id, c.id));
  assert.deepEqual(B.splits([a, b], B.allCases).map(r => r.c.id), scored.map(c => c.id));
});
