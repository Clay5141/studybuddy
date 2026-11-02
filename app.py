#!/usr/bin/env python3
"""StudyBuddy CLI — run one full lesson end to end in the terminal.

    # Offline self-check (no AWS credentials needed):
    python app.py --mode mock

    # Live mode (Strands Agents SDK + Amazon Bedrock):
    STUDYBUDDY_MODE=live python app.py --lesson school-day

The scripted "student" answers most questions correctly and deliberately
misses one, so the Coach's error analysis, weak-word tracking and
progress recording are all exercised.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from studybuddy.config import load_settings  # noqa: E402
from studybuddy.session import SessionRunner  # noqa: E402


def scripted_answers(exercises_with_keys: list[dict]) -> dict[str, str]:
    """Answer like a real student: mostly right, one honest mistake."""
    answers: dict[str, str] = {}
    missed_one = False
    for ex in exercises_with_keys:
        if not ex.get("scored"):
            continue
        if not missed_one and ex["type"] == "choice":
            wrong = next(o for o in ex["options"] if o != ex["answer"])
            answers[ex["id"]] = wrong
            missed_one = True
        else:
            answers[ex["id"]] = ex["answer"]
    return answers


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a StudyBuddy lesson.")
    parser.add_argument("--mode", choices=["mock", "live"], default=None)
    parser.add_argument("--student", default="xiaoming")
    parser.add_argument("--lesson", default="school-day")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    if args.mode:
        os.environ["STUDYBUDDY_MODE"] = args.mode
    settings = load_settings()
    runner = SessionRunner(settings)

    print("=" * 68)
    print(f"学伴 StudyBuddy · 模式={settings.mode} · 学生={args.student} · 课文={args.lesson}")
    print("=" * 68)

    started = runner.start(args.student, args.lesson)
    print("\n" + started["tutor"]["text"])

    quiz = runner.quiz(started["session_id"], seed=args.seed)
    print("\n" + quiz["text"])
    for ex in quiz["exercises"]:
        print(f"\n[{ex['id']}] ({ex['type']}) {ex['prompt']}")
        for j, option in enumerate(ex.get("options", []), start=1):
            print(f"    {j}. {option}")

    # The runner keeps the answer key server-side; the CLI demo reads it
    # back from the session store to script the student's answers.
    keys = runner.sessions[started["session_id"]]["exercises"]
    answers = scripted_answers(keys)
    print("\n学生作答：", answers)

    report = runner.grade(started["session_id"], answers)
    print("\n" + report["text"])
    print("\n学习档案已保存:", report["progress"]["student_id"],
          "| 等级 Lv.%s" % report["progress"]["level"],
          "| 待巩固词(掌握度<2):", "、".join(report["progress"]["weak_words"]) or "无")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
