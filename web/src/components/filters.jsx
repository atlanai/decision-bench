import {track} from '@/lib/analytics';
/* Filter controls bound to the URL: use case, input modality, which models are shown, search. */
import {startTransition, useEffect, useRef, useState} from 'react';
import {CheckIcon, ChevronDownIcon, MinusIcon, SearchIcon} from 'lucide-react';
import {categoryOrder, catInfo, RUNS, keyOf, allCases, fullName} from '@/lib/bench';
import {usePhone, haptic} from '@/lib/device';
import {plural} from '@/lib/format';
import {withQ, go, replace} from '@/lib/route';
import {DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuSeparator, DropdownMenuTrigger} from '@/components/ui/dropdown-menu';
import {Tabs, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {ModelName, Logo} from '@/components/common';
import {BottomSheet, SheetOption} from '@/components/ui/dialog';
import {cn} from '@/lib/utils';

/* The marks in the phone sheets: a round tick for one-of, a square box for many. */
const Tick = ({on}) => <span className={cn('grid size-5 shrink-0 place-items-center rounded-full transition-colors', on ? 'bg-foreground text-background' : 'border border-foreground/20')}>{on && <CheckIcon className="size-3" strokeWidth={3} />}</span>;
const Box = ({on}) => <span className={cn('grid size-5 shrink-0 place-items-center rounded-md border transition-colors', on ? 'border-foreground bg-foreground text-background' : 'border-foreground/25')}>{on === 'indeterminate' ? <MinusIcon className="size-3" strokeWidth={3} /> : on && <CheckIcon className="size-3" strokeWidth={3} />}</span>;
/* Looks like a select, behaves like a non-modal menu (see ui/dropdown-menu), so opening it costs nothing.
   On phones it opens a bottom sheet with a line per use case. */
export function UseCaseSelect({route, className}) {
  const cur = route.q.get('category') || '', phone = usePhone(), [open, setOpen] = useState(false);
  if (phone) {
    const pick = v => { haptic(); setOpen(false); go(withQ(route, {category: v})); };
    return <>
      <Button variant="outline" className={cn('justify-between rounded-full font-normal', className)} data-track="use_case_menu" aria-label="Use case" onClick={() => setOpen(true)}>{cur ? catInfo(cur).name : 'All use cases'}<ChevronDownIcon className="opacity-50" /></Button>
      <BottomSheet open={open} onOpenChange={setOpen} title="Pick a use case" description="Every table and chart on the page follows.">
        <SheetOption selected={!cur} onClick={() => pick('')} lead={<Tick on={!cur} />} sub={plural(allCases.length, 'row')}>All use cases</SheetOption>
        {categoryOrder().map(k => <SheetOption key={k} selected={cur === k} onClick={() => pick(k)} lead={<Tick on={cur === k} />} sub={catInfo(k).description}>{catInfo(k).name}</SheetOption>)}
      </BottomSheet>
    </>;
  }
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild><Button variant="outline" className={cn('justify-between font-normal', className)} data-track="use_case_menu" aria-label="Use case">{cur ? catInfo(cur).name : 'All use cases'}<ChevronDownIcon className="opacity-50" /></Button></DropdownMenuTrigger>
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
  const url = route.q.get('models') || '', phone = usePhone(), [open, setOpen] = useState(false);
  useEffect(() => { setKeys(selectedRuns(route).map(keyOf)); }, [url]); // eslint-disable-line react-hooks/exhaustive-deps
  const set = next => { track('model_selection', {selected_model_count: next.length}); setKeys(next); startTransition(() => go(withQ(route, {models: next.length === all.length ? '' : next.length ? next.join(',') : 'none'}))); };
  const n = keys.length, allOn = n === all.length ? true : n ? 'indeterminate' : false;
  const keep = e => e.preventDefault();
  if (phone) {
    return <>
      <Button variant="outline" data-track="model_picker" className="rounded-full font-normal" onClick={() => setOpen(true)}>Models <span className="text-muted-foreground tabular-nums">{n === all.length ? 'All' : `${n} of ${all.length}`}</span><ChevronDownIcon className="opacity-50" /></Button>
      <BottomSheet open={open} onOpenChange={setOpen} title="Models to show" description={n ? `${n} of ${all.length} on the leaderboard.` : 'None picked yet. Tick at least one.'}
        footer={<Button className="h-11 w-full rounded-xl text-[15px]" onClick={() => setOpen(false)}>Done</Button>}>
        <SheetOption role="checkbox" aria-checked={allOn === 'indeterminate' ? 'mixed' : allOn} onClick={() => { haptic(); set(allOn === true ? [] : all); }} lead={<Box on={allOn} />}>All models</SheetOption>
        <div className="mx-3 my-1 h-px bg-border" />
        {RUNS.map(r => { const k = keyOf(r), on = keys.includes(k);
          return <SheetOption key={k} role="checkbox" aria-checked={on} onClick={() => { haptic(); set(all.filter(x => x === k ? !on : keys.includes(x))); }} lead={<><Box on={on} /><Logo k={k} size={20} /></>}>{fullName(k)}</SheetOption>; })}
      </BottomSheet>
    </>;
  }
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild><Button variant="outline" data-track="model_picker" className="font-normal">Models <span className="text-muted-foreground tabular-nums">{n === all.length ? 'All' : `${n} of ${all.length}`}</span><ChevronDownIcon className="opacity-50" /></Button></DropdownMenuTrigger>
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
