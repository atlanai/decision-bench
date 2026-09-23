/* A dedicated view per task: each record is shown as the thing it is (a diff, a trace, a receipt, a contract).
   Every view lists the fields it places; anything else in the state still renders below it (see Rest). */
import {Component, Fragment, useState} from 'react';
import {Building2Icon, CalendarIcon, DatabaseIcon, FileIcon, KeyRoundIcon, MessageSquareIcon, QuoteIcon, SearchIcon, ShieldAlertIcon, TriangleAlertIcon, UserIcon} from 'lucide-react';
import {assetUrl} from '@/lib/bench';
import {compact} from '@/lib/format';
import {cn} from '@/lib/utils';
import {Badge} from '@/components/ui/badge';
import {GitHubIcon} from '@/components/icons';
import {Record} from '@/components/record';
import {Block, Bubble, Callout, Doc, Expandable, FileHead, Fold, Markdown, Marked, Meta, Note, Redacted, Rest, Stack} from './kit';
import {Trace, parseTrace, findInjection} from './trace';

/* ---------- shared pieces ---------- */
const Figure = ({c, className}) => (c.assets || []).filter(a => String(a.mime_type || '').startsWith('image/')).map(a => (
  <figure key={a.path} className={className}>
    <a href={assetUrl(a)} target="_blank" rel="noopener" className="block overflow-hidden rounded-lg border bg-white"><img src={assetUrl(a)} alt={a.alt_text || ''} width={a.width} height={a.height} className="block h-auto max-h-[560px] w-auto max-w-full" /></a>
    <figcaption className="mt-2 text-xs text-muted-foreground">Sent as an image to vision models; text-only models receive the text rendering.</figcaption>
  </figure>
));
const SPEAKER = ['text-brand', 'text-emerald-600 dark:text-emerald-400', 'text-amber-600 dark:text-amber-400', 'text-pink-600 dark:text-pink-400', 'text-sky-600 dark:text-sky-400'];
const speakerTone = who => { const m = String(who).match(/\(([A-Z])\)/); return SPEAKER[m ? (m[1].charCodeAt(0) - 65) % SPEAKER.length : 0]; };
function Turns({turns, hot}) {
  return <ol className="divide-y rounded-lg border">{turns.map((t, i) => (
    <li key={i} className={cn('grid gap-x-4 gap-y-0.5 px-3.5 py-2 text-sm sm:grid-cols-[180px_minmax(0,1fr)]', i === hot && 'bg-warn-soft ring-1 ring-warn/40 ring-inset')}>
      <span className={cn('truncate text-[13px] font-medium', speakerTone(t.speaker))} title={t.speaker}>{t.speaker}</span>
      <span className="leading-relaxed break-words">{t.text}{i === hot && <Badge variant="warn" className="ml-2 align-middle">This utterance</Badge>}</span>
    </li>))}</ol>;
}
const Chips = ({items, mono}) => <div className="flex flex-wrap gap-1.5">{items.map(x => <Badge key={x} variant="outline" className={cn('font-normal', mono && 'font-mono')}>{x}</Badge>)}</div>;

/* ---------- Engineering ---------- */
function parseDiff(text) {
  const rows = []; let o = 0, n = 0;
  const lines = String(text).split('\n'); if (lines.at(-1) === '') lines.pop();
  for (const l of lines) {
    if (/^(---|\+\+\+) /.test(l) || /^diff --git /.test(l) || /^index [0-9a-f]/.test(l)) continue;
    const h = l.match(/^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$/);
    if (h) { o = +h[1]; n = +h[2]; rows.push({t: 'hunk', text: l}); continue; }
    if (l.startsWith('+')) rows.push({t: 'add', n: n++, text: l.slice(1)});
    else if (l.startsWith('-')) rows.push({t: 'del', o: o++, text: l.slice(1)});
    else if (l.startsWith('\\')) rows.push({t: 'meta', text: l});
    else rows.push({t: 'ctx', o: o++, n: n++, text: l.startsWith(' ') ? l.slice(1) : l});
  }
  return rows;
}
function Diff({diff, file, repo}) {
  const rows = parseDiff(diff), add = rows.filter(r => r.t === 'add').length, del = rows.filter(r => r.t === 'del').length;
  return <div className="overflow-hidden rounded-lg border">
    <FileHead file={file} repo={repo} right={<span className="font-mono text-xs"><span className="text-good">+{add}</span> <span className="text-bad">−{del}</span></span>} />
    <div className="max-h-[560px] overflow-auto"><table className="w-full border-collapse font-mono text-xs leading-5"><tbody>
      {rows.map((r, i) => r.t === 'hunk' || r.t === 'meta'
        ? <tr key={i} className="bg-brand-soft/60 text-muted-foreground"><td colSpan={4} className="px-3 py-0.5 whitespace-pre">{r.text}</td></tr>
        : <tr key={i} className={cn(r.t === 'add' && 'bg-good-soft', r.t === 'del' && 'bg-bad-soft')}>
          <td className="w-10 border-r px-2 text-right text-muted-foreground/70 select-none">{r.o ?? ''}</td>
          <td className="w-10 border-r px-2 text-right text-muted-foreground/70 select-none">{r.n ?? ''}</td>
          <td className={cn('w-5 text-center select-none', r.t === 'add' ? 'text-good' : r.t === 'del' ? 'text-bad' : 'text-transparent')}>{r.t === 'add' ? '+' : r.t === 'del' ? '−' : ' '}</td>
          <td className="pr-4 whitespace-pre">{r.text || ' '}</td>
        </tr>)}
    </tbody></table></div>
  </div>;
}
const ENG1 = ({s}) => { const [title, ...body] = String(s.issue || '').split('\n');
  return <Stack>
    <Block label="Issue"><div className="overflow-hidden rounded-lg border">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b bg-muted/40 px-4 py-2.5 text-xs text-muted-foreground"><GitHubIcon className="size-4 text-foreground" /><span className="font-medium text-foreground">{String(s.repository || '').replace(/^github\.com\//, '')}</span>{s.base_commit && <span>at <code>{String(s.base_commit).slice(0, 10)}</code></span>}</div>
      <div className="px-4 py-3.5"><h4 className="mb-2 text-base font-semibold">{title}</h4><Markdown text={body.join('\n')} /></div>
    </div></Block>
    <Block label="Candidate files" aside={`${(s.candidate_files || []).length} paths`}><ul className="divide-y rounded-lg border font-mono text-xs">{(s.candidate_files || []).map(f => <li key={f} className="flex items-center gap-2.5 px-3 py-2"><FileIcon className="size-3.5 shrink-0 text-muted-foreground" /><span className="break-all">{f}</span></li>)}</ul></Block>
  </Stack>; };
