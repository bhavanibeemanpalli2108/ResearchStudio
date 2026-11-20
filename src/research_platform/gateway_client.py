"""Private Gemini CLI configuration for a scoped gateway token, never a provider key."""

from __future__ import annotations

import ipaddress
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse


def validate_gateway_client(
    base_url: str, token: str, *, allow_loopback_http: bool = False
) -> None:
    parsed = urlparse(base_url)
    try:
        loopback = ipaddress.ip_address(parsed.hostname or "").is_loopback
    except ValueError:
        loopback = parsed.hostname == "localhost"
    if (
        not re.fullmatch(r"gw_[A-Za-z0-9_-]{40,100}", token)
        or not re.fullmatch(r"/runs/[a-f0-9]{32}", parsed.path)
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.scheme != "https"
        and not (allow_loopback_http and loopback and parsed.scheme == "http")
    ):
        raise ValueError("Invalid private gateway client configuration")


def prepare_cli_environment(
    home: Path, base_url: str, token: str, *, allow_loopback_http: bool = False
) -> dict[str, str]:
    validate_gateway_client(base_url, token, allow_loopback_http=allow_loopback_http)
    if home.is_symlink() or not home.is_dir():
        raise ValueError("Use a new private job home")
    directory = home / ".gemini"
    directory.mkdir(mode=0o700)  # refuse existing profiles/settings; never overwrite an OAuth home
    settings = {
        "security": {"auth": {"selectedType": "gemini-api-key"}},
        "privacy": {"usageStatisticsEnabled": False},
        "telemetry": {"enabled": False},
    }
    descriptor = os.open(directory / "settings.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(settings, stream)
    descriptor = os.open(
        home / ".agsci-gateway-profile.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump({"version": 1, "run_id": urlparse(base_url).path.rsplit("/", 1)[-1]}, stream)
    # Caller starts the CLI with a scrubbed environment. No GOOGLE_API_KEY,
    # OAuth/Vertex/ADC settings or user-profile copies may be added.
    return {
        "HOME": str(home),
        "GEMINI_API_KEY": token,
        "GOOGLE_GEMINI_BASE_URL": base_url,
        "GEMINI_TELEMETRY_ENABLED": "false",
    }
