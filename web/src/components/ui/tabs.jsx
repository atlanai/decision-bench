import {Tabs as TabsPrimitive} from 'radix-ui';
import {cn} from '@/lib/utils';

export const Tabs = ({className, ...p}) => <TabsPrimitive.Root data-slot="tabs" className={cn('flex flex-col gap-2', className)} {...p} />;
export const TabsList = ({className, ...p}) => <TabsPrimitive.List data-slot="tabs-list" className={cn('inline-flex h-9 w-fit items-center justify-center rounded-lg bg-muted p-[3px] text-muted-foreground', className)} {...p} />;
export const TabsTrigger = ({className, ...p}) => (
  <TabsPrimitive.Trigger data-slot="tabs-trigger" className={cn("inline-flex h-[calc(100%-1px)] flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-md border border-transparent px-3 py-1 text-sm font-medium whitespace-nowrap text-muted-foreground transition-[color,box-shadow] hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-1 focus-visible:outline-ring disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm dark:data-[state=active]:border-input dark:data-[state=active]:bg-input/30 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4", className)} {...p} />
);
export const TabsContent = ({className, ...p}) => <TabsPrimitive.Content data-slot="tabs-content" className={cn('flex-1 outline-none', className)} {...p} />;
