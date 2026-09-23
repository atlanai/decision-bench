import {Tooltip as TooltipPrimitive} from 'radix-ui';
import {cn} from '@/lib/utils';

export const TooltipProvider = ({delayDuration = 150, ...p}) => <TooltipPrimitive.Provider data-slot="tooltip-provider" delayDuration={delayDuration} {...p} />;
export const Tooltip = p => <TooltipPrimitive.Root data-slot="tooltip" {...p} />;
export const TooltipTrigger = p => <TooltipPrimitive.Trigger data-slot="tooltip-trigger" {...p} />;
export function TooltipContent({className, sideOffset = 6, children, ...p}) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content data-slot="tooltip-content" sideOffset={sideOffset} className={cn('z-50 w-fit max-w-xs origin-(--radix-tooltip-content-transform-origin) rounded-md bg-foreground px-3 py-1.5 text-xs text-balance text-background data-[state=delayed-open]:animate-fade-in', className)} {...p}>{children}</TooltipPrimitive.Content>
    </TooltipPrimitive.Portal>
  );
}
/* One-liner: <Tip content="…"><button/></Tip> */
export const Tip = ({content, side, children}) => content ? <Tooltip><TooltipTrigger asChild>{children}</TooltipTrigger><TooltipContent side={side}>{content}</TooltipContent></Tooltip> : children;
