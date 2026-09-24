import {Component, lazy, Suspense, useEffect, useLayoutEffect, useRef, useState} from 'react';
import {init, caseMap, caseTitle, taskName, M} from '@/lib/bench';
import {pageView, installClicks} from '@/lib/analytics';
import {useRoute} from '@/lib/route';
import {Header, Footer, TabBar} from '@/components/layout';
import {Toaster} from '@/components/toast';
import {ChartTip} from '@/components/tip';
import {TooltipProvider} from '@/components/ui/tooltip';
import {EmptyPage} from '@/components/common';
import {Home} from '@/pages/home';
const Tasks = lazy(() => import('@/pages/tasks').then(m => ({default: m.Tasks})));
const TaskPage = lazy(() => import('@/pages/task').then(m => ({default: m.TaskPage})));
const RowPage = lazy(() => import('@/pages/row').then(m => ({default: m.RowPage})));
const Models = lazy(() => import('@/pages/models').then(m => ({default: m.Models})));
const ModelPage = lazy(() => import('@/pages/models').then(m => ({default: m.ModelPage})));
const Compare = lazy(() => import('@/pages/compare').then(m => ({default: m.Compare})));
const DataPage = lazy(() => import('@/pages/data').then(m => ({default: m.DataPage})));
const Methodology = lazy(() => import('@/pages/methodology').then(m => ({default: m.Methodology})));
const Review = lazy(() => import('@/pages/review').then(m => ({default: m.Review})));

const TITLES = {home: 'Leaderboard', tasks: 'Tasks', models: 'Models', compare: 'Compare', data: 'Data', methodology: 'Methodology', review: 'Review'};

/* CSS ships precompiled. Reveal content after layout, without waiting for fonts or a decorative timer. */
const boot = (msg, f) => window.dbBoot?.(msg, f);
function hideBoot() {
  const el = document.getElementById('boot');
  if (!el || el.dataset.done != null) return;
  boot('Ready', 1);
  el.dataset.done = '';
  setTimeout(() => el.remove(), 200);
}

function useBench() {
  const [state, setState] = useState({ready: false, error: null});
  useEffect(() => {
    (async () => {
      try {
        boot('Fetching the results', .25);
        const [json, ds] = await Promise.all([
          fetch('viewer.json', {cache: 'no-cache', signal: AbortSignal.timeout(30000)}).then(res => res.status === 404 ? fetch('data.json', {cache: 'no-cache', signal: AbortSignal.timeout(30000)}) : res).then(res => { if (!res.ok) throw Error('Results unavailable'); return res.json(); }),
          fetch('datasets.json', {cache: 'no-cache', signal: AbortSignal.timeout(10000)}).then(res => res.ok ? res.json() : null).catch(() => null),
        ]);
        boot('Scoring every model', .6);
        await new Promise(r => setTimeout(r));
        init(json, ds); setState({ready: true, error: null});
      } catch { setState({ready: false, error: 'The benchmark could not be loaded. Please try again.'}); }
    })();
  }, []);
  return state;
}

class PageBoundary extends Component {
  state = {failed: false};
  static getDerivedStateFromError() { return {failed: true}; }
  render() {
    return this.state.failed ? <div className="p-8"><h1 className="text-2xl font-semibold">Unable to load this page</h1><p role="alert" className="mt-3">Please reload to try again.</p><button type="button" className="mt-4 rounded-md border px-4 py-2" onClick={() => location.reload()}>Reload page</button></div> : this.props.children;
  }
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
  /* A new page starts at the top; a filter change on the same page keeps the scroll position. A layout effect, so
     a page transition (see route.js) captures the new page already scrolled to the top. */
  useLayoutEffect(() => {
    if (!ready) return;
    const key = `${route.page}/${route.id}`;
    if (key !== last.current && !(route.page === 'methodology' && route.id) && !(route.page === 'data' && last.current.startsWith('data/'))) scrollTo({top: 0, behavior: 'instant'});
    last.current = key;
    const t = route.page === 'row' ? caseTitle(caseMap.get(route.id) || {id: route.id}) : route.page === 'task' ? taskName(route.id) : route.page === 'model' ? M(route.id).name : TITLES[route.page];
    document.title = `${t} · Decision Bench`;
  }, [ready, route]);

  useEffect(() => { if (ready) pageView(route); }, [ready, route]);
  useEffect(() => installClicks(), []);

  useEffect(() => { if (ready || error) hideBoot(); }, [ready, error]);

  if (error) return <main id="main"><EmptyPage title="Unable to load results"><p role="alert">{error}</p><button type="button" className="mt-4 rounded-md border px-4 py-2" onClick={() => location.reload()}>Try again</button></EmptyPage></main>;
  if (!ready) return null;
  const wide = route.page === 'home';
  return (
    <TooltipProvider>
      <a href="#main" onClick={e => { e.preventDefault(); document.getElementById('main')?.focus(); }} className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:shadow">Skip to content</a>
      <Header page={route.page} id={route.id} />
      <main id="main" tabIndex={-1} className={wide ? 'outline-none' : 'mx-auto max-w-[1240px] px-4 pt-5 pb-16 outline-none md:px-8 md:pt-8 lg:pt-10 lg:pb-20'}>
        <PageBoundary key={`${route.page}/${route.id}`}><Suspense fallback={<p role="status" className="p-8">Loading page…</p>}><Page route={route} /></Suspense></PageBoundary>
      </main>
      <Footer />
      <TabBar page={route.page} />
      <Toaster />
      <ChartTip />
    </TooltipProvider>
  );
}
