/* Small building blocks every page shares: model identity, verdicts, page headers, sections, breadcrumbs. */
import {Fragment} from 'react';
import {ChevronRightIcon, ExternalLinkIcon} from 'lucide-react';
import {M} from '@/lib/bench';
import {modelHref} from '@/lib/route';
import {isHttp} from '@/lib/format';
import {cn} from '@/lib/utils';
import {Badge} from '@/components/ui/badge';

export const Dot = ({k, className}) => <i className={cn('inline-block size-2 shrink-0 rounded-full', className)} style={{background: M(k).color}} />;
export const Logo = ({k, size = 18, className}) => {
  const m = M(k);
  return m.logo
    ? <img src={m.logo} alt="" width={size} height={size} loading="lazy" className={cn('shrink-0 rounded-[4px] border bg-white object-contain', className)} style={{width: size, height: size}} />
    : <Dot k={k} className={className} />;
};
/* One line per model: vendor logo, name, and the interface only when it is not a plain API. */
export function ModelName({k, sub = true, link = true, short = false, className}) {
  const m = M(k);
  const inner = <>
    <Logo k={k} />
    <span className="truncate font-medium text-foreground">{short ? m.short : m.name}</span>
    {sub && m.iface && m.iface !== 'API' && <span className="shrink-0 text-xs text-muted-foreground">{m.iface}</span>}
  </>;
  const cls = cn('inline-flex min-w-0 items-center gap-2 whitespace-nowrap', className);
  return link ? <a href={modelHref(k)} className={cn(cls, 'hover:[&>span:nth-child(2)]:underline')}>{inner}</a> : <span className={cls}>{inner}</span>;
}

const FIT = {ok: 'good', risk: 'warn', no: 'bad', na: 'secondary'};
export const Fit = ({v}) => (
  <Badge variant={FIT[v.k]} className={cn('gap-1.5 rounded-full px-2', v.k === 'na' && 'text-muted-foreground')}>
    <i className="size-1.5 rounded-full bg-current" />{v.t}
  </Badge>
);

export const Ext = ({href, children, className, icon = false}) => isHttp(href)
  ? <a href={href} target="_blank" rel="noopener" className={className}>{children}{icon && <ExternalLinkIcon className="ml-1 inline size-3.5 -translate-y-px opacity-60" />}</a>
  : <span className={className}>{children}</span>;

export function PageHeader({title, description, eyebrow, actions, className}) {
  return (
    <header className={cn('mb-8 flex flex-wrap items-end justify-between gap-x-8 gap-y-4', className)}>
      <div className="min-w-0 max-w-3xl">
        {eyebrow && <div className="mb-2 text-sm font-medium text-muted-foreground">{eyebrow}</div>}
        <h1 className="text-3xl font-semibold tracking-tight text-balance">{title}</h1>
        {description && <p className="mt-2 text-[15px] leading-relaxed text-pretty text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

/* Short notes under a table: one quiet line that wraps, each note on its own. Falsy items are skipped. */
export function Notes({items, className}) {
  const list = items.filter(Boolean);
  return list.length ? <ul className={cn('mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground', className)}>{list.map((n, i) => <li key={i}>{n}</li>)}</ul> : null;
}
export function Section({title, description, actions, children, id, className}) {
  return (
    <section id={id} className={cn('mt-14 scroll-mt-20', className)}>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
          {description && <p className="mt-1 max-w-3xl text-sm text-pretty text-muted-foreground">{description}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

export function Crumbs({items}) {
  return (
    <nav aria-label="Breadcrumb" className="mb-6 flex flex-wrap items-center gap-1.5 text-sm text-muted-foreground">
      {items.map(([t, h], i) => <Fragment key={i}>
        {i > 0 && <ChevronRightIcon className="size-3.5 opacity-60" />}
        {h ? <a href={h} className="transition-colors hover:text-foreground">{t}</a> : <span className="truncate text-foreground">{t}</span>}
      </Fragment>)}
    </nav>
  );
}

export const Notice = ({children, className}) => <div className={cn('max-w-3xl rounded-lg border bg-muted/50 px-4 py-3 text-sm text-muted-foreground', className)}>{children}</div>;
export const Muted = ({children, className}) => <span className={cn('text-muted-foreground', className)}>{children}</span>;
export const Dash = () => <span className="text-muted-foreground/50">—</span>;

/* Stat tile: label over a large tabular value. */
export const Stat = ({label, value, sub, className}) => (
  <div className={cn('rounded-xl border bg-card px-4 py-3.5 shadow-xs', className)}>
    <div className="text-[13px] text-muted-foreground">{label}</div>
    <div className="mt-1 flex items-baseline gap-2"><span className="text-2xl font-semibold tracking-tight tabular-nums">{value}</span>{sub && <span className="text-xs text-muted-foreground">{sub}</span>}</div>
  </div>
);

export function EmptyPage({title, children}) {
  return <div className="grid min-h-[50vh] place-items-center text-center"><div><h1 className="text-xl font-semibold">{title}</h1><div className="mt-2 text-sm text-muted-foreground">{children}</div></div></div>;
}

/* A thin bar showing a share, for accuracy cells. */
export const Meter = ({value, color, className}) => (
  <span className={cn('inline-block h-1.5 w-16 overflow-hidden rounded-full bg-muted align-middle', className)}>
    <i className="block h-full rounded-full" style={{width: `${Math.max(0, Math.min(1, value || 0)) * 100}%`, background: color}} />
  </span>
);
