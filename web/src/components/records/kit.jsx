/* Building blocks for the per-task record views: labelled blocks, a small markdown renderer, highlights,
   collapsible long text, chat bubbles and file headers. Everything renders as text; nothing is injected as HTML. */
import {Fragment, useState} from 'react';
import {ChevronDownIcon, FileCodeIcon, InfoIcon} from 'lucide-react';
import {cn} from '@/lib/utils';
import {labelOf} from '@/lib/format';
import {Value} from '@/components/record';

/* A labelled block inside the record card. */
export const Block = ({label, aside, children, className}) => (
  <section className={cn('px-5 py-4', className)}>
    {(label || aside) && <div className="mb-2.5 flex items-center justify-between gap-3"><h3 className="text-xs font-medium text-muted-foreground">{label}</h3>{aside && <div className="text-xs text-muted-foreground">{aside}</div>}</div>}
    {children}
  </section>
);
export const Stack = ({children}) => <div className="divide-y">{children}</div>;
/* Footnote from the dataset, e.g. what was removed or how a record was rendered. */
export const Note = ({children}) => children ? <p className="flex gap-2 text-xs leading-relaxed text-muted-foreground"><InfoIcon className="mt-0.5 size-3.5 shrink-0" />{children}</p> : null;
export const Meta = ({items}) => {
  const xs = items.filter(([, v]) => v != null && v !== '');
  return xs.length ? <dl className="flex flex-wrap gap-x-6 gap-y-2 text-[13px]">{xs.map(([k, v]) => <div key={k} className="flex items-baseline gap-2"><dt className="text-muted-foreground">{k}</dt><dd className="font-medium">{v}</dd></div>)}</dl> : null;
};
export const Callout = ({icon: Icon, title, tone = 'brand', children}) => (
  <div className={cn('rounded-lg border px-4 py-3', tone === 'warn' ? 'border-warn/30 bg-warn-soft' : tone === 'bad' ? 'border-bad/30 bg-bad-soft' : 'border-brand/20 bg-brand-soft')}>
    {title && <div className={cn('mb-1 flex items-center gap-1.5 text-xs font-semibold', tone === 'warn' ? 'text-warn' : tone === 'bad' ? 'text-bad' : 'text-brand')}>{Icon && <Icon className="size-3.5" />}{title}</div>}
    <div className="text-sm leading-relaxed text-foreground/90">{children}</div>
  </div>
);

/* Highlight every occurrence of needle(s) in text. */
export function Marked({text, needles, className = 'rounded-[3px] bg-warn-soft px-0.5 text-warn ring-1 ring-warn/30'}) {
  const ns = (Array.isArray(needles) ? needles : [needles]).filter(n => n && String(n).trim().length > 1).map(String);
  if (!ns.length) return text;
  const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), re = new RegExp(`(${ns.map(esc).join('|')})`, 'g');
  return String(text).split(re).map((p, i) => ns.includes(p) ? <mark key={i} className={className}>{p}</mark> : <Fragment key={i}>{p}</Fragment>);
}
/* "XXXX" is how CFPB and others redact names and numbers: show it as a redaction bar. */
export const Redacted = ({text}) => String(text).split(/(X{2,}(?:\/X{2,})*)/g).map((p, i) => /^X{2,}/.test(p) ? <span key={i} title="Redacted in the source" className="mx-px inline-block h-[1em] translate-y-[2px] rounded-[2px] bg-foreground/15 align-baseline" style={{width: `${Math.min(p.length, 8) * .5}em`}} /> : <Fragment key={i}>{p}</Fragment>);

