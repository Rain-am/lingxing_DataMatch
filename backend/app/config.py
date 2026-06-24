import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_env: str = "local"
    app_name: str = "lingxing-reconcile"
    sqlite_path: str = "./data/reconcile.db"

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "lingxing_dw"

    ssh_tunnel_enabled: bool = False
    ssh_host: str = ""
    ssh_port: int = 22
    ssh_user: str = ""
    ssh_password: str = ""
    ssh_remote_host: str = ""
    ssh_remote_port: int = 3306

    lingxing_api_base_url: str = ""
    lingxing_app_key: str = ""
    lingxing_app_id: str = ""
    lingxing_app_secret: str = ""
    lingxing_access_token: str = ""
    lingxing_refresh_token: str = ""
    lingxing_token_expires_at: int = 0
    lingxing_access_key: str = ""
    lingxing_access_secret: str = ""
    lingxing_timeout_seconds: int = 30


def _load_env_file() -> dict[str, str]:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env_file_path() -> Path:
    return Path(__file__).resolve().parents[1] / ".env"


def update_env_values(updates: dict[str, str]) -> None:
    env_path = env_file_path()
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    pending = dict(updates)
    output: list[str] = []
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            output.append(raw_line)
            continue
        key = raw_line.split("=", 1)[0].strip()
        if key in pending:
            output.append(f"{key}={pending.pop(key)}")
        else:
            output.append(raw_line)

    if pending and output and output[-1].strip():
        output.append("")
    for key, value in pending.items():
        output.append(f"{key}={value}")

    env_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = env_path.with_suffix(".env.tmp")
    tmp_path.write_text("\n".join(output) + "\n", encoding="utf-8")
    tmp_path.replace(env_path)


def _get(values: dict[str, str], key: str, default: str) -> str:
    return os.environ.get(key, values.get(key, default))


def _get_int(values: dict[str, str], key: str, default: int) -> int:
    raw = _get(values, key, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


def _get_bool(values: dict[str, str], key: str, default: bool) -> bool:
    raw = _get(values, key, str(default)).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


@lru_cache
def get_settings() -> Settings:
    values = _load_env_file()
    return Settings(
        app_env=_get(values, "APP_ENV", "local"),
        app_name=_get(values, "APP_NAME", "lingxing-reconcile"),
        sqlite_path=_get(values, "SQLITE_PATH", "./data/reconcile.db"),
        mysql_host=_get(values, "MYSQL_HOST", "127.0.0.1"),
        mysql_port=_get_int(values, "MYSQL_PORT", 3306),
        mysql_user=_get(values, "MYSQL_USER", "root"),
        mysql_password=_get(values, "MYSQL_PASSWORD", ""),
        mysql_database=_get(values, "MYSQL_DATABASE", "lingxing_dw"),
        ssh_tunnel_enabled=_get_bool(values, "SSH_TUNNEL_ENABLED", False),
        ssh_host=_get(values, "SSH_HOST", ""),
        ssh_port=_get_int(values, "SSH_PORT", 22),
        ssh_user=_get(values, "SSH_USER", ""),
        ssh_password=_get(values, "SSH_PASSWORD", ""),
        ssh_remote_host=_get(values, "SSH_REMOTE_HOST", ""),
        ssh_remote_port=_get_int(values, "SSH_REMOTE_PORT", 3306),
        lingxing_api_base_url=_get(values, "LINGXING_API_BASE_URL", ""),
        lingxing_app_key=_get(values, "LINGXING_APP_KEY", ""),
        lingxing_app_id=_get(values, "LINGXING_APP_ID", ""),
        lingxing_app_secret=_get(values, "LINGXING_APP_SECRET", ""),
        lingxing_access_token=_get(values, "LINGXING_ACCESS_TOKEN", ""),
        lingxing_refresh_token=_get(values, "LINGXING_REFRESH_TOKEN", ""),
        lingxing_token_expires_at=_get_int(values, "LINGXING_TOKEN_EXPIRES_AT", 0),
        lingxing_access_key=_get(values, "LINGXING_ACCESS_KEY", ""),
        lingxing_access_secret=_get(values, "LINGXING_ACCESS_SECRET", ""),
        lingxing_timeout_seconds=_get_int(values, "LINGXING_TIMEOUT_SECONDS", 30),
    )
