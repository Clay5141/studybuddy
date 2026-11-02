# StudyBuddy 学伴 — a Multi-Agent English Tutor for Kids Who Have No English Teacher

**Built with the Strands Agents SDK for the AWS "Strands SDK: Workshop to Ship" hackathon (Social Good · Education).**

## The problem

Across rural and under-resourced parts of China, many primary- and
junior-high-school students study English with **no English teacher
available outside the classroom** — sometimes not even inside it.
Parents often cannot help: they never learned English pronunciation
themselves. A textbook page read silently teaches almost nothing,
because nobody shows the student *how* a word sounds, *why* it sounds
that way, or whether their own attempt was right.

## The solution: three AI teachers, one lesson

StudyBuddy splits the job of a good English teacher into three
specialised agents that collaborate on every lesson:

| Agent | Role | What it does |
|---|---|---|
| 🎓 **Tutor** 讲解员 | Teaches | Explains every new word with a strict 4-step method: **1) how to say it** (IPA + syllables), **2) why it sounds that way** (one simple phonics rule), **3) spell it with me** (letter by letter), **4) now you try** (guided sentence practice). Never dry reading. |
| 📝 **QuizMaster** 出题官 | Practises | Turns the lesson text into guided exercises — multiple choice, fill-in-the-blank, spelling, read-aloud — adapted to the student's level and weak words. |
| 🏅 **Coach** 教练 | Feedback | Grades answers, explains *why* each mistake happened, records weak points into a persistent learner profile, and gives encouragement plus a concrete next step. |

Progress is stored per student (one JSON file each): word mastery
(0–5), weak-word list, level (1–3). Weak words are automatically fed
back into the next exercise set, and the level rises or falls with
performance — a simple, transparent adaptive-learning loop.

## Social impact

* **For students without teachers**: a patient tutor that demonstrates
  pronunciation pedagogy, not just text — on any device with a browser.
* **Cheap to run**: the default model is Amazon Nova Micro on Bedrock;
  grading and exercise generation are deterministic tools, so most of
  the loop costs nothing and is reproducible in classrooms.
* **Runs anywhere**: the web UI uses only the Python standard library;
  mock mode runs fully offline for demos and low-connectivity schools.
* **Measurable progress**: mastery bars and session history make
  improvement visible to students, parents and teachers.

## Architecture

```
                        ┌─────────────────────────────┐
   Student (browser) ──▶│  Web UI (single page)       │
                        │  web/server.py (stdlib)     │
                        └──────────────┬──────────────┘
                                       │ JSON API
                        ┌──────────────▼──────────────┐
                        │  SessionRunner              │
                        │  teach ─▶ quiz ─▶ grade     │
                        └──────┬───────────────┬──────┘
              live mode        │               │        both modes
        ┌──────────────────────▼───┐   ┌───────▼──────────────────┐
        │ Strands Agents SDK       │   │ Deterministic tools      │
        │                          │   │  lookup_word             │
        │  Tutor ──▶ QuizMaster    │   │  generate_exercises      │
        │    ╲        │              │   │  grade_answers           │
        │     ╲       ▼              │   │  get/record_progress ────┼─▶ data/progress/
        │      ╲──▶ Coach            │   └──────────────────────────┘     <student>.json
        │  (Swarm handoffs, or a     │
        │   coordinator using the    │
        │   agents as tools)         │
        │  Model: BedrockModel       │
        │  (Nova Micro, us-east-1)   │
        └────────────────────────────┘
```

Design principle: **the LLM teaches, the tools judge.** Generation is
what the agents are for; scoring children must be fair, explainable
and reproducible, so exercises and grading run through typed tools
the agents call (and that mock mode calls directly).

### Strands Agents SDK APIs used

All verified against the official documentation (strandsagents.com):

* `from strands import Agent, tool` — `Agent(name=, model=, system_prompt=, tools=, callback_handler=None)`, invoked as `agent("...")` (Python Quickstart).
* `from strands.models import BedrockModel` — `BedrockModel(model_id=..., region_name=..., temperature=...)` (Model Providers docs).
* `@tool` decorator for custom tools (vocabulary lookup, exercise generation, progress I/O) with docstring-driven schemas.
* `from strands.multiagent import Swarm` — `Swarm([agents], entry_point=..., max_handoffs=..., max_iterations=...)`; agents hand off via the SDK-injected `handoff_to_agent` tool (Learning path: *Multi-agent patterns: agent swarms*).
* Agents-as-tools: specialist agents wrapped in `@tool` functions for a coordinator agent (documented multi-agent pattern).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) Offline demo — no AWS account needed:
python app.py --mode mock            # full lesson in the terminal
STUDYBUDDY_MODE=mock python web/server.py   # http://localhost:8000

# 2) Live mode — real agents on Amazon Bedrock:
export STUDYBUDDY_MODE=live
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID=us.amazon.nova-micro-v1:0
# + AWS credentials (aws configure / env vars / IAM role),
#   with Bedrock model access enabled for Nova Micro in us-east-1
python app.py                        # step-by-step lesson, live Tutor
python swarm_demo.py                 # one-shot lesson via a real Swarm
STUDYBUDDY_MODE=live python web/server.py
```

## Project layout

```
app.py                  CLI: scripted end-to-end lesson (demo/testing)
swarm_demo.py           One-shot lesson through a Strands Swarm (live)
studybuddy/
  config.py             Environment-driven settings (mode/model/region)
  data.py               Built-in lessons + vocabulary with phonics notes
  tools.py              Word lookup, exercise generation, grading,
                        progress JSON — plain functions + @tool wrappers
  agents.py             BedrockModel, 3 specialist agents, coordinator
                        (agents-as-tools) and Swarm builders (live)
  mock.py               Deterministic offline stand-ins for the agents
  session.py            SessionRunner: teach -> quiz -> grade (both modes)
web/
  server.py             Stdlib HTTP server + JSON API
  static/index.html     Single-page UI: watch the 3 agents work in turns
data/progress/          Per-student progress JSON files (created at runtime)
```

## What a demo shows (under 3 minutes)

1. Pick the lesson *My School Day* → Tutor teaches `library` the
   4-step way (no dry reading).
2. QuizMaster generates a set adapted to the student's level.
3. The student answers (one deliberate mistake) → Coach names the
   error cause, files the weak word, and the progress panel updates.
4. Start again: the weak word comes back first — the adaptive loop
   closes on camera.

## Notes & limitations

* Content currently ships two A1–A2 lessons; adding a lesson is one
  entry in `studybuddy/data.py`.
* Read-aloud exercises are practice tasks (unscored) — automatic
  pronunciation scoring is future work.
* Sessions are in-memory in the demo server; progress files persist.
