from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(r"C:\GammaEnginePython")
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


def _get_env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or str(value).strip() == ""):
        raise RuntimeError(f"Missing required environment variable: {name}")
    return "" if value is None else str(value).strip()


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    data_dir: Path
    logs_dir: Path

    supabase_url: str
    supabase_service_role_key: str
    supabase_anon_key: str

    dhan_client_id: str
    dhan_access_token: str

    timeout_seconds: int


def get_settings() -> Settings:
    return Settings(
        base_dir=BASE_DIR,
        data_dir=BASE_DIR / "data",
        logs_dir=BASE_DIR / "logs",
        supabase_url=_get_env("SUPABASE_URL", required=True),
        supabase_service_role_key=_get_env("SUPABASE_SERVICE_ROLE_KEY", required=True),
        supabase_anon_key=_get_env("SUPABASE_ANON_KEY", default=""),
        dhan_client_id=_get_env("DHAN_CLIENT_ID", default=""),
        dhan_access_token=_get_env("DHAN_API_TOKEN", required=True),
        timeout_seconds=int(_get_env("HTTP_TIMEOUT_SECONDS", default="30")),
    )