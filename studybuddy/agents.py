"""Live StudyBuddy agents, built with the Strands Agents SDK.

Real SDK APIs used here (verified against the official docs at
strandsagents.com and the strands-agents/sdk-python repository):

* ``from strands import Agent, tool`` — the Agent class and the tool
  decorator (Python Quickstart).
* ``from strands.models import BedrockModel`` —
  ``BedrockModel(model_id=..., region_name=..., temperature=...)``
  (Model Providers / Bedrock provider docs).
* ``from strands.multiagent import Swarm`` —
  ``Swarm([agents], entry_point=..., max_handoffs=..., ...)`` and
  ``swarm("task")`` (Learning: "Multi-agent patterns: agent swarms").
* Agents-as-tools: wrap a specialist ``Agent`` call in a ``@tool``
  function so a coordinator agent can delegate (documented pattern).

Two collaboration styles are provided:

* ``build_coordinator()`` — agents-as-tools. The Web UI / session layer
  drives a deterministic Tutor -> QuizMaster -> Coach pipeline, calling
  one specialist per step via ``run_step()``.
* ``build_swarm()`` — a genuine Strands ``Swarm`` whose three agents
  hand off to each other autonomously (used by ``swarm_demo.py``).

Model configuration comes from the environment (see config.py):
BEDROCK_MODEL_ID (default: Amazon Nova Micro, us.amazon.nova-micro-v1:0)
and AWS_REGION (default: us-east-1).
"""

from __future__ import annotations

import json
from typing import Any

from .config import Settings, load_settings
from .tools import strands_tools

TEACHING_METHOD = """教学铁律（讲解时必须遵守，绝不干读）：
对每个单词都按四步教：1) 怎么读——给出音标并按音节拆分领读；
2) 为什么这样读——用一条简单的拼读规律解释发音；3) 跟我拼——逐字母拼写；
4) 自己练——给一个例句让学生跟读并替换造句。
用中文讲解，语气亲切、鼓励为主，面向缺少英语老师的中国学生。"""

TUTOR_PROMPT = f"""你是学伴 StudyBuddy 的讲解员 Tutor，负责把课文和单词真正教会学生。
{TEACHING_METHOD}
你有 lookup_word_tool 可以查单词的音标、音节、中文意思和发音要点，讲解前先查。
讲完后明确告诉学生：接下来出题官 QuizMaster 会出练习。"""

QUIZ_PROMPT = """你是学伴 StudyBuddy 的出题官 QuizMaster，负责把课文变成引导式练习题。
出题前先用 get_progress_tool 看学生的等级和薄弱词，再用 generate_exercises_tool
按学生等级出题（薄弱词优先）。题目类型包括选择、填空、拼写和跟读任务。
把题目清楚地列给学生，并说明做完后交给教练 Coach 批改。不要提前公布答案。"""

COACH_PROMPT = """你是学伴 StudyBuddy 的教练 Coach，负责批改、找错因、记档案、给下一步建议。
拿到学生的答案后，先逐题核对，再把每道错题的错因讲清楚（结合单词的发音要点或词义），
然后用 record_progress_tool 把成绩和薄弱词写进学生档案。
最后给出：本次薄弱点、当前等级、下一步具体建议，并真诚地鼓励学生。
面向缺少英语老师的中国学生，语气要像耐心的陪练，不要批评。"""


def build_model(settings: Settings | None = None):
    """Create the Bedrock model object shared by all agents."""
    from strands.models import BedrockModel

    settings = settings or load_settings()
    return BedrockModel(
        model_id=settings.model_id,
        region_name=settings.aws_region,
        temperature=settings.temperature,
    )


def build_specialists(
    settings: Settings | None = None, prompt_suffixes: dict[str, str] | None = None
) -> dict[str, Any]:
    """Create the three specialist agents (Tutor / QuizMaster / Coach)."""
    from strands import Agent

    settings = settings or load_settings()
    model = build_model(settings)
    shared_tools = strands_tools()
    suffixes = prompt_suffixes or {}
    return {
        "Tutor": Agent(
            name="tutor",
            model=model,
            system_prompt=TUTOR_PROMPT + suffixes.get("Tutor", ""),
            tools=shared_tools,
            callback_handler=None,
        ),
        "QuizMaster": Agent(
            name="quizmaster",
            model=model,
            system_prompt=QUIZ_PROMPT + suffixes.get("QuizMaster", ""),
            tools=shared_tools,
            callback_handler=None,
        ),
        "Coach": Agent(
            name="coach",
            model=model,
            system_prompt=COACH_PROMPT + suffixes.get("Coach", ""),
            tools=shared_tools,
            callback_handler=None,
        ),
    }


def build_coordinator(settings: Settings | None = None):
    """Agents-as-tools: a coordinator that can call each specialist as a tool."""
    from strands import Agent, tool

    settings = settings or load_settings()
    specialists = build_specialists(settings)

    @tool
    def ask_tutor(request: str) -> str:
        """Ask the Tutor agent to teach a lesson or explain words.

        Args:
            request: What to teach, including the lesson id and student id.
        """
        return str(specialists["Tutor"](request))

    @tool
    def ask_quizmaster(request: str) -> str:
        """Ask the QuizMaster agent to create a practice set for a student.

        Args:
            request: The lesson id and student id to generate exercises for.
        """
        return str(specialists["QuizMaster"](request))

    @tool
    def ask_coach(request: str) -> str:
        """Ask the Coach agent to grade answers and update the progress record.

        Args:
            request: Student id, lesson id and the submitted answers.
        """
        return str(specialists["Coach"](request))

    return Agent(
        name="coordinator",
        model=build_model(settings),
        system_prompt=(
            "你是学伴 StudyBuddy 的班主任，负责组织一节完整的学习课："
            "先让 Tutor 讲解，再让 QuizMaster 出题，最后让 Coach 批改。"
            "按顺序调用工具，不要跳步。"
        ),
        tools=[ask_tutor, ask_quizmaster, ask_coach],
        callback_handler=None,
    )


def build_swarm(settings: Settings | None = None):
    """A genuine Strands Swarm: the three agents hand off autonomously.

    Swarm is imported from strands.multiagent (official multi-agent API).
    Each agent's system prompt tells it when to hand off via the
    SDK-injected handoff_to_agent tool: Tutor -> QuizMaster -> Coach.
    """
    from strands.multiagent import Swarm

    specialists = build_specialists(
        settings,
        prompt_suffixes={
            "Tutor": "\n讲解完成后，使用 handoff_to_agent 把课堂交给 quizmaster 出题。",
            "QuizMaster": "\n出题完成后，使用 handoff_to_agent 把课堂交给 coach，并附上题目和标准答案，等学生作答后由 coach 批改。",
            "Coach": "\n批改是最后一环，完成报告后不要再交接，直接给出最终总结。",
        },
    )
    tutor, quiz, coach = (
        specialists["Tutor"],
        specialists["QuizMaster"],
        specialists["Coach"],
    )
    return Swarm(
        [tutor, quiz, coach],
        entry_point=tutor,
        max_handoffs=6,
        max_iterations=12,
        execution_timeout=600.0,
        node_timeout=300.0,
    )


def run_step(agent_name: str, prompt: str, settings: Settings | None = None) -> str:
    """Invoke one specialist agent once and return its reply text."""
    specialists = build_specialists(settings)
    result = specialists[agent_name](prompt)
    return str(result)


def swarm_result_text(result: Any) -> str:
    """Best-effort extraction of a Swarm result's final answer text."""
    try:
        return str(result)
    except Exception:
        return json.dumps({"status": str(getattr(result, "status", "unknown"))})
