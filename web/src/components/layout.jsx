import {useEffect, useState} from 'react';
import {BookOpenIcon, BoxesIcon, ChevronDownIcon, ChevronLeftIcon, ChevronUpIcon, DatabaseIcon, Dice1, Dice2, Dice3, Dice4, Dice5, Dice6, ListChecksIcon, MoonIcon, SunIcon, TrophyIcon} from 'lucide-react';
import {man, data, taskOrder, taskName, taskRows, caseMap, M, REPO, repoOk, HUGGING_FACE_DATASET} from '@/lib/bench';
import {go, replace, href, taskHref, rowHref, navHint, historyPos} from '@/lib/route';
import {haptic} from '@/lib/device';
import {nextTask} from '@/lib/dice';
import {cn} from '@/lib/utils';
import {BrandMark, GitHubIcon} from '@/components/icons';
import {Button} from '@/components/ui/button';
import {Tip} from '@/components/ui/tooltip';

const NAV = [['home', '/', 'Leaderboard'], ['tasks', '/tasks', 'Tasks'], ['models', '/models', 'Models'], ['data', '/data', 'Data'], ['methodology', '/methodology', 'Methodology']];
const SECTION = {task: 'tasks', row: 'tasks', review: 'tasks', model: 'models', compare: 'models'};

/* Switch themes with every transition off for one frame. Otherwise each element with transition-colors animates
   from the old palette to the new one, thousands at once, and the blurred sticky header can stay stuck halfway
   until something repaints it. */
function setTheme(dark) {
  const root = document.documentElement, off = document.createElement('style');
  off.textContent = '*,*::before,*::after{transition:none!important}';
  document.head.appendChild(off);
  root.classList.toggle('dark', dark);
  document.querySelector('meta[name=theme-color]')?.setAttribute('content', dark ? '#19191b' : '#ffffff');
  void getComputedStyle(root).color;
  setTimeout(() => off.remove(), 1);
}

function ThemeToggle() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));
  useEffect(() => {
    const mq = matchMedia('(prefers-color-scheme: dark)');
    const on = e => { let s = null; try { s = localStorage.getItem('db-theme'); } catch {} if (!s) { setTheme(e.matches); setDark(e.matches); } };
    mq.addEventListener('change', on); return () => mq.removeEventListener('change', on);
  }, []);
  const flip = () => { const next = !dark; haptic(); setTheme(next); setDark(next); try { localStorage.setItem('db-theme', next ? 'dark' : 'light'); } catch {} };
  return <Tip content={dark ? 'Light mode' : 'Dark mode'}><Button variant="ghost" size="icon-sm" className="max-lg:size-9" data-track="theme_toggle" onClick={flip} aria-label="Toggle dark mode">{dark ? <SunIcon /> : <MoonIcon />}</Button></Tip>;
}

/* Random task, just for fun (see lib/dice.js). */
const DICE = [Dice1, Dice2, Dice3, Dice4, Dice5, Dice6];

function RandomTask({current}) {
  const [face, setFace] = useState(4), [spin, setSpin] = useState(0);
  const roll = () => {
    const t = nextTask(current); if (!t) return;
    haptic(10); setFace(f => (f + 1 + Math.floor(Math.random() * 5)) % 6); setSpin(n => n + 1);
    go(taskHref(t));
  };
  const Die = DICE[face];
  return <Tip content="Random task"><Button variant="ghost" size="icon-sm" className="max-lg:size-9" data-track="random_task" onClick={roll} aria-label="Open a random task">
    <Die key={spin} className={cn(spin && 'motion-safe:animate-[db-roll_.35s_ease-out]')} />
  </Button></Tip>;
}

