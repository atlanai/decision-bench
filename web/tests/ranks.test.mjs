import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
globalThis.document = {querySelector: () => null};
const B = await import('../src/lib/bench.js');

/* Rows as [correct, questions]; null = the row was not scored (not run, or image excluded). */
const tasksOf = (count, size) => Array.from({length: count * size}, (_, r) => `T${Math.floor(r / size)}`);
const model = (tasks, right) => tasks.map((_, r) => [right(r) ? 1 : 0, 1]);

test('identical models are not separated', () => {
  const tasks = tasksOf(5, 30), m = model(tasks, r => r % 4 !== 0);
  assert.deepEqual(B.rankSpreads([m, m, m], tasks), [[1, 3], [1, 3], [1, 3]]);
});

test('clearly different models get their own rank', () => {
  const tasks = tasksOf(5, 30);
  const spreads = B.rankSpreads([model(tasks, r => r % 30 !== 0), model(tasks, r => r % 2 === 0), model(tasks, r => r % 30 === 0)], tasks);
  assert.deepEqual(spreads, [[1, 1], [2, 2], [3, 3]]);
});

test('a consistent paired gap separates models whose Wilson intervals overlap', () => {
  const tasks = tasksOf(10, 30);
  const weak = model(tasks, r => r % 20 >= 3);
  const strong = model(tasks, r => r % 20 >= 3 || r % 20 === 1);
  const [k1, k2] = [strong, weak].map(m => m.filter(([c]) => c).length);
  const [w1, w2] = [B.wilson(k1, tasks.length), B.wilson(k2, tasks.length)];
  assert.ok(w1[0] < w2[1], 'the old non-overlap rule would give both models rank 1');
  assert.deepEqual(B.rankSpreads([strong, weak], tasks), [[1, 1], [2, 2]]);
});

test('a model with few rows shows its uncertainty instead of taking rank 1', () => {
  const tasks = tasksOf(10, 30), strong = model(tasks, r => r % 20 !== 0);
  const sparse = tasks.map((_, r) => r < 10 ? [r % 5 !== 0 ? 1 : 0, 1] : null);
  assert.deepEqual(B.rankSpreads([strong, sparse], tasks), [[1, 2], [1, 2]]);
});

test('pairs compare only the rows both models were scored on', () => {
  const tasks = tasksOf(6, 30), full = model(tasks, r => r < 150 && r % 5 !== 0);
  const skipsLastTask = full.map((v, r) => r < 150 ? v : null);
  assert.deepEqual(B.rankSpreads([full, skipsLastTask], tasks), [[1, 2], [1, 2]]);
});

test('the published leaderboard gives every full run a range', () => {
  B.init(JSON.parse(readFileSync(new URL('../../site/data.json', import.meta.url), 'utf8')), {});
  const ranks = B.ranks(B.RUNS, B.allCases);
  assert.equal(ranks.size, B.RUNS.length);
  for (const [best, worst] of ranks.values()) assert.ok(best >= 1 && best <= worst && worst <= B.RUNS.length);
});

test('a range of one place shows one number', () => {
  assert.equal(B.rankText([1, 1]), '1');
  assert.equal(B.rankText([2, 5]), '2–5');
  assert.equal(B.rankText(undefined), '—');
});

test('position is the order by accuracy, and equal accuracy shares a position', () => {
  const ms = [{questions: 10, accuracy: .9}, {questions: 10, accuracy: .8}, {questions: 10, accuracy: .9}, {questions: 0, accuracy: null}];
  assert.deepEqual(ms.map(m => B.positionOf(m, ms)), [1, 3, 1, null]);
});
