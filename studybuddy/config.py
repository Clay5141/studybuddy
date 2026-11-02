"""StudyBuddy configuration — everything is driven by environment variables.

Modes
-----
STUDYBUDDY_MODE=live   Use the real Strands Agents SDK + Amazon Bedrock.
STUDYBUDDY_MODE=mock   Offline demo mode: deterministic canned replies,
                       no AWS credentials needed. The same tools, lesson
                       data and progress files are used, so the whole
                       user-facing flow can be verified end to end.

If STUDYBUDDY_MODE is not set, the app defaults to ``mock`` so a first
run always works; set it to ``live`` once Bedrock access is configured.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "progress"


@dataclass(frozen=True)
class Settings:
    mode: str = "mock"  # "mock" | "live"
    model_id: str = "us.amazon.nova-micro-v1:0"
    aws_region: str = "us-east-1"
    temperature: float = 0.3
    data_dir: Path = DEFAULT_DATA_DIR

    @property
    def is_mock(self) -> bool:
        return self.mode != "live"


def load_settings() -> Settings:
    """Build Settings from environment variables (see .env.example)."""
    data_dir = Path(os.environ.get("STUDYBUDDY_DATA_DIR", str(DEFAULT_DATA_DIR)))
    return Settings(
        mode=os.environ.get("STUDYBUDDY_MODE", "mock").strip().lower(),
        model_id=os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-micro-v1:0"),
        aws_region=os.environ.get("AWS_REGION", "us-east-1"),
        temperature=float(os.environ.get("STUDYBUDDY_TEMPERATURE", "0.3")),
        data_dir=data_dir,
    )
