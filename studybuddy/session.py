"""Session layer: one StudyBuddy lesson = teach -> quiz -> grade.

``SessionRunner`` exposes the same three steps in both modes:

* mock - backed by the deterministic stand-ins in ``mock.py``;
* live - the teaching step calls the real Tutor agent (Strands +
  Bedrock). Exercise generation and grading stay tool-driven
  (generate_exercises / grade_answers / record_progress) in both modes
  on purpose: for a children's learning product, scoring must be fair,
  explainable and reproducible - the LLM teaches, the tools judge.
  The fully agent-driven variant (all three agents handing off inside
  a Strands Swarm) lives in ``swarm_demo.py``.

State is kept in memory (one dict per session) - enough for a demo and
for the single-process Web UI in ``web/server.py``.
"""

from __future__ import annotations

import uuid
from typing import Any

from . import mock, tools
from .config import Settings, load_settings
from .data import LESSONS, get_lesson


class SessionRunner:
    """Drives one student's lesson through the three agent steps."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self.sessions: dict[str, dict[str, Any]] = {}

    # -- helpers ------------------------------------------------------
    def list_lessons(self) -> list[dict[str, Any]]:
        return [
            {
                "id": lesson["id"],
                "title": lesson["title"],
                "level": lesson["level"],
                "word_count": len(lesson["words"]),
            }
            for lesson in LESSONS
        ]

    def progress(self, student_id: str) -> dict[str, Any]:
        return tools.get_progress(student_id)

    # -- step 1: Tutor teaches ----------------------------------------
    def start(self, student_id: str, lesson_id: str) -> dict[str, Any]:
        get_lesson(lesson_id)  # validate early
        session_id = uuid.uuid4().hex[:12]
        self.sessions[session_id] = {
            "student_id": student_id,
            "lesson_id": lesson_id,
            "exercises": [],
        }
        if self.settings.is_mock:
            tutor = mock.mock_teach(student_id, lesson_id)
        else:
            from .agents import run_step

            text = run_step(
                "Tutor",
                f"请为学生 {student_id} 讲解课文 {lesson_id}，"
                "严格按四步教学法逐词讲解，最后把课堂交给 QuizMaster。",
                self.settings,
            )
            tutor = {"agent": "Tutor", "role": "讲解员", "text": text}
        return {"session_id": session_id, "tutor": tutor}

    # -- step 2: QuizMaster sets exercises -----------------------------
    def quiz(self, session_id: str, seed: int | None = None) -> dict[str, Any]:
        session = self._session(session_id)
        student_id = session["student_id"]
        lesson_id = session["lesson_id"]
        if self.settings.is_mock:
            result = mock.mock_quiz(student_id, lesson_id, seed=seed)
        else:
            progress = tools.get_progress(student_id)
            exercises = tools.generate_exercises(
                lesson_id,
                difficulty=progress["level"],
                weak_words=progress["weak_words"],
                seed=seed,
            )
            result = {
                "agent": "QuizMaster",
                "role": "出题官",
                "text": (
                    f"【出题官 QuizMaster】根据学生等级 Lv.{progress['level']} 出题完成，"
                    f"共 {len(exercises)} 道。做完请交给教练 Coach 批改。"
                ),
                "exercises": exercises,
                "difficulty": progress["level"],
            }
        session["exercises"] = result["exercises"]
        # The answer key stays server-side; the UI only gets questions.
        public = [self._public_exercise(e) for e in result["exercises"]]
        return {**result, "exercises": public}

    # -- step 3: Coach grades -------------------------------------------
    def grade(self, session_id: str, answers: dict[str, str]) -> dict[str, Any]:
        session = self._session(session_id)
        if not session["exercises"]:
            raise ValueError("No exercises yet - call quiz() before grade().")
        return mock.mock_coach(
            session["student_id"],
            session["lesson_id"],
            session["exercises"],
            answers,
        )

    # -- internals -------------------------------------------------------
    def _session(self, session_id: str) -> dict[str, Any]:
        try:
            return self.sessions[session_id]
        except KeyError:
            raise KeyError(f"Unknown session '{session_id}'") from None

    @staticmethod
    def _public_exercise(exercise: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in exercise.items() if k != "answer"}
