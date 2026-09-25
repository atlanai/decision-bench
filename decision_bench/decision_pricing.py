"""Explicit audit-time estimates for completed, text-only Sage decision runs."""
import copy
import math


def apply(ledger, audit):
    """Keep measured ledgers immutable; only annotate an exported copy with plan value."""
    priced = copy.deepcopy(ledger)
    rate = audit['monthly_price_usd'] / audit['monthly_units']
    total = 0
    for event in priced:
        if event.get('event') != 'finished':
            continue
        tokens = (event.get('usage') or {}).get('input_tokens')
        if event.get('status') != 'ok' or not isinstance(tokens, int) or tokens < 1:
            raise ValueError('Decision pricing requires successful calls with measured input tokens')
        if event.get('cost_usd') is not None:
            raise ValueError('Refusing to overwrite a recorded cost with a plan estimate')
        units = max(1, math.ceil(tokens / audit['tokens_per_unit']))
        total += units
        event.update(cost_usd=units * rate, cost_basis='decision_plan_estimate', decision_units=units)
    if total != audit['benchmark_units']:
        raise ValueError('Reconstructed decision units do not match the audited benchmark total')
    return priced
