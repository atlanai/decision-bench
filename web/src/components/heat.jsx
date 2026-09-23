/* Heatmap of accuracy by task (rows) and model (columns). Only misses are coloured: ≥95% stays faded. */
import {Fragment} from 'react';
import {taskOrder, taskCat, catInfo, taskName, subsetMetrics, runName, keyOf, ident, isImageTask} from '@/lib/bench';
import {pct, ciText} from '@/lib/format';
import {taskHref} from '@/lib/route';
import {tip} from '@/components/tip';
import {Logo} from '@/components/common';
import {cn} from '@/lib/utils';

const SHADES = [[.95, 0], [.9, 12], [.8, 24], [.65, 42], [-1, 66]];
const shade = a => SHADES.find(([t]) => a >= t)[1];
const bg = s => s ? `color-mix(in oklab, var(--bad) ${s}%, transparent)` : undefined;

function Cell({r, m, label}) {
  if (!m?.questions) return <td className="px-1.5 py-1 text-center text-muted-foreground/40">—</td>;
  const s = shade(m.accuracy), v = m.accuracy >= .995 ? '100' : m.accuracy === 0 ? '0' : (m.accuracy * 100).toFixed(m.accuracy >= .1 ? 0 : 1);
  return <td className={cn('px-1.5 py-1 text-center tabular-nums', s ? 'text-foreground' : 'text-muted-foreground/60')} style={{background: bg(s)}}
    data-tip={tip(`${runName(r)} · ${label}`, [['Accuracy', pct(m.accuracy)], ['95% interval', ciText(m.wilson)], ['Correct', `${m.correct}/${m.questions}`]])}>{v}</td>;
}

export function HeatTasks({runs, cases}) {
  const tasks = taskOrder().filter(t => cases.some(c => c.task === t));
  let last = null;
  return (
    <div className="overflow-hidden rounded-xl border bg-card shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full min-w-max border-collapse text-[13px]">
          <thead>
            <tr className="border-b">
              <th className="sticky left-0 z-[1] bg-card py-2 pr-4 pl-5 text-left align-bottom text-[13px] font-medium text-muted-foreground">Task</th>
              {runs.map(r => <th key={r.id} title={runName(r)} className="w-[72px] min-w-[64px] px-1.5 py-2 text-center align-bottom text-xs font-medium text-muted-foreground">
                <Logo k={keyOf(r)} className="mx-auto mb-1 block" /><span className="block leading-tight">{ident(r).short}</span></th>)}
            </tr>
          </thead>
          <tbody>
            {tasks.map(t => { const cat = taskCat(t), head = cat !== last; last = cat; const tc = cases.filter(c => c.task === t);
              return <Fragment key={t}>
                {head && <tr className="border-b bg-muted/40"><th colSpan={runs.length + 1} className="sticky left-0 py-2 pl-5 text-left text-xs font-semibold text-foreground">{catInfo(cat).name}</th></tr>}
                <tr className="border-b last:border-0">
                  <th scope="row" className="sticky left-0 z-[1] max-w-[320px] bg-card py-1.5 pr-4 pl-5 text-left font-normal">
                    <a href={taskHref(t)} className="font-medium hover:underline">{taskName(t)}</a>
                    <span className="ml-1.5 text-xs text-muted-foreground tabular-nums">{tc.length}{isImageTask(t) ? ' · image' : ''}</span>
                  </th>
                  {runs.map(r => <Cell key={r.id} r={r} m={subsetMetrics(r, tc)} label={taskName(t)} />)}
                </tr>
              </Fragment>; })}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 border-t px-5 py-3 text-xs text-muted-foreground">
        {[['≥ 95%', 0], ['90–95', 12], ['80–90', 24], ['65–80', 42], ['< 65', 66]].map(([l, s]) => <span key={l} className="inline-flex items-center gap-1.5"><i className="inline-block h-2.5 w-3.5 rounded-[2px] border" style={{background: bg(s)}} />{l}</span>)}
      </div>
    </div>
  );
}
