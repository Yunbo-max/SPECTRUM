"""Contract tests use explicit fake native components; no emulator scores claimed."""
from contextlib import contextmanager
import dataclasses
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from improving.android import environment as mod
from improving.android.prompting import ActionParseError, build_messages, parse_mobile_action


def tool(args):
    return "Thought: act\nAction: do it\n<tool_call>" + json.dumps({"name": "mobile_use", "arguments": args}) + "</tool_call>"


class ParseTests(unittest.TestCase):
    def test_edges_are_in_screen(self):
        self.assertEqual(parse_mobile_action(tool({"action": "click", "coordinate": [999, 999]}), 100, 200),
                         {"action_type": "click", "x": 99, "y": 199})

    def test_bad_actions_never_become_wait(self):
        for response in ("oops", "<tool_call>{}</tool_call>",
                         tool({"action": "click", "coordinate": [True, 5]}),
                         tool({"action": "click", "coordinate": [-1, 5]}),
                         tool({"action": "system_button", "button": []}),
                         tool({"action": []}),
                         tool({"action": "terminate"}), tool({"action": "mystery"})):
            with self.assertRaises(ActionParseError):
                parse_mobile_action(response, 100, 100)

    def test_explicit_wait_and_answer(self):
        self.assertEqual(parse_mobile_action(tool({"action": "wait"}), 10, 10), {"action_type": "wait"})
        self.assertEqual(parse_mobile_action(tool({"action": "answer", "text": "42"}), 10, 10)["text"], "42")

    def test_prompt_contains_actual_image_and_bounded_history(self):
        result = build_messages("goal", "/tmp/screenshot.png", ["old", "new"], "system", 1)
        self.assertEqual(result[1]["content"][1], {"type": "image", "image": "/tmp/screenshot.png"})
        self.assertIn("Step2: new", result[1]["content"][0]["text"])
        self.assertNotIn("Step1: old", result[1]["content"][0]["text"])


class Task:
    def __init__(self, params):
        self.params = params
        self.goal = f"Find {params.get('value', 'fixed')}"
        self.initialized = False

    @classmethod
    def generate_random_params(cls):
        import random
        return {"value": random.randrange(100000)}

    def initialize_task(self, env):
        self.initialized = True

    def is_successful(self, env):
        if env.verifier_error:
            raise RuntimeError("native verifier offline")
        return env.score

    def tear_down(self, env):
        env.torn_down += 1
        self.initialized = False


class FixedTask(Task):
    @classmethod
    def generate_random_params(cls):
        return {}


class Env:
    def __init__(self, score=1.0, verifier_error=False):
        self.score, self.verifier_error = score, verifier_error
        self.actions, self.torn_down, self.closed = [], 0, False

    def reset(self, go_home=False):
        pass

    def get_state(self, **kwargs):
        return SimpleNamespace(pixels=np.zeros((16, 8, 3), dtype=np.uint8))

    def execute_action(self, action):
        self.actions.append(action)

    def close(self):
        self.closed = True


def instance(split="train"):
    params = {"value": 3}
    return {"instance_id": mod._digest({"task_name": "Task", "params": params}),
            "task_name": "Task", "params": params, "initialization_seed": 7,
            "goal": "Find 3", "split": split}


@contextmanager
def fake_native(env, tasks=None):
    components = (tasks or {"Task": Task}, SimpleNamespace(load_and_setup_env=lambda **kw: env),
                  lambda **kw: SimpleNamespace(**kw))
    with patch.object(mod, "_load_components", return_value=components), \
         patch.object(mod, "load_system_prompt", return_value="test-system"), \
         patch.object(mod, "_execute_native_action", side_effect=lambda e, a, s: e.execute_action(a)):
        yield


