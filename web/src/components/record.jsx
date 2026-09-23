/* Renders a row's state as the artifact it is: diffs, code, transcripts, emails, tables, key/value records. */
import {Fragment, useState} from 'react';
import {CheckIcon, CopyIcon} from 'lucide-react';
import {assetUrl, optionOrder} from '@/lib/bench';
import {labelOf} from '@/lib/format';
import {cn} from '@/lib/utils';
import {Button} from '@/components/ui/button';

const isObj = v => v && typeof v === 'object' && !Array.isArray(v);
const isDiff = s => /^diff --git /m.test(s) || (/^--- \S/m.test(s) && /^\+\+\+ \S/m.test(s)) || /^@@ .* @@/m.test(s);
const CODE_LINE = /^\s{2,}\S|[{};]\s*$|^\s*(def |function |class |import |from \S+ import|SELECT |FROM |WHERE |\$ |>>> |#!|<\/?[a-z][\w-]*[ >])|^\[?\d{4}-\d\d-\d\d[T ]\d\d:|\S {3,}\S/;
function isCodeish(s) { if (/```/.test(s)) return true; const lines = s.split('\n').filter(l => l.trim()); if (lines.length < 2) return /^\s*(def|function|class|import|SELECT|CREATE TABLE)\b/.test(s); return lines.filter(l => CODE_LINE.test(l)).length >= Math.max(2, lines.length * .3); }

export const Code = ({children, wrap, className}) => <pre className={cn('max-h-[560px] overflow-auto rounded-lg border bg-muted/50 px-3.5 py-3 font-mono text-xs leading-relaxed [tab-size:4]', wrap ? 'break-words whitespace-pre-wrap' : 'whitespace-pre', className)}>{children}</pre>;
const None = ({children = 'none'}) => <span className="text-muted-foreground">{children}</span>;

function Str({s}) {
  if (isDiff(s)) return <Code>{s.split('\n').map((l, i) => <span key={i} className={cn('block', /^\+(?!\+\+ )/.test(l) ? 'bg-good-soft text-good' : /^-(?!-- )/.test(l) ? 'bg-bad-soft text-bad' : /^@@/.test(l) && 'text-muted-foreground')}>{l || ' '}</span>)}</Code>;
  if (isCodeish(s)) return <Code>{s}</Code>;
  if (s.length > 160 || /\n/.test(s)) return <p className={cn('text-sm leading-relaxed break-words whitespace-pre-wrap', s.length > 2400 && 'max-h-[480px] overflow-auto border-l-2 pr-2 pl-3')}>{s}</p>;
  return <span className="text-sm">{s}</span>;
}

/* Turn lists: transcripts, logs and tool calls. */
const WHO = ['speaker', 'role', 'from', 'agent', 'author', 'sender', 'name', 'turn_by'], WHAT = ['text', 'content', 'message', 'utterance', 'body', 'said'];
const looksTurn = o => isObj(o) && WHO.some(k => typeof o[k] === 'string') && WHAT.some(k => typeof o[k] === 'string');
const NUMBERED = /^\s*(\d+)[.)]\s+([\s\S]*)$/, RESULT = /^\s*(?:→|->)\s?([\s\S]*)$/;
const looksTurnLine = s => typeof s === 'string' && (/^\s*(\d+[.)]\s*)?[A-Za-z_][\w .()-]{0,60}?:\s/.test(s) || NUMBERED.test(s) || RESULT.test(s));
/* "3. USER: text", "4. CALL tool({...})", "   → result" and {speaker, text} objects, into one shape. */
function parseTurns(v) {
  const out = [];
  v.forEach((o, i) => {
    if (isObj(o)) {
      const who = WHO.map(k => o[k]).find(x => typeof x === 'string') || '';
      let what = WHAT.map(k => o[k]).find(x => typeof x === 'string') || '';
      const rest = Object.entries(o).filter(([k, x]) => !WHO.includes(k) && !WHAT.includes(k) && !['turn', 'step', 'index', 'no'].includes(k) && x != null && x !== '');
      if (rest.length) what += `\n${rest.map(([k, x]) => `${k}: ${typeof x === 'string' ? x : JSON.stringify(x)}`).join('\n')}`;
      out.push({no: o.turn ?? o.step ?? o.index ?? o.no ?? i + 1, who, what, tool: /tool|function|terminal|system/i.test(who)});
      return;
    }
    const s = String(o), r = s.match(RESULT);
    if (r && out.length) { const last = out.at(-1); last.result = last.result ? `${last.result}\n${r[1]}` : r[1]; return; }
    const n = s.match(NUMBERED), body = n ? n[2] : s, no = n ? n[1] : out.length + 1;
    const call = body.match(/^CALL\s+([\s\S]*)$/);
    if (call) { out.push({no, who: 'Tool call', what: call[1], tool: true}); return; }
    const m = body.match(/^([A-Za-z_][\w .()-]{0,60}?):\s([\s\S]*)$/);
    out.push(m ? {no, who: m[1], what: m[2], tool: /tool|function|terminal|system|result/i.test(m[1])} : {no, who: '', what: body, tool: false});
  });
  return out;
}
const ROLE = w => { const x = w.toLowerCase(); return x === 'user' || x === 'customer' ? 'User' : x === 'agent' || x === 'assistant' ? 'Agent' : w; };
function Turns({v}) {
  return <div className="divide-y rounded-lg border">{parseTurns(v).map((t, i) => (
    <div key={i} className={cn('grid grid-cols-[28px_minmax(0,1fr)] gap-x-3 gap-y-1 px-3.5 py-2.5 text-sm sm:grid-cols-[28px_96px_minmax(0,1fr)]', t.tool && 'bg-muted/40')}>
      <span className="pt-px text-right text-xs text-muted-foreground tabular-nums">{t.no}</span>
      <span title={t.who} className={cn('truncate text-[13px] font-medium', t.tool ? 'text-muted-foreground' : /^user$/i.test(t.who) ? 'text-brand' : 'text-foreground')}>{ROLE(t.who)}</span>
      <div className="col-span-2 min-w-0 sm:col-span-1">
        <div className={cn('break-words whitespace-pre-wrap', t.tool ? 'font-mono text-xs leading-relaxed text-foreground/85' : 'leading-relaxed')}>{t.what}</div>
        {t.result != null && <div className="mt-1.5 flex gap-2 font-mono text-xs leading-relaxed text-muted-foreground"><span aria-hidden="true">→</span><span className="min-w-0 break-words whitespace-pre-wrap">{t.result}</span></div>}
      </div>
    </div>
  ))}</div>;
}
const looksEmail = o => isObj(o) && ('subject' in o || 'from' in o) && ('body' in o || 'text' in o);
function Email({o}) {
  const hdr = ['from', 'to', 'cc', 'date', 'subject'].filter(k => o[k] != null), rest = Object.entries(o).filter(([k]) => ![...hdr, 'body', 'text'].includes(k));
  return <>
    <div className="overflow-hidden rounded-lg border">
      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 border-b bg-muted/40 px-4 py-3 text-sm">{hdr.map(k => <Fragment key={k}><dt className="text-muted-foreground">{labelOf(k)}</dt><dd>{String(o[k])}</dd></Fragment>)}</dl>
      <div className="px-4 py-3.5 text-sm leading-relaxed break-words whitespace-pre-wrap">{String(o.body ?? o.text ?? '')}</div>
    </div>
    {rest.length > 0 && <KV entries={rest} depth={2} className="mt-3" />}
  </>;
}
const SimpleTable = ({head, rows}) => (
  <div className="overflow-x-auto rounded-lg border"><table className="w-full text-[13px]">
    <thead><tr className="border-b bg-muted/40">{head.map((k, i) => <th key={i} className="px-3 py-2 text-left font-medium whitespace-nowrap text-muted-foreground">{k}</th>)}</tr></thead>
    <tbody>{rows.map((r, i) => <tr key={i} className="border-b last:border-0">{r.map((x, j) => <td key={j} className="px-3 py-2 align-top">{x}</td>)}</tr>)}</tbody>
  </table></div>
);
const KV = ({entries, depth, className}) => (
  <dl className={cn('grid grid-cols-[minmax(90px,max-content)_minmax(0,1fr)] gap-x-5 gap-y-2', depth > 1 && 'border-l-2 pl-3', className)}>
    {entries.map(([k, x]) => <div key={k} className="contents"><dt className="text-sm text-muted-foreground">{labelOf(k)}</dt><dd className="min-w-0 break-words">{<Value v={x} depth={depth + 1} />}</dd></div>)}
  </dl>
);

export function Value({v, depth = 0}) {
  if (v == null) return <None />;
  if (typeof v === 'string') return <Str s={v} />;
  if (typeof v !== 'object') return <span className="text-sm tabular-nums">{String(v)}</span>;
  if (Array.isArray(v)) {
    if (!v.length) return <None>empty</None>;
    if (v.length >= 2 && v.every(x => looksTurn(x) || looksTurnLine(x))) return <Turns v={v} />;
    if (v.every(isObj)) {
      const keys = [...new Set(v.flatMap(Object.keys))], flat = v.every(o => Object.values(o).every(x => x == null || typeof x !== 'object'));
      if (keys.length <= 8 && flat && v.length > 1) return <SimpleTable head={keys.map(labelOf)} rows={v.map(o => keys.map(k => o[k] == null ? '' : typeof o[k] === 'string' ? <Str s={o[k]} /> : String(o[k])))} />;
      if (depth >= 2) return <Code>{JSON.stringify(v, null, 2)}</Code>;
    }
    if (v.every(x => Array.isArray(x)) && v.length > 1 && v.every(x => x.length === v[0].length && x.every(y => typeof y !== 'object'))) return <SimpleTable head={v[0].map(String)} rows={v.slice(1).map(r => r.map(x => String(x ?? '')))} />;
    return <ol className="list-decimal space-y-1.5 pl-5 marker:text-xs marker:text-muted-foreground">{v.map((x, i) => <li key={i} className="pl-1"><Value v={x} depth={depth + 1} /></li>)}</ol>;
  }
  if (looksEmail(v)) return <Email o={v} />;
  const ents = Object.entries(v); if (!ents.length) return <None>empty</None>;
  if (depth >= 3) return <Code>{JSON.stringify(v, null, 2)}</Code>;
  return <KV entries={ents} depth={depth} />;
}

/* The record card body: images first, then each top-level field under its own label. */
export function Record({c}) {
  const st = c.state, imgs = (c.assets || []).filter(a => String(a.mime_type || '').startsWith('image/'));
  return <div className="divide-y">
    {imgs.map(a => <figure key={a.path} className="p-5">
      <a href={assetUrl(a)} target="_blank" rel="noopener"><img src={assetUrl(a)} alt={a.alt_text || ''} width={a.width} height={a.height} className="block h-auto max-h-[640px] max-w-full rounded-lg border bg-white" /></a>
      <figcaption className="mt-2 text-xs text-muted-foreground">{a.alt_text ? `${a.alt_text} · ` : ''}Sent as an image to vision models; text-only models receive the text below.</figcaption>
    </figure>)}
    {isObj(st) && !looksEmail(st)
      ? Object.entries(st).map(([k, v]) => <section key={k} className="px-5 py-4"><h3 className="mb-2 text-xs font-medium text-muted-foreground">{labelOf(k)}</h3><Value v={v} depth={1} /></section>)
      : <div className="px-5 py-4">{looksEmail(st) ? <Email o={st} /> : <Value v={st} />}</div>}
  </div>;
}

export function CopyButton({text, label = 'Copy'}) {
  const [done, setDone] = useState(false);
  return <Button variant="ghost" size="xs" onClick={() => navigator.clipboard?.writeText(text).then(() => { setDone(true); setTimeout(() => setDone(false), 1500); })}>{done ? <CheckIcon /> : <CopyIcon />}{done ? 'Copied' : label}</Button>;
}
export const exactInput = c => JSON.stringify({state: c.state, question: {instructions: c.questions[0].instructions, options: Object.fromEntries(optionOrder(c.questions[0]).map(k => [k, c.questions[0].options[k]]))}}, null, 2);
