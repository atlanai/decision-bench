import {useState} from 'react';
import {ChevronRightIcon, DownloadIcon, ImageIcon, InfoIcon} from 'lucide-react';
import * as B from '@/lib/bench';
import {pct0, plural, num, human, cap, hostOf} from '@/lib/format';
import {taskHref, dataHref} from '@/lib/route';
import {tip} from '@/components/tip';
import {cn} from '@/lib/utils';
import {PageHeader, Fit, Logo, Dash, Ext} from '@/components/common';
import {UseCaseSelect, ModalityTabs, SearchBox} from '@/components/filters';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogClose} from '@/components/ui/dialog';

/* The dialog behind a row's ⓘ: the question, its options and where the rows come from. */
export function TaskDialog({t, onOpenChange}) {
  const open = !!t;
  let body = null;
  if (t) {
    const i = B.taskInfo(t), rows = B.taskRows(t), q0 = rows[0]?.questions[0], ds = B.datasetsOfTask(t);
    const facts = [['Decision', cap(i.shape || '')], ['Input', i.input_type], ['Rows', rows.length], ['Answer from', i.label_origin || rows[0]?.source?.labelled_by], ['Contamination risk', cap(i.contamination || '')]].filter(([, v]) => v !== '' && v != null);
    body = <>
      <DialogHeader>
        <div className="flex items-center gap-2 text-xs text-muted-foreground"><span>{B.catInfo(B.taskCat(t)).name}</span><span className="font-mono">{t}</span></div>
        <DialogTitle>{B.taskName(t)}</DialogTitle>
        <DialogDescription>{B.taskAsk(t)}</DialogDescription>
      </DialogHeader>
      <div className="space-y-5 border-t pt-5">
        <div>
          <h3 className="mb-2.5 text-xs font-medium text-muted-foreground">Options</h3>
          {i.per_row_options ? <p className="text-sm text-muted-foreground">The options differ per row and come from the record.</p> :
            <ul className="space-y-2">{B.taskOptions(t).map(o => <li key={o} className="grid grid-cols-[minmax(88px,max-content)_1fr] items-baseline gap-3 text-sm"><Badge variant="outline" className="justify-self-start">{human(o)}</Badge><span className="text-foreground/80">{q0?.options?.[o]}</span></li>)}</ul>}
        </div>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">{facts.map(([k, v]) => <div key={k}><dt className="text-xs text-muted-foreground">{k}</dt><dd className="mt-0.5 text-sm font-medium">{v}</dd></div>)}</dl>
        <div>
          <h3 className="mb-2.5 text-xs font-medium text-muted-foreground">Source</h3>
          <div className="space-y-2">{ds.map(d => (
            <div key={d.id} className="rounded-lg border p-3.5">
              <div className="flex flex-wrap items-center gap-2"><span className="text-sm font-medium">{d.name}</span>{d.license && <Badge variant="secondary" className="font-mono text-[11px]">{d.license}</Badge>}</div>
              {d.content && <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">{d.content}</p>}
              <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[13px]">
                {d.homepage && <Ext href={d.homepage} icon className="text-brand hover:underline">{hostOf(d.homepage) || 'Homepage'}</Ext>}
                <a href={dataHref(d.id)} className="text-brand hover:underline" onClick={() => onOpenChange(false)}>Licence and terms</a>
              </div>
            </div>))}{!ds.length && <p className="text-sm text-muted-foreground">No source recorded.</p>}</div>
        </div>
      </div>
      <DialogFooter className="border-t pt-4">
        <DialogClose asChild><Button variant="outline">Close</Button></DialogClose>
        <Button asChild><a href={taskHref(t)} onClick={() => onOpenChange(false)}>Open task<ChevronRightIcon /></a></Button>
      </DialogFooter>
    </>;
  }
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="sm:max-w-xl">{body}</DialogContent></Dialog>;
}

export function Tasks({route}) {
  const [closed, setClosed] = useState(() => new Set()), [info, setInfo] = useState(null);
  const cat = route.q.get('category') || '', mod = route.q.get('modality') || '', q = (route.q.get('q') || '').toLowerCase();
  const tasks = B.taskOrder().filter(t => (!cat || B.taskCat(t) === cat) && (!mod || (mod === 'image') === B.isImageTask(t)) && (!q || `${t} ${B.taskName(t)} ${B.taskAsk(t)} ${B.catInfo(B.taskCat(t)).name} ${B.taskInfo(t).input_type || ''} ${B.datasetsOfTask(t).map(d => d.name).join(' ')}`.toLowerCase().includes(q)));
  const groups = B.categoryOrder().map(k => [k, tasks.filter(t => B.taskCat(t) === k)]).filter(([, ts]) => ts.length);
  const toggle = k => setClosed(s => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n; });
  const H = 'h-10 px-3 text-left text-[13px] font-medium whitespace-nowrap text-muted-foreground';
  return <>
    <PageHeader title="Tasks" description={`Every task is one fixed question with a short list of options, asked of ${plural(B.allCases.length, 'real record')}. Open a task to read its rows and see how each model did.`}
      actions={<Button variant="outline" asChild><a href="corpus.json" download><DownloadIcon />Download all rows</a></Button>} />
    <div className="mb-4 flex flex-wrap items-center gap-2">
      <SearchBox route={route} placeholder="Search tasks, inputs, datasets…" className="w-full sm:w-80" />
      <UseCaseSelect route={route} className="min-w-44" />
      {B.allCases.some(c => B.isImageTask(c.task)) && <ModalityTabs route={route} />}
      <span className="ml-auto text-[13px] text-muted-foreground tabular-nums">{plural(tasks.length, 'task')} · {num(tasks.reduce((n, t) => n + B.taskRows(t).length, 0))} rows</span>
    </div>
    <div className="overflow-hidden rounded-xl border bg-card shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] table-fixed text-sm">
          <colgroup><col className="w-[84px] max-md:w-0" /><col /><col className="w-[220px] max-lg:w-0" /><col className="w-[84px] max-lg:w-0" /><col className="w-[64px]" /><col className="w-[124px] max-md:w-0" /><col className="w-[108px]" /><col className="w-[52px]" /></colgroup>
          <thead><tr className="border-b">
            <th className={cn(H, 'pl-5 max-md:hidden')}>ID</th><th className={cn(H, 'max-md:pl-5')}>Task</th><th className={cn(H, 'max-lg:hidden')}>Input</th><th className={cn(H, 'text-right max-lg:hidden')}>Options</th>
            <th className={cn(H, 'text-right')}>Rows</th><th className={cn(H, 'max-md:hidden')}>Best model</th><th className={H}>Verdict</th><th className={H}><span className="sr-only">Details</span></th>
          </tr></thead>
          {groups.map(([k, ts]) => { const open = !closed.has(k) || !!q; return (
            <tbody key={k}>
              <tr className="border-b bg-muted/50">
                <td colSpan={8} className="p-0">
                  <button type="button" onClick={() => toggle(k)} aria-expanded={open} className="flex h-10 w-full cursor-pointer items-center gap-2 px-5 text-left text-sm outline-none focus-visible:bg-muted">
                    <ChevronRightIcon className={cn('size-4 text-muted-foreground transition-transform', open && 'rotate-90')} />
                    <span className="font-semibold whitespace-nowrap">{B.catInfo(k).name}</span>
                    <Badge variant="secondary" className="bg-background tabular-nums">{ts.length}</Badge>
                    <span className="ml-1 truncate text-[13px] text-muted-foreground max-md:hidden">{B.catInfo(k).description}</span>
                  </button>
                </td>
              </tr>
              {open && ts.map(t => { const i = B.taskInfo(t), b = B.bestOn(t), opts = B.taskOptions(t);
                return <tr key={t} onClick={e => { if (!e.target.closest('a,button')) location.hash = taskHref(t); }} className="group cursor-pointer border-b transition-colors last:border-0 hover:bg-muted/40">
                  <td className="py-2.5 pl-5 font-mono text-xs text-muted-foreground max-md:hidden">{t}</td>
                  <td className="min-w-0 px-3 py-2.5 max-md:pl-5">
                    <a href={taskHref(t)} className="block truncate font-medium hover:underline max-md:whitespace-normal">{B.taskName(t)}</a>
                    <span className="block truncate text-[13px] text-muted-foreground max-md:whitespace-normal">{B.taskAsk(t)}</span>
                  </td>
                  <td className="px-3 py-2.5 max-lg:hidden">{i.input_type && <Badge variant="outline" className="max-w-full font-normal text-foreground/80">{B.isImageTask(t) && <ImageIcon className="text-muted-foreground" />}<span className="truncate">{i.input_type}</span></Badge>}</td>
                  <td className="px-3 py-2.5 text-right tabular-nums max-lg:hidden">{i.per_row_options ? <span className="text-[13px] text-muted-foreground" title="The options come from each record">varies</span> :
                    <span className="cursor-help underline decoration-muted-foreground/40 decoration-dotted underline-offset-4" data-tip={tip(plural(opts.length, 'option'), opts.map(o => [human(o), '']))}>{opts.length}</span>}</td>
                  <td className="px-3 py-2.5 text-right tabular-nums">{B.taskRows(t).length}</td>
                  <td className="px-3 py-2.5 max-md:hidden">{b ? <span className="inline-flex items-center gap-2" title={B.runName(b[0])}><Logo k={B.keyOf(b[0])} /><span className="tabular-nums">{pct0(b[1].accuracy)}</span></span> : <Dash />}</td>
                  <td className="px-3 py-2.5">{b ? <Fit v={B.verdict(b[1])} /> : <Dash />}</td>
                  <td className="py-2.5 pr-3 text-right"><Button variant="ghost" size="icon-sm" className="text-muted-foreground" onClick={() => setInfo(t)} aria-label={`Details and source for ${B.taskName(t)}`}><InfoIcon /></Button></td>
                </tr>; })}
            </tbody>); })}
          {!groups.length && <tbody><tr><td colSpan={8} className="px-5 py-12 text-center text-sm text-muted-foreground">No task matches these filters.</td></tr></tbody>}
        </table>
      </div>
    </div>
    <TaskDialog t={info} onOpenChange={o => { if (!o) setInfo(null); }} />
  </>;
}
