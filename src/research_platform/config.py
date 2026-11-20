"""Environment-only settings. Secrets are deliberately absent from public responses."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./.research-platform/platform.db"
    artifact_root: Path = field(default_factory=lambda: REPO_ROOT / ".research-platform/artifacts")
    checkpoint_path: Path = field(
        default_factory=lambda: REPO_ROOT / ".research-platform/checkpoints.db"
    )
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    app_env: str = "local"
    daily_api_call_budget: int = 100
    max_concurrent_jobs: int = 1
    lease_seconds: int = 30
    default_provider: str = "mock"
    default_model: str = "mock-researcher"
    default_profile: str = "demo"
    max_llm_calls: int = 20
    max_iterations: int = 3
    max_runtime: int = 300
    max_experiment_runtime: int = 60
    inspector_url: str = "http://127.0.0.1:8765"
    upstream_results_root: Path = field(default_factory=lambda: REPO_ROOT / "results")

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv(REPO_ROOT / ".env", override=False)
        data_root = REPO_ROOT / ".research-platform"
        return cls(
            database_url=os.getenv("DATABASE_URL", f"sqlite:///{data_root.as_posix()}/platform.db"),
            artifact_root=Path(os.getenv("ARTIFACT_ROOT", str(data_root / "artifacts"))).resolve(),
            checkpoint_path=Path(
                os.getenv("CHECKPOINT_PATH", str(data_root / "checkpoints.db"))
            ).resolve(),
            cors_origins=tuple(
                os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
            ),
            app_env=os.getenv("APP_ENV", "local"),
            daily_api_call_budget=max(0, int(os.getenv("DAILY_API_CALL_BUDGET", "100"))),
            max_concurrent_jobs=max(1, min(4, int(os.getenv("MAX_CONCURRENT_JOBS", "1")))),
            default_provider=os.getenv("DEFAULT_MODEL_PROVIDER", "mock"),
            default_model=os.getenv("DEFAULT_MODEL", "mock-researcher"),
            default_profile=os.getenv("DEFAULT_RESEARCH_PROFILE", "demo"),
            max_llm_calls=int(os.getenv("MAX_LLM_CALLS_PER_RUN", "20")),
            max_iterations=int(os.getenv("MAX_RESEARCH_ITERATIONS", "3")),
            max_runtime=int(os.getenv("MAX_RUN_RUNTIME_SECONDS", "300")),
            max_experiment_runtime=int(os.getenv("MAX_EXPERIMENT_RUNTIME_SECONDS", "60")),
            inspector_url=os.getenv("INSPECTOR_URL", "http://127.0.0.1:8765"),
            upstream_results_root=Path(
                os.getenv("UPSTREAM_RESULTS_ROOT", str(REPO_ROOT / "results"))
            ).resolve(),
        )

    def prepare(self) -> None:
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
