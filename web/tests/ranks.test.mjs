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

test('a pair that shares one row is not separated', () => {
  const tasks = tasksOf(5, 30), strong = model(tasks, () => true);
  const oneRow = tasks.map((_, r) => r === 0 ? [0, 1] : null);
  assert.deepEqual(B.rankSpreads([strong, oneRow], tasks), [[1, 2], [1, 2]]);
});

B.init(JSON.parse(readFileSync(new URL('../../site/data.json', import.meta.url), 'utf8')), {});

test('a pair gets the difference on shared rows with an interval from the same bootstrap', () => {
  const text = B.textCases(), acc = r => B.subsetMetrics(r, text).accuracy;
  const [best, ...others] = B.RUNS.slice().sort((a, b) => acc(b) - acc(a)), worst = others.at(-1);
  const gap = B.pairedDifference(best, worst, text), none = B.pairedDifference(best, best, text);
  assert.ok(Math.abs(gap.difference - (acc(best) - acc(worst))) < 1e-9);
  assert.ok(gap.interval[0] > 0 && gap.interval[0] < gap.difference && gap.difference < gap.interval[1]);
  assert.deepEqual([none.difference, ...none.interval], [0, 0, 0]);
});

test('every published run is ranked on the text rows, which all of them were scored on', () => {
  const text = B.textCases(), ranks = B.ranks(B.RUNS, text);
  assert.ok(text.length > 0 && text.length < B.allCases.length);
  assert.equal(ranks.size, B.RUNS.length);
  for (const [best, worst] of ranks.values()) assert.ok(best >= 1 && best <= worst && worst <= B.RUNS.length);
});

test('on all rows only the runs scored on every row are ranked', () => {
  const ranked = B.evaluated(B.RUNS, B.allCases);
  assert.ok(ranked.length > 0 && ranked.length < B.RUNS.length);
  for (const r of B.RUNS) assert.equal(ranked.includes(r), B.subsetMetrics(r, B.allCases).cases === B.allCases.length, B.keyOf(r));
  for (const r of ranked) assert.ok(B.allCases.every(c => !B.isImageTask(c.task) || B.rawResult(r.id, c.id).images_sent > 0), B.keyOf(r));
  assert.equal(B.ranks(B.RUNS, B.allCases).size, ranked.length);
});

test('the place of a model is 1 plus the models reliably ahead, so close models share a place', () => {
  const text = B.textCases(), ranks = B.ranks(B.RUNS, text);
  const byAccuracy = B.RUNS.slice().sort((a, b) => B.subsetMetrics(b, text).accuracy - B.subsetMetrics(a, text).accuracy);
  assert.equal(ranks.get(byAccuracy[0].id)[0], 1);
  assert.equal(ranks.get(byAccuracy[1].id)[0], 1, 'the top two models are too close to separate');
  assert.ok(ranks.get(byAccuracy.at(-1).id)[0] > 1);
});

test('a range of one place shows one number', () => {
  assert.equal(B.rankText([1, 1]), '1');
  assert.equal(B.rankText([2, 5]), '2–5');
  assert.equal(B.rankText(undefined), '—');
});

test('the kind filter splits the published runs into decision models and general LLMs', () => {
  const decision = B.runsOfKind(B.RUNS, 'decision').map(B.keyOf), llm = B.runsOfKind(B.RUNS, 'llm').map(B.keyOf);
  assert.equal(decision.length + llm.length, B.RUNS.length);
  assert.ok(decision.includes('microsoft-decision-1') && decision.includes('gpt-6-luna-decisions'));
  assert.ok(llm.includes('gpt-6-luna') && llm.includes('claude-sonnet-5'));
  assert.ok(llm.includes('gpt-5.6-luna'), 'a model that left the config gets its kind from its provider');
  assert.equal(B.runsOfKind(B.RUNS, '').length, B.RUNS.length);
  const text = B.textCases(), places = [...B.ranks(B.evaluated(B.runsOfKind(B.RUNS, 'decision'), text), text).values()];
  assert.equal(places.length, decision.length);
  assert.ok(places.every(([best, worst]) => worst <= decision.length) && places.some(([best]) => best === 1));
});
