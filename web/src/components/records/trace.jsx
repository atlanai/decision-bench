/* Agent runs as a trace: a timeline of user turns, agent messages and tool calls, each call with its result.
   Parses the "N. USER: …", "N. AGENT: …", "N. CALL tool({…})" and "   → result" lines the corpus stores. */
import {BotIcon, TriangleAlertIcon, UserIcon, WrenchIcon} from 'lucide-react';
import {cn} from '@/lib/utils';
import {Badge} from '@/components/ui/badge';
import {Expandable, Markdown} from './kit';

export function parseTrace(lines) {
  const steps = [];
  for (const raw of lines || []) {
    const s = String(raw), res = s.match(/^\s*(?:→|->)\s?([\s\S]*)$/);
    if (res && steps.length) { const last = steps.at(-1); last.result = last.result != null ? `${last.result}\n${res[1]}` : res[1]; continue; }
    const m = s.match(/^\s*(\d+)[.)]\s+([\s\S]*)$/), no = m ? m[1] : String(steps.length + 1), body = m ? m[2] : s;
    const call = body.match(/^CALL\s+([\w.$-]+)\s*\(([\s\S]*)\)\s*$/);
    if (call) { let args = call[2], parsed = null; try { parsed = JSON.parse(args || '{}'); } catch {} steps.push({no, kind: 'tool', name: call[1], args, parsed}); continue; }
    const role = body.match(/^([A-Z][A-Z _-]{1,20}):\s?([\s\S]*)$/);
    const who = role ? role[1].trim().toLowerCase() : '';
    steps.push({no, kind: /user|customer|human/.test(who) ? 'user' : /agent|assistant|model/.test(who) ? 'agent' : who ? 'other' : 'agent', who: role ? role[1] : '', text: role ? role[2] : body});
  }
  return steps;
}

/* An agent message that embeds its own tool request (<function=name>{…}</function>) shows it as a compact line. */
function Fence({text}) {
  const f = text.trim().match(/^<function=([\w.$-]+)>([\s\S]*)<\/function>$/);
  if (f) return <div className="my-2 flex items-center gap-2 font-mono text-xs text-muted-foreground"><WrenchIcon className="size-3.5" />requests <span className="font-medium text-foreground">{f[1]}</span><span className="truncate">{f[2]}</span></div>;
  return <pre tabIndex={0} className="my-2 overflow-x-auto rounded-md border bg-muted/50 px-3 py-2 font-mono text-xs leading-relaxed whitespace-pre">{text}</pre>;
}

const Arg = ({k, v}) => <span className="inline-flex max-w-full items-baseline gap-1 rounded-md border bg-background px-1.5 py-0.5 font-mono text-[11px]"><span className="text-muted-foreground">{k}</span><span className="truncate text-foreground">{typeof v === 'string' ? v : JSON.stringify(v)}</span></span>;

/* Where the injected text shows up in a tool result. Results often re-wrap and re-indent it (YAML, HTML), so
   match word by word across any whitespace; if the whole text is not there, take the longest opening run. */
const escRe = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
export function findInjection(text, injected) {
  if (!injected || !text) return null;
  const words = String(injected).split(/\s+/).filter(Boolean);
  for (let k = words.length; k >= Math.min(8, words.length); k = k > 40 ? Math.floor(k * .8) : k - 1) {
    const m = new RegExp(words.slice(0, k).map(escRe).join('(?:\\s|\\\\n|\\\\)+')).exec(text);
    if (m) return [m.index, m.index + m[0].length];
  }
  return null;
}
const Injected = ({text, range}) => <>{text.slice(0, range[0])}<mark className="rounded-[2px] bg-warn-soft text-warn [box-decoration-break:clone]">{text.slice(range[0], range[1])}</mark>{text.slice(range[1])}</>;

function Step({s, last, injected}) {
  const needle = s.kind === 'tool' ? findInjection(s.result, injected) : null;
  const icon = s.kind === 'user' ? <UserIcon className="size-3.5" /> : s.kind === 'tool' ? <WrenchIcon className="size-3.5" /> : <BotIcon className="size-3.5" />;
  const label = s.kind === 'user' ? 'User' : s.kind === 'tool' ? 'Tool call' : s.kind === 'agent' ? 'Agent' : s.who;
  const err = s.kind === 'tool' && /^\s*error\b/i.test(s.result || '');
  return (
    <li id={`step-${s.no}`} className="relative grid scroll-mt-24 grid-cols-[28px_minmax(0,1fr)] gap-x-3">
      <div className="relative flex justify-center">
        <span className={cn('z-[1] grid size-7 place-items-center rounded-full border bg-card', s.kind === 'user' && 'border-brand/30 bg-brand-soft text-brand', s.kind === 'agent' && 'bg-muted text-foreground', s.kind === 'tool' && 'border-dashed text-muted-foreground', needle && 'border-warn bg-warn-soft text-warn')}>{needle ? <TriangleAlertIcon className="size-3.5" /> : icon}</span>
        {!last && <span className="absolute top-7 bottom-0 w-px bg-border" />}
      </div>
      <div className="min-w-0 pb-5">
        <div className="flex h-7 items-center gap-2">
          <span className="text-[13px] font-medium">{label}</span>
          <span className="text-xs text-muted-foreground tabular-nums">{s.no}</span>
          {needle && <Badge variant="warn">Injected text in the result</Badge>}
        </div>
        {s.kind === 'user' && <div className="mt-1 inline-block max-w-full rounded-lg rounded-tl-sm bg-brand-soft px-3.5 py-2 text-sm leading-relaxed break-words whitespace-pre-wrap">{s.text}</div>}
        {(s.kind === 'agent' || s.kind === 'other') && <Markdown text={s.text} code={Fence} className="mt-1" />}
        {s.kind === 'tool' && <div className="mt-1 overflow-hidden rounded-lg border">
          <div className="flex flex-wrap items-center gap-1.5 bg-muted/40 px-3 py-2">
            <span className="mr-1 font-mono text-xs font-semibold">{s.name}</span>
            {s.parsed && typeof s.parsed === 'object' ? Object.entries(s.parsed).map(([k, v]) => <Arg key={k} k={k} v={v} />) : s.args && <span className="font-mono text-[11px] break-all text-muted-foreground">{s.args}</span>}
          </div>
          {s.result != null && <div className={cn('border-t px-3 py-2', err && 'bg-bad-soft/60')}>
            <div className="mb-1 text-[11px] font-medium text-muted-foreground">Returned</div>
            <Expandable lines={7} always={!!needle || (String(s.result).split('\n').length <= 7 && String(s.result).length < 700)}>
              <div className={cn('font-mono text-xs leading-relaxed break-words whitespace-pre-wrap', err ? 'text-bad' : 'text-foreground/85')}>{needle ? <Injected text={s.result} range={needle} /> : s.result}</div>
            </Expandable>
          </div>}
        </div>}
      </div>
    </li>
  );
}

export function Trace({lines, injected}) {
  const steps = parseTrace(lines), calls = steps.filter(s => s.kind === 'tool').length;
  return <>
    <div className="mb-4 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground tabular-nums"><span>{steps.length} steps</span><span>{calls} tool calls</span><span>{steps.filter(s => s.kind === 'agent').length} agent messages</span></div>
    <ol>{steps.map((s, i) => <Step key={i} s={s} last={i === steps.length - 1} injected={injected} />)}</ol>
  </>;
}
