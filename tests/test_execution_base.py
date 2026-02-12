import unittest

from engine.execution_base import ExecutionBase
from engine.execution_sim import SimExecution


class ExecutionBaseTest(unittest.TestCase):
    def test_sim_execution_implements_base(self):
        self.assertTrue(issubclass(SimExecution, ExecutionBase))


if __name__ == "__main__":
    unittest.main()

