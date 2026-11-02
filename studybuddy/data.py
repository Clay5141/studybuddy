"""Built-in lesson content for StudyBuddy.

Each lesson is a short English passage plus a word list. Every word
carries the four pieces the Tutor needs for the StudyBuddy teaching
method (never just "reading aloud"):

1. how it sounds      -> ``phonetic`` + ``syllables``
2. why it sounds so   -> ``phonics_note`` (one simple spelling rule, in Chinese)
3. spell it with me   -> derived from the word's letters
4. now you try        -> ``example`` sentence used as the practice task

Content is written for Chinese primary / junior-high students (CEFR A1-A2)
in under-resourced areas who often have no English teacher at home.
"""

from __future__ import annotations

from typing import Any

LESSONS: list[dict[str, Any]] = [
    {
        "id": "school-day",
        "title": "My School Day",
        "level": "A1",
        "intro_zh": "课文讲的是小明在学校的一天，里面的词都是学校生活里最常用的。",
        "passage": (
            "I get up at seven. I go to school by bus. "
            "My favourite subject is English. "
            "At noon, I have lunch with my friends in the playground. "
            "After school, I do my homework in the library."
        ),
        "words": [
            {
                "word": "subject",
                "phonetic": "/ˈsʌb.dʒɪkt/",
                "syllables": ["sub", "ject"],
                "meaning_zh": "科目；学科",
                "phonics_note": "字母 j 在这里发 /dʒ/，和 juice 里的 j 一样，是舌尖顶住上颚再放开的声音。",
                "example": "My favourite subject is English.",
            },
            {
                "word": "playground",
                "phonetic": "/ˈpleɪ.ɡraʊnd/",
                "syllables": ["play", "ground"],
                "meaning_zh": "操场；游乐场",
                "phonics_note": "这是个合成词：play（玩）+ ground（地面）。ay 发 /eɪ/，ou 发 /aʊ/，看到长词先拆成认识的小词就不怕了。",
                "example": "We play games in the playground.",
            },
            {
                "word": "homework",
                "phonetic": "/ˈhəʊm.wɜːk/",
                "syllables": ["home", "work"],
                "meaning_zh": "家庭作业",
                "phonics_note": "也是合成词：home（家）+ work（活儿）= 在家做的活儿，就是作业。o 在 home 里发 /əʊ/。",
                "example": "I do my homework after dinner.",
            },
            {
                "word": "library",
                "phonetic": "/ˈlaɪ.brər.i/",
                "syllables": ["li", "brar", "y"],
                "meaning_zh": "图书馆",
                "phonics_note": "字母 i 在这里发 /aɪ/，和 light 里的 i 一样；中间的 br 连读要快，整个词读成三拍：LI-brar-y。",
                "example": "The library is quiet.",
            },
            {
                "word": "friend",
                "phonetic": "/frend/",
                "syllables": ["friend"],
                "meaning_zh": "朋友",
                "phonics_note": "小心陷阱：friend 里的 ie 不发音，只发 /e/。记住一句话——朋友（friend）陪你到最后（end），词尾就是 end。",
                "example": "She is my best friend.",
            },
        ],
    },
    {
        "id": "four-seasons",
        "title": "The Four Seasons",
        "level": "A2",
        "intro_zh": "课文讲四季的变化，学完能用英语说清楚每个季节的天气和活动。",
        "passage": (
            "There are four seasons in a year. "
            "Spring is warm, and the flowers come out. "
            "Summer is hot, so we swim in the river. "
            "Autumn is cool, and the leaves turn yellow. "
            "Winter is cold, and sometimes it snows."
        ),
        "words": [
            {
                "word": "season",
                "phonetic": "/ˈsiː.zən/",
                "syllables": ["sea", "son"],
                "meaning_zh": "季节",
                "phonics_note": "ea 在这里发长音 /iː/，和 sea（大海）里的 ea 一样。把 season 拆成 sea + son 来记，又好读又好记。",
                "example": "Spring is my favourite season.",
            },
            {
                "word": "weather",
                "phonetic": "/ˈweð.ə/",
                "syllables": ["wea", "ther"],
                "meaning_zh": "天气",
                "phonics_note": "th 在这里发 /ð/，舌尖要轻轻咬住再送气，和 the、this 是同一个音，千万别读成 /s/。",
                "example": "The weather is fine today.",
            },
            {
                "word": "autumn",
                "phonetic": "/ˈɔː.təm/",
                "syllables": ["au", "tumn"],
                "meaning_zh": "秋天",
                "phonics_note": "两个陷阱：au 发 /ɔː/；词尾的 n 不发音！秋天是 silent n，读成 AU-tum 就对了。",
                "example": "The leaves fall in autumn.",
            },
            {
                "word": "because",
                "phonetic": "/bɪˈkɔːz/",
                "syllables": ["be", "cause"],
                "meaning_zh": "因为",
                "phonics_note": "重音在后面：be-CAUSE。au 发 /ɔː/，词尾 se 发 /z/ 不是 /s/，轻轻震动声带。",
                "example": "I stay at home because it rains.",
            },
            {
                "word": "sometimes",
                "phonetic": "/ˈsʌm.taɪmz/",
                "syllables": ["some", "times"],
                "meaning_zh": "有时候",
                "phonics_note": "合成词 some（一些）+ times（次数）= 有些时候。i 在 times 里发 /aɪ/，和 time 里的 i 一样。",
                "example": "Sometimes we walk to school.",
            },
        ],
    },
]

LESSON_INDEX: dict[str, dict[str, Any]] = {lesson["id"]: lesson for lesson in LESSONS}


def get_lesson(lesson_id: str) -> dict[str, Any]:
    """Return a lesson by id, raising KeyError with a friendly message."""
    try:
        return LESSON_INDEX[lesson_id]
    except KeyError:
        known = ", ".join(sorted(LESSON_INDEX))
        raise KeyError(f"Unknown lesson '{lesson_id}'. Available: {known}") from None


def all_words() -> list[dict[str, Any]]:
    """Flat list of every word across lessons (used as distractors)."""
    return [word for lesson in LESSONS for word in lesson["words"]]
