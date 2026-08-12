import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from score_chats import score, score_dataset  # noqa: E402


class ScoreChatsTests(unittest.TestCase):
    def test_threshold_boundary_and_slow_reply(self):
        messages = [
            {"role": "buyer", "timestamp": "2026-08-01 10:00:00", "text": "A"},
            {"role": "agent", "timestamp": "2026-08-01 10:00:10", "text": "B"},
            {"role": "buyer", "timestamp": "2026-08-01 10:01:00", "text": "C"},
            {"role": "agent", "timestamp": "2026-08-01 10:01:13", "text": "D"},
        ]

        scored, latencies = score(messages, 10)

        self.assertEqual(latencies, [10, 13])
        self.assertEqual(scored[1]["response_band"], "正常")
        self.assertEqual(scored[3]["response_band"], "回复慢")

    def test_consecutive_buyer_messages_use_latest_timestamp(self):
        messages = [
            {"role": "buyer", "timestamp": "2026-08-01 10:00:00"},
            {"role": "buyer", "timestamp": "2026-08-01 10:00:05"},
            {"role": "agent", "timestamp": "2026-08-01 10:00:12"},
        ]

        scored, latencies = score(messages, 10)

        self.assertEqual(latencies, [7])
        self.assertEqual(scored[2]["response_seconds"], 7)

    def test_invalid_or_reversed_timestamps_are_not_scored(self):
        invalid = [
            {"role": "buyer", "timestamp": "invalid"},
            {"role": "agent", "timestamp": "2026-08-01 10:00:10"},
        ]
        reversed_pair = [
            {"role": "buyer", "timestamp": "2026-08-01 10:00:10"},
            {"role": "agent", "timestamp": "2026-08-01 10:00:00"},
        ]

        _, invalid_latencies = score(invalid, 10)
        reversed_scored, reversed_latencies = score(reversed_pair, 10)

        self.assertEqual(invalid_latencies, [])
        self.assertEqual(reversed_latencies, [])
        self.assertIn("latency_error", reversed_scored[1])

    def test_dataset_scoring_does_not_mutate_input(self):
        source = {
            "conversations": [
                {
                    "index": 1,
                    "messages": [
                        {"role": "buyer", "timestamp": "2026-08-01 10:00:00"},
                        {"role": "agent", "timestamp": "2026-08-01 10:00:13"},
                    ],
                }
            ]
        }
        original = copy.deepcopy(source)

        result = score_dataset(source, 10)

        self.assertEqual(source, original)
        summary = result["conversations"][0]["latency_summary"]
        self.assertEqual(summary, {"count": 1, "average_seconds": 13.0, "max_seconds": 13})

    def test_negative_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            score([], -1)


if __name__ == "__main__":
    unittest.main()

