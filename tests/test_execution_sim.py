import unittest

from engine.execution_sim import SimExecution


class SimExecutionTest(unittest.TestCase):
    def test_force_close_with_commission_and_multiplier(self):
        ex = SimExecution(slippage=0, contract_multiplier=10, commission_per_contract=1.0, commission_min=0.0)
        opened = ex.send_order("M2609", 1, 100.0, 2, contract_multiplier=10)
        self.assertTrue(opened)
        pnl = ex.force_close(101.0)
        self.assertAlmostEqual(pnl, 16.0)
        self.assertEqual(len(ex.trades), 1)
        self.assertAlmostEqual(ex.trades[0]["gross_pnl"], 20.0)
        self.assertAlmostEqual(ex.trades[0]["commission"], 4.0)


if __name__ == "__main__":
    unittest.main()
