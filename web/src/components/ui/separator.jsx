import {Separator as SeparatorPrimitive} from 'radix-ui';
import {cn} from '@/lib/utils';

export const Separator = ({className, orientation = 'horizontal', decorative = true, ...p}) => (
  <SeparatorPrimitive.Root data-slot="separator" decorative={decorative} orientation={orientation} className={cn('shrink-0 bg-border data-[orientation=horizontal]:h-px data-[orientation=horizontal]:w-full data-[orientation=vertical]:h-full data-[orientation=vertical]:w-px', className)} {...p} />
);
