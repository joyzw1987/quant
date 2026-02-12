import unittest

from engine.data_policy import assert_source_allowed, get_data_policy, validate_data_policy


class DataPolicyTest(unittest.TestCase):
    def test_default_policy(self):
        policy = get_data_policy({})
        self.assertEqual(policy["mode"], "research")
        self.assertEqual(policy["approved_sources"], [])

    def test_validate_commercial_requires_sources(self):
        errors, warnings = validate_data_policy({"data_policy": {"mode": "commercial"}})
        self.assertTrue(any("approved_sources" in x for x in errors))
        self.assertTrue(any("commercial_ack" in x for x in warnings))

    def test_assert_source_allowed_blocks_unapproved(self):
        cfg = {
            "data_policy": {
                "mode": "commercial",
                "approved_sources": ["licensed_vendor"],
                "commercial_ack": "contract signed",
            }
        }
        with self.assertRaises(SystemExit):
            assert_source_allowed(cfg, "akshare")

    def test_assert_source_allowed_passes_research(self):
        cfg = {"data_policy": {"mode": "research"}}
        assert_source_allowed(cfg, "akshare")


if __name__ == "__main__":
    unittest.main()
