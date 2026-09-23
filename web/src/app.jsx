import {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {init, caseMap, caseTitle, taskName, M} from '@/lib/bench';
import {pageView, installClicks} from '@/lib/analytics';
import {useRoute} from '@/lib/route';
import {Header, Footer, TabBar} from '@/components/layout';
import {Toaster} from '@/components/toast';
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

/* The loading screen lives in index.html, outside React. It is also the splash screen: on the first load of a
   visit it stays long enough for the mark to finish assembling, then bursts apart as the app zooms in behind it. */
const boot = (msg, f) => window.dbBoot?.(msg, f);
const SPLASH_MS = 1150;
function splashLeft() { let seen = false; try { seen = sessionStorage.getItem('db-splash') === '1'; sessionStorage.setItem('db-splash', '1'); } catch {} return seen ? 0 : Math.max(0, SPLASH_MS - performance.now()); }
function hideBoot() {
  const el = document.getElementById('boot'); if (!el || el.dataset.leaving) return;
  el.dataset.leaving = '1'; boot('Ready', 1);
  setTimeout(() => { el.dataset.done = ''; setTimeout(() => el.remove(), 900); }, splashLeft());
}
/* The Tailwind runtime writes the stylesheet after the page mounts, so the first layout is unstyled and charts
   measure the wrong width until their ResizeObserver catches up. Lift the loading screen once the stylesheet has
   been quiet for a moment, the fonts are in and two frames have let the charts re-measure. */
function hideBootWhenSettled() {
  let t;
  const mo = new MutationObserver(() => quiet()), done = () => { mo.disconnect(); clearTimeout(t); clearTimeout(cap); hideBoot(); };
  const sized = () => [...document.querySelectorAll('[role=img] > svg[width]')].every(s => Math.abs(+s.getAttribute('width') - Math.max(220, s.parentElement.clientWidth)) <= 1);
  const check = () => sized() ? done() : requestAnimationFrame(check);
  const quiet = () => { clearTimeout(t); t = setTimeout(() => (document.fonts?.ready || Promise.resolve()).then(() => requestAnimationFrame(() => requestAnimationFrame(check))), 150); };
  const cap = setTimeout(done, 5000);
  mo.observe(document.head, {subtree: true, childList: true, characterData: true});
  boot('Drawing the charts', .85); quiet();
}

function useBench() {
  const [state, setState] = useState({ready: false, error: null});
  useEffect(() => {
    (async () => {
      try {
        boot('Fetching the results', .25);
        const res = await fetch('data.json', {cache: 'no-store'}); if (!res.ok) throw Error(`HTTP ${res.status}`);
        const json = await res.json();
        boot('Checking the licences', .45);
        let ds = null; try { const d = await fetch('datasets.json', {cache: 'no-store'}); ds = d.ok ? await d.json() : null; } catch {}
        boot('Scoring every model', .6);
        await new Promise(r => setTimeout(r));
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

  useEffect(() => { if (ready) hideBootWhenSettled(); else if (error) hideBoot(); }, [ready, error]);

  if (error) return <EmptyPage title="Nothing to show yet">Run <code>python3 -m decision_bench report</code>, then refresh.<div className="mt-2 opacity-70">{error}</div></EmptyPage>;
  if (!ready) return null;
  const wide = route.page === 'home';
  return (
    <TooltipProvider>
      <a href="#main" onClick={e => { e.preventDefault(); document.getElementById('main')?.focus(); }} className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:shadow">Skip to content</a>
      <Header page={route.page} id={route.id} />
      <main id="main" tabIndex={-1} className={wide ? 'outline-none' : 'mx-auto max-w-[1240px] px-4 pt-5 pb-16 outline-none md:px-8 md:pt-8 lg:pt-10 lg:pb-20'}>
        <Page route={route} />
      </main>
      <Footer />
      <TabBar page={route.page} />
      <Toaster />
      <ChartTip />
    </TooltipProvider>
  );
}
