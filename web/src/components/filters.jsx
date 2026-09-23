/* Filter controls bound to the URL: use case, input modality, which models are shown, search. */
import {startTransition, useEffect, useRef, useState} from 'react';
import {ChevronDownIcon, SearchIcon} from 'lucide-react';
import {categoryOrder, catInfo, RUNS, keyOf} from '@/lib/bench';
import {withQ, go, replace} from '@/lib/route';
import {DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuSeparator, DropdownMenuTrigger} from '@/components/ui/dropdown-menu';
import {Tabs, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {ModelName} from '@/components/common';
import {cn} from '@/lib/utils';

/* Looks like a select, behaves like a non-modal menu (see ui/dropdown-menu), so opening it costs nothing. */
export function UseCaseSelect({route, className}) {
  const cur = route.q.get('category') || '';
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild><Button variant="outline" className={cn('justify-between font-normal', className)} aria-label="Use case">{cur ? catInfo(cur).name : 'All use cases'}<ChevronDownIcon className="opacity-50" /></Button></DropdownMenuTrigger>
      <DropdownMenuContent className="min-w-(--radix-dropdown-menu-trigger-width)">
        <DropdownMenuRadioGroup value={cur || 'all'} onValueChange={v => go(withQ(route, {category: v === 'all' ? '' : v}))}>
          <DropdownMenuRadioItem value="all">All use cases</DropdownMenuRadioItem>
          <DropdownMenuSeparator />
          {categoryOrder().map(k => <DropdownMenuRadioItem key={k} value={k}>{catInfo(k).name}</DropdownMenuRadioItem>)}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function ModalityTabs({route}) {
  return (
    <Tabs value={route.q.get('modality') || 'all'} onValueChange={v => go(withQ(route, {modality: v === 'all' ? '' : v}))}>
      <TabsList aria-label="Input"><TabsTrigger value="all">All inputs</TabsTrigger><TabsTrigger value="text">Text</TabsTrigger><TabsTrigger value="image">Image</TabsTrigger></TabsList>
    </Tabs>
  );
}

export const selectedRuns = route => { const sel = route.q.get('models'); if (!sel) return RUNS; const set = new Set(sel.split(',')); return RUNS.filter(r => set.has(keyOf(r))); };

/* Which models the leaderboard shows: one "All models" row that selects or clears everything (and shows a dash
   for a partial selection), then one checkbox per model. The ticks update at once; the page follows in a transition. */
export function ModelPicker({route}) {
  const fromUrl = selectedRuns(route).map(keyOf), [keys, setKeys] = useState(fromUrl), all = RUNS.map(keyOf);
  const url = route.q.get('models') || '';
  useEffect(() => { setKeys(selectedRuns(route).map(keyOf)); }, [url]); // eslint-disable-line react-hooks/exhaustive-deps
  const set = next => { setKeys(next); startTransition(() => go(withQ(route, {models: next.length === all.length ? '' : next.length ? next.join(',') : 'none'}))); };
  const n = keys.length, allOn = n === all.length ? true : n ? 'indeterminate' : false;
  const keep = e => e.preventDefault();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild><Button variant="outline" className="font-normal">Models <span className="text-muted-foreground tabular-nums">{n === all.length ? 'All' : `${n} of ${all.length}`}</span><ChevronDownIcon className="opacity-50" /></Button></DropdownMenuTrigger>
      <DropdownMenuContent className="w-72">
        <DropdownMenuCheckboxItem checked={allOn} onSelect={keep} onCheckedChange={() => set(allOn === true ? [] : all)} className="font-medium">All models<span className="ml-auto text-xs font-normal text-muted-foreground tabular-nums">{n}/{all.length}</span></DropdownMenuCheckboxItem>
        <DropdownMenuSeparator />
        <div className="max-h-80 overflow-y-auto">
          {RUNS.map(r => { const k = keyOf(r), on = keys.includes(k);
            return <DropdownMenuCheckboxItem key={k} checked={on} onSelect={keep} onCheckedChange={v => set(all.filter(x => x === k ? v : keys.includes(x)))}><ModelName k={k} link={false} /></DropdownMenuCheckboxItem>; })}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/* Search box that writes ?q= without adding history entries. */
export function SearchBox({route, placeholder, className}) {
  const [v, setV] = useState(route.q.get('q') || ''), t = useRef();
  useEffect(() => { setV(route.q.get('q') || ''); }, [route.page]);
  const on = e => { const s = e.target.value; setV(s); clearTimeout(t.current); t.current = setTimeout(() => replace(withQ(route, {q: s})), 150); };
  return (
    <label className={`relative block ${className || ''}`}>
      <SearchIcon className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input type="search" value={v} onChange={on} placeholder={placeholder} aria-label={placeholder} className="pl-9" />
    </label>
  );
}
