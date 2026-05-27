"""Tests for usage tracker."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.usage.tracker import record_llm_call, get_report, reset


class TestUsageTracker:
    def setup_method(self):
        reset()

    def test_records_call(self):
        record_llm_call("u1", "claude-sonnet", None, 100, 50)
        report = get_report()
        assert report["by_user"]["u1"]["calls"] == 1
        assert report["by_model"]["claude-sonnet"]["input_tokens"] == 100

    def test_cost_calculation(self):
        record_llm_call("u1", "claude-sonnet", None, 1000, 1000)
        report = get_report()
        # input: 1000/1000 * 0.003 + output: 1000/1000 * 0.015 = 0.018
        assert abs(report["by_model"]["claude-sonnet"]["cost_usd"] - 0.018) < 0.001

    def test_skill_tracking(self):
        record_llm_call("u1", "gpt-4o", "code-review", 200, 100)
        report = get_report()
        assert report["by_skill"]["code-review"]["calls"] == 1

    def test_total_cost_aggregates(self):
        record_llm_call("u1", "claude-sonnet", None, 1000, 0)
        record_llm_call("u2", "gpt-4o", None, 1000, 0)
        report = get_report()
        assert report["total_cost_usd"] > 0

    def test_multiple_users(self):
        record_llm_call("u1", "claude-sonnet", None, 100, 50)
        record_llm_call("u2", "claude-sonnet", None, 200, 80)
        report = get_report()
        assert report["by_user"]["u1"]["calls"] == 1
        assert report["by_user"]["u2"]["calls"] == 1
