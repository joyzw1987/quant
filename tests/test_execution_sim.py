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

    def test_cost_profile_applied(self):
        ex = SimExecution(
            slippage=1,
            contract_multiplier=10,
            commission_per_contract=1.0,
            commission_min=0.0,
            fill_ratio_min=1.0,
            fill_ratio_max=1.0,
            cost_model={
                "profiles": [
                    {
                        "name": "night",
                        "start": "21:00",
                        "end": "23:00",
                        "slippage": 2.0,
                        "commission_multiplier": 1.5,
                        "fill_ratio_min": 1.0,
                        "fill_ratio_max": 1.0,
                    }
                ]
            },
        )
        opened = ex.send_order("M2609", 1, 100.0, 2, bar_time="2026-02-12 21:05")
        self.assertTrue(opened)
        self.assertAlmostEqual(ex.position["entry_price"], 102.0)
        pnl = ex.force_close(103.0)
        self.assertAlmostEqual(pnl, 14.0)
        self.assertEqual(ex.trades[0]["cost_profile"], "night")

    def test_partial_fill(self):
        ex = SimExecution(
            slippage=0,
            contract_multiplier=10,
            commission_per_contract=1.0,
            commission_min=0.0,
            fill_ratio_min=0.5,
            fill_ratio_max=0.5,
        )
        opened = ex.send_order("M2609", 1, 100.0, 2, bar_time="2026-02-12 09:05")
        self.assertTrue(opened)
        self.assertAlmostEqual(ex.position["size"], 1.0)
        pnl = ex.force_close(101.0)
        self.assertAlmostEqual(pnl, 8.0)

    def test_reject_prob_blocks_order(self):
        ex = SimExecution(
            slippage=0,
            contract_multiplier=10,
            commission_per_contract=0.0,
            commission_min=0.0,
            cost_model={
                "profiles": [
                    {
                        "name": "day",
                        "start": "09:00",
                        "end": "15:00",
                        "reject_prob": 1.0,
                    }
                ]
            },
        )
        opened = ex.send_order("M2609", 1, 100.0, 1, bar_time="2026-02-12 09:05")
        self.assertFalse(opened)
        self.assertIsNone(ex.position)


if __name__ == "__main__":
    unittest.main()
