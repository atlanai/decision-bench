/* Phone lists, in place of wide tables: one grouped card, one tappable line per item, the way a native settings or
   inbox list reads. Lines press in slightly under a finger. */
import {ChevronRightIcon} from 'lucide-react';
import {cn} from '@/lib/utils';

export const List = ({children, className}) => <ul className={cn('overflow-hidden rounded-2xl border bg-card shadow-xs [&>li+li]:border-t', className)}>{children}</ul>;

export const ListHead = ({children, aside, onClick, open, className}) => {
  const inner = <>{children}{aside != null && <span className="ml-auto flex items-center gap-2 font-normal text-muted-foreground tabular-nums">{aside}</span>}</>;
  const cls = cn('flex w-full items-center gap-2 bg-muted/50 px-4 py-2.5 text-left text-[13px] font-semibold', className);
  return <li>{onClick ? <button type="button" onClick={onClick} aria-expanded={open} className={cn(cls, 'cursor-pointer active:bg-muted')}>{inner}</button> : <div className={cls}>{inner}</div>}</li>;
};

export function Item({href, onClick, lead, title, sub, trail, chevron, wrap, className, children, ...p}) {
  const inner = <>
    {lead != null && <span className="flex shrink-0 items-center">{lead}</span>}
    <span className="min-w-0 flex-1">
      <span className={cn('block text-[15px] leading-snug font-medium', wrap ? 'line-clamp-2' : 'truncate')}>{title}</span>
      {sub && <span className={cn('mt-0.5 block text-[13px] leading-snug text-muted-foreground', wrap ? 'line-clamp-2' : 'truncate')}>{sub}</span>}
    </span>
    {trail != null && <span className="flex shrink-0 items-center gap-2 text-right">{trail}</span>}
    {(chevron ?? !!(href || onClick)) && <ChevronRightIcon className="size-4 shrink-0 text-muted-foreground/50" />}
  </>;
  const cls = cn('flex min-h-[52px] w-full items-center gap-3 px-4 py-2.5 text-left transition-[background-color,transform] duration-150', (href || onClick) && 'cursor-pointer active:scale-[.99] active:bg-muted/70', className);
  return <li>
    {href ? <a href={href} className={cls} {...p}>{inner}</a> : onClick ? <button type="button" onClick={onClick} className={cls} {...p}>{inner}</button> : <div className={cls} {...p}>{inner}</div>}
    {children}
  </li>;
}
