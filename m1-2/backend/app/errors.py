from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class StudyCoachError(Exception):
    """Base class for public domain errors."""


class DuplicateDateError(StudyCoachError):
    pass


class RecordNotFoundError(StudyCoachError):
    pass


class DataStoreError(StudyCoachError):
    pass


class AIProviderError(StudyCoachError):
    pass


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "location": list(item["loc"]),
                "message": item["msg"],
                "type": item["type"],
            }
            for item in error.errors()
        ]
        return error_response(
            422,
            "validation_error",
            "입력값을 확인해 주세요.",
            details,
        )

    @app.exception_handler(DuplicateDateError)
    async def duplicate_date_handler(
        _request: Request, _error: DuplicateDateError
    ) -> JSONResponse:
        return error_response(
            409,
            "duplicate_date",
            "해당 날짜의 데이터가 이미 존재합니다.",
        )

    @app.exception_handler(RecordNotFoundError)
    async def record_not_found_handler(
        _request: Request, _error: RecordNotFoundError
    ) -> JSONResponse:
        return error_response(
            404,
            "record_not_found",
            "요청한 데이터를 찾을 수 없습니다.",
        )

    @app.exception_handler(DataStoreError)
    async def datastore_error_handler(
        _request: Request, _error: DataStoreError
    ) -> JSONResponse:
        return error_response(
            503,
            "datastore_unavailable",
            "데이터 저장소를 일시적으로 사용할 수 없습니다.",
        )
