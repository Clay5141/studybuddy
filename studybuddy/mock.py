"""Offline mock stand-ins for the three StudyBuddy agents.

Used when STUDYBUDDY_MODE=mock (no AWS credentials). The replies are
deterministic and generated from the real lesson data and the real
tools in ``tools.py`` - only the *language generation* is canned.
This lets anyone run the complete Tutor -> QuizMaster -> Coach flow
(and the Web UI) with zero setup:

    STUDYBUDDY_MODE=mock python app.py

The mock Tutor still follows the house teaching method for every word:
1) how to say it, 2) why it sounds that way, 3) spell it with me,
4) now you try. Never dry reading.
"""

from __future__ import annotations

from typing import Any

from . import tools

ENCOURAGEMENTS = [
    "你已经比昨天更敢开口了，这就是进步。",
    "错不可怕，能找到错因，下次就不会再错。",
    "坚持每天练一点点，单词会一个一个被你拿下。",
]


def mock_teach(student_id: str, lesson_id: str) -> dict[str, Any]:
    """Tutor's lesson, built word by word with the 4-step method."""
    from .data import get_lesson

    lesson = get_lesson(lesson_id)
    progress = tools.get_progress(student_id)
    lines = [
        f"【讲解员 Tutor】你好，我是你的英语讲解员。今天我们学《{lesson['title']}》"
        f"（难度 {lesson['level']}）。{lesson['intro_zh']}",
        f"先把课文读给你听，听的时候注意生词的发音：\n{lesson['passage']}",
    ]
    for entry in lesson["words"]:
        info = tools.lookup_word(entry["word"], lesson_id)
        spell = "-".join(list(entry["word"].upper()))
        lines.append(
            f"\n—— 单词 {entry['word']} ——\n"
            f"1) 怎么读：{entry['phonetic']}，按音节拆开是 "
            f"{' · '.join(info['syllables'])}，跟着我一拍一拍读。\n"
            f"2) 为什么这样读：{info['phonics_note']}\n"
            f"3) 跟我拼：{spell}，一边拼一边写，拼完再连起来读三遍。\n"
            f"4) 自己练：读一读这个句子，读完试着自己替换一个词造句 —— "
            f"“{info['example']}”"
        )
    if progress["weak_words"]:
        lines.append(
            "\n另外提醒：你上次的薄弱词是 "
            + "、".join(progress["weak_words"])
            + "，今天练习时出题官会先考它们，咱们把它们攻下来。"
        )
    lines.append("\n讲解完了！接下来交给【出题官 QuizMaster】给你出引导式练习。")
    return {"agent": "Tutor", "role": "讲解员", "text": "\n".join(lines)}


def mock_quiz(student_id: str, lesson_id: str, seed: int | None = None) -> dict[str, Any]:
    """QuizMaster's exercise set, adapted to the student's level/weak words."""
    progress = tools.get_progress(student_id)
    exercises = tools.generate_exercises(
        lesson_id,
        difficulty=progress["level"],
        weak_words=progress["weak_words"],
        seed=seed,
    )
    intro = (
        f"【出题官 QuizMaster】根据你现在的等级（Lv.{progress['level']}）"
        f"和薄弱点，我为你准备了 {len(exercises)} 道题。"
        "先做会的，拿不准的回想一下讲解员讲的拼读规律。做完交给【教练 Coach】批改。"
    )
    return {
        "agent": "QuizMaster",
        "role": "出题官",
        "text": intro,
        "exercises": exercises,
        "difficulty": progress["level"],
    }


def mock_coach(
    student_id: str,
    lesson_id: str,
    exercises: list[dict[str, Any]],
    answers: dict[str, str],
) -> dict[str, Any]:
    """Coach's grading report: score, error causes, weak spots, next step."""
    grade = tools.grade_answers(exercises, answers)
    progress = tools.record_progress(student_id, lesson_id, grade)

    lines = [f"【教练 Coach】批改完成：{grade['score']} / {grade['total']} 分。"]
    for item in grade["items"]:
        if item["correct"] is None:
            lines.append(f"· {item['word']}：{item['note']}")
        elif item["correct"]:
            lines.append(f"· {item['word']}：✅ {item['note']}")
        else:
            given = item["given"] or "（空）"
            lines.append(f"· {item['word']}：❌ 你写的是「{given}」。{item['note']}")
    if grade["weak_words"]:
        lines.append(
            "本次薄弱点：" + "、".join(grade["weak_words"])
            + "。我已经记进你的学习档案，下次出题会优先再考它们，直到你连续答对为止。"
        )
    else:
        lines.append("这次没有新的薄弱点，全部拿下！")
    lines.append(
        f"当前等级 Lv.{progress['level']}，已完成 {progress['sessions']} 次练习。"
    )
    if grade["weak_words"]:
        next_step = (
            "回到讲解员那里，把薄弱词按「怎么读—为什么—跟我拼—自己练」"
            "再过一遍，然后重新挑战一组练习。"
        )
    else:
        next_step = "可以进入下一课，或者把难度升一级挑战自己。"
    lines.append("下一步建议：" + next_step)
    lines.append(ENCOURAGEMENTS[progress["sessions"] % len(ENCOURAGEMENTS)])
    return {
        "agent": "Coach",
        "role": "教练",
        "text": "\n".join(lines),
        "grade": grade,
        "progress": progress,
    }