ENG1.uses = ['issue', 'candidate_files', 'base_commit', 'repository'];
const ENG2 = ({s}) => <Block label="Diff"><Diff diff={s.diff} file={s.file} repo={s.repository} /></Block>;
ENG2.uses = ['diff', 'file', 'repository'];
const ENG3 = ({s}) => <Block label="CVE record"><div className="rounded-lg border px-4 py-3.5">
  <div className="mb-2.5 flex flex-wrap items-center gap-2"><ShieldAlertIcon className="size-4 text-bad" /><span className="font-mono text-sm font-semibold">{s.cve_id}</span>{s.published && <span className="text-xs text-muted-foreground">published {s.published}</span>}</div>
  <p className="text-sm leading-relaxed">{s.description}</p></div></Block>;
ENG3.uses = ['cve_id', 'description', 'published'];
const ENG4 = ({s}) => { const lines = String(s.code || '').split('\n');
  return <Block label="Code" aside={<span className="inline-flex items-center gap-1.5"><KeyRoundIcon className="size-3.5" />flagged <code className="rounded bg-warn-soft px-1 text-warn">{s.flagged_value}</code></span>}>
    <div className="overflow-hidden rounded-lg border"><FileHead file={s.file} repo={s.repository} />
      <div className="overflow-x-auto"><table className="w-full font-mono text-xs leading-5"><tbody>{lines.map((l, i) => { const hot = l.startsWith('>');
        return <tr key={i} className={cn(hot && 'bg-warn-soft')}><td className={cn('w-8 border-r px-2 text-center select-none', hot ? 'font-bold text-warn' : 'text-muted-foreground/60')}>{hot ? '›' : ''}</td><td className="px-3 whitespace-pre"><Marked text={hot ? ' ' + l.slice(1) : l} needles={s.flagged_value} /></td></tr>; })}</tbody></table></div>
    </div>
    <p className="mt-2 text-xs text-muted-foreground">The line marked › is the one the scanner flagged.</p>
  </Block>; };
ENG4.uses = ['code', 'file', 'flagged_value', 'repository'];
const ENG5 = ({s}) => <Stack>
  <Block label="Diff"><Diff diff={s.diff} file={s.file} repo={s.repository} /></Block>
  <Block label="Candidate commit messages"><ul className="divide-y rounded-lg border">{Object.entries(s.candidate_messages || {}).map(([k, v]) => <li key={k} className="flex items-baseline gap-3 px-3 py-2 text-sm"><code className="shrink-0 text-muted-foreground">{k}</code><span>{v}</span></li>)}</ul></Block>
</Stack>;
ENG5.uses = ['diff', 'file', 'repository', 'candidate_messages'];