/* Inline markdown: `code`, **bold**. */
function inline(s, key = '') {
  return String(s).split(/(`[^`\n]+`|\*\*[^*\n]+\*\*)/g).map((p, i) =>
    /^`[^`]+`$/.test(p) ? <code key={key + i} className="rounded bg-muted px-1 py-px text-[0.85em]">{p.slice(1, -1)}</code>
      : /^\*\*[^*]+\*\*$/.test(p) ? <strong key={key + i} className="font-semibold">{p.slice(2, -2)}</strong> : p);
}
/* Block markdown: headings, bullet and numbered lists, fenced code, paragraphs. Enough for policies, release
   notes, issues and model responses; anything else stays as plain text. */
export function Markdown({text, className, code: CodeFence}) {
  const lines = String(text || '').replace(/\r/g, '').split('\n'), out = [];
  let i = 0, k = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (/^\s*```/.test(l)) { const body = []; i++; while (i < lines.length && !/^\s*```/.test(lines[i])) body.push(lines[i++]); i++; out.push(CodeFence ? <CodeFence key={k++} text={body.join('\n')} /> : <pre key={k++} className="my-2 overflow-x-auto rounded-md border bg-muted/50 px-3 py-2 font-mono text-xs leading-relaxed whitespace-pre">{body.join('\n')}</pre>); continue; }
    const h = l.match(/^(#{1,4})\s+(.*)$/);
    if (h) { out.push(<div key={k++} className={cn('font-semibold text-foreground', h[1].length === 1 ? 'mt-4 text-base first:mt-0' : 'mt-3 text-sm first:mt-0')}>{inline(h[2])}</div>); i++; continue; }
    if (/^\s*[-*•]\s+/.test(l)) { const items = []; while (i < lines.length && /^\s*[-*•]\s+/.test(lines[i])) { let t = lines[i].replace(/^\s*[-*•]\s+/, ''); i++; while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*[-*•]\s+/.test(lines[i])) t += ' ' + lines[i++].trim(); items.push(t); } out.push(<ul key={k++} className="my-1.5 list-disc space-y-1 pl-5 marker:text-muted-foreground/60">{items.map((t, j) => <li key={j}>{inline(t, j)}</li>)}</ul>); continue; }
    if (/^\s*\d+[.)]\s+/.test(l)) { const items = []; while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) { let t = lines[i].replace(/^\s*\d+[.)]\s+/, ''); i++; while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*\d+[.)]\s+/.test(lines[i])) t += ' ' + lines[i++].trim(); items.push(t); } out.push(<ol key={k++} className="my-1.5 list-decimal space-y-1 pl-5 marker:text-muted-foreground">{items.map((t, j) => <li key={j}>{inline(t, j)}</li>)}</ol>); continue; }
    if (!l.trim()) { i++; continue; }
    const para = []; while (i < lines.length && lines[i].trim() && !/^\s*(```|#{1,4}\s|[-*•]\s|\d+[.)]\s)/.test(lines[i])) para.push(lines[i++]);
    out.push(<p key={k++} className="my-1.5 first:mt-0 last:mb-0">{para.map((p, j) => <Fragment key={j}>{j > 0 && <br />}{inline(p, j)}</Fragment>)}</p>);
  }
  return <div className={cn('text-sm leading-relaxed break-words text-foreground/90', className)}>{out}</div>;
}

/* Long text that opens on demand; the first lines stay visible. */
export function Expandable({children, lines = 6, label = 'Show all', className, always = false}) {
  const [open, setOpen] = useState(false);
  return <div className={className}>
    <div className={cn('relative', !open && !always && 'overflow-hidden')} style={!open && !always ? {maxHeight: `${lines * 1.625}rem`} : undefined}>
      {children}
      {!open && !always && <div className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-card to-transparent" />}
    </div>
    {!always && <button type="button" onClick={() => setOpen(v => !v)} className="mt-1.5 inline-flex cursor-pointer items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
      {open ? 'Show less' : label}<ChevronDownIcon className={cn('size-3.5 transition-transform', open && 'rotate-180')} />
    </button>}
  </div>;
}
/* Collapsed section with a one-line preview: system prompts, policies, agreements. */
export function Fold({label, preview, children, defaultOpen = false}) {
  const [open, setOpen] = useState(defaultOpen);
  return <section className="px-5 py-3.5">
    <button type="button" onClick={() => setOpen(v => !v)} aria-expanded={open} className="flex w-full cursor-pointer items-center gap-3 text-left">
      <ChevronDownIcon className={cn('size-4 shrink-0 text-muted-foreground transition-transform', !open && '-rotate-90')} />
      <span className="shrink-0 text-xs font-medium text-muted-foreground">{label}</span>
      {!open && preview && <span className="min-w-0 truncate text-[13px] text-muted-foreground/80">{preview}</span>}
    </button>
    {open && <div className="mt-3 pl-7">{children}</div>}
  </section>;
}

/* Chat bubble. side: 'user' sits on the right in brand tint, 'assistant' on the left. */
export const Bubble = ({who, side = 'user', children, className}) => (
  <div className={cn('flex flex-col gap-1', side === 'user' ? 'items-end' : 'items-start')}>
    {who && <span className="px-1 text-xs text-muted-foreground">{who}</span>}
    <div className={cn('max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed break-words whitespace-pre-wrap', side === 'user' ? 'rounded-br-md bg-brand-soft text-foreground' : 'rounded-bl-md border bg-muted/40', className)}>{children}</div>
  </div>
);

/* File header for diffs and code: icon, path, repository. */
export const FileHead = ({file, repo, right}) => (
  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b bg-muted/40 px-4 py-2.5">
    <FileCodeIcon className="size-4 shrink-0 text-muted-foreground" />
    <span className="min-w-0 font-mono text-xs font-medium break-all">{file}</span>
    {repo && <span className="text-xs text-muted-foreground">{repo.replace(/^github\.com\//, '')}</span>}
    {right && <span className="ml-auto">{right}</span>}
  </div>
);

/* Document page: readable measure, generous leading. */
export const Doc = ({children, className}) => <div className={cn('rounded-lg border bg-background px-5 py-4 text-sm leading-7 break-words whitespace-pre-wrap text-foreground/90', className)}>{children}</div>;

/* Any field a view did not place itself is still shown, so nothing the model saw is hidden. */
export function Rest({state, used}) {
  const rest = Object.entries(state || {}).filter(([k]) => !used.includes(k));
  return rest.map(([k, v]) => <Block key={k} label={labelOf(k)}><Value v={v} depth={1} /></Block>);
}
