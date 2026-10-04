from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ACCOUNT_FIELDS = {"type", "project_id", "private_key", "client_email"}


def _resolve_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else BACKEND_ROOT / candidate


def load_service_account(path: str) -> dict[str, Any]:
    resolved = _resolve_path(path)
    if not resolved.is_file():
        raise FileNotFoundError(f"Firebase service account file not found: {resolved}")
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Firebase service account file is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("Firebase service account must be a JSON object")
    if not REQUIRED_ACCOUNT_FIELDS.issubset(value):
        raise ValueError("Firebase service account is missing required fields")
    return value


def create_firestore_client(path: str) -> Any:
    account = load_service_account(path)
    try:
        app = firebase_admin.get_app()
    except ValueError:
        app = firebase_admin.initialize_app(credentials.Certificate(account))
    return firestore.client(app=app)
