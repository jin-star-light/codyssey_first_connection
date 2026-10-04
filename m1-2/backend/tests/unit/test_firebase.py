import json
from pathlib import Path

import pytest

from app.firebase import create_firestore_client, load_service_account


VALID_ACCOUNT = {
    "type": "service_account",
    "project_id": "demo-project",
    "private_key": "placeholder-only",
    "client_email": "demo@example.invalid",
}


def test_load_service_account_accepts_valid_json(tmp_path: Path):
    path = tmp_path / "firebase.json"
    path.write_text(json.dumps(VALID_ACCOUNT), encoding="utf-8")
    assert load_service_account(str(path)) == VALID_ACCOUNT


def test_load_service_account_rejects_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Firebase service account file not found"):
        load_service_account(str(tmp_path / "missing.json"))


@pytest.mark.parametrize("content", ["not-json", "[]", '{"type":"service_account"}'])
def test_load_service_account_rejects_invalid_content_without_leaking_it(
    tmp_path: Path, content: str
):
    path = tmp_path / "firebase.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError) as error:
        load_service_account(str(path))
    assert "private_key" not in str(error.value)
    assert content not in str(error.value)


def test_create_firestore_client_reuses_existing_app(monkeypatch, tmp_path: Path):
    path = tmp_path / "firebase.json"
    path.write_text(json.dumps(VALID_ACCOUNT), encoding="utf-8")
    existing_app = object()
    expected_client = object()
    monkeypatch.setattr("app.firebase.firebase_admin.get_app", lambda: existing_app)
    monkeypatch.setattr(
        "app.firebase.firebase_admin.initialize_app",
        lambda *_args, **_kwargs: pytest.fail("must reuse existing app"),
    )
    monkeypatch.setattr(
        "app.firebase.firestore.client",
        lambda *, app: expected_client if app is existing_app else None,
    )
    assert create_firestore_client(str(path)) is expected_client
