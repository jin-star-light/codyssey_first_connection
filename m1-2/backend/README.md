# 백엔드

FastAPI 백엔드는 Router → Service → Repository 구조입니다. 테스트에서는 메모리 저장소를, 운영에서는 Firestore를 사용합니다.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m pytest -q
uvicorn app.main:create_app --factory --reload
```

`.env`에는 `COPA_API_KEY`, `FIREBASE_SERVICE_ACCOUNT_FILE`, `ALLOWED_ORIGINS`를 설정합니다. Firebase JSON과 `.env`는 절대 커밋하지 않습니다. 샘플 데이터는 먼저 `python scripts/import_csv.py data/study_hours.csv --dry-run`으로 검증합니다.
