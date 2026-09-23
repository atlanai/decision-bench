/* Filter controls bound to the URL: use case, input modality, which models are shown, search. */
import {useEffect, useRef, useState} from 'react';
import {ChevronDownIcon, SearchIcon} from 'lucide-react';
import {categoryOrder, catInfo, RUNS, keyOf} from '@/lib/bench';
import {withQ, go, replace} from '@/lib/route';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SelectSeparator} from '@/components/ui/select';
import {Tabs, TabsList, TabsTrigger} from '@/components/ui/tabs';
import {Popover, PopoverContent, PopoverTrigger} from '@/components/ui/popover';
import {Checkbox} from '@/components/ui/checkbox';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {ModelName} from '@/components/common';

export function UseCaseSelect({route, className}) {
  const cur = route.q.get('category') || 'all';
  return (
    <Select value={cur} onValueChange={v => go(withQ(route, {category: v === 'all' ? '' : v}))}>
      <SelectTrigger className={className} aria-label="Use case"><SelectValue /></SelectTrigger>
      <SelectContent>
        <SelectItem value="all">All use cases</SelectItem>
        <SelectSeparator />
        {categoryOrder().map(k => <SelectItem key={k} value={k}>{catInfo(k).name}</SelectItem>)}
      </SelectContent>
    </Select>
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

export function ModelPicker({route}) {
  const sel = selectedRuns(route), n = sel.length;
  const set = keys => go(withQ(route, {models: keys.length === RUNS.length ? '' : keys.length ? keys.join(',') : 'none'}));
  const toggle = (k, on) => { const s = new Set(sel.map(keyOf)); on ? s.add(k) : s.delete(k); set(RUNS.map(keyOf).filter(x => s.has(x))); };
  return (
    <Popover>
      <PopoverTrigger asChild><Button variant="outline">Models <span className="text-muted-foreground tabular-nums">{n}{n < RUNS.length ? ` of ${RUNS.length}` : ''}</span><ChevronDownIcon className="opacity-50" /></Button></PopoverTrigger>
      <PopoverContent align="start" className="w-72 p-1">
        <div className="flex gap-1 border-b p-1 pb-2">
          <Button size="xs" variant="ghost" onClick={() => set(RUNS.map(keyOf))}>Select all</Button>
          <Button size="xs" variant="ghost" onClick={() => set([])}>Clear</Button>
        </div>
        <div className="max-h-80 overflow-y-auto py-1">
          {RUNS.map(r => { const k = keyOf(r), on = sel.includes(r);
            return <label key={k} className="flex cursor-pointer items-center gap-3 rounded-sm px-2 py-1.5 text-sm hover:bg-accent">
              <Checkbox checked={on} onCheckedChange={v => toggle(k, !!v)} /><ModelName k={k} link={false} />
            </label>; })}
        </div>
      </PopoverContent>
    </Popover>
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
