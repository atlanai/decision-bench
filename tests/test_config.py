import json
import unittest

from decision_bench import config

import fixtures


class Config(unittest.TestCase):
    def write(self, root, models):
        (root / "config/models.json").write_text(json.dumps({"models": models}))

    def test_rejects_bad_entries(self):
        good = dict(fixtures.MODELS["models"][0])
        bad = [dict(good, id="Has Space"), dict(good, provider="litellm"), dict(good, model="https://host/v1"),
               dict(good, base_url="https://host"), dict(good, request={"api_base": "x"}),
               dict(good, request={"response_format": "xml"}),
               dict(good, pricing={"input_per_mtok": -1, "output_per_mtok": 1, "source_url": "https://e.com"}),
               dict(good, pricing={"input_per_mtok": 1, "output_per_mtok": 1, "source_url": "http://e.com"})]
        with fixtures.repo() as root:
            for entry in bad:
                self.write(root, [entry])
                with self.assertRaises(config.ConfigError, msg=str(entry)):
                    config.load_models()
            self.write(root, [good, good])
            with self.assertRaises(config.ConfigError):
                config.load_models()
            self.write(root, [good])
            self.assertEqual(config.get_model("fake-model")["model"], "fake/model-1")
            with self.assertRaises(config.ConfigError):
                config.get_model("missing")

    def test_env_file_is_read_after_the_environment(self):
        with fixtures.repo({"DECISION_BENCH_API_KEY": "from-env"}) as root:
            (root / ".env").write_text("# comment\nDECISION_BENCH_BASE_URL='http://localhost:1/v1'\nDECISION_BENCH_API_KEY=from-file\n")
            self.assertEqual(config.env_value("DECISION_BENCH_BASE_URL"), "http://localhost:1/v1")
            self.assertEqual(config.env_value("DECISION_BENCH_API_KEY"), "from-env")
            self.assertIsNone(config.env_value("TYPESAFE_API_KEY"))

    def test_price_estimate(self):
        pricing = {"input_per_mtok": 1.0, "cached_input_per_mtok": 0.1, "output_per_mtok": 4.0}
        usage = {"input_tokens": 1000, "cached_input_tokens": 400, "output_tokens": 100}
        self.assertAlmostEqual(config.estimate_cost(pricing, usage), (600 * 1 + 400 * .1 + 100 * 4) / 1e6)
        self.assertIsNone(config.estimate_cost(pricing, {"input_tokens": 10}))
        self.assertIsNone(config.estimate_cost(None, usage))
        no_cache = {"input_per_mtok": 1.0, "output_per_mtok": 4.0}
        self.assertAlmostEqual(config.estimate_cost(no_cache, usage), (1000 + 400) / 1e6)

    def test_committed_config_is_valid(self):
        models = config.load_models()
        ids = {m["id"] for m in models}
        self.assertTrue({"jev-1.13", "gpt-6-luna-codex", "claude-sonnet-5-cli", "gemini-3.5-flash"} <= ids)
        self.assertEqual({m["provider"] for m in models}, config.PROVIDERS)


if __name__ == "__main__":
    unittest.main()
