import {Popover as PopoverPrimitive} from 'radix-ui';
import {cn} from '@/lib/utils';

export const Popover = p => <PopoverPrimitive.Root data-slot="popover" {...p} />;
export const PopoverTrigger = p => <PopoverPrimitive.Trigger data-slot="popover-trigger" {...p} />;
export function PopoverContent({className, align = 'center', sideOffset = 6, ...p}) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content data-slot="popover-content" align={align} sideOffset={sideOffset} className={cn('z-50 w-72 origin-(--radix-popover-content-transform-origin) rounded-md border bg-popover p-4 text-popover-foreground shadow-md outline-hidden data-[state=open]:animate-pop-in', className)} {...p} />
    </PopoverPrimitive.Portal>
  );
}
