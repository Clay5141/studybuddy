"""StudyBuddy tools — plain Python functions with real, deterministic logic.

The same functions are used in two ways:

* **Live mode** — they are wrapped with the Strands Agents SDK ``@tool``
  decorator (see ``strands_tools`` below) and handed to the Tutor /
  QuizMaster / Coach agents, which decide when to call them.
* **Mock mode** — the offline stand-ins in ``mock.py`` call them directly,
  so the full flow (vocabulary lookup, exercise generation, grading,
  progress tracking) is exercised without any model or AWS account.

Progress is stored as one JSON file per student under the data dir
(configurable with STUDYBUDDY_DATA_DIR), e.g. ``data/progress/xiaoming.json``.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any

from .config import load_settings
from .data import all_words, get_lesson

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


def lookup_word(word: str, lesson_id: str = "") -> dict[str, Any]:
    """Look up a word's phonetics, meaning and teaching notes.

    Args:
        word: The English word to look up, e.g. "library".
        lesson_id: Optional lesson id to scope the search.

    Returns:
        A dict with phonetic, syllables, meaning_zh, phonics_note and
        example, or {"found": False} when the word is not in the content.
    """
    pool = get_lesson(lesson_id)["words"] if lesson_id else all_words()
    for entry in pool:
        if entry["word"].lower() == word.strip().lower():
            return {"found": True, "lesson_id": lesson_id or _lesson_of(entry), **entry}
    return {"found": False, "word": word}


def _lesson_of(word_entry: dict[str, Any]) -> str:
    from .data import LESSONS

    for lesson in LESSONS:
        if word_entry in lesson["words"]:
            return lesson["id"]
    return ""


# ---------------------------------------------------------------------------
# Exercise generation (QuizMaster's toolbox)
# ---------------------------------------------------------------------------


def generate_exercises(
    lesson_id: str,
    difficulty: int = 1,
    weak_words: list[str] | None = None,
    count: int = 4,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """Generate a guided practice set from a lesson.

    Exercise types by difficulty:
      1 -> multiple choice only ("这个词是什么意思？")
      2 -> multiple choice + fill-in-the-blank from the passage
      3 -> fill-in-the-blank + spelling (type the word from meaning+phonetic)
    Every set also ends with one unscored read-aloud task.

    Weak words (from the student's progress) are always included first,
    which is what makes the difficulty adaptive per student.

    Args:
        lesson_id: Lesson to draw words/sentences from.
        difficulty: 1, 2 or 3.
        weak_words: Words the student previously got wrong; prioritised.
        count: Number of scored exercises to generate.
        seed: Optional RNG seed for reproducible sets (used in tests/demo).

    Returns:
        A list of exercise dicts. Each has id, type, word, prompt and —
        for scored types — options (choice) and answer.
    """
    rng = random.Random(seed)
    lesson = get_lesson(lesson_id)
    words = list(lesson["words"])
    weak = [w for w in words if weak_words and w["word"] in weak_words]
    rest = [w for w in words if w not in weak]
    rng.shuffle(rest)
    chosen = (weak + rest)[:count]

    exercises: list[dict[str, Any]] = []
    for i, entry in enumerate(chosen, start=1):
        if difficulty <= 1:
            kind = "choice"
        elif difficulty == 2:
            kind = "choice" if i % 2 == 1 else "fill"
        else:
            kind = "fill" if i % 2 == 1 else "spell"
        exercises.append(_make_exercise(kind, entry, lesson, rng, i))

    last = chosen[-1] if chosen else words[0]
    exercises.append(
        {
            "id": f"q{len(exercises) + 1}",
            "type": "repeat",
            "word": last["word"],
            "prompt": f"跟读任务：请大声读三遍这个句子 —— “{last['example']}” 读的时候注意 {last['word']} 的发音 {last['phonetic']}。",
            "scored": False,
        }
    )
    return exercises


def _make_exercise(
    kind: str, entry: dict[str, Any], lesson: dict[str, Any], rng: random.Random, idx: int
) -> dict[str, Any]:
    word = entry["word"]
    base = {"id": f"q{idx}", "type": kind, "word": word, "scored": True}
    if kind == "choice":
        distractors = rng.sample(
            [w["meaning_zh"] for w in all_words() if w["meaning_zh"] != entry["meaning_zh"]],
            k=3,
        )
        options = distractors + [entry["meaning_zh"]]
        rng.shuffle(options)
        return {
            **base,
            "prompt": f"单词 “{word}” {entry['phonetic']} 的意思是？",
            "options": options,
            "answer": entry["meaning_zh"],
        }
    if kind == "fill":
        sentence = _sentence_with_word(lesson["passage"], word) or entry["example"]
        blanked = re.sub(re.escape(word), "______", sentence, flags=re.IGNORECASE)
        return {
            **base,
            "prompt": f"填空：{blanked}（填入课文中学过的词）",
            "answer": word,
        }
    # spell
    return {
        **base,
        "prompt": f"拼写：请拼出意思是「{entry['meaning_zh']}」、读音 {entry['phonetic']} 的单词。",
        "answer": word,
    }


def _sentence_with_word(passage: str, word: str) -> str | None:
    for sentence in re.split(r"(?<=[.!?])\s+", passage):
        if re.search(rf"\b{re.escape(word)}\b", sentence, flags=re.IGNORECASE):
            return sentence
    return None


# ---------------------------------------------------------------------------
# Grading (Coach's toolbox)
# ---------------------------------------------------------------------------


def grade_answers(
    exercises: list[dict[str, Any]], answers: dict[str, str]
) -> dict[str, Any]:
    """Grade submitted answers against an exercise set.

    Comparison is forgiving for children: case-insensitive and tolerant
    of surrounding whitespace / trailing punctuation.

    Args:
        exercises: The exercise list produced by generate_exercises.
        answers: Mapping of exercise id -> student's answer.

    Returns:
        {"score": int, "total": int, "items": [...], "weak_words": [...]}
        Each item explains *why* a wrong answer is wrong using the word's
        phonics note, so the Coach can teach from it.
    """
    items: list[dict[str, Any]] = []
    weak_words: list[str] = []
    score = 0
    total = 0
    for ex in exercises:
        if not ex.get("scored"):
            items.append(
                {"id": ex["id"], "type": ex["type"], "word": ex["word"],
                 "correct": None, "note": "跟读任务不计分，读出声就算完成。"}
            )
            continue
        total += 1
        given = str(answers.get(ex["id"], "")).strip()
        expected = str(ex["answer"])
        correct = _normalise(given) == _normalise(expected)
        if correct:
            score += 1
            note = "答对了！"
        else:
            weak_words.append(ex["word"])
            entry = lookup_word(ex["word"])
            note = (
                f"正确答案是「{expected}」。"
                f"错因提醒：{entry.get('phonics_note', '')}"
            )
        items.append(
            {"id": ex["id"], "type": ex["type"], "word": ex["word"],
             "given": given, "expected": expected, "correct": correct, "note": note}
        )
    return {"score": score, "total": total, "items": items, "weak_words": weak_words}


def _normalise(text: str) -> str:
    return re.sub(r"[\s。.!！?？]+$", "", text.strip().lower())


# ---------------------------------------------------------------------------
# Progress tracking (Coach's toolbox) — one JSON file per student
# ---------------------------------------------------------------------------


def _progress_path(student_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", student_id.strip()) or "student"
    data_dir = load_settings().data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / f"{safe}.json"


def get_progress(student_id: str) -> dict[str, Any]:
    """Load a student's progress record (created empty on first use).

    Returns:
        {"student_id", "level", "sessions", "mastery": {word: 0-5},
         "weak_words": [...], "history": [...]}
    """
    path = _progress_path(student_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "student_id": student_id,
        "level": 1,
        "sessions": 0,
        "mastery": {},
        "weak_words": [],
        "history": [],
    }


def record_progress(
    student_id: str,
    lesson_id: str,
    grade: dict[str, Any],
) -> dict[str, Any]:
    """Update and persist a student's progress after a graded session.

    Mastery moves +1 for each correct word and -1 for each wrong word
    (clamped to 0..5). Words below mastery 2 stay on the weak list and
    are fed back into the next exercise set. Level rises when a session
    is fully correct, and drops back when most answers are wrong — the
    adaptive-difficulty loop QuizMaster relies on.

    Args:
        student_id: Student identifier (name or id).
        lesson_id: Lesson that was practised.
        grade: The dict returned by grade_answers.

    Returns:
        The updated progress record.
    """
    progress = get_progress(student_id)
    mastery = progress.setdefault("mastery", {})
    for item in grade["items"]:
        if item.get("correct") is None:
            continue
        word = item["word"]
        delta = 1 if item["correct"] else -1
        mastery[word] = max(0, min(5, mastery.get(word, 0) + delta))

    # Weak words = anything not yet mastered (mastery below 2). They are
    # fed back into the next exercise set by generate_exercises.
    progress["weak_words"] = sorted(w for w, m in mastery.items() if m < 2)
    progress["sessions"] = progress.get("sessions", 0) + 1
    if grade["total"] and grade["score"] == grade["total"]:
        progress["level"] = min(3, progress.get("level", 1) + 1)
    elif grade["total"] and grade["score"] * 2 < grade["total"]:
        progress["level"] = max(1, progress.get("level", 1) - 1)
    progress.setdefault("history", []).append(
        {
            "lesson_id": lesson_id,
            "score": grade["score"],
            "total": grade["total"],
            "weak_words": grade.get("weak_words", []),
        }
    )
    _progress_path(student_id).write_text(
        json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return progress


# ---------------------------------------------------------------------------
# Strands @tool wrappers (live mode only)
#
# The functions above stay plain so mock mode and unit checks can import
# this module without the SDK. When strands-agents is installed, the
# wrappers below expose the very same logic as proper Strands tools.
# ---------------------------------------------------------------------------


def strands_tools() -> list:
    """Return the tools as Strands ``@tool`` objects for live agents."""
    from strands import tool

    @tool
    def lookup_word_tool(word: str, lesson_id: str = "") -> str:
        """Look up a word's phonetic transcription, Chinese meaning and pronunciation notes.

        Args:
            word: The English word to look up.
            lesson_id: Optional lesson id to scope the search.
        """
        return json.dumps(lookup_word(word, lesson_id), ensure_ascii=False)

    @tool
    def generate_exercises_tool(
        lesson_id: str, difficulty: int = 1, weak_words: str = ""
    ) -> str:
        """Generate a guided practice set (choice / fill-in-blank / spelling) for a lesson.

        Args:
            lesson_id: The lesson id, e.g. "school-day".
            difficulty: 1, 2 or 3 — higher means harder question types.
            weak_words: Comma-separated words the student previously missed;
                they are always practised first.
        """
        weak = [w.strip() for w in weak_words.split(",") if w.strip()]
        exercises = generate_exercises(lesson_id, difficulty, weak)
        return json.dumps(exercises, ensure_ascii=False)

    @tool
    def get_progress_tool(student_id: str) -> str:
        """Read a student's saved progress: level, word mastery and weak words.

        Args:
            student_id: The student's id or name.
        """
        return json.dumps(get_progress(student_id), ensure_ascii=False)

    @tool
    def record_progress_tool(student_id: str, lesson_id: str, grade_json: str) -> str:
        """Save the result of a graded session into the student's progress file.

        Args:
            student_id: The student's id or name.
            lesson_id: The lesson that was practised.
            grade_json: JSON string produced by the grading step.
        """
        updated = record_progress(student_id, lesson_id, json.loads(grade_json))
        return json.dumps(updated, ensure_ascii=False)

    return [lookup_word_tool, generate_exercises_tool, get_progress_tool, record_progress_tool]
