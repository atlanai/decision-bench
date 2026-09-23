import {DropdownMenu as MenuPrimitive} from 'radix-ui';
import {CheckIcon, MinusIcon} from 'lucide-react';
import {cn} from '@/lib/utils';

/* Non-modal by default: a modal menu locks page scroll and hides the rest of the page from assistive tech, which
   restyles every element on the leaderboard each time it opens or closes. Filters don't need that. */
export const DropdownMenu = ({modal = false, ...p}) => <MenuPrimitive.Root data-slot="dropdown-menu" modal={modal} {...p} />;
export const DropdownMenuTrigger = p => <MenuPrimitive.Trigger data-slot="dropdown-menu-trigger" {...p} />;
export function DropdownMenuContent({className, sideOffset = 6, align = 'start', ...p}) {
  return (
    <MenuPrimitive.Portal>
      <MenuPrimitive.Content data-slot="dropdown-menu-content" sideOffset={sideOffset} align={align} className={cn('z-50 max-h-(--radix-dropdown-menu-content-available-height) min-w-[8rem] origin-(--radix-dropdown-menu-content-transform-origin) overflow-x-hidden overflow-y-auto rounded-md border bg-popover p-1 text-popover-foreground shadow-md outline-hidden data-[state=open]:animate-pop-in', className)} {...p} />
    </MenuPrimitive.Portal>
  );
}
const ITEM = 'relative flex cursor-pointer items-center gap-2.5 rounded-sm py-1.5 pr-2 pl-8 text-sm outline-hidden select-none focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50';
export const DropdownMenuRadioGroup = p => <MenuPrimitive.RadioGroup data-slot="dropdown-menu-radio-group" {...p} />;
export function DropdownMenuRadioItem({className, children, ...p}) {
  return (
    <MenuPrimitive.RadioItem data-slot="dropdown-menu-radio-item" className={cn(ITEM, className)} {...p}>
      <span className="absolute left-2 flex size-4 items-center justify-center"><MenuPrimitive.ItemIndicator><CheckIcon className="size-4" /></MenuPrimitive.ItemIndicator></span>
      {children}
    </MenuPrimitive.RadioItem>
  );
}
/* A checkbox row. checked may be 'indeterminate' for a "select all" row over a partial selection. */
export function DropdownMenuCheckboxItem({className, children, checked, ...p}) {
  return (
    <MenuPrimitive.CheckboxItem data-slot="dropdown-menu-checkbox-item" checked={checked} className={cn(ITEM, className)} {...p}>
      <span className={cn('absolute left-2 flex size-4 items-center justify-center rounded-[4px] border border-input shadow-xs', checked && 'border-primary bg-primary text-primary-foreground')}>
        <MenuPrimitive.ItemIndicator>{checked === 'indeterminate' ? <MinusIcon className="size-3" /> : <CheckIcon className="size-3" />}</MenuPrimitive.ItemIndicator>
      </span>
      {children}
    </MenuPrimitive.CheckboxItem>
  );
}
export const DropdownMenuLabel = ({className, ...p}) => <MenuPrimitive.Label data-slot="dropdown-menu-label" className={cn('px-2 py-1.5 text-xs font-medium text-muted-foreground', className)} {...p} />;
export const DropdownMenuSeparator = ({className, ...p}) => <MenuPrimitive.Separator data-slot="dropdown-menu-separator" className={cn('-mx-1 my-1 h-px bg-border', className)} {...p} />;
