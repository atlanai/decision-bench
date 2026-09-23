import {useEffect, useState} from 'react';
import {MoonIcon, SunIcon} from 'lucide-react';
import {man, data, taskOrder, REPO, repoOk} from '@/lib/bench';
import {cn} from '@/lib/utils';
import {BrandMark, GitHubIcon} from '@/components/icons';
import {Button} from '@/components/ui/button';
import {Tip} from '@/components/ui/tooltip';

const NAV = [['home', '#/', 'Leaderboard'], ['tasks', '#/tasks', 'Tasks'], ['models', '#/models', 'Models'], ['data', '#/data', 'Data'], ['methodology', '#/methodology', 'Methodology']];
const SECTION = {task: 'tasks', row: 'tasks', review: 'tasks', model: 'models', compare: 'models'};

function ThemeToggle() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));
  useEffect(() => {
    const mq = matchMedia('(prefers-color-scheme: dark)');
    const on = e => { let s = null; try { s = localStorage.getItem('db-theme'); } catch {} if (!s) { document.documentElement.classList.toggle('dark', e.matches); setDark(e.matches); } };
    mq.addEventListener('change', on); return () => mq.removeEventListener('change', on);
  }, []);
  const flip = () => { const next = !dark; document.documentElement.classList.toggle('dark', next); setDark(next); try { localStorage.setItem('db-theme', next ? 'dark' : 'light'); } catch {} };
  return <Tip content={dark ? 'Light mode' : 'Dark mode'}><Button variant="ghost" size="icon-sm" onClick={flip} aria-label="Toggle dark mode">{dark ? <SunIcon /> : <MoonIcon />}</Button></Tip>;
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

export function Header({page}) {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-14 max-w-[1240px] items-center gap-6 px-4 md:px-8">
        <a href="#/" className="flex shrink-0 items-center gap-2 font-mono text-xs font-medium tracking-[.08em] uppercase" aria-label="Decision Bench home">
          <BrandMark className="h-[15px] w-3 text-brand" />Decision Bench
        </a>
        <NavLinks page={page} className="hidden md:flex" />
        <div className="ml-auto flex items-center gap-1">
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