/* ---------- AI agents & evals ---------- */
function params(p) { const m = String(p || '').match(/required:\s*([^;]*?)\s*(?:;\s*optional:\s*(.*?))?\.?\s*$/i); if (!m) return null; const split = x => (x || '').split(',').map(t => t.trim().replace(/\.$/, '')).filter(t => t && t !== 'none'); return {req: split(m[1]), opt: split(m[2])}; }
const AGT1 = ({s}) => <Stack>
  <Block label="User request"><Bubble side="user">{s.user_request}</Bubble></Block>
  <Block label="Available tools" aside={`${(s.available_tools || []).length} tools`}><ul className="divide-y rounded-lg border">{(s.available_tools || []).map(t => { const p = params(t.parameters);
    return <li key={t.name} className="px-4 py-3">
      <div className="font-mono text-[13px] font-semibold break-all">{t.name}</div>
      {t.description && <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">{t.description}</p>}
      {p ? <div className="mt-2 flex flex-wrap gap-1.5">{p.req.map(x => <Badge key={x} variant="outline" className="font-mono font-medium">{x}</Badge>)}{p.opt.map(x => <Badge key={x} variant="secondary" className="font-mono font-normal text-muted-foreground">{x}?</Badge>)}</div>
        : t.parameters && <p className="mt-2 font-mono text-xs text-muted-foreground">{typeof t.parameters === 'string' ? t.parameters : JSON.stringify(t.parameters)}</p>}
    </li>; })}</ul>
    <p className="mt-2 text-xs text-muted-foreground">Outlined parameters are required; grey ones with ? are optional.</p></Block>
</Stack>;
AGT1.uses = ['available_tools', 'user_request'];
const AGT2 = ({s}) => { const steps = parseTrace(s.transcript), where = steps.filter(x => x.kind === 'tool' && findInjection(x.result, s.injected_text)).map(x => x.no), first = steps.find(x => x.kind === 'user');
  return <Stack>
    {first?.text?.trim() !== String(s.user_task || '').trim() && <Block label="User task"><Bubble side="user">{s.user_task}</Bubble></Block>}
    <Block><Callout tone="warn" icon={TriangleAlertIcon} title="Injected instruction, planted in a tool result">
      <div className="max-h-48 overflow-auto font-mono text-xs leading-relaxed whitespace-pre-wrap">{s.injected_text}</div>
      {where.length > 0 && <div className="mt-2 text-xs text-muted-foreground">The agent receives it at {where.map((n, i) => <Fragment key={n}>{i > 0 && ', '}<a href={`#step-${n}`} onClick={e => { e.preventDefault(); document.getElementById(`step-${n}`)?.scrollIntoView({behavior: 'smooth', block: 'center'}); }} className="font-medium text-warn underline-offset-2 hover:underline">step {n}</a></Fragment>)}.</div>}
    </Callout></Block>
    <Fold label="System prompt" preview={String(s.system_prompt || '').split('\n')[0]}><div className="font-mono text-xs leading-relaxed whitespace-pre-wrap text-foreground/85">{s.system_prompt}</div></Fold>
    <Block label="Trace"><Trace lines={s.transcript} injected={s.injected_text} /></Block>
  </Stack>; };
AGT2.uses = ['injected_text', 'system_prompt', 'transcript', 'user_task'];
const AGT3 = ({s}) => <Stack>
  <Block label="What the simulated customer wants"><Callout icon={UserIcon} title="Customer scenario">{s.user_scenario}</Callout></Block>
  <Fold label="Agent policy" preview={String(s.policy || '').replace(/^#.*\n+/, '').split('\n')[0]}><Markdown text={s.policy} /></Fold>
  <Block label="Trace"><Trace lines={s.transcript} /></Block>
</Stack>;
AGT3.uses = ['policy', 'transcript', 'user_scenario'];
function AGT4({s}) {
  const [hot, setHot] = useState(null), srcs = (s.sources || []).map(x => { const m = String(x).match(/^\s*\[(\d+)\]\s*([\s\S]*)$/); return m ? {n: m[1], text: m[2]} : {n: '', text: String(x)}; });
  const cite = (n, i) => <button key={i} type="button" onMouseEnter={() => setHot(n)} onMouseLeave={() => setHot(null)} onClick={() => document.getElementById(`src-${n}`)?.scrollIntoView({behavior: 'smooth', block: 'nearest'})} className="mx-0.5 inline-grid h-4 min-w-4 cursor-pointer place-items-center rounded bg-brand-soft px-1 align-[1px] text-[10px] font-semibold text-brand hover:bg-brand hover:text-background">{n}</button>;
  return <Stack>
    <Block label="Setting"><p className="text-sm text-muted-foreground">{s.setting}</p></Block>
    <Block label="Conversation"><div className="space-y-3">
      <Bubble side="user" who="User">{s.user_message}</Bubble>
      <Bubble side="assistant" who="Answer">{String(s.answer || '').split(/(\[\d+\])/).map((p, i) => { const m = p.match(/^\[(\d+)\]$/); return m ? cite(m[1], i) : <Fragment key={i}>{p}</Fragment>; })}</Bubble>
    </div></Block>
    <Block label="Sources" aside={`${srcs.length} passages`}><ol className="space-y-2">{srcs.map(x => <li key={x.n || x.text.slice(0, 20)} id={`src-${x.n}`} className={cn('grid grid-cols-[24px_minmax(0,1fr)] gap-3 rounded-lg border px-3 py-2.5 text-[13px] leading-relaxed transition-colors', hot === x.n && 'border-brand/40 bg-brand-soft')}>
      <span className="grid size-5 place-items-center rounded bg-muted text-[11px] font-semibold tabular-nums">{x.n}</span><span>{x.text}</span></li>)}</ol></Block>
  </Stack>;
}
AGT4.uses = ['answer', 'setting', 'sources', 'user_message'];
const AGT5 = ({s}) => <Stack>
  <Block label="Question"><Bubble side="user">{s.question}</Bubble></Block>
  <Block label="Two responses"><div className="grid gap-3 md:grid-cols-2">{['A', 'B'].map(k => <div key={k} className="rounded-lg border">
    <div className="flex items-center gap-2 border-b bg-muted/40 px-4 py-2 text-xs font-semibold"><span className="grid size-5 place-items-center rounded bg-foreground text-[11px] text-background">{k}</span>Response {k}</div>
    <Markdown text={s[`response_${k}`]} className="px-4 py-3" />
  </div>)}</div></Block>
</Stack>;
AGT5.uses = ['question', 'response_A', 'response_B'];

/* ---------- Trust & safety, support ---------- */
const SAF1 = ({s}) => <Block label={s.channel ? `Sent as a ${s.channel}` : 'Message'}><Bubble side="user" who="User">{s.message}</Bubble></Block>;
SAF1.uses = ['channel', 'message'];
const SAF2 = ({s}) => <Block label="Comment"><div className="flex gap-3 rounded-lg border px-4 py-3">
  <span className="grid size-8 shrink-0 place-items-center rounded-full bg-muted"><MessageSquareIcon className="size-4 text-muted-foreground" /></span>
  <div className="min-w-0"><div className="text-xs text-muted-foreground">{s.channel}</div><p className="mt-1 text-sm leading-relaxed break-words whitespace-pre-wrap">{s.comment}</p></div>
</div></Block>;
SAF2.uses = ['channel', 'comment'];
const SUP = ({s}) => <Block label="Complaint"><div className="overflow-hidden rounded-lg border">
  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b bg-muted/40 px-4 py-2 text-xs text-muted-foreground"><span className="font-medium text-foreground">{s.channel}</span>{s.date_received && <span className="inline-flex items-center gap-1"><CalendarIcon className="size-3.5" />received {s.date_received}</span>}</div>
  <p className="px-4 py-3.5 text-sm leading-7 break-words whitespace-pre-wrap"><Redacted text={s.narrative} /></p>
</div><p className="mt-2 text-xs text-muted-foreground">Grey bars are names and numbers the source redacted (XXXX).</p></Block>;
SUP.uses = ['channel', 'date_received', 'narrative'];

/* ---------- Sales & commerce ---------- */
function Product({p}) {
  const title = p.title || p.item_name || p.name, bullets = p.bullet_points || [], specs = Object.entries(p).filter(([k, v]) => !['title', 'item_name', 'name', 'bullet_points', 'brand'].includes(k) && v != null && typeof v !== 'object');
  return <div className="rounded-lg border px-4 py-3.5">
    {p.brand && <div className="text-xs font-medium text-muted-foreground">{p.brand}</div>}
    <h4 className="mt-0.5 text-[15px] leading-snug font-semibold">{title}</h4>
    {bullets.length > 0 && <ul className="mt-3 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-foreground/85 marker:text-muted-foreground/60">{bullets.map((b, i) => <li key={i}>{b}</li>)}</ul>}
    {specs.length > 0 && <dl className="mt-3 grid grid-cols-[max-content_minmax(0,1fr)] gap-x-4 gap-y-1 border-t pt-3 text-[13px]">{specs.map(([k, v]) => <Fragment key={k}><dt className="text-muted-foreground capitalize">{k.replaceAll('_', ' ')}</dt><dd>{String(v)}</dd></Fragment>)}</dl>}
  </div>;
}
const COM1 = ({s}) => <Stack>
  <Block label={`Search on ${s.marketplace || 'the marketplace'}`}><div className="flex h-10 items-center gap-2.5 rounded-full border bg-background px-4 text-sm shadow-xs"><SearchIcon className="size-4 text-muted-foreground" />{s.search_query}</div></Block>
  <Block label="Product in the results"><Product p={s.product || {}} /></Block>
</Stack>;
COM1.uses = ['marketplace', 'product', 'search_query'];
const COM2 = ({s}) => <Block label={`Listing on ${s.marketplace || 'the marketplace'}`}><Product p={s.listing || {}} /></Block>;
COM2.uses = ['listing', 'marketplace'];

/* ---------- Filings and documents ---------- */
const Filing = ({meta, text, note, label = 'Passage'}) => <Block label={label}>
  {meta && <div className="mb-3"><Meta items={meta} /></div>}
  <Doc><Expandable lines={14} always={String(text || '').length < 1800}>{text}</Expandable></Doc>
  {note && <div className="mt-2.5"><Note>{note}</Note></div>}
</Block>;
const COM3 = ({s}) => <Filing label="Filing excerpt" meta={[['Source', s.filing]]} text={s.item_1_excerpt} />;
COM3.uses = ['filing', 'item_1_excerpt'];
const FIN1 = ({s}) => <Filing meta={[['Filer', <span className="inline-flex items-center gap-1"><Building2Icon className="size-3.5" />{s.filer}</span>], ['Form', s.form], ['Fiscal year', s.fiscal_year], ['Industry', s.industry]]} text={s.passage} note={s.note} />;
FIN1.uses = ['filer', 'fiscal_year', 'form', 'industry', 'note', 'passage'];
const FIN2 = ({s}) => <Filing label="Report body" meta={[['Filer', s.filer], ['Form', s.form], ['Report date', s.date_of_report], ['Filed', s.filed]]} text={s.body} note={s.note} />;
FIN2.uses = ['body', 'date_of_report', 'filed', 'filer', 'form', 'note'];
function Receipt({text}) {
  return <div className="rounded-md border border-dashed bg-background px-4 py-3 font-mono text-xs leading-6 shadow-xs">
    {String(text).split('\n').map((l, i) => { const m = l.match(/^(.*?)\s+([\d.,]+)$/); return m ? <div key={i} className={cn('flex justify-between gap-4', /^(total|cash|change|subtotal)/i.test(m[1]) && 'font-semibold')}><span>{m[1]}</span><span className="tabular-nums">{m[2]}</span></div> : <div key={i}>{l}</div>; })}
  </div>;
}
const FIN3 = ({s, c}) => <Stack>
  <Block label="Receipt"><div className="grid items-start gap-5 md:grid-cols-[minmax(0,1fr)_minmax(220px,300px)]">
    <Figure c={c} />
    <div><div className="mb-1.5 text-xs font-medium text-muted-foreground">Text rendering (OCR)</div><Receipt text={s.ocr_text} /><div className="mt-2.5"><Note>{s.ocr_note}</Note></div></div>
  </div></Block>
  <Block label="Candidate figures"><Chips items={s.candidate_figures || []} mono /></Block>
</Stack>;
FIN3.uses = ['candidate_figures', 'image', 'ocr_note', 'ocr_text'];
const FIN4 = ({s}) => <Block label="Filing sentence">
  <Doc>{String(s.sentence).split(/(\[\[[^\]]+\]\])/).map((p, i) => /^\[\[.*\]\]$/.test(p) ? <mark key={i} className="rounded-[3px] bg-brand-soft px-1 font-semibold text-brand ring-1 ring-brand/30">{p.slice(2, -2)}</mark> : <Fragment key={i}>{p}</Fragment>)}</Doc>
  <div className="mt-2.5 space-y-1.5"><Note>{s.note}</Note><Note>Source: {s.source}. The number in question: <code>{s.marked_number}</code>.</Note></div>
</Block>;
FIN4.uses = ['marked_number', 'note', 'sentence', 'source'];

/* ---------- Legal ---------- */
const InContext = ({before, focus, after, label}) => <Doc className="leading-7">
  {before && <span className="text-muted-foreground">{before} </span>}
  <mark className="rounded-[3px] bg-brand-soft px-1 py-0.5 text-foreground ring-1 ring-brand/25 [box-decoration-break:clone]" title={label}>{focus}</mark>
  {after && <span className="text-muted-foreground"> {after}</span>}
</Doc>;
const LEG1 = ({s}) => <Stack>
  <Block label="Statement to check"><Callout icon={QuoteIcon} title="Does the agreement say this?">{s.statement}</Callout></Block>
  <Block label="Agreement"><Doc><Expandable lines={16}>{s.agreement}</Expandable></Doc></Block>
</Stack>;
LEG1.uses = ['agreement', 'statement'];
const LEG2 = ({s}) => <Block label="Clause, with the text around it"><InContext before={s.context_before} focus={s.clause} after={s.context_after} label="The clause" /><p className="mt-2 text-xs text-muted-foreground">The highlighted text is the clause; the grey text around it is context.</p></Block>;
LEG2.uses = ['clause', 'context_after', 'context_before'];
const LEG3 = ({s}) => <Block label="Sentence, with its neighbours"><InContext before={s.previous_sentence} focus={s.sentence} after={s.next_sentence} label="The sentence" /><p className="mt-2 text-xs text-muted-foreground">The highlighted sentence is the one to judge.</p></Block>;
LEG3.uses = ['next_sentence', 'previous_sentence', 'sentence'];
const LEG4 = ({s}) => <Stack>
  <Block label="Clause type"><Callout icon={QuoteIcon} title={s.clause_type}>{s.clause_type_definition}</Callout></Block>
  <Block label="Contract excerpt" aside={s.excerpt_position}><Doc><Expandable lines={16}>{s.contract_excerpt}</Expandable></Doc></Block>
</Stack>;
LEG4.uses = ['clause_type', 'clause_type_definition', 'contract_excerpt', 'excerpt_position'];

/* ---------- Product ---------- */
const PRD1 = ({s}) => <Stack>
  <Block label="Two packages for the same story"><div className="grid gap-3 md:grid-cols-2">{['A', 'B'].map(k => { const p = s[`package_${k}`] || {};
    return <article key={k} className="rounded-lg border px-4 py-3.5"><div className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground"><span className="grid size-5 place-items-center rounded bg-foreground text-[11px] text-background">{k}</span>Package {k}</div>
      <h4 className="text-lg leading-snug font-semibold text-balance">{p.headline}</h4>{p.excerpt && <p className="mt-1.5 text-sm text-muted-foreground">{p.excerpt}</p>}</article>; })}</div>
    {s.picture && <div className="mt-2.5"><Note>{s.picture}</Note></div>}</Block>
  <Block label="Story lede"><Doc>{s.story_lede}</Doc></Block>
</Stack>;
PRD1.uses = ['package_A', 'package_B', 'picture', 'story_lede'];
const PRD2 = ({s}) => <Block label={`Release notes · ${s.project}`}><Doc className="whitespace-normal"><Markdown text={s.release_notes} /></Doc></Block>;
PRD2.uses = ['project', 'release_notes'];

/* ---------- Data & analytics ---------- */
const SQL_KW = /\b(SELECT|FROM|WHERE|JOIN|INNER|LEFT|RIGHT|OUTER|ON|AS|GROUP|ORDER|BY|HAVING|LIMIT|EXCEPT|UNION|INTERSECT|AND|OR|NOT|IN|COUNT|SUM|AVG|MIN|MAX|DISTINCT|DESC|ASC|LIKE|BETWEEN|IS|NULL)\b/gi;
const Sql = ({q}) => <code className="block font-mono text-xs leading-relaxed break-words whitespace-pre-wrap">{String(q).split(/('[^']*'|"[^"]*")/).map((p, i) => /^['"]/.test(p) ? <span key={i} className="text-good">{p}</span> : p.split(SQL_KW).map((t, j) => j % 2 ? <span key={j} className="font-semibold text-brand">{t.toUpperCase()}</span> : t))}</code>;
function DAT1({s}) {
  const tables = (s.schema?.tables || []).map(t => { const m = String(t).match(/^(\w+)\((.*)\)$/); return m ? {name: m[1], cols: m[2].split(',').map(x => x.trim()).map(x => ({name: x.replace(/\*$/, ''), pk: x.endsWith('*')}))} : {name: String(t), cols: []}; });
  return <Stack>
    <Block label="Question"><Callout icon={DatabaseIcon} title={s.database}>{s.question}</Callout></Block>
    <Block label="Schema" aside={`${tables.length} tables`}>
      <div className="grid gap-2.5 sm:grid-cols-2">{tables.map(t => <div key={t.name} className="overflow-hidden rounded-lg border"><div className="border-b bg-muted/40 px-3 py-1.5 font-mono text-xs font-semibold">{t.name}</div>
        <ul className="px-3 py-1.5 font-mono text-[11px] leading-5">{t.cols.map(c => <li key={c.name} className="flex items-center gap-1.5">{c.pk ? <KeyRoundIcon className="size-3 text-warn" /> : <span className="w-3" />}<span className={cn(c.pk && 'font-semibold')}>{c.name}</span></li>)}</ul></div>)}</div>
      {(s.schema?.foreign_keys || []).length > 0 && <div className="mt-3"><div className="mb-1 text-xs text-muted-foreground">Foreign keys</div><ul className="space-y-0.5 font-mono text-[11px] text-foreground/80">{s.schema.foreign_keys.map(f => <li key={f}>{String(f).replace('->', '→')}</li>)}</ul></div>}
    </Block>
    <Block label="Candidate queries"><ul className="space-y-2">{Object.entries(s.candidate_queries || {}).map(([k, q]) => <li key={k} className="grid grid-cols-[32px_minmax(0,1fr)] items-start gap-2 rounded-lg border px-3 py-2.5"><span className="font-mono text-xs font-semibold text-muted-foreground">{k}</span><Sql q={q} /></li>)}</ul></Block>
  </Stack>;
}
DAT1.uses = ['candidate_queries', 'database', 'question', 'schema'];
const DAT2 = ({s}) => { const t = s.table || {}, cols = t.columns || [], rows = t.rows || [];
  return <Stack>
    <Block label="Question"><Callout>{s.question}</Callout></Block>
    <Block label="Table" aside={`${rows.length} rows × ${cols.length} columns`}><div className="max-h-[480px] overflow-auto rounded-lg border"><table className="w-full text-[13px]">
      <thead className="sticky top-0 bg-muted"><tr>{['#', ...cols].map((c, i) => <th key={i} className={cn('border-b px-3 py-2 text-left font-medium whitespace-nowrap text-muted-foreground', i === 0 && 'w-10 text-right')}>{c}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i} className="border-b last:border-0 even:bg-muted/30"><td className="px-3 py-1.5 text-right text-xs text-muted-foreground tabular-nums">{i + 1}</td>{r.map((x, j) => <td key={j} className="px-3 py-1.5">{String(x ?? '')}</td>)}</tr>)}</tbody>
    </table></div></Block>
  </Stack>; };
DAT2.uses = ['question', 'table'];
function DAT3({s, c}) {
  const ch = s.chart || {}, used = s.text_rendering?.data_points_used_by_the_claim || {}, series = s.text_rendering?.series_sampled_every_10_years || {};
  const years = [...new Set(Object.values(series).flatMap(o => Object.keys(o)))].sort();
  return <Stack>
    <Block label="Claim to check"><Callout icon={QuoteIcon} title="The claim">{s.claim}</Callout>{s.claim_origin && <div className="mt-2"><Note>{s.claim_origin}</Note></div>}</Block>
    <Block label="Chart"><Figure c={c} /><div className="mt-3"><Meta items={[['Title', ch.title], ['Type', ch.type], ['Unit', ch.unit], ['Years', ch.years], ['Countries', (ch.countries || []).join(', ')], ['Data', ch.data_source], ['Publisher', ch.publisher]]} /></div></Block>
    <Block label="Text rendering: the values the claim uses"><div className="flex flex-wrap gap-2">{Object.entries(used).flatMap(([k, o]) => Object.entries(o).map(([y, v]) => <div key={k + y} className="rounded-lg border px-3 py-2"><div className="text-xs text-muted-foreground">{k} · {y}</div><div className="font-mono text-sm font-semibold tabular-nums">{Number(v).toLocaleString('en-US')}</div></div>))}</div></Block>
    {years.length > 0 && <Fold label="Text rendering: every series, sampled every ten years" preview={Object.keys(series).join(', ')}>
      <div className="overflow-x-auto rounded-lg border"><table className="w-full text-xs tabular-nums"><thead className="bg-muted/50"><tr><th className="px-3 py-1.5 text-left font-medium text-muted-foreground">Series</th>{years.map(y => <th key={y} className="px-2 py-1.5 text-right font-medium text-muted-foreground">{y}</th>)}</tr></thead>
        <tbody>{Object.entries(series).map(([k, o]) => <tr key={k} className="border-t"><td className="px-3 py-1.5 font-medium whitespace-nowrap">{k}</td>{years.map(y => <td key={y} className="px-2 py-1.5 text-right" title={o[y] != null ? Number(o[y]).toLocaleString('en-US') : ''}>{o[y] != null ? compact(o[y]) : '—'}</td>)}</tr>)}</tbody></table></div>
    </Fold>}
  </Stack>;
}
DAT3.uses = ['chart', 'claim', 'claim_origin', 'text_rendering'];
function DAT4({s}) {
  const n = s.columns_in_file || 0, pos = s.hidden_column_position, others = [...(s.other_headers || [])], heads = Array.from({length: n}, (_, i) => i + 1 === pos ? null : others.shift());
  return <Stack>
    <Block label="File"><div className="font-mono text-xs">{s.file}</div></Block>
    <Block label={`Headers, column ${pos} of ${n} hidden`}><div className="overflow-x-auto"><div className="flex w-max overflow-hidden rounded-lg border font-mono text-[11px]">{heads.map((h, i) => <div key={i} className={cn('border-r px-2.5 py-1.5 whitespace-nowrap last:border-0', h == null ? 'bg-brand-soft font-semibold text-brand' : 'text-muted-foreground')}><span className="mr-1.5 opacity-50">{i + 1}</span>{h ?? '?'}</div>)}</div></div></Block>
    <Block label="Values from the hidden column" aside={`${(s.values_from_the_hidden_column || []).length} values`}><div className="flex flex-wrap gap-1.5">{(s.values_from_the_hidden_column || []).map((v, i) => <span key={i} className="rounded-md border bg-background px-2 py-1 font-mono text-xs">{String(v)}</span>)}</div></Block>
  </Stack>;
}
DAT4.uses = ['columns_in_file', 'file', 'hidden_column_position', 'other_headers', 'values_from_the_hidden_column'];

/* ---------- Documents & meetings ---------- */
function DOC1({s, c}) {
  const blocks = String(s.text_rendering || '').split(/\n{2,}(?=\[[A-Za-z-]+\])/).map(b => { const m = b.match(/^\[([A-Za-z-]+)\]\s?([\s\S]*)$/); return m ? {tag: m[1], text: m[2]} : {tag: '', text: b}; });
  return <Stack>
    <Block label="Page" aside={s.layout_blocks}><Figure c={c} /></Block>
    <Block label="Text rendering, block by block"><Expandable lines={18}><ol className="space-y-2">{blocks.map((b, i) => <li key={i} className="grid grid-cols-[92px_minmax(0,1fr)] gap-3">
      <span className="pt-0.5"><Badge variant="secondary" className="font-normal">{b.tag || 'Text'}</Badge></span>
      <span className={cn('text-[13px] leading-relaxed break-words whitespace-pre-wrap', /formula/i.test(b.tag) && 'font-mono text-xs')}>{b.text}</span></li>)}</ol></Expandable></Block>
  </Stack>;
}
DOC1.uses = ['layout_blocks', 'page', 'text_rendering'];
function DOC2({s}) {
  const turns = (s.transcript || []).map(t => typeof t === 'string' ? {speaker: t.split(':')[0], text: t.slice(t.indexOf(':') + 1).trim()} : {speaker: t.speaker, text: t.text});
  const hot = turns.findIndex(t => `${t.speaker}: ${t.text}` === s.highlighted_utterance);
  return <Stack>
    <Block label="Meeting"><p className="text-sm text-muted-foreground">{s.meeting}</p></Block>
    <Block label="Utterance to classify"><Callout icon={MessageSquareIcon} title={String(s.highlighted_utterance).split(':')[0]}>{String(s.highlighted_utterance).slice(String(s.highlighted_utterance).indexOf(':') + 1).trim()}</Callout></Block>
    <Block label="Transcript around it"><Turns turns={turns} hot={hot} /></Block>
  </Stack>;
}
DOC2.uses = ['highlighted_utterance', 'meeting', 'transcript'];
function DOC3({s}) {
  const turns = String(s.transcript_excerpt || '').split('\n').filter(Boolean).map(l => { const i = l.indexOf(':'); return i > 0 && i < 60 ? {speaker: l.slice(0, i), text: l.slice(i + 1).trim()} : {speaker: '', text: l}; });
  return <Stack>
    <Block label="Meeting"><p className="text-sm text-muted-foreground">{s.meeting}</p></Block>
    <Block label="Transcript excerpt" aside={`${turns.length} utterances`}><Expandable lines={16}><Turns turns={turns} /></Expandable></Block>
    <Block label="Candidate summaries"><div className="grid gap-3 md:grid-cols-2">{Object.entries(s.candidate_summaries || {}).map(([k, v]) => <div key={k} className="rounded-lg border px-4 py-3">
      <div className="mb-1.5 flex items-center gap-2 text-xs font-semibold text-muted-foreground"><span className="grid size-5 place-items-center rounded bg-foreground text-[11px] text-background">{k}</span>Summary {k}</div>
      <p className="text-[13px] leading-relaxed">{v}</p></div>)}</div></Block>
  </Stack>;
}
DOC3.uses = ['candidate_summaries', 'meeting', 'transcript_excerpt'];

/* ---------- Design ---------- */
const DSN1 = ({s, c}) => <Stack>
  <Block label="Icon"><div className="flex justify-center rounded-lg border bg-[repeating-conic-gradient(var(--muted)_0_25%,transparent_0_50%)] bg-[length:16px_16px] p-6">{(c.assets || []).map(a => <img key={a.path} src={assetUrl(a)} alt={a.alt_text || ''} width="160" height="160" className="size-40 rounded-md bg-white shadow-xs" />)}</div>
    <div className="mt-2.5 space-y-1.5"><Note>{s.image}</Note><Note>Text rendering: {s.text_rendering}</Note></div></Block>
  <Block label="Candidate names"><Chips items={s.candidate_names || []} mono /></Block>
</Stack>;
DSN1.uses = ['candidate_names', 'image', 'text_rendering'];

const VIEWS = {'ENG-1': ENG1, 'ENG-2': ENG2, 'ENG-3': ENG3, 'ENG-4': ENG4, 'ENG-5': ENG5, 'AGT-1': AGT1, 'AGT-2': AGT2, 'AGT-3': AGT3, 'AGT-4': AGT4, 'AGT-5': AGT5,
  'SAF-1': SAF1, 'SAF-2': SAF2, 'SUP-1': SUP, 'SUP-2': SUP, 'COM-1': COM1, 'COM-2': COM2, 'COM-3': COM3, 'FIN-1': FIN1, 'FIN-2': FIN2, 'FIN-3': FIN3, 'FIN-4': FIN4,
  'LEG-1': LEG1, 'LEG-2': LEG2, 'LEG-3': LEG3, 'LEG-4': LEG4, 'PRD-1': PRD1, 'PRD-2': PRD2, 'DAT-1': DAT1, 'DAT-2': DAT2, 'DAT-3': DAT3, 'DAT-4': DAT4,
  'DOC-1': DOC1, 'DOC-2': DOC2, 'DOC-3': DOC3, 'DSN-1': DSN1};

/* A view that throws on an unexpected record falls back to the generic renderer instead of breaking the page. */
class Fallback extends Component {
  state = {failed: false};
  static getDerivedStateFromError() { return {failed: true}; }
  componentDidCatch(e) { console.error('Record view failed; using the generic view.', e); }
  render() { return this.state.failed ? <Record c={this.props.c} /> : this.props.children; }
}
export function RecordView({c}) {
  const View = VIEWS[c.task];
  if (!View || !c.state || typeof c.state !== 'object' || Array.isArray(c.state)) return <Record c={c} />;
  return <Fallback key={c.id} c={c}><div className="divide-y"><View s={c.state} c={c} /><Rest state={c.state} used={View.uses} /></div></Fallback>;
}