/* Selected page: full-strength text and a straight 2px bar resting on the header's bottom border. No box. */
function NavLinks({page, className, bar = 'after:-bottom-[12px]'}) {
  const cur = SECTION[page] || page;
  return (
    <nav aria-label="Main navigation" className={cn('flex items-center gap-1', className)}>
      {NAV.map(([k, h, t]) => { const on = cur === k;
        return <a key={k} href={h} aria-current={on ? 'page' : undefined}
          className={cn('relative inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none',
            "after:absolute after:inset-x-3 after:h-[2px] after:origin-center after:scale-x-0 after:bg-foreground after:transition-transform after:duration-200 after:content-['']", bar, on && 'text-foreground after:scale-x-100')}>
          {t}{k === 'tasks' && <span className={cn('rounded-full bg-muted px-1.5 text-[11px] leading-[18px] tabular-nums text-muted-foreground', on && 'text-foreground')}>{taskOrder().length}</span>}
        </a>; })}
    </nav>
  );
}

/* ---------- Compact screens (phones, tablets in portrait): a top bar and a tab bar, like an app ---------- */

/* What the top bar says on each page, and where "up" goes when there is no in-app page to go back to. */
function barFor(page, id) {
  switch (page) {
    case 'task': return {title: taskName(id), up: ['Tasks', href('tasks')]};
    case 'row': {
      const c = caseMap.get(id); if (!c) return {title: 'Row', up: ['Tasks', href('tasks')]};
      const rows = taskRows(c.task), i = rows.indexOf(c);
      return {title: `Row ${i + 1} of ${rows.length}`, short: `Row ${i + 1}`, up: [taskName(c.task), taskHref(c.task)], prev: rows[i - 1], next: rows[i + 1]};
    }
    case 'model': return {title: M(id).name, up: ['Models', href('models')]};
    case 'compare': return {title: 'Compare', up: ['Models', href('models')]};
    case 'review': return {title: 'Review', up: ['Leaderboard', '/']};
    default: return {title: {home: 'Leaderboard', tasks: 'Tasks', models: 'Models', data: 'Data', methodology: 'Methodology'}[page] || 'Decision Bench'};
  }
}
/* The title of each history entry this visit, so Back can name the page it returns to. */
const titles = new Map();

/* True once the page's own big heading has scrolled up under the bar: the bar then shows the title instead,
   the way a large title collapses into an iOS navigation bar. */
function useTitleTucked(key) {
  const [tucked, setTucked] = useState(false), [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    setTucked(false);
    /* live: an observer can still deliver a queued entry after disconnect(), which would tuck the next page. */
    let io, live = true;
    const t = setTimeout(() => {
      const h = document.querySelector('#main h1'); if (!h) { setTucked(true); return; }
      io = new IntersectionObserver(([e]) => { if (live) setTucked(!e.isIntersecting && e.boundingClientRect.top < 80); }, {rootMargin: '-60px 0px 0px 0px'});
      io.observe(h);
    }, 30);
    return () => { live = false; clearTimeout(t); io?.disconnect(); };
  }, [key]);
  useEffect(() => { const on = () => setScrolled(scrollY > 4); on(); addEventListener('scroll', on, {passive: true}); return () => removeEventListener('scroll', on); }, []);
  return [tucked, scrolled];
}

