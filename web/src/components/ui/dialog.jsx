import {useEffect, useRef} from 'react';
import {Dialog as DialogPrimitive} from 'radix-ui';
import {XIcon} from 'lucide-react';
import {cn} from '@/lib/utils';
import {haptic, usePhone} from '@/lib/device';

export const Dialog = p => <DialogPrimitive.Root data-slot="dialog" {...p} />;
export const DialogTrigger = p => <DialogPrimitive.Trigger data-slot="dialog-trigger" {...p} />;
export const DialogClose = p => <DialogPrimitive.Close data-slot="dialog-close" {...p} />;
const Overlay = ({className, ...p}) => <DialogPrimitive.Overlay data-slot="dialog-overlay" className={cn('fixed inset-0 z-50 bg-black/50 backdrop-blur-[2px] data-[state=open]:animate-fade-in', className)} {...p} />;
const CloseX = ({className}) => <DialogPrimitive.Close className={cn('absolute top-4 right-4 cursor-pointer rounded-md p-1 text-muted-foreground opacity-80 transition hover:bg-accent hover:text-foreground hover:opacity-100 focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none', className)}><XIcon className="size-4" /><span className="sr-only">Close</span></DialogPrimitive.Close>;

/* On phones every dialog and side sheet is a sheet that rises from the bottom. Drag the handle down to let it go:
   past 120px, or a quick flick, closes it; anything less springs back. */
function Grab() {
  const ref = useRef(null), close = useRef(null);
  useEffect(() => {
    const el = ref.current?.closest('[data-slot=phone-sheet]'); if (!el) return;
    let s = null;
    const down = e => { if (!e.target.closest('[data-grab]') || e.button > 0) return; s = {y0: e.clientY, y: e.clientY, t: performance.now(), dy: 0, v: 0}; try { el.setPointerCapture(e.pointerId); } catch {} el.style.transition = 'none'; };
    const move = e => {
      if (!s) return; const now = performance.now(), dy = e.clientY - s.y0;
      s.v = (e.clientY - s.y) / Math.max(1, now - s.t); s.y = e.clientY; s.t = now;
      s.dy = dy > 0 ? dy : -Math.sqrt(-dy) * 2; el.style.transform = `translateY(${s.dy}px)`;
    };
    const up = () => {
      if (!s) return; const {dy, v} = s; s = null;
      if (dy > 120 || (dy > 24 && v > .45)) { el.style.transition = ''; haptic(); close.current?.click(); return; }
      el.style.transition = 'transform .38s cubic-bezier(.32,.72,0,1)'; el.style.transform = '';
    };
    el.addEventListener('pointerdown', down); el.addEventListener('pointermove', move); el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
    return () => { el.removeEventListener('pointerdown', down); el.removeEventListener('pointermove', move); el.removeEventListener('pointerup', up); el.removeEventListener('pointercancel', up); };
  }, []);
  return <>
    <div ref={ref} data-grab aria-hidden="true" className="flex shrink-0 cursor-grab touch-none justify-center pt-2.5 pb-2"><span className="h-[5px] w-10 rounded-full bg-foreground/20" /></div>
    <DialogPrimitive.Close ref={close} tabIndex={-1} aria-hidden="true" className="hidden" />
  </>;
}
function PhoneSheet({className, children, ...p}) {
  return (
    <DialogPrimitive.Portal>
      <Overlay className="bg-black/40 backdrop-blur-[1px] data-[state=closed]:animate-fade-out" />
      <DialogPrimitive.Content data-slot="phone-sheet" className={cn('fixed inset-x-0 bottom-0 z-50 flex max-h-[88dvh] flex-col rounded-t-[22px] border-t bg-background pb-[env(safe-area-inset-bottom)] shadow-[0_-12px_40px_-12px_rgb(0_0_0/.3)] outline-none data-[state=closed]:animate-sheet-down data-[state=open]:animate-sheet-up', className)} {...p}>
        <Grab />
        {children}
        <CloseX className="top-3 right-3 p-1.5" />
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DialogContent({className, children, showClose = true, ...p}) {
  const phone = usePhone();
  if (phone) return <PhoneSheet {...p}><div className="grid min-h-0 gap-4 overflow-y-auto overscroll-contain px-5 pt-1 pb-5">{children}</div></PhoneSheet>;
  return (
    <DialogPrimitive.Portal>
      <Overlay />
      <DialogPrimitive.Content data-slot="dialog-content" className={cn('fixed top-1/2 left-1/2 z-50 grid max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 overflow-y-auto rounded-xl border bg-background p-6 shadow-lg outline-none data-[state=open]:animate-dialog-in', className)} {...p}>
        {children}
        {showClose && <CloseX />}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
export const DialogHeader = ({className, ...p}) => <div data-slot="dialog-header" className={cn('flex flex-col gap-1.5 pr-8', className)} {...p} />;
export const DialogFooter = ({className, ...p}) => <div data-slot="dialog-footer" className={cn('flex flex-col-reverse gap-2 sm:flex-row sm:justify-end', className)} {...p} />;
export const DialogTitle = ({className, ...p}) => <DialogPrimitive.Title data-slot="dialog-title" className={cn('text-lg leading-snug font-semibold tracking-tight', className)} {...p} />;
export const DialogDescription = ({className, ...p}) => <DialogPrimitive.Description data-slot="dialog-description" className={cn('text-sm text-muted-foreground', className)} {...p} />;

/* Sheet: the same primitive docked to the right edge; on phones, a full-height bottom sheet. */
export function SheetContent({className, children, ...p}) {
  const phone = usePhone();
  if (phone) return <PhoneSheet className="h-[88dvh]" {...p}>{children}</PhoneSheet>;
  return (
    <DialogPrimitive.Portal>
      <Overlay />
      <DialogPrimitive.Content data-slot="sheet-content" className={cn('fixed inset-y-0 right-0 z-50 flex h-full w-full flex-col border-l bg-background shadow-lg outline-none data-[state=open]:animate-sheet-in sm:max-w-xl', className)} {...p}>
        {children}
        <CloseX />
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

/* A bottom sheet for pickers on phones: a title, a scrolling list, and an optional footer. */
export function BottomSheet({open, onOpenChange, title, description, footer, children}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <PhoneSheet>
        <div className="shrink-0 px-5 pb-2">
          <DialogTitle className="pr-8 text-[17px]">{title}</DialogTitle>
          {description ? <DialogDescription className="mt-0.5 text-[13px]">{description}</DialogDescription> : <DialogPrimitive.Description className="sr-only">{title}</DialogPrimitive.Description>}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-2 pb-3">{children}</div>
        {footer && <div className="shrink-0 border-t px-4 pt-3 pb-3">{footer}</div>}
      </PhoneSheet>
    </DialogPrimitive.Root>
  );
}
/* One tappable line inside a BottomSheet. */
export const SheetOption = ({selected, onClick, children, sub, lead, className, ...p}) => (
  <button type="button" aria-pressed={p.role ? undefined : !!selected} onClick={onClick} {...p} className={cn('flex min-h-12 w-full cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-[background-color,transform] duration-150 active:scale-[.985] active:bg-muted', selected && 'bg-muted/70', className)}>
    {lead}
    <span className="min-w-0 flex-1"><span className="block text-[15px] font-medium">{children}</span>{sub && <span className="mt-0.5 block text-[13px] leading-snug text-muted-foreground">{sub}</span>}</span>
  </button>
);
