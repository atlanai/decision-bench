import {useEffect, useRef, useState} from 'react';
import {init, caseMap, caseTitle, taskName, M} from '@/lib/bench';
import {useRoute} from '@/lib/route';
import {Header, Footer} from '@/components/layout';
import {ChartTip} from '@/components/tip';
import {TooltipProvider} from '@/components/ui/tooltip';
import {EmptyPage} from '@/components/common';
import {Home} from '@/pages/home';
import {Tasks} from '@/pages/tasks';
import {TaskPage} from '@/pages/task';
import {RowPage} from '@/pages/row';
import {Models, ModelPage} from '@/pages/models';
import {Compare} from '@/pages/compare';
import {DataPage} from '@/pages/data';
import {Methodology} from '@/pages/methodology';
import {Review} from '@/pages/review';

const TITLES = {home: 'Leaderboard', tasks: 'Tasks', models: 'Models', compare: 'Compare', data: 'Data', methodology: 'Methodology', review: 'Review'};

function useBench() {
  const [state, setState] = useState({ready: false, error: null});
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('data.json', {cache: 'no-store'}); if (!res.ok) throw Error(`HTTP ${res.status}`);
        const json = await res.json();
        let ds = null; try { const d = await fetch('datasets.json', {cache: 'no-store'}); ds = d.ok ? await d.json() : null; } catch {}
        init(json, ds); setState({ready: true, error: null});
      } catch (e) { console.error(e); setState({ready: false, error: e.message}); }
    })();
  }, []);
  return state;
}

function Page({route}) {
  const {page, id} = route;
  switch (page) {
    case 'tasks': return <Tasks route={route} />;
    case 'task': return <TaskPage key={id} id={id} route={route} />;
    case 'row': return <RowPage key={id} id={id} />;
    case 'models': return <Models />;
    case 'model': return <ModelPage key={id} id={id} />;
    case 'compare': return <Compare route={route} />;
    case 'data': return <DataPage id={id} route={route} />;
    case 'methodology': return <Methodology id={id} />;
    case 'review': return <Review id={id} />;
    default: return <Home route={route} />;
  }
}

export function App() {
  const {ready, error} = useBench(), route = useRoute(), last = useRef('');
  /* A new page starts at the top; a filter change on the same page keeps the scroll position. */
  useEffect(() => {
    if (!ready) return;
    const key = `${route.page}/${route.id}`;
    if (key !== last.current && !(route.page === 'methodology' && route.id) && !(route.page === 'data' && last.current.startsWith('data/'))) scrollTo({top: 0, behavior: 'instant'});
    last.current = key;
    const t = route.page === 'row' ? caseTitle(caseMap.get(route.id) || {id: route.id}) : route.page === 'task' ? taskName(route.id) : route.page === 'model' ? M(route.id).name : TITLES[route.page];
    document.title = `${t} · Decision Bench`;
  }, [ready, route]);

  if (error) return <EmptyPage title="Results are not built yet">Run <code>python3 -m decision_bench report</code>, then refresh.<div className="mt-2 opacity-70">{error}</div></EmptyPage>;
  if (!ready) return <div className="grid min-h-[80vh] place-items-center text-sm text-muted-foreground">Loading Decision Bench…</div>;
  const wide = route.page === 'home';
  return (
    <TooltipProvider>
      <a href="#main" onClick={e => { e.preventDefault(); document.getElementById('main')?.focus(); }} className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:shadow">Skip to content</a>
      <Header page={route.page} id={route.id} />
      <main id="main" tabIndex={-1} className={wide ? 'outline-none' : 'mx-auto max-w-[1240px] px-4 pt-8 pb-20 outline-none md:px-8 md:pt-10'}>
        <Page route={route} />
      </main>
      <Footer />
      <ChartTip />
    </TooltipProvider>
  );
}
