from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_render_configuration_contains_required_runtime_contract():
    config = read("backend/render.yaml")
    for expected in (
        "rootDir: m1-2/backend",
        "pip install -r requirements.txt",
        "uvicorn app.main:create_app --factory",
        "--port $PORT",
        "healthCheckPath: /health",
        "PYTHON_VERSION",
        "COPA_API_KEY",
        "https://copa.codyssey.kr/v1",
        "gpt-5.4-mini",
        "/etc/secrets/firebase-service-account.json",
        "ALLOWED_ORIGINS",
    ):
        assert expected in config


def test_main_readme_documents_submission_and_deployment_requirements():
    content = read("README.md")
    for expected in (
        "POST /api/data",
        "GET /api/data",
        "GET /api/data/summary",
        "PUT /api/data/{id}",
        "DELETE /api/data/{id}",
        "POST /api/chat",
        "POST /api/conversations",
        "GET /api/conversations/{id}",
        "python scripts/import_csv.py",
        "COPA_API_KEY",
        "FIREBASE_SERVICE_ACCOUNT_FILE",
        "ALLOWED_ORIGINS",
        "API_BASE_URL",
        "무료 서버",
        "Render",
        "Vercel",
        "/docs",
        "스크린샷",
    ):
        assert expected in content


def test_component_readmes_and_feature_screen_index_exist():
    assert "pytest" in read("backend/README.md")
    assert "node --test" in read("frontend/README.md")
    screenshots = read("screenshots/README.md")
    assert screenshots.count("- [x]") == 7
    for filename in (
        "01-ai-chat-summary.jpg",
        "03-conversation-history.jpg",
        "04-data-crud.jpg",
    ):
        assert filename in screenshots
