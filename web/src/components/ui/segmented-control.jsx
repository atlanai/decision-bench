/* Filters and sort controls choose a value; they do not control tab panels. */
import {RadioGroup as RadioGroupPrimitive} from 'radix-ui';
import {cn} from '@/lib/utils';

export const SegmentedControl = ({className, ...p}) => <RadioGroupPrimitive.Root orientation="horizontal" data-slot="segmented-control" className={cn('flex flex-col gap-2', className)} {...p} />;
export const SegmentedList = ({className, ...p}) => <div data-slot="segmented-list" className={cn('inline-flex h-9 w-fit items-center justify-center rounded-lg bg-muted p-[3px] text-muted-foreground', className)} {...p} />;
export const SegmentedOption = ({className, ...p}) => (
  <RadioGroupPrimitive.Item data-slot="segmented-option" className={cn("inline-flex h-[calc(100%-1px)] flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-md border border-transparent px-3 py-1 text-sm font-medium whitespace-nowrap text-muted-foreground transition-[color,box-shadow] hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-1 focus-visible:outline-ring disabled:pointer-events-none disabled:opacity-50 data-[state=checked]:bg-background data-[state=checked]:text-foreground data-[state=checked]:shadow-sm dark:data-[state=checked]:border-input dark:data-[state=checked]:bg-input/30 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4", className)} {...p} />
);
