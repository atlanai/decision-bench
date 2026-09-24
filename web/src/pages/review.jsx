import {track} from '@/lib/analytics';
/* Review mode (maintainers): step through rows, mark each, keep a note, export. Stored in this browser only. */
import {useEffect, useRef, useState} from 'react';
import {ArrowLeftIcon, ArrowRightIcon, CheckIcon, DownloadIcon, FlagIcon, Undo2Icon, UploadIcon} from 'lucide-react';
import * as B from '@/lib/bench';
import {num, plural} from '@/lib/format';
import {href, navHint} from '@/lib/route';
import {cn} from '@/lib/utils';
import {PageHeader} from '@/components/common';
import {RowView} from '@/pages/row';
import {Swipe} from '@/components/swipe';
import {toast} from '@/components/toast';
import {haptic, usePhone} from '@/lib/device';
import {Button} from '@/components/ui/button';
import {Textarea} from '@/components/ui/input';
import {SegmentedControl, SegmentedList, SegmentedOption} from '@/components/ui/segmented-control';

const KEY = sha => `db-review:${sha}`;
const mem = {};
function store() { const sha = B.data.corpus_sha256; if (!mem[sha]) { let v = {}; try { v = JSON.parse(localStorage.getItem(KEY(sha)) || '{}') || {}; } catch { v = {}; } mem[sha] = v; } return mem[sha]; }
function save() { try { localStorage.setItem(KEY(B.data.corpus_sha256), JSON.stringify(store())); } catch {} }
const reviewOf = c => store()[c.id] || null;
function setReview(c, patch) { const st = store(), cur = st[c.id] || {}; st[c.id] = {...cur, ...patch, at: new Date().toISOString()}; if (!st[c.id].status && !st[c.id].note) delete st[c.id]; save(); }