function TopBar({page, id}) {
  const bar = barFor(page, id), pos = historyPos(), [tucked, scrolled] = useTitleTucked(`${page}/${id}`);
  useEffect(() => { titles.set(pos, bar.short || bar.title); }, [pos, bar.short, bar.title]);
  const before = titles.get(pos - 1), label = before || bar.up?.[0];
  const back = () => { haptic(); if (before) history.back(); else { navHint('pop'); go(bar.up[1]); } };
  const step = (c, k) => { if (!c) return; haptic(); navHint(k); replace(rowHref(c)); };
  return (
    <header className="vt-topbar sticky top-0 z-40 bg-background/80 pt-[env(safe-area-inset-top)] backdrop-blur-xl supports-[backdrop-filter]:bg-background/70 lg:hidden">
      <div className={cn('relative mx-auto flex h-12 max-w-[1240px] items-center px-1.5 transition-shadow duration-200 md:px-4', scrolled && 'shadow-[inset_0_-1px_0_var(--border)]')}>
        {bar.up ? <button type="button" data-track="back" onClick={back} className="relative z-[1] flex h-9 max-w-[45%] min-w-0 cursor-pointer items-center rounded-lg pr-2 text-[15px] text-foreground transition-opacity active:opacity-50" aria-label={`Back to ${label}`}>
          <ChevronLeftIcon className="size-[26px] shrink-0" strokeWidth={2} />
          <span className={cn('truncate transition-opacity duration-200', tucked && 'opacity-0')}>{label}</span>
        </button> : <a href="/" aria-label="Decision Bench home" className="relative z-[1] flex h-9 items-center gap-2 px-2.5 font-mono text-[11px] font-medium tracking-[.08em] uppercase">
          <BrandMark className="h-[15px] w-3 text-brand" /><span className={cn('transition-opacity duration-200', tucked && 'opacity-0')}>Decision Bench</span>
        </a>}
        <div aria-hidden={!tucked} className={cn('pointer-events-none absolute inset-x-24 truncate text-center text-[15px] font-semibold transition-[opacity,transform] duration-200', tucked ? 'opacity-100' : 'translate-y-1.5 opacity-0')}>{bar.title}</div>
        <div className="relative z-[1] ml-auto flex items-center">
          {page === 'row' ? <>
            <Button variant="ghost" size="icon" aria-label="Previous row" disabled={!bar.prev} data-track="previous_row" onClick={() => step(bar.prev, 'prev')}><ChevronUpIcon className="size-5" /></Button>
            <Button variant="ghost" size="icon" aria-label="Next row" disabled={!bar.next} data-track="next_row" onClick={() => step(bar.next, 'next')}><ChevronDownIcon className="size-5" /></Button>
          </> : <><RandomTask current={page === 'task' ? id : ''} /><ThemeToggle /></>}
        </div>
      </div>
    </header>
  );
}

/* The tab bar floats above the page and slips away while you read downwards; any scroll up brings it back. */
function useTucked() {
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    let last = scrollY, run = 0;
    const on = () => {
      const y = scrollY, d = y - last; last = y;
      if (y < 80 || innerHeight + y >= document.documentElement.scrollHeight - 60) { run = 0; setHidden(false); return; }
      run = Math.sign(d) === Math.sign(run) ? run + d : d;
      if (run > 48) setHidden(true); else if (run < -24) setHidden(false);
    };
    const show = () => setHidden(false);
    addEventListener('scroll', on, {passive: true}); addEventListener('popstate', show); addEventListener('db:navigate', show);
    return () => { removeEventListener('scroll', on); removeEventListener('popstate', show); removeEventListener('db:navigate', show); };
  }, []);
  return hidden;
}

