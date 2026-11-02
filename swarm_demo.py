#!/usr/bin/env python3
"""One-shot full lesson through a genuine Strands Swarm (live mode only).

    STUDYBUDDY_MODE=live python swarm_demo.py

The three specialist agents (Tutor -> QuizMaster -> Coach) hand off to
each other autonomously via the SDK's handoff_to_agent tool — no
orchestrator code decides the order; each agent's system prompt does.
This is the multi-agent pattern from the Strands Agents SDK learning
path ("Multi-agent patterns: agent swarms") applied to a classroom.

Requires AWS credentials with Amazon Bedrock access (see README).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from studybuddy.config import load_settings  # noqa: E402


def main() -> int:
    settings = load_settings()
    if settings.is_mock:
        print(
            "swarm_demo.py needs live mode (real model calls).\n"
            "Set STUDYBUDDY_MODE=live and configure AWS credentials, "
            "or use `python app.py --mode mock` for the offline demo."
        )
        return 2

    from studybuddy.agents import build_swarm, swarm_result_text

    swarm = build_swarm(settings)
    result = swarm(
        "给学生 xiaoming 上一节完整的英语课，课文是 school-day："
        "先由 Tutor 按四步教学法讲解全部生词，然后 QuizMaster 出题"
        "（学生口头作答：意思题选出正确答案，填空题填课文原词），"
        "最后 Coach 汇总本课要点、指出最容易错的两个词并给出下一步建议。"
    )
    print(swarm_result_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