function exportReviews() {
  const out = []; for (const c of B.rowsInOrder()) { const r = reviewOf(c); if (r) out.push({id: c.id, task: c.task, title: B.caseTitle(c), status: r.status === 'ok' ? 'looks_right' : r.status === 'flag' ? 'flagged' : 'note_only', note: r.note || '', reviewed_at: r.at}); }
  const doc = {kind: 'decision-bench-review', exported_at: new Date().toISOString(), corpus: {version: B.man().version, sha256: B.data.corpus_sha256}, count: out.length, reviews: out};
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(doc, null, 2)], {type: 'application/json'})); a.download = `decision-bench-review-${B.man().version || 'v'}-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
}
function importReviews(text) {
  let doc; try { doc = JSON.parse(text); } catch { return 'That file is not valid JSON.'; }
  const items = Array.isArray(doc) ? doc : Array.isArray(doc?.reviews) ? doc.reviews : null; if (!items) return 'No reviews found in that file.';
  let n = 0, skip = 0; const st = store();
  for (const it of items) { const c = B.caseMap.get(it?.id); if (!c) { skip++; continue; } st[c.id] = {status: it.status === 'looks_right' || it.status === 'ok' ? 'ok' : it.status === 'flagged' || it.status === 'flag' ? 'flag' : undefined, note: it.note || '', at: it.reviewed_at || new Date().toISOString()}; if (!st[c.id].status) delete st[c.id].status; n++; }
  save(); return `Imported ${plural(n, 'review')}${skip ? `; skipped ${num(skip)} for rows not in this version` : ''}.`;
}
/* The phone review buttons: round, like a dating app's, the two verdicts bigger than the steps either side. */
const Round = ({big, on, label, className, children, ...p}) => <button type="button" aria-label={label} title={label} className={cn('grid shrink-0 cursor-pointer place-items-center rounded-full border bg-background shadow-[0_6px_20px_-8px_rgb(0_0_0/.3)] transition-transform duration-150 active:scale-90', big ? 'size-16' : 'size-12 text-muted-foreground', on && 'ring-2 ring-current ring-offset-2 ring-offset-background', className)} {...p}>{children}</button>;
const Kbd = ({children}) => <kbd className="ml-1 rounded border bg-muted px-1 font-mono text-[10px] text-muted-foreground">{children}</kbd>;

export function Review({id}) {
  const [filter, setFilter] = useState('all'), [msg, setMsg] = useState(''), [, bump] = useState(0), noteRef = useRef(null), fileRef = useRef(null);
  const all = B.rowsInOrder(), phone = usePhone();
  const list = all.filter(c => { const r = reviewOf(c); return filter === 'todo' ? !r?.status : filter === 'flagged' ? r?.status === 'flag' : true; });
  const c = B.caseMap.get(id) || list[0];
  const [note, setNote] = useState(c ? reviewOf(c)?.note || '' : '');
  useEffect(() => { setNote(c ? reviewOf(c)?.note || '' : ''); }, [c?.id]);
  const step = dir => { if (!c) return false; let i = list.indexOf(c), n; if (i < 0) { const j = all.indexOf(c); n = dir > 0 ? all.slice(j + 1).find(x => list.includes(x)) : all.slice(0, j).reverse().find(x => list.includes(x)); } else n = list[i + dir]; if (n) { navHint(dir > 0 ? 'next' : 'prev', true); location.hash = href(`review/${encodeURIComponent(n.id)}`); } return !!n; };
  /* Returns whether it moved to another row. */
  const act = a => {
    if (!c) return false; track('review_action', {action: a}); setReview(c, {note});
    if (a === 'prev') return step(-1);
    if (a === 'next') return step(1);
    if (a === 'ok') { setReview(c, {status: 'ok'}); setMsg(''); const moved = step(1); if (!moved) { bump(x => x + 1); toast('That was the last row here. Nicely done.'); } return moved; }
    if (a === 'flag') { setReview(c, {status: 'flag'}); bump(x => x + 1); setTimeout(() => noteRef.current?.focus(), 0); }
    return false;
  };
  const actRef = useRef(act); actRef.current = act;
  useEffect(() => {
    const on = e => { if (e.metaKey || e.ctrlKey || e.altKey) return; if (['TEXTAREA', 'INPUT', 'SELECT'].includes(e.target.tagName)) { if (e.key === 'Escape') e.target.blur(); return; } const a = {j: 'next', k: 'prev', y: 'ok', f: 'flag'}[e.key.toLowerCase()]; if (a) { e.preventDefault(); actRef.current(a); } };
    addEventListener('keydown', on); return () => removeEventListener('keydown', on);
  }, []);
  const t = useRef();
  const onNote = e => { const v = e.target.value; setNote(v); clearTimeout(t.current); t.current = setTimeout(() => c && setReview(c, {note: v}), 250); };
  const done = all.filter(x => reviewOf(x)?.status).length, flagged = all.filter(x => reviewOf(x)?.status === 'flag').length, r = c && reviewOf(c);
  return <>
    <div className="sticky top-[calc(env(safe-area-inset-top)+48px)] z-30 -mx-4 -mt-5 mb-6 border-b bg-background/90 px-4 py-3 backdrop-blur-md md:-mx-8 md:-mt-8 md:mb-8 md:px-8 lg:top-14 lg:-mt-10">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <div className="flex min-w-60 flex-1 items-center gap-3">
          <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-muted" role="progressbar" aria-label="Rows reviewed" aria-valuemin={0} aria-valuemax={all.length} aria-valuenow={done}>
            <i className="absolute inset-y-0 left-0 bg-good" style={{width: `${all.length ? done / all.length * 100 : 0}%`}} /><i className="absolute inset-y-0 left-0 bg-warn" style={{width: `${all.length ? flagged / all.length * 100 : 0}%`}} />
          </div>
          <span className="text-[13px] whitespace-nowrap text-muted-foreground tabular-nums">{num(done)} / {num(all.length)} reviewed · {num(flagged)} flagged</span>
        </div>
        <SegmentedControl aria-label="Review filter" value={filter} onValueChange={v => { track('review_filter', {filter: v}); setFilter(v); setMsg(''); }}><SegmentedList><SegmentedOption value="all">All<span className="max-md:hidden"> rows</span></SegmentedOption><SegmentedOption value="todo"><span className="md:hidden">To review</span><span className="max-md:hidden">Not reviewed</span></SegmentedOption><SegmentedOption value="flagged">Flagged</SegmentedOption></SegmentedList></SegmentedControl>
        <div className="flex gap-2 max-md:ml-auto">
          <Button variant="outline" size="sm" className="max-md:size-9 max-md:px-0" data-track="review_export" onClick={exportReviews} aria-label="Export reviews"><DownloadIcon /><span className="max-md:hidden">Export</span></Button>
          <Button variant="outline" size="sm" className="max-md:size-9 max-md:px-0" data-track="review_import" onClick={() => fileRef.current?.click()} aria-label="Import reviews"><UploadIcon /><span className="max-md:hidden">Import</span></Button>
          <input ref={fileRef} type="file" accept="application/json,.json" hidden onChange={e => { const f = e.target.files?.[0]; if (f) f.text().then(x => { setMsg(importReviews(x)); bump(n => n + 1); }); e.target.value = ''; }} />
        </div>
      </div>
      {msg && <p role="status" className="mt-2 text-[13px] text-good">{msg}</p>}
    </div>
    {!c ? <><PageHeader title="Review" /><p className="text-sm text-muted-foreground">{filter === 'flagged' ? 'No flagged rows. Clean slate.' : 'Every row has been reviewed. Export your notes before you go.'}</p></> : <>
      {/* Touch screens: swipe right if the key looks right, left to flag it and write why. */}
      <Swipe key={c.id} hint="Swipe right if it looks right, left to flag" hintKey="review-swipe"
        right={{label: 'Looks right', tone: 'good', run: () => act('ok')}} left={{label: 'Flag', tone: 'warn', stay: true, run: () => act('flag')}}>
        <RowView c={c} review />
      </Swipe>
      <div className="sticky bottom-0 z-30 -mx-4 mt-8 border-t bg-background/90 px-4 pt-3 pb-[max(env(safe-area-inset-bottom),12px)] backdrop-blur-md md:-mx-8 md:px-8 md:pb-3">
        {phone ? <div>
          <Textarea ref={noteRef} value={note} onChange={onNote} rows={1} placeholder="Note: why is this row wrong or unclear?" aria-label="Note" className="min-h-11 rounded-xl bg-background" />
          <div className="mt-3 flex items-center justify-center gap-5">
            <Round label="Previous row" onClick={() => act('prev')}><Undo2Icon className="size-5" /></Round>
            <Round big label="Flag" className="text-warn" on={r?.status === 'flag'} onClick={() => { haptic(); act('flag'); }}><FlagIcon className="size-6" /></Round>
            <Round big label="Looks right" className="text-good" on={r?.status === 'ok'} onClick={() => { haptic(); act('ok'); }}><CheckIcon className="size-7" strokeWidth={2.6} /></Round>
            <Round label="Skip to the next row" onClick={() => act('next')}><ArrowRightIcon className="size-5" /></Round>
          </div>
          <p className={cn('mt-2 text-center text-xs', r?.status === 'ok' ? 'text-good' : r?.status === 'flag' ? 'text-warn' : 'text-muted-foreground')}>{r?.status === 'ok' ? '✓ You said it looks right' : r?.status === 'flag' ? '⚑ Flagged. Say why above' : 'Not reviewed yet'}</p>
        </div> : <div className="flex flex-wrap items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => act('prev')}><ArrowLeftIcon />Previous<Kbd>k</Kbd></Button>
          <Button size="sm" className="bg-good text-white hover:bg-good/90 dark:text-black" onClick={() => act('ok')}><CheckIcon />Looks right<Kbd>y</Kbd></Button>
          <Button variant="outline" size="sm" className="border-warn/40 text-warn hover:bg-warn-soft hover:text-warn" onClick={() => act('flag')}><FlagIcon />Flag<Kbd>f</Kbd></Button>
          <Button variant="outline" size="sm" onClick={() => act('next')}>Next<ArrowRightIcon /><Kbd>j</Kbd></Button>
          <span className={cn('text-[13px]', r?.status === 'ok' ? 'text-good' : r?.status === 'flag' ? 'text-warn' : 'text-muted-foreground')}>{r?.status === 'ok' ? '✓ Looks right' : r?.status === 'flag' ? '⚑ Flagged' : 'Not reviewed'}</span>
          <Textarea ref={noteRef} value={note} onChange={onNote} rows={1} placeholder="Note: why is this row wrong or unclear?" aria-label="Note" className="min-h-9 flex-1 basis-72 bg-background" />
        </div>}
      </div>
    </>}
  </>;
}
