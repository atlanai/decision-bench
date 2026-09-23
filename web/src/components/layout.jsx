import {useEffect, useState} from 'react';
import {Dice1, Dice2, Dice3, Dice4, Dice5, Dice6, MoonIcon, SunIcon} from 'lucide-react';
import {man, data, taskOrder, REPO, repoOk} from '@/lib/bench';
import {go, taskHref} from '@/lib/route';
import {cn} from '@/lib/utils';
import {BrandMark, GitHubIcon} from '@/components/icons';
import {Button} from '@/components/ui/button';
import {Tip} from '@/components/ui/tooltip';

const NAV = [['home', '#/', 'Leaderboard'], ['tasks', '#/tasks', 'Tasks'], ['models', '#/models', 'Models'], ['data', '#/data', 'Data'], ['methodology', '#/methodology', 'Methodology']];
const SECTION = {task: 'tasks', row: 'tasks', review: 'tasks', model: 'models', compare: 'models'};

/* Switch themes with every transition off for one frame. Otherwise each element with transition-colors animates
   from the old palette to the new one, thousands at once, and the blurred sticky header can stay stuck halfway
   until something repaints it. */
function setTheme(dark) {
  const root = document.documentElement, off = document.createElement('style');
  off.textContent = '*,*::before,*::after{transition:none!important}';
  document.head.appendChild(off);
  root.classList.toggle('dark', dark);
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
  const flip = () => { const next = !dark; setTheme(next); setDark(next); try { localStorage.setItem('db-theme', next ? 'dark' : 'light'); } catch {} };
  return <Tip content={dark ? 'Light mode' : 'Dark mode'}><Button variant="ghost" size="icon-sm" data-track="theme_toggle" onClick={flip} aria-label="Toggle dark mode">{dark ? <SunIcon /> : <MoonIcon />}</Button></Tip>;
}

/* Random task, just for fun. A shuffled bag, so repeated rolls visit every task before any comes round again. */
const DICE = [Dice1, Dice2, Dice3, Dice4, Dice5, Dice6];
let bag = [];
function nextTask(current) {
  const all = taskOrder();
  if (all.length < 2) return all[0];
  if (!bag.length) { bag = [...all]; for (let i = bag.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [bag[i], bag[j]] = [bag[j], bag[i]]; } }
  if (bag[bag.length - 1] === current) bag.unshift(bag.pop());
  return bag.pop();
}

function RandomTask({current}) {
  const [face, setFace] = useState(4), [spin, setSpin] = useState(0);
  const roll = () => {
    const t = nextTask(current); if (!t) return;
    setFace(f => (f + 1 + Math.floor(Math.random() * 5)) % 6); setSpin(n => n + 1);
    go(taskHref(t));
  };
  const Die = DICE[face];
  return <Tip content="Random task"><Button variant="ghost" size="icon-sm" data-track="random_task" onClick={roll} aria-label="Open a random task">
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

export function Header({page, id}) {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-14 max-w-[1240px] items-center gap-6 px-4 md:px-8">
        <a href="#/" className="flex shrink-0 items-center gap-2 font-mono text-xs font-medium tracking-[.08em] uppercase" aria-label="Decision Bench home">
          <BrandMark className="h-[15px] w-3 text-brand" />Decision Bench
        </a>
        <NavLinks page={page} className="hidden md:flex" />
        <div className="ml-auto flex items-center gap-1">
          <RandomTask current={page === 'task' ? id : ''} />
          {repoOk() && <Tip content="Source on GitHub"><Button variant="ghost" size="icon-sm" asChild><a href={REPO} target="_blank" rel="noopener" aria-label="GitHub"><GitHubIcon className="size-4" /></a></Button></Tip>}
          <ThemeToggle />
        </div>
      </div>
      <NavLinks page={page} bar="after:-bottom-[8px]" className="mx-auto max-w-[1240px] overflow-x-auto px-3 pb-2 [scrollbar-width:none] md:hidden" />
    </header>
  );
}

export function Footer() {
  const sha = (data?.corpus_sha256 || '').slice(0, 12);
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-[1240px] flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-6 text-xs text-muted-foreground md:px-8">
        <span>Decision Bench {man().version} · corpus <code>{sha}</code> · built {data?.generated_at ? new Date(data.generated_at).toLocaleDateString() : ''}</span>
        <span className="flex flex-wrap gap-x-4 gap-y-1">
          <span>Code MIT · rows keep their <a href="#/data" className="underline-offset-4 hover:text-foreground hover:underline">source licences</a></span>
          <a href="#/review" className="hover:text-foreground">Review mode</a>
          <a href="privacy.html" className="hover:text-foreground">Privacy</a>
          <a href="#" data-analytics-preferences className="hover:text-foreground">Analytics preferences</a>
        </span>
      </div>
    </footer>
  );
}
