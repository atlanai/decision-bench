/* Data: every dataset in one calm, grouped list. Details (licence terms, selection rule, changes, citation)
   open in a side sheet, so the list stays scannable. #/data/<id> opens that dataset's sheet. */
import {DownloadIcon, ChevronRightIcon, ExternalLinkIcon, FlagIcon, FileTextIcon} from 'lucide-react';
import * as B from '@/lib/bench';
import {plural, num, hostOf} from '@/lib/format';
import {withQ, go, taskHref, dataHref} from '@/lib/route';
import {cn} from '@/lib/utils';
import {PageHeader, Stat, Ext} from '@/components/common';
import {SearchBox, UseCaseSelect} from '@/components/filters';
import {CopyButton, Code} from '@/components/record';
import {GitHubIcon} from '@/components/icons';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Dialog, DialogTitle, DialogDescription, SheetContent} from '@/components/ui/dialog';

const dsCat = d => B.taskCat(d.tasks[0]);
const Licence = ({d}) => <span className="inline-flex flex-wrap items-center gap-1.5">
  {d.license && <Badge variant="outline" className="font-mono text-[11px] font-normal">{d.license}</Badge>}
  {d.content_license && d.content_license !== d.license && <Badge variant="secondary" className="font-mono text-[11px] font-normal text-muted-foreground" title="Licence of the text or images inside the dataset">content {d.content_license}</Badge>}
</span>;

function Field({label, children}) {
  if (!children) return null;
  return <div className="py-4 first:pt-0"><dt className="mb-1.5 text-xs font-medium text-muted-foreground">{label}</dt><dd className="text-sm leading-relaxed text-foreground/85">{children}</dd></div>;
}

function DatasetSheet({d, onClose}) {
  return (
    <Dialog open={!!d} onOpenChange={o => { if (!o) onClose(); }}>
      <SheetContent aria-describedby={undefined}>
        {d && <>
          <div className="border-b px-6 pt-6 pb-5">
            <div className="text-xs font-medium text-muted-foreground">{B.catInfo(dsCat(d)).name}</div>
            <DialogTitle className="mt-1 pr-8 text-xl font-semibold tracking-tight">{d.name}</DialogTitle>
            <DialogDescription className="sr-only">Licence, terms and how rows were chosen from {d.name}</DialogDescription>
            <div className="mt-3 flex flex-wrap items-center gap-3"><Licence d={d} /><span className="text-xs text-muted-foreground tabular-nums">{plural(d.rows.length, 'row')}</span></div>
          </div>
          <div className="flex-1 overflow-y-auto px-6 py-5">
            <dl className="divide-y">
              <Field label="Used for"><ul className="-mx-2">{d.tasks.map(t => <li key={t}><a href={taskHref(t)} className="flex items-center gap-3 rounded-md px-2 py-1.5 hover:bg-accent">
                <span className="w-12 shrink-0 font-mono text-xs text-muted-foreground">{t}</span><span className="min-w-0 flex-1 truncate font-medium">{B.taskName(t)}</span>
                <span className="text-xs text-muted-foreground tabular-nums">{d.rows.filter(c => c.task === t).length} rows</span><ChevronRightIcon className="size-4 text-muted-foreground" /></a></li>)}</ul></Field>
              <Field label="What a row is">{d.content}</Field>
              <Field label="Answers from">{d.labelled_by}</Field>
              <Field label="How rows were chosen">{d.selection}</Field>
              <Field label="What we changed">{d.changes}</Field>
              <Field label="Terms of the material">{d.content_terms}</Field>
              <Field label="Citation">{d.citation && <><p>{d.citation}</p><div className="mt-2 -ml-2 flex gap-1"><CopyButton text={d.citation} label="Copy citation" />{d.bibtex && <CopyButton text={d.bibtex} label="Copy BibTeX" />}</div></>}</Field>
              {d.bibtex && <Field label="BibTeX"><Code wrap className="max-h-48">{d.bibtex}</Code></Field>}
            </dl>
          </div>
          {(d.homepage || d.license_url) && <div className="flex flex-wrap gap-2 border-t px-6 py-4">
            {d.homepage && <Button variant="outline" size="sm" asChild><Ext href={d.homepage}><ExternalLinkIcon />{hostOf(d.homepage) || 'Homepage'}</Ext></Button>}
            {d.license_url && <Button variant="outline" size="sm" asChild><Ext href={d.license_url}><FileTextIcon />Licence text</Ext></Button>}
          </div>}
        </>}
      </SheetContent>
    </Dialog>
  );
}

