import {Slot} from 'radix-ui';
import {cva} from 'class-variance-authority';
import {cn} from '@/lib/utils';

export const badgeVariants = cva(
  'inline-flex w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-md border px-2 py-0.5 text-xs font-medium whitespace-nowrap transition-[color,box-shadow] [&>svg]:pointer-events-none [&>svg]:size-3',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground',
        secondary: 'border-transparent bg-secondary text-secondary-foreground',
        outline: 'text-foreground [a&]:hover:bg-accent [a&]:hover:text-accent-foreground',
        brand: 'border-transparent bg-brand-soft text-brand',
        good: 'border-transparent bg-good-soft text-good',
        warn: 'border-transparent bg-warn-soft text-warn',
        bad: 'border-transparent bg-bad-soft text-bad',
      },
    },
    defaultVariants: {variant: 'default'},
  },
);

export function Badge({className, variant, asChild = false, ...props}) {
  const Comp = asChild ? Slot.Root : 'span';
  return <Comp data-slot="badge" className={cn(badgeVariants({variant}), className)} {...props} />;
}
