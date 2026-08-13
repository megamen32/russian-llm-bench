from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "full_benchmark_runner.py"


def load_module():
    spec = importlib.util.spec_from_file_location("full_benchmark_runner", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FullBenchmarkRunnerTest(unittest.TestCase):
    def test_loads_only_test_splits_and_never_exports_gold_answers(self) -> None:
        runner = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            slava = root / "slava.jsonl"
            slava.write_text(
                json.dumps(
                    {
                        "id": 7,
                        "instruction": "Назовите {item}.",
                        "inputs": {"item": "ответ"},
                        "outputs": "gold must not be exported",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            mera = root / "mera"
            (mera / "task-a").mkdir(parents=True)
            (mera / "task-a" / "test.jsonl").write_text(
                json.dumps(
                    {
                        "instruction": "Выберите {option}.",
                        "inputs": {"option": "верный вариант"},
                        "outputs": "hidden-or-empty",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            (mera / "task-a" / "train.jsonl").write_text(
                json.dumps(
                    {
                        "instruction": "Нельзя включать train.",
                        "inputs": {},
                        "outputs": "train gold",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            tasks = runner.load_tasks(slava, mera)

        self.assertEqual([task.task_id for task in tasks], ["slava:7", "mera:task-a:0"])
        self.assertEqual(tasks[0].prompt, "Назовите ответ.")
        self.assertEqual(tasks[1].prompt, "Выберите верный вариант.")
        self.assertNotIn("gold", runner.batch_prompt(tasks))

    def test_parse_requires_one_nonempty_answer_for_each_task_id(self) -> None:
        runner = load_module()
        task_ids = ["slava:7", "mera:task-a:0"]

        parsed = runner.parse_batch_answer(
            '{"records":[{"id":"slava:7","answer":"x"},'
            '{"id":"mera:task-a:0","answer":"y"}]}',
            task_ids,
        )
        self.assertEqual(parsed, {"slava:7": "x", "mera:task-a:0": "y"})

        with self.assertRaises(ValueError):
            runner.parse_batch_answer('{"records":[{"id":"slava:7","answer":"x"}]}', task_ids)

    def test_m3_request_disables_thinking_without_unsupported_json_schema(self) -> None:
        runner = load_module()
        task_ids = ["slava:7"]
        payload = runner.omniroute_payload("minimax/MiniMax-M3", "prompt", 256)

        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertTrue(payload["reasoning_split"])
        self.assertEqual(payload["max_completion_tokens"], 256)
        self.assertNotIn("response_format", payload)

    def test_two_shards_are_disjoint_and_keep_rutie_out_of_parallel_lanes(self) -> None:
        runner = load_module()
        tasks = [
            runner.Task(f"slava:{index}", "slava", "open", index, "prompt")
            for index in range(40)
        ] + [
            runner.Task(f"mera:rutie:{index}", "mera", "rutie", index, "", True)
            for index in range(3)
        ]

        first = runner.select_shard(tasks, 0, 2, include_sequential=True)
        second = runner.select_shard(tasks, 1, 2, include_sequential=True)
        first_ids = {task.task_id for task in first}
        second_ids = {task.task_id for task in second}

        self.assertFalse(first_ids & second_ids)
        self.assertEqual(first_ids | second_ids, {task.task_id for task in tasks})
        self.assertFalse(any(task.task == "rutie" for task in first))
        self.assertEqual(
            [task.task_id for task in second if task.task == "rutie"],
            ["mera:rutie:0", "mera:rutie:1", "mera:rutie:2"],
        )
        self.assertFalse(any(task.sequential for task in runner.select_shard(tasks, 1, 2)))

    def test_rutie_prompt_uses_prior_filtered_answer_as_context(self) -> None:
        runner = load_module()
        previous = {
            "instruction": "Ввод:\n{context}\n{question}\n1. {choice1}\n2. {choice2}\nОтвет:",
            "inputs": {"question": "Предыдущий", "choice1": "да", "choice2": "нет"},
            "meta": {"dialog_id": 0, "question_id": 0},
        }
        current = {
            "instruction": "Ввод:\n{context}\n{question}\n1. {choice1}\n2. {choice2}\nОтвет:",
            "inputs": {"question": "Текущий", "choice1": "верно", "choice2": "неверно"},
            "meta": {"dialog_id": 0, "question_id": 1},
        }

        prompt = runner.rutie_prompt(current, [previous], {0: "2"})

        self.assertEqual(
            prompt,
            "Ввод:\nПредыдущий\n1. да\n2. нет\nОтвет: 2\n\n"
            "Текущий\n1. верно\n2. неверно\nОтвет:",
        )
        self.assertEqual(runner.normalize_rutie_answer("Выбор: 2."), "2")
        self.assertEqual(runner.normalize_rutie_answer("без цифры"), "-1")

    def test_rutie_resume_rebuilds_context_from_completed_records(self) -> None:
        runner = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mera = root / "mera"
            (mera / "rutie").mkdir(parents=True)
            rows = [
                {
                    "instruction": "Ввод:\n{context}\n{question}\n1. {choice1}\n2. {choice2}\nОтвет:",
                    "inputs": {"question": "Первый", "choice1": "а", "choice2": "б"},
                    "meta": {"dialog_id": 0, "question_id": 0},
                },
                {
                    "instruction": "Ввод:\n{context}\n{question}\n1. {choice1}\n2. {choice2}\nОтвет:",
                    "inputs": {"question": "Второй", "choice1": "в", "choice2": "г"},
                    "meta": {"dialog_id": 0, "question_id": 1},
                },
            ]
            (mera / "rutie" / "test.jsonl").write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )
            output = root / "answers.jsonl"
            output.write_text(
                json.dumps(
                    {"id": "mera:rutie:0", "task": "rutie", "index": 0, "answer": "2"},
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            observed_prompts = []
            original_run = runner.run_codex
            runner.run_codex = lambda *args: observed_prompts.append(args[1]) or '{"records":[{"id":"mera:rutie:1","answer":"1"}]}'
            try:
                runner.run_rutie_codex("sol", output, root, mera, 1)
            finally:
                runner.run_codex = original_run

        self.assertEqual(len(observed_prompts), 1)
        self.assertIn("Первый\n1. а\n2. б\nОтвет: 2", observed_prompts[0])

    def test_codex_retries_a_transient_failure_before_returning_output(self) -> None:
        runner = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            schema = root / "schema.json"
            answer = root / "answer.json"
            calls = []

            def fake_run(*args, **kwargs):
                calls.append(1)
                command = args[0]
                answer_path = Path(command[command.index("-o") + 1])
                if len(calls) == 2:
                    answer_path.write_text('{"records":[]}', encoding="utf-8")
                    return type("Result", (), {"returncode": 0, "stderr": ""})()
                return type("Result", (), {"returncode": 1, "stderr": "temporary unavailable"})()

            with patch.object(runner.subprocess, "run", side_effect=fake_run), patch.object(runner.time, "sleep"):
                result = runner.run_codex("sol", "prompt", {"type": "object"}, 1, root, retries=1)

        self.assertEqual(result, '{"records":[]}')
        self.assertEqual(len(calls), 2)

    def test_batch_prompt_requires_machine_readable_records(self) -> None:
        runner = load_module()
        task = runner.Task("slava:1", "slava", "open", 1, "Ответ")
        prompt = runner.batch_prompt([task])
        self.assertIn('"records"', prompt)
        self.assertIn('"answer"', prompt)
        self.assertIn("каждый запрошенный id", prompt) if "каждый запрошенный id" in prompt else self.assertIn("every requested id", prompt)


if __name__ == "__main__":
    unittest.main()