export function DataPage({id, route}) {
  const q = (route.q.get('q') || '').toLowerCase(), cat = route.q.get('category') || '';
  const items = B.DATASETS.filter(d => (!cat || dsCat(d) === cat) && (!q || `${d.name} ${d.license || ''} ${d.content_license || ''} ${d.content || ''} ${d.tasks.join(' ')} ${d.tasks.map(B.taskName).join(' ')}`.toLowerCase().includes(q)));
  const groups = B.categoryOrder().map(k => [k, items.filter(d => dsCat(d) === k)]).filter(([, ds]) => ds.length);
  const rest = items.filter(d => !B.categoryOrder().includes(dsCat(d))); if (rest.length) groups.push(['', rest]);
  const open = B.DATASETS.find(d => d.id === id) || null, licences = new Set(B.DATASETS.map(d => d.license).filter(Boolean));
  const openHref = d => withQ({...route, page: 'data', id: d.id}, {});
  const H = 'h-10 px-3 text-left text-[13px] font-medium whitespace-nowrap text-muted-foreground';
  return <>
    <PageHeader title="Data" description={`${B.DATASETS.length} public datasets supply every row. Each keeps its own licence; the harness and site code are MIT. A dataset is used only when both its licence and the terms of the material inside it allow anyone to copy, change and redistribute it, commercially too.`}
      actions={<>
        <Button variant="outline" asChild><a href="corpus.json" download><DownloadIcon />All rows</a></Button>
        <Button variant="outline" asChild><a href="datasets.json" download><DownloadIcon />Dataset records</a></Button>
      </>} />
    <div className="mb-8 grid grid-cols-2 gap-3 md:grid-cols-4">
      <Stat label="Datasets" value={B.DATASETS.length} /><Stat label="Rows" value={num(B.allCases.length)} />
      <Stat label="Licences" value={licences.size} sub="all open" /><Stat label="Use cases" value={B.categoryOrder().length} />
    </div>
    <div className="mb-4 flex flex-wrap items-center gap-2">
      <SearchBox route={route} placeholder="Search datasets, licences, tasks…" className="w-full sm:w-80" />
      <UseCaseSelect route={route} className="min-w-44" />
      <span className="ml-auto text-[13px] text-muted-foreground tabular-nums">{plural(items.length, 'dataset')}</span>
    </div>
    <div className="overflow-hidden rounded-xl border bg-card shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] table-fixed text-sm">
          <colgroup><col /><col className="w-[220px] max-md:w-[140px]" /><col className="w-[150px] max-lg:w-0" /><col className="w-[72px]" /><col className="w-[44px]" /></colgroup>
          <thead><tr className="border-b"><th className={cn(H, 'pl-5')}>Dataset</th><th className={H}>Licence</th><th className={cn(H, 'max-lg:hidden')}>Tasks</th><th className={cn(H, 'text-right')}>Rows</th><th className={H}><span className="sr-only">Open</span></th></tr></thead>
          {groups.map(([k, ds]) => <tbody key={k || 'other'}>
            <tr className="border-b bg-muted/50"><td colSpan={5} className="h-9 px-5 text-[13px]"><span className="font-semibold">{k ? B.catInfo(k).name : 'Other'}</span><span className="ml-2 text-muted-foreground tabular-nums">{ds.length}</span></td></tr>
            {ds.map(d => <tr key={d.id} onClick={e => { if (!e.target.closest('a')) go(openHref(d)); }} className={cn('group cursor-pointer border-b transition-colors last:border-0 hover:bg-muted/40', open === d && 'bg-muted/50')}>
              <td className="min-w-0 py-3 pr-3 pl-5">
                <a href={openHref(d)} className="block truncate font-medium group-hover:underline">{d.name}</a>
                {d.content && <span className="mt-0.5 block truncate text-[13px] text-muted-foreground">{d.content}</span>}
              </td>
              <td className="px-3 py-3"><Licence d={d} /></td>
              <td className="px-3 py-3 font-mono text-xs text-muted-foreground max-lg:hidden"><span className="line-clamp-2">{d.tasks.join(', ')}</span></td>
              <td className="px-3 py-3 text-right tabular-nums">{d.rows.length}</td>
              <td className="py-3 pr-4 text-right"><ChevronRightIcon className="ml-auto size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" /></td>
            </tr>)}
          </tbody>)}
          {!groups.length && <tbody><tr><td colSpan={5} className="px-5 py-12 text-center text-sm text-muted-foreground">No dataset matches these filters.</td></tr></tbody>}
        </table>
      </div>
    </div>
    {B.repoOk() && <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-[13px]">
      <a href={B.gh('data/SOURCES.md')} target="_blank" rel="noopener" className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground"><GitHubIcon className="size-4" />Sources and attribution</a>
      <a href={B.ghIssue('data-removal.yml')} target="_blank" rel="noopener" className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground"><FlagIcon className="size-4" />Ask for a row to be removed</a>
    </div>}
    <DatasetSheet d={open} onClose={() => go(withQ({...route, id: ''}, {}))} />
  </>;
}
