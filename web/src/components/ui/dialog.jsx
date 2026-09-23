import {Dialog as DialogPrimitive} from 'radix-ui';
import {XIcon} from 'lucide-react';
import {cn} from '@/lib/utils';

export const Dialog = p => <DialogPrimitive.Root data-slot="dialog" {...p} />;
export const DialogTrigger = p => <DialogPrimitive.Trigger data-slot="dialog-trigger" {...p} />;
export const DialogClose = p => <DialogPrimitive.Close data-slot="dialog-close" {...p} />;
const Overlay = ({className, ...p}) => <DialogPrimitive.Overlay data-slot="dialog-overlay" className={cn('fixed inset-0 z-50 bg-black/50 backdrop-blur-[2px] data-[state=open]:animate-fade-in', className)} {...p} />;
export function DialogContent({className, children, showClose = true, ...p}) {
  return (
    <DialogPrimitive.Portal>
      <Overlay />
      <DialogPrimitive.Content data-slot="dialog-content" className={cn('fixed top-1/2 left-1/2 z-50 grid max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 overflow-y-auto rounded-xl border bg-background p-6 shadow-lg outline-none data-[state=open]:animate-dialog-in', className)} {...p}>
        {children}
        {showClose && <DialogPrimitive.Close className="absolute top-4 right-4 cursor-pointer rounded-md p-1 text-muted-foreground opacity-80 transition hover:bg-accent hover:text-foreground hover:opacity-100 focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"><XIcon className="size-4" /><span className="sr-only">Close</span></DialogPrimitive.Close>}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
export const DialogHeader = ({className, ...p}) => <div data-slot="dialog-header" className={cn('flex flex-col gap-1.5 pr-8', className)} {...p} />;
export const DialogFooter = ({className, ...p}) => <div data-slot="dialog-footer" className={cn('flex flex-col-reverse gap-2 sm:flex-row sm:justify-end', className)} {...p} />;
export const DialogTitle = ({className, ...p}) => <DialogPrimitive.Title data-slot="dialog-title" className={cn('text-lg leading-snug font-semibold tracking-tight', className)} {...p} />;
export const DialogDescription = ({className, ...p}) => <DialogPrimitive.Description data-slot="dialog-description" className={cn('text-sm text-muted-foreground', className)} {...p} />;

/* Sheet: the same primitive docked to the right edge. */
export function SheetContent({className, children, ...p}) {
  return (
    <DialogPrimitive.Portal>
      <Overlay />
      <DialogPrimitive.Content data-slot="sheet-content" className={cn('fixed inset-y-0 right-0 z-50 flex h-full w-full flex-col border-l bg-background shadow-lg outline-none data-[state=open]:animate-sheet-in sm:max-w-xl', className)} {...p}>
        {children}
        <DialogPrimitive.Close className="absolute top-4 right-4 cursor-pointer rounded-md p-1 text-muted-foreground opacity-80 transition hover:bg-accent hover:text-foreground hover:opacity-100 focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"><XIcon className="size-4" /><span className="sr-only">Close</span></DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
