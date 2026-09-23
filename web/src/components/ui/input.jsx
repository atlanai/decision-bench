import {cn} from '@/lib/utils';

export const Input = ({className, type, ...p}) => (
  <input type={type} data-slot="input" className={cn('h-9 w-full min-w-0 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-[color,box-shadow] outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-input/30 [&::-webkit-search-cancel-button]:cursor-pointer', className)} {...p} />
);
export const Textarea = ({className, ...p}) => (
  <textarea data-slot="textarea" className={cn('flex field-sizing-content min-h-16 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs transition-[color,box-shadow] outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30', className)} {...p} />
);
