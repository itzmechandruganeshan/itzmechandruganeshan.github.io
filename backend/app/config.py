"""All tunables live here or in data/*.yaml. No magic numbers in the code paths."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    env: str = "dev"  # dev | prod
    data_dir: Path = BACKEND_DIR / "data"
    db_path: Path = BACKEND_DIR / "var" / "app.db"
    checkpoint_path: Path = BACKEND_DIR / "var" / "checkpoints.db"

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base: str = "https://openrouter.ai/api"
    llm_models: list[str] = ["anthropic/claude-haiku-5.5", "deepseek/deepseek-v4.1-flash"]
    llm_cheap_model: str = "deepseek/deepseek-v4.1-flash"  # summaries, extraction
    llm_temperature: float = 0.7
    llm_first_token_timeout_s: float = 2.0
    llm_total_timeout_s: float = 12.0
    tokens_per_burst: int = 70  # bubble text + hidden citation tags

    # Jev (OpenRouter Decisions API, alpha)
    jev_model: str = "typesafe/jev-1.14"
    jev_timeout_s: float = 1.5  # measured 480-850ms from a laptop in India; recalibrate from Fly sin

    # Jev thresholds (gates, J3, J7, J6): placeholders until calibrated with eval/run_eval.py + golden
    t_identity: float = 0.5  # real probes scored 0.53-0.58 on 2026-10-21; calibrate with eval identity
    t_identity_regex: float = 0.35
    t_injection: float = 0.7
    t_off_limits: float = 0.7
    t_personal: float = 0.6
    t_grounded: float = 0.5
    t_partisan: float = 0.3
    t_news_relevant: float = 0.6
    t_tool_valid: float = 0.5   # J8: LLM tool call verified by Jev
    t_answered: float = 0.5     # J9: reply answers the lead/meeting question
    t_connect: float = 0.6      # gate: visitor wants to connect even if the LLM didn't call start_connect

    # Retrieval
    retrieval_backend: str = "cloud"  # cloud | embedded
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_local_path: Path = BACKEND_DIR / "var" / "qdrant"
    dense_model: str = "BAAI/bge-small-en-v1.5"
    sparse_model: str = "Qdrant/bm25"
    embed_cache_dir: Path = BACKEND_DIR / "var" / "models"
    allow_unreviewed_cards: bool = False  # dev only: answer from cards Chandru hasn't approved yet
    cards_collection: str = "cards"
    news_collection: str = "news"
    hybrid_top_k: int = 8
    news_top_k: int = 5
    news_half_life_days: float = 7.0

    # Conversation
    history_turns: int = 12
    max_message_chars: int = 500
    max_turns_per_session: int = 40
    who_hook_after_messages: list[int] = [2, 3]
    idle_nudge_s: float = 75.0
    rate_per_min_session: int = 20
    rate_per_day_session: int = 200
    rate_per_min_ip: int = 60
    allowed_origins: list[str] = [
        "https://itzmechandruganeshan.github.io",
        "http://localhost:3000",
    ]

    # Tools
    resume_url: str = "/resume/chandru-ganeshan-resume.pdf"
    site_origin: str = "https://itzmechandruganeshan.github.io"
    alert_email: str = "chandruganeshan24@gmail.com"
    composio_api_key: str = ""
    composio_user_id: str = "chandru"   # Chandru's own Composio user; his Google account is connected to it
    calendar_id: str = "primary"
    meeting_minutes: int = 30
    meeting_buffer_min: int = 15
    meeting_days_ahead: int = 10
    meeting_work_hours: tuple[int, int] = (10, 18)
    meeting_slots_offered: int = 3
    lead_key_b64: str = ""  # 32-byte AES-GCM key, base64. Required in prod.

    retention_days: int = 30          # visitor memory + conversations forgotten after this much inactivity
    conversation_gap_min: int = 30    # silence longer than this starts a new conversation (memory carries over)
    timezone: str = "Asia/Kolkata"
    seed: int | None = Field(default=None, description="Fix RNG for tests/eval")

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
