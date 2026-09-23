import {cn} from '@/lib/utils';

export const Table = ({className, wrapClassName, ...p}) => (
  <div data-slot="table-container" className={cn('relative w-full overflow-x-auto', wrapClassName)}>
    <table data-slot="table" className={cn('w-full caption-bottom text-sm', className)} {...p} />
  </div>
);
export const TableHeader = ({className, ...p}) => <thead data-slot="table-header" className={cn('[&_tr]:border-b', className)} {...p} />;
export const TableBody = ({className, ...p}) => <tbody data-slot="table-body" className={cn('[&_tr:last-child]:border-0', className)} {...p} />;
export const TableRow = ({className, ...p}) => <tr data-slot="table-row" className={cn('border-b transition-colors hover:bg-muted/40 data-[state=selected]:bg-muted', className)} {...p} />;
export const TableHead = ({className, ...p}) => <th data-slot="table-head" className={cn('h-10 px-3 text-left align-middle text-[13px] font-medium whitespace-nowrap text-muted-foreground first:pl-5 last:pr-5', className)} {...p} />;
export const TableCell = ({className, ...p}) => <td data-slot="table-cell" className={cn('px-3 py-2.5 align-middle first:pl-5 last:pr-5', className)} {...p} />;
