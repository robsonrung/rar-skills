#!/usr/bin/env python3
"""Offline tests for isolated Cline lane configuration and capacity locking."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from cline_lanes import (  # noqa: E402
    LaneCapacityError,
    LaneConfigError,
    acquire_lane_slot,
    apply_lane,
    load_lane,
)


def provisioned_lane_file(root: Path, max_concurrency: int = 2) -> Path:
    lane_data = root / "kimi-state"
    providers = lane_data / "settings" / "providers.json"
    providers.parent.mkdir(parents=True)
    providers.write_text("{}", encoding="utf-8")
    config = root / "lanes.json"
    config.write_text(
        json.dumps(
            {
                "lanes": {
                    "kimi": {
                        "provider": "openrouter",
                        "model": "moonshotai/kimi-k3",
                        "data_dir": str(lane_data),
                        "credential_pool": "openrouter-primary",
                        "max_concurrency": max_concurrency,
                        "lock_dir": str(root / "locks"),
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return config


class ClineLaneTests(unittest.TestCase):
    def test_lane_supplies_immutable_provider_model_and_state(self):
        with tempfile.TemporaryDirectory() as directory:
            config = provisioned_lane_file(Path(directory))
            lane = load_lane("kimi", str(config))
            self.assertEqual(
                apply_lane(lane, None, None, None),
                ("openrouter", "moonshotai/kimi-k3", lane.data_dir),
            )
            with self.assertRaises(LaneConfigError):
                apply_lane(lane, "cline", None, None)

    def test_lane_requires_provisioned_authenticated_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "lanes.json"
            config.write_text(
                json.dumps({"lanes": {"kimi": {
                    "provider": "openrouter", "model": "moonshotai/kimi-k3",
                    "data_dir": str(root / "empty"), "credential_pool": "pool", "max_concurrency": 1,
                }}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(LaneConfigError, "authenticated providers state"):
                load_lane("kimi", str(config))

    def test_credential_pool_respects_its_configured_capacity(self):
        with tempfile.TemporaryDirectory() as directory:
            lane = load_lane("kimi", str(provisioned_lane_file(Path(directory), max_concurrency=2)))
            with acquire_lane_slot(lane, 0), acquire_lane_slot(lane, 0):
                with self.assertRaises(LaneCapacityError):
                    with acquire_lane_slot(lane, 0):
                        pass

    def test_builtin_kimi_lane_needs_no_environment_variable_or_repo_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_dir = root / "kimi"
            providers = data_dir / "settings" / "providers.json"
            providers.parent.mkdir(parents=True)
            providers.write_text('{"lastUsedProvider":"openrouter"}', encoding="utf-8")
            with patch("cline_lanes.default_lane_root", return_value=root):
                lane = load_lane("kimi")
            self.assertEqual(lane.provider, "openrouter")
            self.assertIsNone(lane.model)
            self.assertEqual(lane.data_dir, str(data_dir))
            self.assertEqual(
                apply_lane(lane, None, "moonshotai/kimi-k3", None),
                ("openrouter", "moonshotai/kimi-k3", str(data_dir)),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
