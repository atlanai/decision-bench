import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {imageInputExclusion} from '../src/lib/eligibility.js';
// Import browser metrics with a minimal document fixture; exercise real scores,
// not a duplicate implementation of the eligibility predicate.
globalThis.document = {querySelector: () => null};
const B = await import('../src/lib/bench.js');
const data = JSON.parse(readFileSync(new URL('../../site/data.json', import.meta.url), 'utf8'));
B.init(data, {});
test('image-only rows need actual image delivery; usable text tasks remain eligible', () => {
  assert.ok(imageInputExclusion({task:'DSN-1'}, {images_sent:0}));
  assert.ok(imageInputExclusion({task:'DSN-1'}, {}));
  assert.equal(imageInputExclusion({task:'DSN-1'}, {images_sent:1}), null);
  for (const task of ['FIN-3','DAT-3','DOC-1','ENG-1']) assert.equal(imageInputExclusion({task}, {images_sent:0}), null);
});
test('Jev scores exclude blind icon guesses but preserve them for audit', () => {
  const run = B.RUNS.find(r=>B.keyOf(r)==='jev-1.13');
  const m=B.subsetMetrics(run,B.allCases);
  assert.equal(m.questions,1041);assert.equal(m.correct,976);assert.equal(m.excluded,30);
  assert.equal(B.subsetMetrics(run,B.taskRows('DSN-1')).accuracy,null);
  assert.equal(B.verdict(B.subsetMetrics(run,B.taskRows('DSN-1'))).t,'Not evaluated');
  const c=B.taskRows('DSN-1')[0];assert.ok(B.rawResult(run.id,c.id));assert.equal(B.result(run.id,c.id),undefined);
  assert.equal(B.subsetMetrics(run,B.taskRows('FIN-3')).questions,30);
  assert.ok(!B.caseStats(c).dots.some(d=>d.k==='jev-1.13'));
});
test('vision-model icon scores remain intact', () => {
 const run=B.RUNS.find(r=>B.keyOf(r)==='gemini-3.5-flash');
 assert.equal(B.subsetMetrics(run,B.taskRows('DSN-1')).questions,30);
});
