import {Accordion as AccordionPrimitive} from 'radix-ui';
import {ChevronDownIcon} from 'lucide-react';
import {cn} from '@/lib/utils';

export const Accordion = p => <AccordionPrimitive.Root data-slot="accordion" {...p} />;
export const AccordionItem = ({className, ...p}) => <AccordionPrimitive.Item data-slot="accordion-item" className={cn('border-b last:border-b-0', className)} {...p} />;
export function AccordionTrigger({className, children, ...p}) {
  return (
    <AccordionPrimitive.Header className="flex">
      <AccordionPrimitive.Trigger data-slot="accordion-trigger" className={cn('flex flex-1 cursor-pointer items-start justify-between gap-4 rounded-md py-4 text-left text-sm font-medium transition-all outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 [&[data-state=open]>svg]:rotate-180', className)} {...p}>
        {children}
        <ChevronDownIcon className="pointer-events-none mt-0.5 size-4 shrink-0 text-muted-foreground transition-transform duration-200" />
      </AccordionPrimitive.Trigger>
    </AccordionPrimitive.Header>
  );
}
export function AccordionContent({className, children, ...p}) {
  return (
    <AccordionPrimitive.Content data-slot="accordion-content" className="overflow-hidden text-sm data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down" {...p}>
      <div className={cn('pt-0 pb-4', className)}>{children}</div>
    </AccordionPrimitive.Content>
  );
}
