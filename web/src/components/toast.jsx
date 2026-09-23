/* A one-line message that rises above the tab bar and leaves on its own: toast('Copied'), or with an action,
   toast('Last row', {action: ['Random task', fn]}). One at a time; a new one replaces the last. */
import {useEffect, useState} from 'react';
import {cn} from '@/lib/utils';

let push = null;
export const toast = (text, opts = {}) => push?.({text, ...opts, key: Date.now() + Math.random()});

export function Toaster() {
  const [t, setT] = useState(null);
  useEffect(() => { push = setT; return () => { push = null; }; }, []);
  useEffect(() => { if (!t) return; const id = setTimeout(() => setT(null), t.ms || 3200); return () => clearTimeout(id); }, [t]);
  if (!t) return null;
  const [label, run] = t.action || [];
  return (
    <div role="status" aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-[calc(env(safe-area-inset-bottom)+92px)] z-[70] flex justify-center px-4 lg:bottom-6">
      <div key={t.key} className={cn('pointer-events-auto flex max-w-md items-center gap-3 rounded-full bg-foreground py-2 pr-2 pl-4 text-[13px] text-background shadow-lg motion-safe:animate-toast-in', !run && 'pr-4')}>
        {t.icon && <t.icon className="size-4 shrink-0 opacity-80" />}
        <span className="min-w-0">{t.text}</span>
        {run && <button type="button" onClick={() => { setT(null); run(); }} className="shrink-0 cursor-pointer rounded-full bg-background/15 px-3 py-1 font-medium transition-colors hover:bg-background/25 active:scale-95">{label}</button>}
      </div>
    </div>
  );
}
