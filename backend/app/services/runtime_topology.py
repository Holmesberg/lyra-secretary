"""Runtime topology integrity helpers.

Topology is part of epistemic integrity: a browser trace is not trustworthy if
the public frontend, auth base, API origin, and CORS contract disagree.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import Request

from app.core.config import Settings, settings


DEFAULT_RUNTIME_TOPOLOGY_CONTRACT: dict[str, Any] = {
    "version": "runtime_topology_v1",
    "topologies": {
        "local": {
            "topology_class": "local",
            "frontend_origin": "http://localhost:3000",
            "api_origin": "http://localhost:8000",
            "nextauth_url": "http://localhost:3000",
        },
        "public": {
            "topology_class": "public",
            "frontend_origin": "https://lyraos.org",
            "api_origin": "https://api.lyraos.org",
            "nextauth_url": "https://lyraos.org",
        },
    },
    "declared_browser_origins": [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://lyraos.org",
    ],
}


def normalize_origin(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.strip().rstrip("/")


def _contract_candidates() -> list[Path]:
    here = Path(__file__).resolve()
    candidates = []
    configured = os.getenv("RUNTIME_TOPOLOGY_PATH")
    if configured:
        candidates.append(Path(configured))
    candidates.extend([
        Path("/runtime_topology.json"),
        Path.cwd() / "runtime_topology.json",
        here.parents[3] / "runtime_topology.json",
        here.parents[2] / "runtime_topology.json",
        here.parents[1] / "core" / "runtime_topology.json",
    ])
    return candidates


def load_runtime_topology_contract() -> dict[str, Any]:
    for path in _contract_candidates():
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except OSError:
            continue
    return DEFAULT_RUNTIME_TOPOLOGY_CONTRACT


def _origin_from_request(request: Request, *, public_host: str, local_scheme: str) -> str:
    host = (request.headers.get("host") or request.url.netloc or "").lower()
    if host == public_host:
        return f"https://{public_host}"
    if host.startswith("localhost") or host.startswith("127.0.0.1"):
        return f"{local_scheme}://{host}"
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme or local_scheme
    return f"{scheme}://{host}" if host else ""


def _topology_by_api_origin(contract: dict[str, Any], api_origin: str) -> Optional[str]:
    for name, topology in contract.get("topologies", {}).items():
        if normalize_origin(topology.get("api_origin")) == normalize_origin(api_origin):
            return name
    return None


def backend_topology_report(
    request: Request,
    *,
    app_settings: Settings = settings,
) -> dict[str, Any]:
    contract = load_runtime_topology_contract()
    api_origin = _origin_from_request(
        request,
        public_host="api.lyraos.org",
        local_scheme="http",
    )
    topology_class = _topology_by_api_origin(contract, api_origin) or "unknown"
    expected = contract.get("topologies", {}).get(topology_class, {})
    cors_allowed = [normalize_origin(origin) for origin in app_settings.cors_allowed_origins]
    expected_frontend = normalize_origin(expected.get("frontend_origin"))
    expected_api = normalize_origin(expected.get("api_origin"))
    verified_topology = bool(
        topology_class != "unknown"
        and expected_api == normalize_origin(api_origin)
        and expected_frontend in cors_allowed
    )

    return {
        "topology_class": topology_class,
        "api_origin": normalize_origin(api_origin),
        "cors_allowed_origins": cors_allowed,
        "build_id": os.getenv("BUILD_ID")
        or os.getenv("GIT_COMMIT")
        or os.getenv("RENDER_GIT_COMMIT")
        or "dev",
        "runtime_stamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "verified_topology": verified_topology,
        "contract_version": contract.get("version"),
        "expected_frontend_origin": expected_frontend or None,
        "expected_api_origin": expected_api or None,
    }
