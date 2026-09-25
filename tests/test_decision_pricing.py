import unittest
from decision_bench.decision_pricing import apply

class DecisionPricing(unittest.TestCase):
    def test_unit_boundary_and_immutable_measured_ledger(self):
        ledger=[{'event':'finished','status':'ok','usage':{'input_tokens':t},'cost_usd':None} for t in [100,4000,4083]]
        audit={'monthly_price_usd':49,'monthly_units':60000,'tokens_per_unit':4000,'benchmark_units':4}
        priced=apply(ledger,audit)
        self.assertEqual([x['decision_units'] for x in priced],[1,1,2])
        self.assertAlmostEqual(sum(x['cost_usd'] for x in priced),4*49/60000)
        self.assertTrue(all(x['cost_usd'] is None for x in ledger))
        audit['benchmark_units']=3
        with self.assertRaises(ValueError): apply(ledger,audit)

    def test_missing_tokens_and_failures_are_not_priced(self):
        audit={'monthly_price_usd':49,'monthly_units':60000,'tokens_per_unit':4000,'benchmark_units':1}
        for e in [{'event':'finished','status':'ok','usage':{}},
                  {'event':'finished','status':'429','usage':{'input_tokens':100}}]:
            with self.assertRaises(ValueError): apply([e],audit)