class ManifestTests(unittest.TestCase):
    def test_native_row_and_image_parameters_round_trip_without_pickle(self):
        from PIL import Image
        row_type = dataclasses.make_dataclass("Expense", [("name", str), ("value", int)])
        row_type.__module__ = "android_world.task_evals.utils.sqlite_schema_utils"
        original = {"rows": [row_type("meal", 5)], "target": Image.new("RGB", (3, 2), "red"), "pair": (1, 2)}
        encoded = mod._encode_params(original)
        json_payload = json.loads(json.dumps(encoded))
        with patch.object(mod.importlib, "import_module", return_value=SimpleNamespace(Expense=row_type)):
            restored = mod._decode_params(json_payload)
        self.assertEqual(restored["rows"][0], original["rows"][0])
        self.assertEqual(restored["target"].tobytes(), original["target"].tobytes())
        self.assertEqual(restored["pair"], (1, 2))
        with self.assertRaises(ValueError):
            mod._decode_params({"__android_type__": "arbitrary.module.Constructor", "fields": {}})

    def test_parameterized_selection_keeps_fixed_tasks_in_eval(self):
        cfg = {"data": {"seed": 91, "train_task_limit": 1, "calibration_task_limit": 1,
                        "split_counts": {"train": 2, "calibration": 1, "eval": 1}, "max_param_attempts": 20}}
        with TemporaryDirectory() as directory, fake_native(Env(), {"Task": Task, "FixedTask": FixedTask}):
            a = mod.prepare_manifest("unused", Path(directory)/"a.json", cfg)
            b = mod.prepare_manifest("unused", Path(directory)/"b.json", cfg)
            self.assertEqual(a, b)
            self.assertEqual(len(a["instances"]), 5)
            self.assertEqual(a["selected_tasks"]["eval"], ["FixedTask", "Task"])
            self.assertEqual(a["selected_tasks"]["train"], ["Task"])
            self.assertEqual(len({v["instance_id"] for v in a["instances"]}), 5)
            self.assertEqual((Path(directory)/"a.json").stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                mod.prepare_manifest("unused", Path(directory)/"a.json", cfg)

    def test_cannot_relabel_identical_static_instance_into_train_and_eval(self):
        cfg = {"data": {"tasks": ["FixedTask"], "seed": 3, "max_param_attempts": 8,
                        "split_counts": {"train": 1, "calibration": 1, "eval": 1}}}
        with TemporaryDirectory() as directory, fake_native(Env(), {"FixedTask": FixedTask}):
            with self.assertRaisesRegex(ValueError, "disjoint"):
                mod.prepare_manifest("unused", Path(directory)/"manifest.json", cfg)


class CollectionTests(unittest.TestCase):
    config = {"android": {"upstream_root": "unused", "max_steps": 2, "wait_after_action_seconds": 0}}

    def collect(self, directory, response, env, config=None):
        with fake_native(env):
            return mod.collect_episodes([instance()], lambda m: {"response": response, "response_token_ids": [7, 8]},
                                        Path(directory)/"episodes", config or self.config, "native", "checkpoint", 1)

    def test_declared_success_is_not_native_success(self):
        env = Env(score=0)
        with TemporaryDirectory() as directory:
            result = self.collect(directory, tool({"action": "terminate", "status": "success"}), env)
            self.assertFalse(result[0]["success"])
            self.assertEqual(result[0]["native_score"], 0)
            self.assertTrue(env.closed)
            self.assertEqual(env.torn_down, 1)

    def test_malformed_outputs_preserved_and_never_executed(self):
        env = Env()
        with TemporaryDirectory() as directory:
            result = self.collect(directory, "invalid output", env)
            self.assertFalse(result[0]["success"])
            self.assertEqual(len(result[0]["steps"]), 2)
            self.assertEqual(env.actions, [])
            self.assertEqual(result[0]["steps"][0]["response_token_ids"], [7, 8])
            self.assertEqual(result[0]["steps"][0]["feedback_kind"], "action_error")

    def test_native_verifier_error_aborts_without_false_failure_label(self):
        env = Env(verifier_error=True)
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "verifier offline"):
                self.collect(directory, tool({"action": "terminate", "status": "success"}), env)
            partial = next((Path(directory)/"episodes").glob("*/episode.partial.json"))
            record = json.loads(partial.read_text())
            self.assertIsNone(record["success"])
            self.assertEqual(record["status"], "aborted")
            self.assertFalse((Path(directory)/"episodes/episodes.jsonl").exists())
            self.assertTrue(env.closed)

    def test_group_repeats_and_complete_success(self):
        env = Env()
        cfg = {**self.config, "collection": {"repeats": 2}}
        with TemporaryDirectory() as directory:
            result = self.collect(directory, tool({"action": "terminate", "status": "success"}), env, cfg)
            self.assertEqual([e["repeat_id"] for e in result], [0, 1])
            self.assertTrue(all(e["success"] for e in result))
            self.assertEqual(len({e["episode_id"] for e in result}), 2)
            self.assertEqual(env.torn_down, 2)

    def test_native_adb_failure_is_not_silently_accepted(self):
        failure = SimpleNamespace(success=False, to_dict=lambda: {"success": False, "adb_errors": ["disconnected"]})
        actuation = SimpleNamespace(execute_adb_action=lambda *args: failure)
        env = SimpleNamespace(logical_screen_size=(8, 16), controller=object())
        state = SimpleNamespace(ui_elements=[])
        with patch.object(mod.importlib, "import_module", return_value=actuation):
            with self.assertRaisesRegex(RuntimeError, "disconnected"):
                mod._execute_native_action(env, SimpleNamespace(action_type="click"), state)

    def test_goal_uses_native_post_initialization_rewording(self):
        class RewordingTask(Task):
            def initialize_task(self, env):
                super().initialize_task(env)
                self.goal = "Native rewritten date goal"

        env = Env()
        with TemporaryDirectory() as directory, fake_native(env, {"Task": RewordingTask}):
            result = mod.collect_episodes([instance()], lambda m: {"response": tool({"action": "terminate", "status": "success"}), "response_token_ids": [7]},
                                          Path(directory)/"episodes", self.config, "native", "checkpoint", 1)
            self.assertEqual(result[0]["goal"], "Native rewritten date goal")
            self.assertIn("Native rewritten date goal", result[0]["steps"][0]["messages"][1]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