const TABS = [['home', '/', 'Leaderboard', TrophyIcon], ['tasks', '/tasks', 'Tasks', ListChecksIcon], ['models', '/models', 'Models', BoxesIcon], ['data', '/data', 'Data', DatabaseIcon], ['methodology', '/methodology', 'Methodology', BookOpenIcon]];
export function TabBar({page}) {
  const hidden = useTucked(), cur = SECTION[page] || page, i = TABS.findIndex(t => t[0] === cur);
  if (page === 'review') return null;
  /* Tapping the tab you are on goes to its top, or back to its first page from a page inside it. */
  const tap = (e, k) => {
    haptic();
    if (k === page) { e.preventDefault(); scrollTo({top: 0, behavior: 'smooth'}); }
    else navHint(k === cur ? 'pop' : 'tab');
  };
  return (
    <nav aria-label="Main navigation" className={cn('vt-tabbar pointer-events-none fixed inset-x-0 bottom-0 z-40 px-3 pb-[max(env(safe-area-inset-bottom),10px)] transition-transform duration-300 ease-[cubic-bezier(.32,.72,0,1)] motion-safe:animate-tabbar-in lg:hidden', hidden && 'translate-y-[calc(100%+6px)]')}>
      <div className="pointer-events-auto relative mx-auto grid max-w-md grid-cols-5 rounded-[26px] border bg-background/90 p-1 shadow-[0_10px_34px_-10px_rgb(0_0_0/.28)] backdrop-blur-xl backdrop-saturate-150 select-none supports-[backdrop-filter]:bg-background/75 dark:shadow-[0_10px_34px_-10px_rgb(0_0_0/.6)]">
        <i aria-hidden="true" className={cn('absolute inset-y-1 left-1 w-[calc((100%-8px)/5)] rounded-[22px] bg-foreground/[.07] transition-[transform,opacity] duration-400 ease-[cubic-bezier(.3,1.12,.5,1)] dark:bg-foreground/[.1]', i < 0 && 'opacity-0')} style={{transform: `translateX(${Math.max(0, i) * 100}%)`}} />
        {TABS.map(([k, h, t, Icon], j) => { const on = j === i;
          return <a key={k} href={h} onClick={e => tap(e, k)} aria-current={on ? 'page' : undefined} className={cn('relative flex h-[50px] flex-col items-center justify-center gap-[3px] rounded-[22px] text-[10px] font-medium tracking-[.01em] text-muted-foreground max-[360px]:text-[9px] max-[360px]:tracking-normal transition-[color,transform] duration-150 active:scale-90', on && 'text-foreground')}>
            <Icon key={on ? 'on' : 'off'} className={cn('size-[21px]', on && 'motion-safe:animate-tab-pop')} strokeWidth={on ? 2.2 : 1.7} />
            <span>{t}</span>
          </a>; })}
      </div>
    </nav>
  );
}

export function Header({page, id}) {
  return <>
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/70 max-lg:hidden">
      <div className="mx-auto flex h-14 max-w-[1240px] items-center gap-6 px-4 md:px-8">
        <a href="/" className="flex shrink-0 items-center gap-2 font-mono text-xs font-medium tracking-[.08em] uppercase" aria-label="Decision Bench home">
          <BrandMark className="h-[15px] w-3 text-brand" /><span className="leading-none [text-box:trim-both_cap_alphabetic]">Decision Bench</span>
        </a>
        <NavLinks page={page} />
        <div className="ml-auto flex items-center gap-1">
          <RandomTask current={page === 'task' ? id : ''} />
          {repoOk() && <Tip content="Source on GitHub"><Button variant="ghost" size="icon-sm" asChild><a href={REPO} target="_blank" rel="noopener" aria-label="GitHub"><GitHubIcon className="size-4" /></a></Button></Tip>}
          <ThemeToggle />
        </div>
      </div>
    </header>
    <TopBar page={page} id={id} />
  </>;
}

export function Footer() {
  const sha = (data?.corpus_sha256 || '').slice(0, 12);
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-[1240px] flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-6 text-xs text-muted-foreground max-lg:pb-[calc(env(safe-area-inset-bottom)+96px)] md:px-8">
        <span>Decision Bench {man().version} · corpus <code>{sha}</code> · built {data?.generated_at ? new Date(data.generated_at).toLocaleDateString() : ''}</span>
        <span className="flex flex-wrap gap-x-4 gap-y-1">
          <span>Code MIT · rows keep their <a href="/data" className="underline-offset-4 hover:text-foreground hover:underline">source licences</a></span>
          <a href="https://x.com/rohanatlan/article/2103188107143307541" target="_blank" rel="noopener noreferrer" className="hover:text-foreground" title="Putting Jev to the test with Decision Bench">Jev benchmark article</a>
          <a href="/review" className="hover:text-foreground">Review mode</a>
          {HUGGING_FACE_DATASET && <a href={HUGGING_FACE_DATASET} target="_blank" rel="noopener noreferrer" className="hover:text-foreground">Hugging Face</a>}
          {repoOk() && <a href={REPO} target="_blank" rel="noopener" className="hover:text-foreground lg:hidden">GitHub</a>}
          <a href="#" data-analytics-preferences className="hover:text-foreground">Analytics preferences</a>
        </span>
      </div>
    </footer>
  );
}
