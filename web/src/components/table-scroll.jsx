export function TableScroll({children, label = 'Results table'}) {
  return <div role="region" aria-label={label} tabIndex={0} className="w-full min-w-0 overflow-x-auto focus-visible:outline-2 focus-visible:outline-ring">{children}</div>;
}
