import json
import logging
from time import perf_counter
from uuid import uuid4

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from frotad.services.tenancy import DomainError

logger = logging.getLogger("frotad.requests")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


def install_http(app):
    def error(request, status, code, fields=None):
        headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
        return JSONResponse(
            status_code=status,
            headers=headers,
            content={
                "error": {
                    "code": code,
                    "request_id": request.state.request_id,
                    **({"fields": fields} if fields is not None else {}),
                }
            },
        )

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        return error(request, exc.status, exc.code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return error(
            request,
            422,
            "validation_error",
            [{"path": list(item["loc"]), "type": item["type"]} for item in exc.errors()],
        )

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error(request, exc.status_code, "http_error")

    @app.middleware("http")
    async def request_context(request, call_next):
        request.state.request_id = str(uuid4())
        start = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            response = error(request, 500, "internal_error")
        response.headers["X-Request-ID"] = request.state.request_id
        logger.info(
            json.dumps(
                {
                    "request_id": request.state.request_id,
                    "method": request.method,
                    "status": response.status_code,
                    "duration_ms": round((perf_counter() - start) * 1000, 2),
                }
            )
        )
        return response
